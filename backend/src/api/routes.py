from fastapi import APIRouter

from src.api.endpoints.availability import router as availability_router
from src.api.endpoints.bookings import router as bookings_router
from src.api.endpoints.buyers import router as buyers_router
from src.api.endpoints.calls import router as calls_router
from src.api.endpoints.graph import insights_router
from src.api.endpoints.graph import router as graph_router
from src.api.endpoints.listings import router as listings_router
from src.api.endpoints.matches import router as matches_router
from src.api.endpoints.onboard import router as onboard_router
from src.api.endpoints.pipeline import router as pipeline_router
from src.api.endpoints.realtor import router as realtor_router
from src.api.endpoints.recall import router as recall_router
from src.api.endpoints.settings import router as settings_router
from src.api.endpoints.token import router as token_router
from src.api.endpoints.users import router as users_router

routers = APIRouter(prefix="/v1")
routers.include_router(users_router)
routers.include_router(token_router)
routers.include_router(onboard_router)
routers.include_router(listings_router)
routers.include_router(realtor_router)
routers.include_router(recall_router)
routers.include_router(buyers_router)
routers.include_router(availability_router)
routers.include_router(bookings_router)
routers.include_router(calls_router)
routers.include_router(matches_router)
routers.include_router(pipeline_router)
routers.include_router(settings_router)
routers.include_router(graph_router)
routers.include_router(insights_router)
