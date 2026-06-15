from pydantic import BaseModel, ConfigDict, model_validator
from typing import List, Optional, Any
from datetime import date, datetime
from uuid import UUID
from .meals import MealResponse

class PlannedMealBase(BaseModel):
    meal_id: UUID
    status: Optional[str] = 'planned'

class PlannedMealResponse(PlannedMealBase):
    id: UUID
    meal_plan_id: UUID
    scheduled_date: str
    scheduled_time: Optional[str] = None
    meal: Optional[MealResponse] = None

    @model_validator(mode='before')
    @classmethod
    def split_datetime(cls, data: Any) -> Any:
        if isinstance(data, dict) and 'scheduled_date' in data:
            val = data['scheduled_date']
            if val and 'T' in str(val):
                dt_str = str(val)
                parts = dt_str.split('T')
                data['scheduled_date'] = parts[0]
                time_part = parts[1].replace('Z', '').replace('+00:00', '')
                time_str = time_part[:5] if time_part else None
                
                # If time is exactly midnight, assume no time was selected
                if time_str == "00:00":
                    time_str = None
                    
                data['scheduled_time'] = time_str
        return data

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
    meal_id: str
    scheduled_date: str  # YYYY-MM-DD
    scheduled_time: Optional[str] = None  # HH:MM

class UpdatePlannedMealStatusRequest(BaseModel):
    """Request body for PATCH /meal-plan/{plan_id}/status."""
    status: str
