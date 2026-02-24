from fastapi import APIRouter
from app.api.v1.endpoints import updates, authorities, login, users, chat, notifications, gamification

api_router = APIRouter()
api_router.include_router(login.router, tags=["login"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(updates.router, prefix="/updates", tags=["updates"])
api_router.include_router(authorities.router, prefix="/authorities", tags=["authorities"])
api_router.include_router(chat.router, prefix="/ai", tags=["ai"])
api_router.include_router(notifications.router, prefix="/notifications", tags=["notifications"])
api_router.include_router(gamification.router, prefix="/gamification", tags=["gamification"])
