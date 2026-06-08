from fastapi import APIRouter, Depends
# from app.api.dependencies import get_db

router = APIRouter()

@router.get("/")
async def get_meals():
    return {"message": "List of meals"}
