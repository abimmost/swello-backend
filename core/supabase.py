from supabase import create_client, Client
from .config import get_settings
from utils.logger import setup_logger

logger = setup_logger(__name__)

settings = get_settings()

try:
    supabase: Client = create_client(settings.supabase_url, settings.supabase_key)
    logger.info("Supabase client initialized successfully.")
except Exception as e:
    logger.error(f"Failed to initialize Supabase client: {e}")
    raise
