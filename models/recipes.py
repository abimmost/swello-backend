from pydantic import BaseModel, ConfigDict
from typing import List, Optional
from uuid import UUID
from .meals import MealResponse


class IngredientBase(BaseModel):
    name: str
    name_fr: Optional[str] = None
    category: Optional[str] = None

class IngredientResponse(IngredientBase):
    id: UUID
    model_config = ConfigDict(from_attributes=True)

class RecipeIngredientBase(BaseModel):
    ingredient_id: UUID
    measurement_value: Optional[str] = None
    is_essential: bool = False

class RecipeIngredientResponse(RecipeIngredientBase):
    ingredient: Optional[IngredientResponse] = None
    model_config = ConfigDict(from_attributes=True)

class RecipeBase(BaseModel):
    steps: List[str] = []
    steps_fr: List[str] = []
    cookware: List[str] = []
    cookware_fr: List[str] = []

class RecipeResponse(RecipeBase):
    id: UUID
    meal_id: UUID
    is_ai_generated: bool
    parent_recipe_id: Optional[UUID] = None
    editor_id: Optional[UUID] = None
    recipe_ingredients: List[RecipeIngredientResponse] = []
    meal: Optional[MealResponse] = None

    model_config = ConfigDict(from_attributes=True)


# --- Request schemas (used by api/recipes.py) ---

class CreateRecipeRequest(BaseModel):
    """Request body for creating a custom user recipe (POST /recipes)."""
    # Meal fields
    title: str
    title_fr: Optional[str] = None
    description: Optional[str] = None
    description_fr: Optional[str] = None
    image_url: Optional[str] = None
    tags: List[str] = []
    duration_minutes: Optional[int] = None
    # Recipe fields
    ingredients: List[dict] = []
    steps: List[str] = []
    steps_fr: List[str] = []
    cookware: List[str] = []
    cookware_fr: List[str] = []
    is_custom: Optional[bool] = False
    parent_recipe_id: Optional[str] = None
    balanced_level_score: Optional[int] = None
    protein_grams: Optional[float] = None
    carb_grams: Optional[float] = None
    fat_grams: Optional[float] = None
