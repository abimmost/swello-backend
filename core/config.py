from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    supabase_url: str
    supabase_key: str
    gemini_api_key: str

    class Config:
        env_file = ".env"

@lru_cache()
def get_settings():
    return Settings()
