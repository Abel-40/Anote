from fastapi import FastAPI,Depends,HTTPException,Request,UploadFile,File,Query,status
from fastapi.responses import JSONResponse
from config import setting
from utility import hash_password,upload_file,success_response,error_response,PaginatedResponse,paginated_query
from typing import Annotated,List
from sqlalchemy.orm import Session,joinedload
from sqlalchemy.exc import IntegrityError
from pydantic_models import UserOut,UserCreate,UserDbIn,NoteCreate,NoteOut,ApiResponse,QueryParams,NoteUpdate
from fastapi.security import OAuth2PasswordRequestForm
from jwt.exceptions import InvalidTokenError
from dependencies import get_current_user,get_db,authenticate,token_generator,validate_tag,verify_token
from datetime import timedelta
import jwt
import db_models

# important variables

app = FastAPI()
ACCESS_SECRET_KEY = setting.ACCESS_SECRET_KEY
REFRESH_SECRET_KEY = setting.REFRESH_SECRET_KEY
ALGOR = setting.ALGORITHUM
TOKEN_EXPIRY = setting.TOKEN_EXPIRY_DATE



#endpoints  

# **********************Auth Endpoints******************************* 
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
async def create_note(
  user:Annotated[db_models.User,Depends(get_current_user)],
  files:Annotated[List[UploadFile],File(default_factory=list)],
  note:NoteCreate = Depends(NoteCreate.as_form), 
  tag_names:List[str]=Depends(validate_tag),
  db:Session = Depends(get_db)
  ):
  existing_tags = []
  new_tags = []
  print(f"TAGS:----> {tag_names}")
  if tag_names:
    existing_tags = (db.query(db_models.Tag).filter(db_models.Tag.name.in_(tag_names)).all())
    existing_names = {tag.name for tag in existing_tags}
    new_tags = [db_models.Tag(name=name) for name in tag_names if name not in existing_names]
    db.add_all(new_tags)
    
  note_for_db = db_models.Note(**note.model_dump(),user_id=user.id)
  db.add(note_for_db)
  db.flush()
  note_for_db.tags.extend(existing_tags + new_tags)
  

  for f in files:
    f_path = upload_file(f)
    files_for_db = db_models.MediaFile(file_name=f.filename,file_path=f_path,content_type=f.content_type,note_id=note_for_db.id)
    db.add(files_for_db)
  db.commit()
  
  return {"message":"note created successfully"}
  
@app.get(
    "/notes/",
    response_model=ApiResponse[PaginatedResponse[NoteOut]]
)
async def get_notes(
    q: QueryParams = Depends(),
    current_user: db_models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    query = (
        db.query(db_models.Note)
        .options(
            joinedload(db_models.Note.tags),
            joinedload(db_models.Note.files)
        )
        .filter(db_models.Note.user_id == current_user.id)
        .order_by(db_models.Note.created_at.desc())
    )

    result = paginated_query(
        query,
        page=q.page,
        page_size=q.page_size
    )

    return success_response(
        message="Notes fetched successfully",
        data={
            "items": result["items"],
            "pagination": result["meta"]
        },
        status_code=status.HTTP_200_OK
    )

@app.get("/notes/{id}",response_model=ApiResponse[NoteOut])
async def get_note_by_id(id:int,db:Session = Depends(get_db),current_user:db_models.User = Depends(get_current_user)):
  note = (
  db.query(db_models.Note)
  .options(
    joinedload(db_models.Note.files),
    joinedload(db_models.Note.tags)
  )
  .filter(db_models.Note.id == id,db_models.Note.user_id == current_user.id)
  .first()
  )
  if not note:
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,detail="Note doesn't exist.")
  
  return success_response(message="Note fetched successfully!!!",status_code=status.HTTP_200_OK,data=note,meta=None)
 
@app.put("/notes/{id}",response_model=ApiResponse[NoteOut])
async def update_note(id:int,note_content:NoteUpdate,db:Session=Depends(get_db),current_user:db_models.User = Depends(get_current_user)):
  note_to_update = db.query(db_models.Note).filter(db_models.Note.id == id,db_models.Note.user_id == current_user.id).first()
  if not note_to_update:
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,detail="Note doesn't exist.")
  for key,value in note_content.model_dump(exclude_none=True).items():
    setattr(note_to_update,key,value)
  db.commit()
  return success_response(message="Note Updated Successfully!!!",status_code=status.HTTP_200_OK,data=note_to_update)
  
@app.delete("/notes/{id}")
async def delete_note(id:int,db:Session=Depends(get_db),current_user:db_models.User = Depends(get_current_user)):
  note_to_delete = db.query(db_models.Note).filter(db_models.Note.id == id,db_models.Note.user_id == current_user.id).first()
  if not note_to_delete:
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,detail="Note doesn't exist.")
  db.delete(note_to_delete)
  db.commit()

  return {"message":"Note successfully deleted!!!"}



@app.post("/check/",dependencies=[Depends(verify_token)])
async def check(file:UploadFile):
  return {"file name":file.filename}