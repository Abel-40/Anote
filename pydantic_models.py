from pydantic import BaseModel,EmailStr,Field,field_validator
from typing import Annotated,List,Optional,Generic,TypeVar,Any
from fastapi import Form
from datetime import datetime
class User(BaseModel):
  username:Annotated[str,Field(min_length=2,max_length=50)]
  email:EmailStr
  full_name:Annotated[str,Field(max_length=100)]

class UserCreate(User):
  password:str

class UserDbIn(User):
  hashed_password:str
  
class UserOut(User):
  id:int
  is_active:bool
  class Config:
    from_attributes = True

class MediaFileCreate(BaseModel):
  file_name:str
  file_path:str
  content_type:str
  note_id:int
  
class MediaFileOut(BaseModel):
  id:int
  file_name:str
  file_path:str
  content_type:str
  class Config:
    from_attributes = True 
 
 
class TagCreate(BaseModel):
  name:str
  
  @classmethod
  def as_form(cls,name:str=Form(...)):
    return cls(name=name)
  @field_validator("name")
  @classmethod
  def no_hashtag(cls,value):
    if not value.startswith("#"):
      raise ValueError("Tags must start with a '#'")
    return value

class TagOut(BaseModel):
  id:int
  name:str
  class Config:
    from_attributes = True
       
class NoteCreate(BaseModel):
  title:str
  content:str
  
  @classmethod
  def as_form(cls,title:str = Form(...),content:str = Form(...)):
    return cls(title=title,content=content)
class NoteOut(BaseModel):
    id: int
    title: str
    content: Optional[str]
    created_at: datetime
    tags: List[TagOut] = []
    files: List[MediaFileOut] = []

    class Config:
        from_attributes = True
class NoteUpdate(BaseModel):
  title: Optional[str] = Field(default=None, min_length=1)
  content: Optional[str] = Field(default=None)

class QueryParams(BaseModel):
  page:int = Field(default=1,ge=1)
  page_size:int = Field(default=10,le=100)
  tags:Optional[List[str]] = None
  
T = TypeVar("T")

class ApiResponse(BaseModel,Generic[T]):
  success:bool
  message:str
  data:Optional[T] = None
  meta:Optional[dict[str,Any]] = None
  errors:Optional[Any] = None

class PaginationMeta(BaseModel):
  page:int
  page_size:int
  total_items:int
  total_pages:int
  
I = TypeVar("I")
class PaginatedResponse(BaseModel,Generic[I]):
  items:List[I]
  pagination:PaginationMeta
  
class ErrorResponse(BaseModel):
    success: bool = False
    message: str
    errors: dict | None = None
