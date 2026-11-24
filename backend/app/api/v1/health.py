from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict

from fastapi import APIRouter, Response, status

from app.core.config import settings
from app.core.database import check_db_connection, check_tenant_isolation
from app.core.redis import check_redis_connection
from app.schemas.common import SuccessResponse

router = APIRouter(prefix="/health", tags=["Health"])


@router.get("", response_model=SuccessResponse[Dict])
async def health_check() -> SuccessResponse[Dict]:
    """Basic health check - always returns 200 if the app process is running."""
    return SuccessResponse(
        data={
            "status": "healthy",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "version": settings.APP_VERSION,
            "environment": settings.ENVIRONMENT,
        }
    )


@router.get("/detailed", response_model=SuccessResponse[Dict])
async def detailed_health_check() -> SuccessResponse[Dict]:
    """Detailed health check - verifies database and Redis connectivity."""
    db_ok = await check_db_connection()
    redis_ok = await check_redis_connection()

    all_healthy = db_ok and redis_ok
    status = "healthy" if all_healthy else "degraded"

    return SuccessResponse(
        data={
            "status": status,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "version": settings.APP_VERSION,
            "environment": settings.ENVIRONMENT,
            "dependencies": {
                "database": "ok" if db_ok else "error",
                "redis": "ok" if redis_ok else "error",
            },
        }
    )


@router.get("/ready", response_model=SuccessResponse[Dict])
async def readiness_check(response: Response) -> SuccessResponse[Dict]:
    database_ok = await check_db_connection()
    redis_ok = await check_redis_connection()
    isolation_ok = not settings.is_production or (
        database_ok and await check_tenant_isolation()
    )
    ready = database_ok and redis_ok and isolation_ok
    if not ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return SuccessResponse(
        success=ready,
        data={
            "status": "ready" if ready else "degraded",
            "dependencies": {
                "database": "ok" if database_ok else "error",
                "redis": "ok" if redis_ok else "error",
                "tenant_isolation": "ok" if isolation_ok else "error",
            },
        },
    )
