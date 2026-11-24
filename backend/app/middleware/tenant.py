from __future__ import annotations

import uuid
from typing import Callable, Optional

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from app.core.logging import get_logger
from app.core.tenant_context import reset_current_tenant_id, set_current_tenant_id

logger = get_logger(__name__)

SUPER_ADMIN_PATHS = {"/api/v1/super-admin", "/api/v1/health"}


class TenantContextMiddleware(BaseHTTPMiddleware):
    """
    Resolves tenant context from:
      1. X-Tenant-ID header (API / development / mobile / testing)
      2. Subdomain: tenant1.app.example.com -> looks up tenant by subdomain

    Sets request.state.tenant_id and updates the thread-safe contextvars
    current_tenant_id so that database sessions and repositories automatically
    bind the query to the active tenant.
    """

    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        if any(request.url.path.startswith(p) for p in SUPER_ADMIN_PATHS):
            request.state.tenant_id = None
            token = set_current_tenant_id(None)
            try:
                return await call_next(request)
            finally:
                reset_current_tenant_id(token)

        tenant_id = await self._resolve_tenant(request)
        request.state.tenant_id = tenant_id
        token = set_current_tenant_id(tenant_id)

        try:
            if tenant_id:
                logger.debug("Tenant resolved", tenant_id=str(tenant_id), path=request.url.path)
            response = await call_next(request)
            return response
        finally:
            reset_current_tenant_id(token)

    async def _resolve_tenant(self, request: Request) -> Optional[uuid.UUID]:
        tenant_header = request.headers.get("X-Tenant-ID")
        if tenant_header:
            try:
                return uuid.UUID(tenant_header)
            except ValueError:
                pass

        host = request.headers.get("host", "")
        subdomain = self._extract_subdomain(host)
        if subdomain and subdomain not in ("www", "app", "api", "localhost", "127"):
            # Lookup can be cached in Redis in Module 0.5
            pass

        return None

    @staticmethod
    def _extract_subdomain(host: str) -> Optional[str]:
        parts = host.split(":")[0].split(".")
        if len(parts) >= 3:
            return parts[0]
        return None
