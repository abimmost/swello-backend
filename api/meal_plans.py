from fastapi import APIRouter, Depends, HTTPException
from typing import Any
from supabase import Client
from core.supabase import supabase
from core.auth import get_current_user, get_authed_client
from models.meal_plans import AddPlannedMealRequest
from services.nutrition import calculate_balanced_level_score, aggregate_weekly_nutrition
from utils.logger import setup_logger

logger = setup_logger(__name__)
router = APIRouter(prefix="/meal-plan", tags=["meal-plan"])



@router.get("")
async def get_meal_plan(start_date: str, end_date: str, current_user: Any = Depends(get_current_user)):
    """
    Fetch the user's meal plan for a specific date range.
    Returns both the daily meal schedule AND an aggregated weekly_nutrition_balance
    so the frontend Plan.tsx "Week at a Glance" card doesn't have to calculate it client-side.
    """
    logger.info(f"Fetching meal plan for user {current_user.id} from {start_date} to {end_date}")
    try:
        plan_response = supabase.table("meal_plans").select(
            "*, planned_meals(*, meals(*, nutrient_profiles(*)))"
        ).eq("user_id", current_user.id).gte("start_date", start_date).lte("end_date", end_date).execute()

        data = plan_response.data

        # Calculate real weekly nutrition aggregation
        weekly_balance = aggregate_weekly_nutrition(data)

        logger.info(f"Meal plan fetched: {len(data)} plans, weekly score: {weekly_balance['score']}")
        return {
            "plans": data,
            "weekly_nutrition_balance": weekly_balance
        }
    except Exception as e:
        logger.error(f"Error fetching meal plan: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/add")
async def add_to_meal_plan(
    request: AddPlannedMealRequest,
    current_user: Any = Depends(get_current_user),
    authed_client: Client = Depends(get_authed_client)
):
    """Assign a recipe to a specific day in the plan."""
    logger.info(
        f"Adding meal {request.meal_id} to plan {request.meal_plan_id} "
        f"on {request.scheduled_date} for user {current_user.id}"
    )
    try:
        # Verify the plan belongs to the user (read — global client is fine)
        plan_check = supabase.table("meal_plans").select("id").eq(
            "id", request.meal_plan_id
        ).eq("user_id", current_user.id).single().execute()

        if not plan_check.data:
            logger.warning(f"Plan {request.meal_plan_id} not found for user {current_user.id}")
            raise HTTPException(status_code=404, detail="Meal plan not found")

        # Write using authed_client so RLS sees the user
        response = authed_client.table("planned_meals").insert({
            "meal_plan_id": request.meal_plan_id,
            "meal_id": request.meal_id,
            "scheduled_date": request.scheduled_date,
            "status": "planned"
        }).execute()

        logger.info(f"Meal added to plan successfully.")
        return {"status": "success", "data": response.data}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error adding meal to plan: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.delete("/{plan_id}")
async def remove_from_meal_plan(
    plan_id: str,
    current_user: Any = Depends(get_current_user),
    authed_client: Client = Depends(get_authed_client)
):
    """Remove a planned meal from the schedule."""
    logger.info(f"Removing planned meal {plan_id} for user {current_user.id}")
    try:
        # Use authed_client so RLS enforces ownership
        response = authed_client.table("planned_meals").delete().eq("id", plan_id).execute()
        logger.info(f"Planned meal {plan_id} removed successfully.")
        return {"status": "success", "message": "Planned meal removed"}
    except Exception as e:
        logger.error(f"Error removing planned meal: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

