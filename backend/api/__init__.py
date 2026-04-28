"""
API 路由模块导出
"""

from fastapi import APIRouter

from backend.api.chat import router as chat_router
from backend.api.sessions import router as sessions_router
from backend.api.files import router as files_router
from backend.api.tokens import router as tokens_router
from backend.api.config_api import router as config_router
from backend.api.platform import router as platform_router
from backend.api.knowledge import router as knowledge_router


# 主路由
api_router = APIRouter()

# 注册子路由
api_router.include_router(chat_router)
api_router.include_router(sessions_router)
api_router.include_router(files_router)
api_router.include_router(tokens_router)
api_router.include_router(config_router)
api_router.include_router(platform_router)
api_router.include_router(knowledge_router)


__all__ = [
    "api_router",
    "chat_router",
    "sessions_router",
    "files_router",
    "tokens_router",
    "config_router",
    "platform_router",
    "knowledge_router",
]
