from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Any, Optional
from supabase import Client
from core.supabase import supabase
from core.auth import get_current_user, get_authed_client
from models.recipes import CreateRecipeRequest
from utils.logger import setup_logger

logger = setup_logger(__name__)
router = APIRouter(prefix="/recipes", tags=["recipes"])


@router.get("")
async def list_recipes(
    limit: int = Query(10, ge=1, le=50),
    offset: int = Query(0, ge=0)
):
    logger.info(f"Fetching recipes - limit: {limit}, offset: {offset}")
    try:
        response = supabase.table("recipes").select("*, meals(*)").range(offset, offset + limit - 1).execute()
        return response.data
    except Exception as e:
        logger.error(f"Error fetching recipes: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/search")
async def search_recipes(
    q: Optional[str] = None,
    tags: Optional[str] = None
):
    logger.info(f"Searching recipes - q: {q}, tags: {tags}")
    try:
        query = supabase.table("meals").select("*, recipes(*)")
        if q:
            query = query.ilike("title", f"%{q}%")
        if tags:
            tag_list = [t.strip() for t in tags.split(",")]
            query = query.contains("tags", tag_list)

        response = query.execute()
        return response.data
    except Exception as e:
        logger.error(f"Error searching recipes: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/{recipe_id}")
async def get_recipe(recipe_id: str):
    logger.info(f"Fetching recipe details for: {recipe_id}")
    try:
        response = supabase.table("recipes").select(
            "*, meals(*), recipe_ingredients(*, ingredients(*))"
        ).eq("id", recipe_id).single().execute()

        if not response.data:
            raise HTTPException(status_code=404, detail="Recipe not found")
        return response.data
    except Exception as e:
        logger.error(f"Error fetching recipe {recipe_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("")
async def create_recipe(
    request: CreateRecipeRequest,
    current_user: Any = Depends(get_current_user),
    authed_client: Client = Depends(get_authed_client)
):
    """
    Creates a custom user-added meal + recipe pair.
    The `balanced_level_score` will be null until the user runs it through
    POST /ai/nutrition/calculate separately (to keep AI calls optional).
    """
    logger.info(f"Creating custom recipe '{request.title}' for user {current_user.id}")
    try:
        # 1. Insert the parent meal record (use authed_client for RLS)
        meal_response = authed_client.table("meals").insert({
            "title": request.title,
            "description": request.description,
            "image_url": request.image_url,
            "tags": request.tags,
            "duration_minutes": request.duration_minutes,
            "is_custom": True,
            "author_id": str(current_user.id),
        }).execute()

        if not meal_response.data:
            raise HTTPException(status_code=500, detail="Failed to create meal record")

        meal_id = meal_response.data[0]["id"]
        logger.info(f"Meal record created with id: {meal_id}")

        # 2. Insert the recipe linked to the meal (use authed_client for RLS)
        recipe_response = authed_client.table("recipes").insert({
            "meal_id": meal_id,
            "steps": request.steps,
            "cookware": request.cookware,
            "is_ai_generated": False,
            "editor_id": str(current_user.id),
        }).execute()

        if not recipe_response.data:
            raise HTTPException(status_code=500, detail="Failed to create recipe record")

        recipe_id = recipe_response.data[0]["id"]
        logger.info(f"Recipe record created with id: {recipe_id}. Custom recipe creation complete.")

        return {
            "status": "success",
            "meal_id": meal_id,
            "recipe_id": recipe_id,
            "message": "Custom recipe created. Run POST /ai/nutrition/calculate to get the Balanced Level Score."
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating custom recipe: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/{recipe_id}/bookmark")
async def bookmark_recipe(
    recipe_id: str,
    current_user: Any = Depends(get_current_user),
    authed_client: Client = Depends(get_authed_client)
):
    """Saves a recipe to the user's bookmarks."""
    logger.info(f"Bookmarking recipe {recipe_id} for user {current_user.id}")
    try:
        # Check if already bookmarked (read-only, global client is fine)
        existing = supabase.table("bookmarks").select("*").eq(
            "user_id", str(current_user.id)
        ).eq("recipe_id", recipe_id).execute()
        
        if existing.data:
            return {"status": "success", "message": "Recipe is already bookmarked"}

        # Insert new bookmark using authed_client so RLS sees the correct user
        authed_client.table("bookmarks").insert({
            "user_id": str(current_user.id),
            "recipe_id": recipe_id,
        }).execute()
        
        logger.info(f"Recipe {recipe_id} bookmarked successfully.")
        return {"status": "success", "message": "Recipe bookmarked"}
    except Exception as e:
        logger.error(f"Error bookmarking recipe {recipe_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

