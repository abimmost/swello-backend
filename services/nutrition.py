"""
Balanced Level Score Algorithm

Calculates a custom 0-100 score representing how nutritionally balanced a meal is.
This is a first-class concept in Swello — not a standard nutritional index.

The algorithm evaluates how closely a meal's macronutrient distribution matches
an ideal balance, with penalties for extreme imbalances and bonuses for
micronutrient diversity.
"""
from utils.logger import setup_logger

logger = setup_logger(__name__)

# Named constants — no magic numbers (per GEMINI.md §7)
IDEAL_PROTEIN_PERCENTAGE = 25.0
IDEAL_CARB_PERCENTAGE = 50.0
IDEAL_FAT_PERCENTAGE = 25.0

# Maximum deviation allowed before score drops to 0 for that macro
MAX_DEVIATION = 40.0

# Weights for each macro and micronutrient diversity in the overall BLS
PROTEIN_WEIGHT = 0.38
CARB_WEIGHT = 0.35
FAT_WEIGHT = 0.22
MICRONUTRIENT_WEIGHT = 0.05

# Micronutrient thresholds for "present" (non-zero contribution)
MICRO_FIELDS = [
    "fiber_g", "iron_mg", "vitamin_c_mg", "vitamin_a_iu",
    "calcium_mg", "potassium_mg"
]
MAX_MICRO_BONUS_POINTS = 100  # Perfect micronutrient diversity score


def calculate_balanced_level_score(nutrient_data: dict) -> int:
    """
    Calculates the Balanced Level Score (0-100) for a meal.

    Args:
        nutrient_data: A dict with keys like protein_grams, carb_grams, fat_grams,
                       and optional micronutrient fields.

    Returns:
        An integer score from 0 to 100.
    """
    logger.debug(f"Calculating BLS for nutrient data: {nutrient_data}")

    protein_g = nutrient_data.get("protein_grams", 0) or 0
    carb_g = nutrient_data.get("carb_grams", 0) or 0
    fat_g = nutrient_data.get("fat_grams", 0) or 0

    total_g = protein_g + carb_g + fat_g

    if total_g == 0:
        logger.warning("Total macronutrients are zero. Returning score 0.")
        return 0

    # Calculate actual percentages
    actual_protein_pct = (protein_g / total_g) * 100
    actual_carb_pct = (carb_g / total_g) * 100
    actual_fat_pct = (fat_g / total_g) * 100

    logger.debug(
        f"Macro percentages — Protein: {actual_protein_pct:.1f}%, "
        f"Carbs: {actual_carb_pct:.1f}%, Fat: {actual_fat_pct:.1f}%"
    )

    # Score each macro based on deviation from ideal
    protein_score = _deviation_score(actual_protein_pct, IDEAL_PROTEIN_PERCENTAGE)
    carb_score = _deviation_score(actual_carb_pct, IDEAL_CARB_PERCENTAGE)
    fat_score = _deviation_score(actual_fat_pct, IDEAL_FAT_PERCENTAGE)

    # Micronutrient diversity bonus
    micro_score = _micronutrient_diversity_score(nutrient_data)

    # Weighted combination
    final_score = (
        protein_score * PROTEIN_WEIGHT +
        carb_score * CARB_WEIGHT +
        fat_score * FAT_WEIGHT +
        micro_score * MICRONUTRIENT_WEIGHT
    )

    # Clamp to 0-100
    result = max(0, min(100, round(final_score)))
    logger.info(f"Balanced Level Score calculated: {result}/100")
    return result


def _deviation_score(actual: float, ideal: float) -> float:
    """
    Scores a single macronutrient based on its deviation from the ideal.
    Returns a value from 0 to 100.
    """
    deviation = abs(actual - ideal)
    if deviation >= MAX_DEVIATION:
        return 0.0
    return ((MAX_DEVIATION - deviation) / MAX_DEVIATION) * 100


def _micronutrient_diversity_score(nutrient_data: dict) -> float:
    """
    Scores how many different micronutrients are present (non-zero).
    More diversity = higher score.
    """
    present_count = 0
    for field in MICRO_FIELDS:
        value = nutrient_data.get(field, 0) or 0
        if value > 0:
            present_count += 1

    if len(MICRO_FIELDS) == 0:
        return 0.0

    score = (present_count / len(MICRO_FIELDS)) * MAX_MICRO_BONUS_POINTS
    logger.debug(f"Micronutrient diversity: {present_count}/{len(MICRO_FIELDS)} present, score: {score:.1f}")
    return score


def aggregate_weekly_nutrition(plans_data: list) -> dict:
    """
    Aggregates nutrient profiles across all planned meals in a set of plans
    to produce a weekly nutrition balance summary for the frontend.
    Called by api/meal_plans.py — lives here to keep business logic out of routers.
    """
    total_protein = 0.0
    total_carbs = 0.0
    total_fat = 0.0
    days_with_meals = set()

    if not plans_data:
        return {
            "score": 0,
            "protein_percentage": 0,
            "carb_percentage": 0,
            "fat_percentage": 0,
            "days_logged": 0,
            "total_days": 7
        }

    for plan in plans_data:
        for planned_meal in plan.get("planned_meals", []):
            meal = planned_meal.get("meals", {})
            nutrient_profile = meal.get("nutrient_profiles", {}) or {}

            total_protein += nutrient_profile.get("protein_grams", 0) or 0
            total_carbs += nutrient_profile.get("carb_grams", 0) or 0
            total_fat += nutrient_profile.get("fat_grams", 0) or 0

            scheduled_date = planned_meal.get("scheduled_date")
            if scheduled_date:
                days_with_meals.add(scheduled_date)

    total_macros = total_protein + total_carbs + total_fat

    if total_macros == 0:
        return {
            "score": 0,
            "protein_percentage": 0,
            "carb_percentage": 0,
            "fat_percentage": 0,
            "days_logged": len(days_with_meals),
            "total_days": 7
        }

    protein_pct = round((total_protein / total_macros) * 100, 1)
    carb_pct = round((total_carbs / total_macros) * 100, 1)
    fat_pct = round((total_fat / total_macros) * 100, 1)

    weekly_score = calculate_balanced_level_score({
        "protein_grams": total_protein,
        "carb_grams": total_carbs,
        "fat_grams": total_fat,
    })

    logger.debug(
        f"Weekly aggregation: P={protein_pct}%, C={carb_pct}%, F={fat_pct}%, "
        f"Score={weekly_score}, Days={len(days_with_meals)}/7"
    )

    return {
        "score": weekly_score,
        "protein_percentage": protein_pct,
        "carb_percentage": carb_pct,
        "fat_percentage": fat_pct,
        "days_logged": len(days_with_meals),
        "total_days": 7
    }
