from pydantic import BaseModel, Field
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


# --- Gemini structured output schemas ---

class GeminiMacroShift(BaseModel):
    """The macro shift returned by Gemini after removing an ingredient."""
    protein_shift_g: float = Field(description="Change in protein grams (negative means decrease).")
    carb_shift_g: float = Field(description="Change in carb grams (negative means decrease).")
    fat_shift_g: float = Field(description="Change in fat grams (negative means decrease).")
    new_protein_percentage: float = Field(description="New protein percentage of the modified meal.")
    new_carb_percentage: float = Field(description="New carb percentage of the modified meal.")
    new_fat_percentage: float = Field(description="New fat percentage of the modified meal.")

class GeminiEditResult(BaseModel):
    """The full structured response from Gemini for an AI meal edit."""
    is_valid: bool = Field(description="Whether the edit is valid. False if an essential ingredient cannot be removed.")
    validation_error: Optional[str] = Field(default=None, description="If is_valid is False, a clear explanation of why the edit is impossible.")
    insights: List[str] = Field(default_factory=list, description="A list of 2-4 human-readable insights about how this change affects the meal.")
    macro_shift: Optional[GeminiMacroShift] = Field(default=None, description="The macro nutrient shift resulting from the edit. Null if the edit is invalid.")
    new_cooking_time_minutes: Optional[int] = Field(default=None, description="The new estimated cooking time in minutes after the edit.")
    new_balanced_level_score: Optional[int] = Field(default=None, description="The new Balanced Level Score (0-100) after the edit.")
    adjusted_steps: List[str] = Field(default_factory=list, description="The adjusted cooking steps after the ingredient removal.")
    adjusted_cookware: List[str] = Field(default_factory=list, description="The adjusted cookware list after the ingredient removal.")

class NutritionEstimate(BaseModel):
    """Structured output for Gemini nutrition estimation."""
    protein_grams: float = Field(description="Estimated protein in grams.")
    protein_percentage: float = Field(description="Protein as percentage of total macros.")
    carb_grams: float = Field(description="Estimated carbohydrates in grams.")
    carb_percentage: float = Field(description="Carbs as percentage of total macros.")
    fat_grams: float = Field(description="Estimated fat in grams.")
    fat_percentage: float = Field(description="Fat as percentage of total macros.")
    fiber_g: float = Field(description="Estimated fiber in grams.")
    iron_mg: float = Field(description="Estimated iron in milligrams.")
    vitamin_c_mg: float = Field(description="Estimated vitamin C in milligrams.")
    balanced_level_score: int = Field(description="The Balanced Level Score from 0-100.")
