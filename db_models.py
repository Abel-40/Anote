from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column,Integer,String
Base = declarative_base()


class User(Base):
  __tablename__ = "User"
  id = Column(Integer, primary_key=True)
  username = Column(String,unique=True)
  email = Column(String,unique=True,nullable=True)
  hasshed_password = Column(String)
  full_name = Column(String)
  