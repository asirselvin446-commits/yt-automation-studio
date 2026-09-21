from fastapi import APIRouter
from app.api.v1.system import router as system_router
from app.api.v1.videos import router as videos_router
from app.api.v1.youtube import router as youtube_router
from app.api.v1.analytics import router as analytics_router
from app.api.v1.brain import router as brain_router
from app.api.v1.ideas import router as ideas_router
from app.api.v1.calendar import router as calendar_router
from app.api.v1.monetization import router as monetization_router
from app.api.v1.automation import router as automation_router
from app.api.v1.settings import router as settings_router
from app.api.v1.uploads import router as uploads_router
from app.api.v1.autosource import router as autosource_router
from app.api.v1.accounts import router as accounts_router

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(system_router)
api_router.include_router(videos_router)
api_router.include_router(youtube_router)
api_router.include_router(analytics_router)
api_router.include_router(brain_router)
api_router.include_router(ideas_router)
api_router.include_router(calendar_router)
api_router.include_router(monetization_router)
api_router.include_router(automation_router)
api_router.include_router(settings_router)
api_router.include_router(uploads_router)
api_router.include_router(autosource_router)
api_router.include_router(accounts_router)
