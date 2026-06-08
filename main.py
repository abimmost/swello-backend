from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from utils.logger import setup_logger

logger = setup_logger(__name__)

from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Swello Backend starting up...")
    yield

app = FastAPI(
    title="Swello Backend API",
    description="Backend for the Cameroonian Nutritional & Meal Planning App",
    version="1.0.0",
    lifespan=lifespan
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # For development, allow all origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from api import users_router, recipes_router, meal_plans_router, ai_router, auth_router

app.include_router(users_router)
app.include_router(recipes_router)
app.include_router(meal_plans_router)
app.include_router(ai_router)
app.include_router(auth_router)

@app.get("/health")
def health_check():
    logger.info("Health check endpoint called")
    return {"status": "ok", "message": "Swello API is running"}
