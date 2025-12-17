from pydantic import BaseModel,EmailStr,Field,field_validator,ValidationError
from typing import Annotated,List
from fastapi import Form
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
    
class NoteCreate(BaseModel):
  title:str
  content:str
  
  @classmethod
  def as_form(cls,title:str = Form(...),content:str = Form(...)):
    return cls(title=title,content=content)
class NoteOut(BaseModel):
  id:int
  title:str
  content:str
  files:List[MediaFileOut]
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
  notes:List[NoteOut]
  
  class Config:
    from_attributes = True
    
