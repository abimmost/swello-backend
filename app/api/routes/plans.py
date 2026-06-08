from fastapi import APIRouter

router = APIRouter()

@router.get("/")
async def get_plans():
    return {"message": "List of meal plans"}
