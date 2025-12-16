from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column,Integer,String,DateTime,Text,ForeignKey,Table
from sqlalchemy.orm import relationship
from datetime import datetime,timezone
Base = declarative_base()


class User(Base):
  __tablename__ = "users"
  id = Column(Integer, primary_key=True)
  username = Column(String,unique=True,index=True)
  email = Column(String,unique=True,nullable=True,index=True)
  hashed_password = Column(String,nullable=False)
  full_name = Column(String)
  created_at = Column(DateTime, default=datetime.utcnow)
  
  notes = relationship("Note",back_populates="user",cascade="all, delete")
  
  
note_tag = Table(
  "note_tag",
  Base.metadata,
  Column("note_id",Integer,ForeignKey("notes.id"),primary_key=True),
  Column("tag_id",Integer,ForeignKey("tags.id"),primary_key=True)
)
class Note(Base):
  __tablename__ = "notes"
  id = Column(Integer,primary_key=True)
  title = Column(String,nullable=False)
  content = Column(Text,nullable=True)
  user_id = Column(Integer,ForeignKey("users.id",ondelete="CASCADE"))
  created_at = Column(DateTime,default=datetime.utcnow)
  user = relationship("User",back_populates="notes")
  tags = relationship("Tag",secondary=note_tag,back_populates="notes")
  files = relationship("MediaFile",back_populates="note",cascade="all,delete-orphan")

class Tag(Base):
  __tablename__ = "tags"
  id = Column(Integer,primary_key=True)
  name = Column(String,nullable=False,unique=True,index=True)

  notes = relationship("Note",secondary=note_tag,back_populates="tags")
  

class MediaFile(Base):
  __tablename__ = "media_files"
  id = Column(Integer,primary_key=True)
  file_name = Column(String,nullable=False)
  file_path = Column(String,nullable=False)
  content_type = Column(String)
  note_id = Column(Integer,ForeignKey("notes.id",ondelete="CASCADE"))
  
  note = relationship("Note",back_populates="files")
  