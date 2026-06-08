from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from supabase import Client, create_client
from .supabase import supabase
from .config import get_settings
from utils.logger import setup_logger

logger = setup_logger(__name__)

security = HTTPBearer()

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """
    Validates the Supabase JWT token and retrieves the current user.
    """
    token = credentials.credentials
    try:
        user = supabase.auth.get_user(token)
        if not user or not user.user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return user.user
    except Exception as e:
        logger.warning(f"Authentication failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


def get_authed_client(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Client:
    """
    Returns a Supabase client authenticated with the user's own JWT.
    This is REQUIRED for any INSERT/UPDATE/DELETE against RLS-protected tables
    (e.g. bookmarks, meal_plans, planned_meals, profiles).
    Using the global anon-key client for writes will be rejected by RLS.
    """
    token = credentials.credentials
    settings = get_settings()
    client: Client = create_client(settings.supabase_url, settings.supabase_key)
    client.auth.set_session(token, token)
    return client
