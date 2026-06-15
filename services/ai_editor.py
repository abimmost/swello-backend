"""
AI Meal Editor Service

An isolated service module (per GEMINI.md §7) that handles:
1. Validating whether an ingredient removal is possible (essential ingredient check).
2. Calling the Gemini API to recalculate macros, cooking time, and insights.
3. Returning a structured JSON response for the frontend AIEditor.tsx to consume directly.

HARD RULE: The AI must validate and reject impossible removals
(e.g., flour from cookies) with an explanation.
"""
from google import genai
from pydantic import BaseModel, Field
from typing import List, Optional
from models.ai import GeminiEditResult, NutritionEstimate
from core.config import get_settings
from core.supabase import supabase
from utils.logger import setup_logger

logger = setup_logger(__name__)

FALLBACK_MODELS = [
    "gemini-3.5-flash",
    "gemini-3-flash",
    "gemini-2.5-flash",
    "gemini-3.1-flash-lite",
    "gemini-2.5-flash-lite"
]

def _execute_with_fallback(prompt: str, schema: dict) -> str:
    """Executes the Gemini API call with rate limit detection and fallback routing."""
    for model_name in FALLBACK_MODELS:
        try:
            logger.debug(f"AI Editor: Attempting Gemini call with model {model_name}")
            interaction = client.interactions.create(
                model=model_name,
                input=prompt,
                response_format={
                    "type": "text",
                    "mime_type": "application/json",
                    "schema": schema
                },
            )
            return interaction.output_text
        except Exception as e:
            error_msg = str(e).lower()
            # 429 Too Many Requests, Quota Exceeded, or Resource Exhausted
            if "429" in error_msg or "quota" in error_msg or "rate limit" in error_msg or "exhausted" in error_msg:
                logger.warning(f"AI Editor: Model {model_name} rate limited/quota exceeded. Falling back...")
                continue
            else:
                logger.error(f"AI Editor: Non-rate-limit error with {model_name}: {e}")
                raise e
    
    raise Exception("All fallback models exhausted due to rate limits.")

# --- Initialize Gemini client ---

# --- Initialize Gemini client ---

settings = get_settings()
client = genai.Client(api_key=settings.gemini_api_key)
logger.info("Gemini AI client initialized for AI Meal Editor service.")


# --- Core AI Editor Logic ---

async def validate_and_edit_recipe(recipe_id: str, intended_change: str) -> dict:
    """
    Main entry point for the AI Meal Editor.

    1. Fetches the recipe and its ingredients from Supabase.
    2. Checks if the intended change targets an essential ingredient.
    3. If essential, rejects with a clear explanation (no AI call needed).
    4. If valid, calls Gemini to recalculate everything.

    Args:
        recipe_id: The UUID of the recipe to edit.
        intended_change: A natural language description of the change (e.g. "remove chicken").

    Returns:
        A dict matching the AIEditResponse schema.
    """
    logger.info(f"AI Editor: Processing edit for recipe {recipe_id} — '{intended_change}'")

    # Step 1: Fetch recipe with ingredients from DB
    try:
        recipe_response = supabase.table("recipes").select(
            "*, meals(*, nutrient_profiles(*)), recipe_ingredients(*, ingredients(*))"
        ).eq("id", recipe_id).single().execute()
    except Exception as e:
        logger.error(f"AI Editor: Failed to fetch recipe {recipe_id}: {e}")
        raise ValueError(f"Recipe not found: {recipe_id}")

    recipe_data = recipe_response.data
    if not recipe_data:
        logger.warning(f"AI Editor: Recipe {recipe_id} not found in database.")
        raise ValueError(f"Recipe not found: {recipe_id}")

    meal_data = recipe_data.get("meals", {})
    recipe_ingredients = recipe_data.get("recipe_ingredients", [])

    logger.debug(f"AI Editor: Recipe '{meal_data.get('title', 'Unknown')}' has {len(recipe_ingredients)} ingredients.")

    # Step 2: Check for essential ingredient removal
    essential_rejection = _check_essential_ingredients(intended_change, recipe_ingredients)
    if essential_rejection:
        logger.warning(f"AI Editor: Essential ingredient rejection — {essential_rejection}")
        return {
            "is_valid": False,
            "validation_error": essential_rejection,
            "insights": [],
            "macro_shift": None,
            "new_time": None,
            "new_score": None,
        }

    # Step 3: Call Gemini for the actual edit analysis
    logger.info(f"AI Editor: Calling Gemini API for recipe edit analysis...")
    gemini_result = await _call_gemini_for_edit(meal_data, recipe_data, recipe_ingredients, intended_change)

    # Step 4: Map the Gemini result to our API response format
    response = {
        "is_valid": gemini_result.is_valid,
        "validation_error": gemini_result.validation_error,
        "insights": gemini_result.insights,
        "macro_shift": {
            "protein_g": gemini_result.macro_shift.new_protein_g,
            "carb_g": gemini_result.macro_shift.new_carb_g,
            "fat_g": gemini_result.macro_shift.new_fat_g,
            "protein_percentage": gemini_result.macro_shift.new_protein_percentage,
            "carb_percentage": gemini_result.macro_shift.new_carb_percentage,
            "fat_percentage": gemini_result.macro_shift.new_fat_percentage,
        } if gemini_result.macro_shift else None,
        "new_time": gemini_result.new_cooking_time_minutes,
        "new_score": gemini_result.new_balanced_level_score,
    }
    logger.info(f"AI Editor: Edit analysis complete. Valid: {response['is_valid']}, New score: {response.get('new_score')}")
    return response


