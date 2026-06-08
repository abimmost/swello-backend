from pydantic import BaseModel
from typing import List, Optional


class MacroShift(BaseModel):
    protein_shift_g: float
    carb_shift_g: float
    fat_shift_g: float
    protein_percentage: float
    carb_percentage: float
    fat_percentage: float


class AIEditResponse(BaseModel):
    is_valid: bool
    validation_error: Optional[str] = None
    insights: List[str] = []
    macro_shift: Optional[MacroShift] = None
    new_time: Optional[int] = None
    new_score: Optional[int] = None


# --- Request schemas (used by api/ai.py) ---

class RecipeEditRequest(BaseModel):
    """Request body for POST /ai/recipe-edit."""
    recipe_id: str
    intended_change: str  # e.g. "remove chicken"


class IngredientInput(BaseModel):
    """A single ingredient entry for nutrition calculation."""
    name: str
    quantity: str
    unit: str = ""


class NutritionCalculateRequest(BaseModel):
    """Request body for POST /ai/nutrition/calculate."""
    ingredients: List[IngredientInput]
