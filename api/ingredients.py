from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from core.supabase import supabase
from utils.logger import setup_logger

logger = setup_logger(__name__)
router = APIRouter(prefix="/ingredients", tags=["ingredients"])


@router.get("")
async def search_ingredients(q: Optional[str] = None, limit: int = Query(20, ge=1, le=100)):
    """
    Fetch a list of ingredients for the live search/autocomplete frontend component.
    Optionally filters by name if `q` is provided.
    """
    logger.info(f"Searching ingredients - q: {q}, limit: {limit}")
    try:
        query = supabase.table("ingredients").select("id, name, category")
        if q:
            query = query.ilike("name", f"%{q}%")
        
        # Order alphabetically and limit results for performance
        response = query.order("name").limit(limit).execute()
        return response.data
    except Exception as e:
        logger.error(f"Error fetching ingredients: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
