from pydantic import BaseModel,EmailStr,Field
from typing import Annotated
class User(BaseModel):
  username:Annotated[str,Field(min_length=2,max_length=50)]
  email:EmailStr
  full_name:Annotated[str,Field(max_length=100)]

class UserCreate(User):
  password:str

class UserDbIn(User):
  hasshed_password:str
  
class UserOut(User):
  id:int
  class Config:
    from_attributes = True