from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from utils.logger import setup_logger

logger = setup_logger(__name__)

from contextlib import asynccontextmanager
from core.config import get_settings

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Swello Backend starting up...")
    
    settings = get_settings()
    ngrok_tunnel = None
    
    if settings.ngrok_authtoken:
        try:
            from pyngrok import ngrok
            ngrok.set_auth_token(settings.ngrok_authtoken)
            ngrok_tunnel = ngrok.connect(8000, domain="marisela-falsifiable-ridiculously.ngrok-free.dev")
            logger.info(f"🚀 ngrok tunnel created: {ngrok_tunnel.public_url}")
            logger.info(f"👉 Public API Docs available at: {ngrok_tunnel.public_url}/docs")
        except Exception as e:
            logger.error(f"Failed to start ngrok: {e}")

    yield
    
    if ngrok_tunnel:
        try:
            from pyngrok import ngrok
            logger.info("Closing ngrok tunnel...")
            ngrok.disconnect(ngrok_tunnel.public_url)
            ngrok.kill()
        except:
            pass

app = FastAPI(
    title="Swello Backend API",
    description="Backend for the Cameroonian Nutritional & Meal Planning App",
    version="1.0.0",
    lifespan=lifespan
)

# CORS configuration
settings_global = get_settings()
origins = [origin.strip() for origin in settings_global.cors_origins.split(",")] if settings_global.cors_origins else []

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from api import users_router, recipes_router, meal_plans_router, ai_router, ingredients_router

app.include_router(users_router)
app.include_router(recipes_router)
app.include_router(meal_plans_router)
app.include_router(ai_router)
app.include_router(ingredients_router)

@app.get("/health")
def health_check():
    logger.info("Health check endpoint called")
    return {"status": "ok", "message": "Swello API is running"}
