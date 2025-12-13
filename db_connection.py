from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from config import setting

engine = create_engine(url=setting.DB_URL)
session = sessionmaker(autoflush=False,autocommit=False,bind=engine)