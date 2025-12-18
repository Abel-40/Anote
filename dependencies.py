from sqlalchemy.orm import Session
from fastapi import HTTPException,Form,Depends
from typing import List,Annotated
from db_connection import session
from utility import validate_password
from fastapi.security import OAuth2PasswordBearer
from config import setting
from jwt.exceptions import InvalidTokenError
from datetime import datetime,timedelta,timezone
import jwt 
import db_models

ACCESS_SECRET_KEY = setting.ACCESS_SECRET_KEY
auth_scheme = OAuth2PasswordBearer(tokenUrl="login")
ALGOR = setting.ALGORITHUM

#dependancy funxtions
def get_user(username:str,db:Session):
  user = db.query(db_models.User).filter(db_models.User.username == username).first()
  return user

def validate_tag(
    tag_names: List[str] = Form(default_factory=list)
) -> List[str]:
    for tag in tag_names:
        if not tag.startswith("#"):
            raise HTTPException(
                status_code=422,
                detail="Tags must start with '#'"
            )
    return tag_names
  
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

def get_current_user(token:Annotated[str,Depends(auth_scheme)],db:Session = Depends(get_db))->db_models.User:
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