"""API Routes Package."""
from api.routes.control import router as control_router
from api.routes.telemetry import router as telemetry_router
from api.routes.webhooks import router as webhooks_router

__all__ = ["telemetry_router", "control_router", "webhooks_router"]
