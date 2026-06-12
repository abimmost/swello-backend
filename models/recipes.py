from pydantic import BaseModel, ConfigDict
from typing import List, Optional
from uuid import UUID
from .meals import MealResponse


class IngredientBase(BaseModel):
    name: str
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
    cookware: List[str] = []

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
    description: Optional[str] = None
    image_url: Optional[str] = None
    tags: List[str] = []
    duration_minutes: Optional[int] = None
    # Recipe fields
    steps: List[str] = []
    cookware: List[str] = []
