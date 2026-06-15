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
        response = supabase.table("recipes").select("*, meals(*, profiles(display_name))").eq("is_ai_generated", False).range(offset, offset + limit - 1).execute()
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
            "*, meals(*, nutrient_profiles(*), profiles(display_name)), recipe_ingredients(*, ingredients(*))"
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
            "balanced_level_score": request.balanced_level_score,
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
            "parent_recipe_id": request.parent_recipe_id,
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
                    
                # Find existing ingredient using authed_client
                ing_res = authed_client.table("ingredients").select("id").ilike("name", ing_name).execute()
                if ing_res.data:
                    ingredient_id = ing_res.data[0]["id"]
                else:
                    # Create new ingredient in catalog using authed_client
                    new_ing = authed_client.table("ingredients").insert({
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
                # Use authed_client now that RLS policies allow editor to insert
                authed_client.table("recipe_ingredients").insert(recipe_ingredients_to_insert).execute()

        # 4. Insert nutrient profile if macros are provided
        if request.protein_grams is not None:
            authed_client.table("nutrient_profiles").insert({
                "meal_id": meal_id,
                "protein_grams": request.protein_grams,
                "carb_grams": request.carb_grams,
                "fat_grams": request.fat_grams,
            }).execute()

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

@router.delete("/{recipe_id}")
async def delete_custom_recipe(
    recipe_id: str,
    current_user: Any = Depends(get_current_user),
    authed_client: Client = Depends(get_authed_client)
):
    """Deletes a custom/AI-generated recipe created by the user."""
    logger.info(f"Deleting recipe {recipe_id} for user {current_user.id}")
    try:
        # First, fetch the recipe to get the meal_id and ensure it belongs to the user
        recipe_response = authed_client.table("recipes").select("meal_id, editor_id").eq("id", recipe_id).execute()
        if not recipe_response.data:
            raise HTTPException(status_code=404, detail="Recipe not found")
            
        recipe = recipe_response.data[0]
        if str(recipe.get("editor_id")) != str(current_user.id):
            raise HTTPException(status_code=403, detail="Not authorized to delete this recipe")
            
        meal_id = recipe["meal_id"]
        
        # Delete the parent meal (which will cascade to recipes, recipe_ingredients, bookmarks, planned_meals)
        # We ensure it only deletes if the author_id matches and it's a custom meal
        delete_response = authed_client.table("meals").delete().eq("id", meal_id).eq("author_id", str(current_user.id)).eq("is_custom", True).execute()
        
        if not delete_response.data:
            # Fallback if the meal deletion didn't work (e.g. not a custom meal or mismatch)
            raise HTTPException(status_code=400, detail="Could not delete recipe. Ensure it is a custom recipe you authored.")
            
        logger.info(f"Custom recipe {recipe_id} and parent meal {meal_id} deleted successfully.")
        return {"status": "success", "message": "Recipe deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting recipe {recipe_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

