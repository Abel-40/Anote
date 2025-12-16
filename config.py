from pydantic_settings import BaseSettings

class Settings(BaseSettings):
  ACCESS_SECRET_KEY:str
  REFRESH_SECRET_KEY:str
  ALGORITHUM:str
  TOKEN_EXPIRY_DATE:int
  DB_URL:str
  UPLOAD_DIR:str
  class Config:
    env_file = ".env"
    
setting = Settings()