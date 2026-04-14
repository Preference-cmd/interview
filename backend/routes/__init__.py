from __future__ import annotations

from backend.routes.alerts import router as alerts_router
from backend.routes.dashboard import router as dashboard_router
from backend.routes.stores import router as stores_router
from backend.routes.workflows import router as workflows_router

__all__ = [
    "alerts_router",
    "dashboard_router",
    "stores_router",
    "workflows_router",
]
