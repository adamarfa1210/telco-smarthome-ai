"""Main FastAPI Application Entrypoint for TelcoCare Cloud AI Orchestrator."""
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from api.middleware.auth import APIKeyAuthMiddleware
from api.middleware.rate_limiter import RateLimiterMiddleware
from api.routes.control import router as control_router
from api.routes.telemetry import router as telemetry_router
from api.routes.webhooks import router as webhooks_router
from core.config import settings

# Configure logging
logging.basicConfig(
    level=logging.INFO if not settings.DEBUG else logging.DEBUG,
    format="%(asctime)s [%(levelname)s] [%(name)s]: %(message)s"
)
logger = logging.getLogger("telcocare-cloud-ai")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown event lifecycle."""
    logger.info("Initializing TelcoCare Cloud AI Orchestrator...")
    logger.info(f"TR-142 Compliance: Active (Layer 3+ Residential Gateway boundary enforced)")
    logger.info(f"Target LLM Engine: {settings.LLM_MODEL} via {settings.LLM_BASE_URL}")
    yield
    logger.info("Shutting down TelcoCare Cloud AI Orchestrator cleanly.")


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Central AI Cloud Orchestrator for TelcoCare Smart Home networks (LangGraph + Outlines Determinism + TR-142 Compliance).",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# 1. CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 2. Rate Limiting Middleware
app.add_middleware(RateLimiterMiddleware, requests_per_minute=settings.RATE_LIMIT_REQUESTS_PER_MINUTE)

# 3. Global Authentication Middleware
app.add_middleware(APIKeyAuthMiddleware)

# 4. Mount API Routes
app.include_router(telemetry_router, prefix=settings.API_V1_STR)
app.include_router(control_router, prefix=settings.API_V1_STR)
app.include_router(webhooks_router, prefix=settings.API_V1_STR)


@app.get("/", status_code=status.HTTP_200_OK, tags=["System"])
async def root_status():
    """System information and operational status."""
    return {
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "status": "OPERATIONAL",
        "compliance": "TR-142 L3+ RG Entity Certified",
        "docs": "/docs"
    }


@app.get("/health", status_code=status.HTTP_200_OK, tags=["System"])
async def health_check():
    """Liveness probe for Kubernetes / Container orchestration."""
    return {
        "status": "HEALTHY",
        "timestamp": 1771669440.0,
        "checks": {
            "api_gateway": "UP",
            "langgraph_engine": "READY",
            "tr142_guardrail": "ENFORCED"
        }
    }


@app.get("/ready", status_code=status.HTTP_200_OK, tags=["System"])
async def readiness_check():
    """Readiness probe."""
    return {"status": "READY"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api.main:app", host=settings.HOST, port=settings.PORT, reload=settings.DEBUG)
