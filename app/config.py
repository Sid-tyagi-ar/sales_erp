from pydantic_settings import BaseSettings, SettingsConfigDict
from dotenv import load_dotenv

load_dotenv()

class Settings(BaseSettings):
    FIREBASE_CREDENTIALS_PATH: str
    FIREBASE_PROJECT_ID: str
    APP_ENV: str = "development"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()