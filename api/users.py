from fastapi import APIRouter, Depends, HTTPException, status
from typing import Any
from supabase import Client
from core.supabase import supabase
from core.auth import get_current_user, get_authed_client
from models.users import ProfileResponse, ProfileUpdate
from utils.logger import setup_logger

logger = setup_logger(__name__)
router = APIRouter(prefix="/users", tags=["users"])

@router.get("/me", response_model=ProfileResponse)
async def get_my_profile(
    current_user: Any = Depends(get_current_user),
    authed_client: Client = Depends(get_authed_client)
):
    logger.info(f"Fetching profile for user: {current_user.id}")
    try:
        response = authed_client.table("profiles").select("*").eq("id", current_user.id).single().execute()
        if not response.data:
            logger.warning(f"Profile not found for user: {current_user.id}")
            raise HTTPException(status_code=404, detail="Profile not found")
        return response.data
    except Exception as e:
        logger.error(f"Error fetching profile: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.patch("/me", response_model=ProfileResponse)
async def update_my_profile(
    profile_update: ProfileUpdate,
    current_user: Any = Depends(get_current_user),
    authed_client: Client = Depends(get_authed_client)
):
    logger.info(f"Updating profile for user: {current_user.id}")
    try:
        update_data = profile_update.model_dump(exclude_unset=True)
        response = authed_client.table("profiles").update(update_data).eq("id", current_user.id).execute()
        if not response.data:
            logger.warning(f"Failed to update profile for user: {current_user.id}")
            raise HTTPException(status_code=400, detail="Profile update failed")
        return response.data[0]
    except Exception as e:
        logger.error(f"Error updating profile: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/me/bookmarks")
async def get_my_bookmarks(
    current_user: Any = Depends(get_current_user),
    authed_client: Client = Depends(get_authed_client)
):
    logger.info(f"Fetching bookmarks for user: {current_user.id}")
    try:
        response = authed_client.table("bookmarks").select("recipe_id, recipes(*, meals(*))").eq("user_id", current_user.id).execute()
        return response.data
    except Exception as e:
        logger.error(f"Error fetching bookmarks: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.delete("/me/bookmarks/{recipe_id}")
async def remove_bookmark(
    recipe_id: str,
    current_user: Any = Depends(get_current_user),
    authed_client: Client = Depends(get_authed_client)
):
    logger.info(f"Removing bookmark {recipe_id} for user: {current_user.id}")
    try:
        response = authed_client.table("bookmarks").delete().eq("user_id", current_user.id).eq("recipe_id", recipe_id).execute()
        return {"status": "success", "message": "Bookmark removed"}
    except Exception as e:
        logger.error(f"Error removing bookmark: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
