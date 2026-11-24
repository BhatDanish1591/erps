from __future__ import annotations

import time
from contextlib import asynccontextmanager
from typing import AsyncGenerator

try:
    import sentry_sdk
except ImportError:
    sentry_sdk = None
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.config import settings
from app.core.database import engine
from app.core.exceptions import AppException
from app.core.logging import configure_logging, get_logger
from app.core.redis import close_redis
from app.middleware.tenant import TenantContextMiddleware
from app.api.v1.health import router as health_router
from app.api.v1.auth import router as auth_router
from app.api.v1.roles import router as roles_router
from app.api.v1.super_admin import router as super_admin_router
from app.api.v1.institutions import router as institutions_router
from app.api.v1.subscriptions import router as subscriptions_router
from app.api.v1.students import router as students_router
from app.api.v1.teachers import router as teachers_router
from app.api.v1.academics import router as academics_router
from app.api.v1.attendance import router as attendance_router
from app.api.v1.examinations import router as examinations_router
from app.api.v1.results import router as results_router
from app.api.v1.materials import router as materials_router
from app.api.v1.assignments import router as assignments_router
from app.api.v1.timetable import router as timetable_router
from app.api.v1.fees import router as fees_router
from app.api.v1.parents import router as parents_router
from app.api.v1.notifications import router as notifications_router
from app.api.v1.integrations import router as integrations_router
from app.api.v1.library import router as library_router
from app.api.v1.transport import router as transport_router
from app.api.v1.hostel import router as hostel_router
from app.api.v1.reports import router as reports_router

configure_logging()
logger = get_logger(__name__)

if settings.SENTRY_DSN and sentry_sdk:
    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        environment=settings.ENVIRONMENT,
        traces_sample_rate=0.1 if settings.is_production else 1.0,
    )


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    logger.info(
        "EduSaaS CRM starting up",
        version=settings.APP_VERSION,
        environment=settings.ENVIRONMENT,
    )
    yield
    logger.info("EduSaaS CRM shutting down")
    await engine.dispose()
    await close_redis()


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description="Multi-Tenant School & College Management SaaS CRM",
        docs_url="/docs" if not settings.is_production else None,
        redoc_url="/redoc" if not settings.is_production else None,
        openapi_url="/openapi.json" if not settings.is_production else None,
        lifespan=lifespan,
    )

    _register_middleware(app)
    _register_exception_handlers(app)
    _register_routers(app)

    return app


def _register_middleware(app: FastAPI) -> None:
    if settings.is_production:
        app.add_middleware(
            TrustedHostMiddleware,
            allowed_hosts=settings.get_allowed_hosts(),
        )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.get_allowed_origins(),
        allow_origin_regex=r"^https?://.*" if not settings.is_production else None,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID", "X-Total-Count"],
    )

    app.add_middleware(TenantContextMiddleware)

    @app.middleware("http")
    async def add_process_time_header(request: Request, call_next):
        start = time.perf_counter()
        response = await call_next(request)
        duration = time.perf_counter() - start
        response.headers["X-Process-Time"] = f"{duration:.4f}s"
        return response


def _register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppException)
    async def app_exception_handler(request: Request, exc: AppException):
        logger.warning(
            "Application error",
            error_code=exc.error_code,
            message=exc.message,
            path=request.url.path,
        )
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "success": False,
                "error": {
                    "code": exc.error_code,
                    "message": exc.message,
                    "details": exc.details,
                },
            },
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        details = [
            {"field": " > ".join(str(loc) for loc in e["loc"]), "message": e["msg"]}
            for e in exc.errors()
        ]
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "success": False,
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": "Request validation failed",
                    "details": details,
                },
            },
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "success": False,
                "error": {
                    "code": "HTTP_ERROR",
                    "message": exc.detail,
                    "details": [],
                },
            },
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        logger.error("Unhandled exception", exc_info=exc, path=request.url.path)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "success": False,
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": "An unexpected error occurred",
                    "details": [],
                },
            },
        )


def _register_routers(app: FastAPI) -> None:
    @app.get("/", tags=["Root"])
    async def root():
        return {
            "name": settings.APP_NAME,
            "version": settings.APP_VERSION,
            "environment": settings.ENVIRONMENT,
            "status": "online",
            "docs": "/docs",
            "api_v1": "/api/v1",
            "health": "/api/v1/health",
        }

    @app.get("/health", tags=["Root"])
    async def root_health():
        return {
            "status": "healthy",
            "version": settings.APP_VERSION,
        }

    API_V1_PREFIX = "/api/v1"
    app.include_router(health_router, prefix=API_V1_PREFIX)
    app.include_router(auth_router, prefix=API_V1_PREFIX)
    app.include_router(roles_router, prefix=API_V1_PREFIX)
    app.include_router(super_admin_router, prefix=API_V1_PREFIX)
    app.include_router(institutions_router, prefix=API_V1_PREFIX)
    app.include_router(subscriptions_router, prefix=API_V1_PREFIX)
    app.include_router(students_router, prefix=API_V1_PREFIX)
    app.include_router(teachers_router, prefix=API_V1_PREFIX)
    app.include_router(academics_router, prefix=API_V1_PREFIX)
    app.include_router(attendance_router, prefix=API_V1_PREFIX)
    app.include_router(examinations_router, prefix=API_V1_PREFIX)
    app.include_router(results_router, prefix=API_V1_PREFIX)
    app.include_router(materials_router, prefix=API_V1_PREFIX)
    app.include_router(assignments_router, prefix=API_V1_PREFIX)
    app.include_router(timetable_router, prefix=API_V1_PREFIX)
    app.include_router(fees_router, prefix=API_V1_PREFIX)
    app.include_router(parents_router, prefix=API_V1_PREFIX)
    app.include_router(notifications_router, prefix=API_V1_PREFIX)
    app.include_router(integrations_router, prefix=API_V1_PREFIX)
    app.include_router(library_router, prefix=API_V1_PREFIX)
    app.include_router(transport_router, prefix=API_V1_PREFIX)
    app.include_router(hostel_router, prefix=API_V1_PREFIX)
    app.include_router(reports_router, prefix=API_V1_PREFIX)


app = create_app()
