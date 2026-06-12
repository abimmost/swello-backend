from pydantic import BaseModel, ConfigDict
from typing import List, Optional
from uuid import UUID

class NutrientProfileBase(BaseModel):
    protein_grams: float
    protein_percentage: float
    carb_grams: float
    carb_percentage: float
    fat_grams: float
    fat_percentage: float
    saturated_fat_g: Optional[float] = None
    cholesterol_mg: Optional[float] = None
    sodium_mg: Optional[float] = None
    potassium_mg: Optional[float] = None
    fiber_g: Optional[float] = None
    sugar_g: Optional[float] = None
    vitamin_a_iu: Optional[float] = None
    vitamin_c_mg: Optional[float] = None
    calcium_mg: Optional[float] = None
    iron_mg: Optional[float] = None

class NutrientProfileResponse(NutrientProfileBase):
    meal_id: UUID
    model_config = ConfigDict(from_attributes=True)

class MealBase(BaseModel):
    title: str
    description: Optional[str] = None
    image_url: Optional[str] = None
    tags: List[str] = []
    duration_minutes: Optional[int] = None
    balanced_level_score: Optional[int] = None

class MealCreate(MealBase):
    pass

class MealResponse(MealBase):
    id: UUID
    is_custom: bool
    author_id: Optional[UUID] = None
    nutrient_profile: Optional[NutrientProfileResponse] = None
    
    model_config = ConfigDict(from_attributes=True)
