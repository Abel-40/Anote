from fastapi import FastAPI,Depends,HTTPException,Cookie,Request,UploadFile,File
from fastapi.responses import JSONResponse
from config import setting
from pwdlib import PasswordHash
from typing import Annotated,List
from db_connection import session
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from pathlib import Path
from datetime import timedelta,datetime,timezone
from pydantic_models import UserOut,UserCreate,UserDbIn,MediaFileOut,MediaFileCreate,NoteCreate,NoteOut,TagCreate,TagOut
from fastapi.security import OAuth2PasswordBearer,OAuth2PasswordRequestForm
from jwt.exceptions import InvalidTokenError
from uuid import uuid4
import jwt
import db_models
import shutil

# important variables
auth_scheme = OAuth2PasswordBearer(tokenUrl="login")
app = FastAPI()
ACCESS_SECRET_KEY = setting.ACCESS_SECRET_KEY
REFRESH_SECRET_KEY = setting.REFRESH_SECRET_KEY
ALGOR = setting.ALGORITHUM
TOKEN_EXPIRY = setting.TOKEN_EXPIRY_DATE
password_hash = PasswordHash.recommended()
UPLOAD_DIR = Path(setting.UPLOAD_DIR)
UPLOAD_DIR.mkdir(parents=True,exist_ok=True)

# utility functions
def hash_password(plain_password):
  return password_hash.hash(plain_password)
def validate_password(plain_password,hashed_password):
  return password_hash.verify(plain_password,hashed_password)

async def upload_file(file_to_upload:UploadFile):
  suffix = Path(file_to_upload.filename).suffix  # ".png", ".pdf", ""
  unique_name = f"{uuid4()}{suffix}"
  file_path = UPLOAD_DIR / unique_name
  with file_path.open("wb") as buffer:
    shutil.copyfileobj(file_to_upload.file,buffer)
  return str(file_path)

#dependancy funxtions
def get_user(username:str,db:Session):
  user = db.query(db_models.User).filter(db_models.User.username == username).first()
  return user

def get_db():
  db = session()
  try:
    yield db
  finally:
    db.close()

def authenticate(database:Session,username:str, password:str):
  user = get_user(username=username,db=database)
  if not user:
    return False
  if not validate_password(password,user.hashed_password):
    return False
  return user

def get_current_user(token:Annotated[str,Depends(auth_scheme)],db:Session = Depends(get_db)):
  credentials_exception = HTTPException(status_code=401,detail="Invalid Credentials!!!", headers = {"WWW-Authenticate":"Bearer"})
  try:
    payload = jwt.decode(token,ACCESS_SECRET_KEY,algorithms=[ALGOR])
    username = payload.get("sub")
    if payload.get("type") != "access":
      raise credentials_exception

    if not username:
      raise credentials_exception
    user = get_user(username,db)
    if not user:
      raise credentials_exception
    return user
  except InvalidTokenError:
    raise credentials_exception

def token_generator(data:dict,token_type:str,token_expiry:timedelta | None = None):
    to_encode = data.copy()
    if token_expiry:
      token_expiry = datetime.now(timezone.utc) + token_expiry
    else:
      token_expiry = datetime.now(timezone.utc) + timedelta(days=15)
    to_encode.update({"exp":token_expiry})
    token = jwt.encode(to_encode,token_type,ALGOR)
    return token
  
def verify_token(token:str = Depends(auth_scheme)):
  try:
    jwt.decode(token,ACCESS_SECRET_KEY,algorithms=[ALGOR])
  except InvalidTokenError:
    raise HTTPException(401,"Invalid Token!!!")
    
#endpoints  
@app.post("/register/",response_model=UserOut)
def register(user_data:UserCreate,db:Annotated[Session,Depends(get_db)]):
  db_data = UserDbIn(**user_data.model_dump(exclude={"password"}),hashed_password=hash_password(user_data.password))
  user = db_models.User(**db_data.model_dump())
  db.add(user)
    
  try:
    db.commit()
  except IntegrityError as e:
      db.rollback()
      if "email" in str(e.orig):
          raise HTTPException(409, "Email already registered")
      if "username" in str(e.orig):
          raise HTTPException(409, "Username already taken")
      raise HTTPException(400, "Invalid data")

  db.refresh(user)
  return UserOut.model_validate(user)

  
@app.post("/login/")
async def login(form:Annotated[OAuth2PasswordRequestForm,Depends()],db:Session = Depends(get_db)):
  username = form.username
  password = form.password
  credentials_exception = HTTPException(status_code=401,detail="Invalid username or password!!!",headers={"WWW-Authenticate":"Bearer"})
  user = authenticate(db,username,password)
  if not user:
    raise credentials_exception
  acces_token = token_generator(data={"sub":username,"type":"access"},token_type=ACCESS_SECRET_KEY,token_expiry=timedelta(minutes=TOKEN_EXPIRY))
  refresh_token = token_generator(data={"sub":username,"type":"refresh"},token_type=REFRESH_SECRET_KEY,token_expiry=timedelta(days=30))
  response = JSONResponse(content={"id":user.id,"username":user.username,"email":user.email,"full_name":user.full_name,"access_token":acces_token})
  response.set_cookie(
    key="refresh_token",
    value=refresh_token,
    httponly=True,
    secure=False,
    max_age=7 * 24 * 60 * 60
  )
  return response


@app.post("/refresh/")
async def refresh(request:Request):
  refresh_token = request.cookies.get("refresh_token")
  if not refresh_token:
    raise HTTPException(401, "Missing refresh token")
  try:
    decoder = jwt.decode(refresh_token,REFRESH_SECRET_KEY,algorithms=[ALGOR])
    username = decoder.get("sub")
    if not username:
      raise HTTPException(401,"username doesn't exist!!!")
    access_token = token_generator(data={"sub":username},token_type=ACCESS_SECRET_KEY,token_expiry=timedelta(minutes=TOKEN_EXPIRY))
    return {"access_token":access_token,"token_type":"Bearer"}
  except InvalidTokenError:
    raise HTTPException(401,"Invalid Token!!!")
  
 
# **********************Note Endpoints ******************************* 
@app.post("/notes/")
async def create_note(note:NoteCreate,user:Annotated[get_current_user,Depends(get_current_user)],tag_names:List[str | None]=None,files:Annotated[List[UploadFile | None],File()] = None,db:Session = Depends(get_db)):
  
  if tag_names:
    existing_tags = (db.query(db_models.Tag).filter(db_models.Tag.name.in_(tag_names)).all())
    existing_names = {tag.name for tag in existing_tags}
    new_tags = [db_models.Tag(name=name) for name in tag_names if name not in existing_names]
    db.add_all(new_tags)
  
  note_for_db = db_models.Note(**note.model_dump(),user_id=user.id)
  db.add(note_for_db)
  db.flush()
  note_for_db.tags.extend(existing_tags + new_tags)
  
  if files:
    for f in files:
      f_path = upload_file(f)
      files_for_db = db_models.MediaFileCreate(file_name=f.filename,file_path=f_path,content_typ=f.content_type,note_id=note_for_db.id)
      db.add(files_for_db)
  db.commit()
  
  return {"message":"note created successfully"}
  
 
 
 
    
@app.get("/check/",dependencies=[Depends(verify_token)])
async def check():
  return {"current user":"work"}