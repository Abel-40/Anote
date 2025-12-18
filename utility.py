from pwdlib import PasswordHash
from fastapi import HTTPException,UploadFile,status
from pydantic_models import ApiResponse, PaginatedResponse
from pathlib import Path
from config import setting
from uuid import uuid4
from math import ceil
import shutil


password_hash = PasswordHash.recommended()
UPLOAD_DIR = Path(setting.UPLOAD_DIR)
UPLOAD_DIR.mkdir(parents=True,exist_ok=True)

# utility functions
def hash_password(plain_password):
  return password_hash.hash(plain_password)
def validate_password(plain_password,hashed_password):
  return password_hash.verify(plain_password,hashed_password)


def upload_file(file:UploadFile):
  allowed_suffixes = {"xlsx",".pdf", ".jpeg","jpg", ".csv", ".docx",".txt"}
  suffix = Path(file.filename).suffix.lower()
  if suffix not in allowed_suffixes:
      raise HTTPException(
          status_code=status.HTTP_400_BAD_REQUEST,
          detail="Invalid file type. Allowed types: pdf, jpeg, csv, docx"
      )

  file_name = f"{uuid4}{suffix}"
  file_path = UPLOAD_DIR / file_name
  with file_path.open("wb") as buffer:
    shutil.copyfileobj(file.file,buffer)
  return str(file_path) 

def success_response(message:str,status_code:int,data:any=None,meta:dict[str,any]=None):
  return ApiResponse(success=True,message=message,data=data,status_code=status_code,meta=meta,errors=None)
def error_response(message:str,status_code:int,meta:dict[str,any]=None,error:any=None):
  return ApiResponse(success=False,message=message,data=None,satus_code=status_code,meta=meta,errors=error)


def paginated_query(query,page:int,page_size:int):
  total_items = query.count()
  total_pages = ceil(total_items/page_size)
  items = (
    query
    .offset((page - 1) * page_size)
    .limit(page_size)
    .all()
  )
  return {
    "items":items,
    "meta":{
      "page":page,
      "page_size":page_size,
      "total_items":total_items,
      "total_pages":total_pages
    }
  }