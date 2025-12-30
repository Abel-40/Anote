from pwdlib import PasswordHash
from fastapi import HTTPException,UploadFile,status
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
from pydantic_models import ApiResponse, PaginatedResponse,Optional
from pathlib import Path
from config import setting
from uuid import uuid4
from math import ceil
from datetime import datetime,timezone
import shutil
import json

password_hash = PasswordHash.recommended()
UPLOAD_DIR = Path(setting.UPLOAD_DIR)
UPLOAD_DIR.mkdir(parents=True,exist_ok=True)
LOGFILE_DIR = Path(setting.LOGFILEDIR)
LOGFILE_DIR.mkdir(parents=True,exist_ok=True)

def write_log_file(data):
  current_datetime = datetime.now()
  today_date = current_datetime.date()
  full_path = LOGFILE_DIR / f"{today_date}.log"
  log_entry = {
      "time": current_datetime.isoformat(),
      "method": data["method"],
      "url": data["url"],
      "user_id":data["user_id"],
      "status_code": data["status_code"],
      "response_time_ms": data["response_time_ms"],
      "request_id":data["request_id"]
  }
  with full_path.open("a", encoding="utf-8") as buffer:
      buffer.write(json.dumps(log_entry))
      buffer.write("\n")
def log_file_format(method:str,url:str,status_code:int,response_time_ms:int,request_id:str,user_id:Optional[int] = None):
  current_datetime = datetime.now()
  return {
    "time":str(current_datetime),
    "method":method,
    "url":url,
    "user_id":user_id,
    "status_code":status_code,
    "response_time_ms":response_time_ms,
    "request_id":request_id
          }
# utility functions
def hash_password(plain_password):
  return password_hash.hash(plain_password)
def validate_password(plain_password,hashed_password):
  return password_hash.verify(plain_password,hashed_password)


def upload_file(file:UploadFile):
  allowed_suffixes = {"xlsx",".pdf", ".jpeg",".jpg", ".csv", ".docx",".txt"}
  suffix = Path(file.filename).suffix.lower()
  if suffix not in allowed_suffixes:
      raise HTTPException(
          status_code=status.HTTP_400_BAD_REQUEST,
          detail="Invalid file type. Allowed types: pdf, jpeg, csv, docx"
      )

  file_name = f"{uuid4()}{suffix}"
  file_path = UPLOAD_DIR / file_name
  with file_path.open("wb") as buffer:
    shutil.copyfileobj(file.file,buffer)
  return str(file_path) 

def success_response(message:str,status_code:int,data:any=None,meta:dict[str,any]=None):
  return ApiResponse(success=True,message=message,data=data,meta=meta,errors=None)
def error_response(message:str,status_code:int,meta:dict[str,any]=None,errors:any=None,request_id:str | None =None):

  return  JSONResponse(
          status_code=status_code,
          content=ApiResponse(
            success=False,
            message=message,
            data=None,
            meta={"request_id": request_id} if request_id else None,
            errors=errors
            ).model_dump()
          )


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
  

  