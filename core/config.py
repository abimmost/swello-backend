from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import Optional

class Settings(BaseSettings):
    supabase_url: str
    supabase_key: str
    gemini_api_key: str
    ngrok_authtoken: Optional[str] = None
    cors_origins: str

    class Config:
        env_file = ".env"

@lru_cache()
def get_settings():
    return Settings()
