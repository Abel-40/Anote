from pydantic_settings import BaseSettings

class Settings(BaseSettings):
  SECRET_KEY:str
  ALGORITHUM:str
  TOKEN_EXPIRY_DATE:int
  DB_URL:str
  
  class Config:
    env_file = ".env"
    
setting = Settings()