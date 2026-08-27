from app.api.routes.analytics import router as analytics_router
from app.api.routes.api_keys import router as api_keys_router
from app.api.routes.auth import router as auth_router
from app.api.routes.chat import router as chat_router
from app.api.routes.logs import router as logs_router
from app.api.routes.models import router as models_router
from app.api.routes.providers import router as providers_router
from app.api.routes.routing import router as routing_router

__all__ = [
    "auth_router",
    "providers_router",
    "models_router",
    "chat_router",
    "api_keys_router",
    "logs_router",
    "analytics_router",
    "routing_router",
]
