from __future__ import annotations

import uuid
from typing import Optional

from fastapi import Depends, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import NotFoundException, TenantException
from app.models.enums import InstitutionType
from app.models.tenant import Tenant
from app.models.user import User
from app.permissions.rbac import get_active_tenant_id, get_current_user, get_current_user_claims


async def registered_institution_type(session: AsyncSession, tenant_id: uuid.UUID) -> InstitutionType:
    institution_type = await session.scalar(
        select(Tenant.institution_type).where(Tenant.id == tenant_id, Tenant.is_deleted.is_(False))
    )
    if institution_type is None:
        raise NotFoundException("Institution not found")
    return institution_type


async def get_registered_institution_type(
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    session: AsyncSession = Depends(get_db),
) -> InstitutionType:
    return await registered_institution_type(session, tenant_id)


def require_institution_type(expected: InstitutionType):
    async def check(institution_type: InstitutionType = Depends(get_registered_institution_type)) -> None:
        if institution_type != expected:
            label = "schools" if expected == InstitutionType.SCHOOL else "colleges"
            raise TenantException(f"This feature is available to registered {label} only.")

    return check


async def get_optional_tenant_id(
    request: Request,
    claims: dict = Depends(get_current_user_claims),
    user: User = Depends(get_current_user),
) -> Optional[uuid.UUID]:
    """Return the active tenant ID if present, else None."""
    if claims.get("tenant_id"):
        return uuid.UUID(str(claims["tenant_id"]))
    return getattr(request.state, "tenant_id", None) if user.is_superadmin else None


async def require_tenant_id(
    tenant_id: Optional[uuid.UUID] = Depends(get_optional_tenant_id),
) -> uuid.UUID:
    """
    Enforce that the request is executed within a validated tenant context.
    Raises TenantException (403) if no tenant context is resolved.
    """
    if not tenant_id:
        raise TenantException(message="Tenant context is required for this operation")
    return tenant_id
