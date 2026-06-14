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
        response = supabase.table("recipes").select("*, meals(*)").eq("is_ai_generated", False).range(offset, offset + limit - 1).execute()
        return response.data
    except Exception as e:
        logger.error(f"Error fetching recipes: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/search")
async def search_recipes(
    q: Optional[str] = None,
    tags: Optional[str] = None,
    ingredients: Optional[str] = None
):
    logger.info(f"Searching recipes - q: {q}, tags: {tags}, ingredients: {ingredients}")
    try:
        query = supabase.table("meals").select("*, recipes(*)")
        if q:
            query = query.ilike("title", f"%{q}%")
        if tags:
            tag_list = [t.strip() for t in tags.split(",")]
            query = query.contains("tags", tag_list)
            
        if ingredients:
            ing_list = [i.strip() for i in ingredients.split(",")]
            # Step 1: Find ingredient IDs using case-insensitive ilike per ingredient
            ing_ids = []
            for ing_name in ing_list:
                res = supabase.table("ingredients").select("id").ilike("name", ing_name).execute()
                if res.data:
                    ing_ids.append(res.data[0]["id"])

            # Must find a valid DB match for every requested ingredient — enforce AND semantics
            if len(ing_ids) == len(ing_list):
                # Step 2: Find recipe IDs containing those ingredients
                ri_res = supabase.table("recipe_ingredients").select("recipe_id, ingredient_id").in_("ingredient_id", ing_ids).execute()
                if ri_res.data:
                    # Group by recipe_id to enforce AND logic
                    from collections import defaultdict
                    recipe_ing_map = defaultdict(set)
                    for row in ri_res.data:
                        recipe_ing_map[row["recipe_id"]].add(row["ingredient_id"])

                    # Keep only recipes that have ALL the requested ingredients
                    recipe_ids = [r_id for r_id, i_ids in recipe_ing_map.items() if len(i_ids) == len(ing_ids)]

                    if recipe_ids:
                        # Step 3: Find meal IDs for those recipes
                        r_res = supabase.table("recipes").select("meal_id").in_("id", recipe_ids).execute()
                        if r_res.data:
                            meal_ids = [r["meal_id"] for r in r_res.data]
                            query = query.in_("id", meal_ids)
                        else:
                            query = query.in_("id", ["00000000-0000-0000-0000-000000000000"]) # Force empty
                    else:
                        query = query.in_("id", ["00000000-0000-0000-0000-000000000000"])
                else:
                    query = query.in_("id", ["00000000-0000-0000-0000-000000000000"])
            else:
                query = query.in_("id", ["00000000-0000-0000-0000-000000000000"])

        response = query.execute()
        
        # Filter out AI generated recipes from the nested meals results
        for meal in response.data:
            if "recipes" in meal:
                meal["recipes"] = [r for r in meal["recipes"] if not r.get("is_ai_generated", False)]
                
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
            "is_ai_generated": request.is_custom if request.is_custom is not None else False,
            "editor_id": str(current_user.id),
        }).execute()

        if not recipe_response.data:
            raise HTTPException(status_code=500, detail="Failed to create recipe record")

        recipe_id = recipe_response.data[0]["id"]
        
        # 3. Handle ingredients
        if request.ingredients:
            recipe_ingredients_to_insert = []
            for ing in request.ingredients:
                ing_name = ing.get("name", "").strip()
                if not ing_name:
                    continue
                    
                # Find existing ingredient using global client to bypass read restrictions if any
                ing_res = supabase.table("ingredients").select("id").ilike("name", ing_name).execute()
                if ing_res.data:
                    ingredient_id = ing_res.data[0]["id"]
                else:
                    # Create new ingredient in catalog (requires global client to bypass RLS)
                    new_ing = supabase.table("ingredients").insert({
                        "name": ing_name,
                        "category": "Other"
                    }).execute()
                    ingredient_id = new_ing.data[0]["id"]
                    
                recipe_ingredients_to_insert.append({
                    "recipe_id": recipe_id,
                    "ingredient_id": ingredient_id,
                    "measurement_value": str(ing.get("quantity", "")),
                    "is_essential": ing.get("is_essential", False)
                })
                
            # Insert all into recipe_ingredients
            if recipe_ingredients_to_insert:
                # Use global client since recipe_ingredients writes are restricted to backend service role
                supabase.table("recipe_ingredients").insert(recipe_ingredients_to_insert).execute()

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

