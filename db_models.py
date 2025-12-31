from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column,Integer,String,DateTime,Text,ForeignKey,Table
from sqlalchemy.orm import relationship
from datetime import datetime,timezone
Base = declarative_base()

role_permission = Table(
  "role_permissions",
  Base.metadata,
  Column("role_id",Integer,ForeignKey("role.id"),primary_key=True),
  Column("permission_id",Integer,ForeignKey("permission.id"),primary_key=True)
)

user_roles = Table(
  "user_roles",
  Base.metadata,
  Column("user_id",Integer,ForeignKey("users.id"),primary_key=True),
  Column("role_id",Integer,ForeignKey("role.id"),primary_key=True)
)

note_tag = Table(
  "note_tag",
  Base.metadata,
  Column("note_id",Integer,ForeignKey("notes.id"),primary_key=True),
  Column("tag_id",Integer,ForeignKey("tags.id"),primary_key=True)
)
class User(Base):
  __tablename__ = "users"
  id = Column(Integer, primary_key=True)
  username = Column(String,unique=True,index=True)
  email = Column(String,unique=True,nullable=True,index=True)
  hashed_password = Column(String,nullable=False)
  full_name = Column(String)
  created_at = Column(DateTime, default=datetime.utcnow)
  
  notes = relationship("Note",back_populates="user",cascade="all, delete")
  roles = relationship("Role",secondary=user_roles,back_populates="users")
  
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
  

class Permission(Base):
  __tablename__ = "permission"
  
  id = Column(Integer,primary_key=True)
  name = Column(String,unique=True,index=True)
  description = Column(String,nullable=True)
  
  roles = relationship("Role",secondary=role_permission,back_populates="permission")
class Role(Base):
  __tablename__ = "role"
  
  id = Column(Integer,primary_key=True)
  name = Column(String,unique=True)
  description = Column(String,nullable=True)
  
  permission = relationship("Permission",secondary=role_permission,back_populates="roles")
  users = relationship("User",secondary=user_roles,back_populates="roles")
