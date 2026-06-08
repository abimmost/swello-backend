from fastapi import APIRouter, Depends, HTTPException
from typing import Any
from core.auth import get_current_user
from models.ai import AIEditResponse, RecipeEditRequest, NutritionCalculateRequest
from services.ai_editor import validate_and_edit_recipe, calculate_nutrition_with_ai
from utils.logger import setup_logger

logger = setup_logger(__name__)
router = APIRouter(prefix="/ai", tags=["ai"])


@router.post("/recipe-edit", response_model=AIEditResponse)
async def ai_edit_recipe(request: RecipeEditRequest, current_user: Any = Depends(get_current_user)):
    """
    Submit an intended recipe change. The AI validates if the ingredient is
    essential, recalibrates macros, adjusts cooking steps, and returns a
    structured diff for the frontend AIEditor.tsx to display.
    """
    logger.info(
        f"AI Edit requested by user {current_user.id} for recipe {request.recipe_id} "
        f"with change: '{request.intended_change}'"
    )
    try:
        result = await validate_and_edit_recipe(request.recipe_id, request.intended_change)
        logger.info(f"AI Edit completed. Valid: {result.get('is_valid')}")
        return result
    except ValueError as e:
        logger.warning(f"AI Edit validation error: {e}")
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"AI Edit unexpected error: {e}")
        raise HTTPException(status_code=500, detail="AI processing failed")


@router.post("/nutrition/calculate")
async def calculate_nutrition(request: NutritionCalculateRequest, current_user: Any = Depends(get_current_user)):
    """
    Calculate the Balanced Level Score and macros for a user-provided
    ingredient list (used when adding custom recipes).
    """
    logger.info(
        f"Nutrition calculation requested by user {current_user.id} "
        f"for {len(request.ingredients)} ingredients"
    )
    try:
        ingredients_data = [ing.model_dump() for ing in request.ingredients]
        result = await calculate_nutrition_with_ai(ingredients_data)
        logger.info(f"Nutrition calculation complete. BLS: {result.get('balanced_level_score')}")
        return result
    except ValueError as e:
        logger.warning(f"Nutrition calculation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error(f"Nutrition calculation unexpected error: {e}")
        raise HTTPException(status_code=500, detail="Nutrition calculation failed")
