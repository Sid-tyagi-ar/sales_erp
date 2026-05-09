from pydantic_settings import BaseSettings, SettingsConfigDict
from dotenv import load_dotenv
from typing import Optional

load_dotenv()

class Settings(BaseSettings):
    FIREBASE_CREDENTIALS_PATH: Optional[str] = None # Keep for backward compatibility
    FIREBASE_CREDENTIALS_JSON: Optional[str] = None # New field for JSON string
    FIREBASE_PROJECT_ID: str
    APP_ENV: str = "development"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()
