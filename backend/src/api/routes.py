from fastapi import APIRouter

from src.api.endpoints.listings import router as listings_router
from src.api.endpoints.onboard import router as onboard_router
from src.api.endpoints.recall import router as recall_router
from src.api.endpoints.token import router as token_router
from src.api.endpoints.users import router as users_router

routers = APIRouter(prefix="/v1")
routers.include_router(users_router)
routers.include_router(token_router)
routers.include_router(onboard_router)
routers.include_router(listings_router)
routers.include_router(recall_router)
