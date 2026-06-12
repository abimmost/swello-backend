from fastapi import APIRouter, Depends, HTTPException
from typing import Any
from datetime import timedelta, datetime, time as dt_time
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
    """Assign a recipe to a specific day/time, auto-creating the weekly plan if needed."""
    logger.info(
        f"Adding meal {request.meal_id} on {request.scheduled_date} for user {current_user.id}"
    )
    try:
        # 1. Combine scheduled_date and scheduled_time into ISO8601
        date_obj = datetime.strptime(request.scheduled_date, "%Y-%m-%d").date()
        if request.scheduled_time:
            # Shift explicit midnight selections to 00:01 to preserve them from the "no time" guardrail
            if request.scheduled_time == "00:00":
                time_obj = dt_time(0, 1)
            else:
                time_obj = datetime.strptime(request.scheduled_time, "%H:%M").time()
        else:
            time_obj = dt_time(0, 0)
        
        combined_dt = datetime.combine(date_obj, time_obj)
        iso_datetime_str = combined_dt.isoformat() + "Z"

        # Determine week start (Monday) and end (Sunday)
        week_start = date_obj - timedelta(days=date_obj.weekday())
        week_end = week_start + timedelta(days=6)

        # 2. Find existing plan
        plan_check = authed_client.table("meal_plans").select("id").eq(
            "user_id", current_user.id
        ).eq("start_date", str(week_start)).eq("end_date", str(week_end)).execute()

        if plan_check.data:
            meal_plan_id = plan_check.data[0]['id']
        else:
            # 3. Create new plan for this week
            plan_create = authed_client.table("meal_plans").insert({
                "user_id": current_user.id,
                "start_date": str(week_start),
                "end_date": str(week_end)
            }).execute()
            meal_plan_id = plan_create.data[0]['id']

        # 4. Insert into planned_meals
        response = authed_client.table("planned_meals").insert({
            "meal_plan_id": meal_plan_id,
            "meal_id": request.meal_id,
            "scheduled_date": iso_datetime_str,
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

