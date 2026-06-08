from pydantic import BaseModel, ConfigDict
from typing import List, Optional
from datetime import date
from uuid import UUID
from .meals import MealResponse

class PlannedMealBase(BaseModel):
    meal_id: UUID
    scheduled_date: date
    status: Optional[str] = 'planned'

class PlannedMealResponse(PlannedMealBase):
    meal_plan_id: UUID
    meal: Optional[MealResponse] = None
    model_config = ConfigDict(from_attributes=True)

class MealPlanBase(BaseModel):
    start_date: date
    end_date: date

class WeeklyNutritionBalance(BaseModel):
    score: int
    protein_percentage: float
    carb_percentage: float
    fat_percentage: float
    days_logged: int
    total_days: int

class MealPlanResponse(MealPlanBase):
    id: UUID
    user_id: UUID
    planned_meals: List[PlannedMealResponse] = []
    weekly_nutrition_balance: Optional[WeeklyNutritionBalance] = None
    
    model_config = ConfigDict(from_attributes=True)


# --- Request schemas (used by api/meal_plans.py) ---

class AddPlannedMealRequest(BaseModel):
    """Request body for POST /meal-plan/add."""
    meal_plan_id: str
    meal_id: str
    scheduled_date: str  # YYYY-MM-DD