def _check_essential_ingredients(intended_change: str, recipe_ingredients: list) -> Optional[str]:
    """
    Pre-validation: Check if the intended change tries to remove an essential ingredient.
    Returns an error message string if blocked, or None if the edit is allowed to proceed.
    """
    change_lower = intended_change.lower()

    for ri in recipe_ingredients:
        ingredient = ri.get("ingredients", {})
        ingredient_name = ingredient.get("name", "").lower()
        is_essential = ri.get("is_essential", False)

        if is_essential and ingredient_name in change_lower:
            return (
                f"'{ingredient.get('name')}' is an essential ingredient in this recipe "
                f"and cannot be removed. Removing it would fundamentally change the dish "
                f"beyond recognition. Please try removing a different ingredient."
            )

    return None


async def _call_gemini_for_edit(
    meal_data: dict,
    recipe_data: dict,
    recipe_ingredients: list,
    intended_change: str
) -> GeminiEditResult:
    """
    Calls the Gemini API with structured output to analyze the recipe edit.
    """
    # Build the ingredient list string for the prompt
    ingredients_text = "\n".join([
        f"- {ri.get('ingredients', {}).get('name', 'Unknown')}: "
        f"{ri.get('measurement_value', '')} "
        f"({'ESSENTIAL' if ri.get('is_essential') else 'removable'})"
        for ri in recipe_ingredients
    ])

    # Build the nutrient profile string
    nutrient_profile = meal_data.get("nutrient_profiles", {}) or {}
    nutrient_text = (
        f"Protein: {nutrient_profile.get('protein_grams', 'N/A')}g, "
        f"Carbs: {nutrient_profile.get('carb_grams', 'N/A')}g, "
        f"Fat: {nutrient_profile.get('fat_grams', 'N/A')}g"
    )

    steps_text = "\n".join([f"{i+1}. {step}" for i, step in enumerate(recipe_data.get("steps", []))])
    cookware_text = ", ".join(recipe_data.get("cookware", []))

    prompt = f"""You are an expert Cameroonian nutritionist and chef. Analyze the following recipe edit request.

## Current Recipe: {meal_data.get('title', 'Unknown')}
- Description: {meal_data.get('description', 'N/A')}
- Cooking Time: {meal_data.get('duration_minutes', 'N/A')} minutes
- Difficulty: {meal_data.get('difficulty', 'N/A')}
- Current Balanced Level Score: {meal_data.get('balanced_level_score', 'N/A')}/100
- Current Nutrients: {nutrient_text}

## Ingredients:
{ingredients_text}

## Cooking Steps:
{steps_text}

## Cookware:
{cookware_text}

## Requested Edit:
"{intended_change}"

## Instructions:
1. Determine if this edit is valid. If an ingredient marked ESSENTIAL is being removed, set is_valid to false and explain why.
2. If valid, calculate the NEW TOTAL absolute macronutrients in grams for the entire meal (protein, carbs, and fat).
3. Provide 2-4 concise insights about how this change affects the meal (e.g., "Becomes vegetarian-friendly", "Protein drops significantly").
4. Estimate the new cooking time in minutes.
5. Calculate a new Balanced Level Score from 0-100 (where 100 is perfectly balanced across protein, carbs, fat, and micronutrients).
6. Provide the adjusted cooking steps and cookware list with the ingredient removed.
"""

    logger.debug(f"AI Editor: Sending prompt to Gemini (length: {len(prompt)} chars)")

    try:
        output_text = _execute_with_fallback(
            prompt=prompt,
            schema=GeminiEditResult.model_json_schema()
        )

        result = GeminiEditResult.model_validate_json(output_text)
        logger.info(f"AI Editor: Gemini response parsed successfully. Valid: {result.is_valid}")
        return result

    except Exception as e:
        logger.error(f"AI Editor: Gemini API call failed: {e}")
        # Return a safe fallback
        return GeminiEditResult(
            is_valid=False,
            validation_error=f"AI processing encountered an error: {str(e)}. Please try again.",
            insights=[],
            macro_shift=None,
            new_cooking_time_minutes=None,
            new_balanced_level_score=None,
            adjusted_steps=[],
            adjusted_cookware=[]
        )


async def calculate_nutrition_with_ai(ingredients: list) -> dict:
    """
    Uses Gemini to estimate nutritional content for a user-provided ingredient list.
    Used by the POST /nutrition/calculate endpoint for custom recipes.
    """
    logger.info(f"AI Nutrition: Calculating nutrients for {len(ingredients)} ingredients.")

    ingredients_text = "\n".join([
        f"- {ing.get('name', 'Unknown')}: {ing.get('quantity', 'N/A')} {ing.get('unit', '')}"
        for ing in ingredients
    ])

    prompt = f"""You are an expert nutritionist specializing in Cameroonian cuisine.
Calculate the nutritional content for the following ingredient list.

## Ingredients:
{ingredients_text}

Provide estimates for all macronutrients and available micronutrients.
Calculate a Balanced Level Score from 0-100 based on the nutritional balance.
"""

    try:
        output_text = _execute_with_fallback(
            prompt=prompt,
            schema=NutritionEstimate.model_json_schema()
        )

        result = NutritionEstimate.model_validate_json(output_text)
        logger.info(f"AI Nutrition: Calculation complete. BLS: {result.balanced_level_score}/100")
        return result.model_dump()

    except Exception as e:
        logger.error(f"AI Nutrition: Gemini API call failed: {e}")
        raise ValueError(f"Failed to calculate nutrition: {str(e)}")
