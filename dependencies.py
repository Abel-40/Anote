from sqlalchemy.orm import Session
from sqlalchemy import select
from fastapi import HTTPException,Form,Depends,Request
from typing import List,Annotated
from db_connection import session
from utility import validate_password
from fastapi.security import OAuth2PasswordBearer
from config import setting
from jwt.exceptions import InvalidTokenError,PyJWTError
from datetime import datetime,timedelta,timezone
import jwt 
import db_models
from db_models import Permission

ACCESS_SECRET_KEY = setting.ACCESS_SECRET_KEY
auth_scheme = OAuth2PasswordBearer(tokenUrl="login")
ALGOR = setting.ALGORITHUM

#dependancy funxtions
def get_user(username:str,db:Session):
  user = db.execute(select(db_models.User).where(db_models.User.username == username)).scalar_one_or_none()
  return user


def parse_and_validate_tags(tag_names: str | None) -> list[str]:

    if not tag_names:
        return []

    tag_list = tag_names.split()
    validated_tags: list[str] = []

    for tag in tag_list:
        if not tag.startswith("#"):
            raise HTTPException(
                status_code=422,
                detail="Tags must start with '#'"
            )
        validated_tags.append(tag)

    return validated_tags


def validate_tag(
    tag_names: str = Form(...)
) -> list[str]:
    return parse_and_validate_tags(tag_names)

  
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

def get_current_user(request:Request,token:Annotated[str,Depends(auth_scheme)],db:Session = Depends(get_db)):
  credentials_exception = HTTPException(status_code=401,detail="Invalid Credentials!!!", headers = {"WWW-Authenticate":"Bearer"})
  try:
    payload = jwt.decode(token,ACCESS_SECRET_KEY,algorithms=[ALGOR])
    user_id = int(payload.get("sub"))
    if payload.get("type") != "access":
      raise credentials_exception

    if not user_id:
      raise credentials_exception
    user = db.execute(select(db_models.User).where(db_models.User.id == user_id)).scalar_one_or_none()
    if not user:
      raise credentials_exception
    request.state.user_id = user.id
    return payload
  except PyJWTError as e:
    print("JWT ERROR TYPE:", type(e).__name__)
    print("JWT ERROR MSG:", str(e))
    raise credentials_exception

def token_generator(data:dict,secret_key,token_expiry:timedelta | None = None):
    to_encode = data.copy()
    if token_expiry:
      token_expiry = datetime.now(timezone.utc) + token_expiry
    else:
      token_expiry = datetime.now(timezone.utc) + timedelta(days=15)
    to_encode.update({"exp":token_expiry})
    token = jwt.encode(to_encode,secret_key,ALGOR)
    return token
  
def verify_token(token:str = Depends(auth_scheme)):
  try:
    jwt.decode(token,ACCESS_SECRET_KEY,algorithms=[ALGOR])
  except InvalidTokenError:
    raise HTTPException(401,"Invalid Token!!!")
  
  
def required_permission(required_permissions:list[str]):
    def check(current_user:db_models.User = Depends(get_current_user)):
      user_permissions = set(current_user["perm"])
      if not set(required_permissions).issubset(user_permissions):
        raise HTTPException(status_code=403,detail="you don't have permission to do this!!!")
      return current_user
    
    return check