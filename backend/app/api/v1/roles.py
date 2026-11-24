from __future__ import annotations

import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.dependencies.tenant import get_optional_tenant_id, require_tenant_id
from app.permissions.rbac import get_current_user, require_permission
from app.models.user import User
from app.schemas.common import SuccessResponse
from app.schemas.role import CreateRoleRequest, PermissionResponse, RoleResponse, UpdateRoleRequest
from app.services.role_service import RoleService

router = APIRouter(prefix="/roles", tags=["Roles & Permissions"])


@router.get("/permissions", response_model=SuccessResponse[List[PermissionResponse]])
async def list_permissions(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SuccessResponse[List[PermissionResponse]]:
    """List all available granular system permissions."""
    service = RoleService(db)
    perms = await service.list_permissions()
    return SuccessResponse(data=perms)


@router.get("", response_model=SuccessResponse[List[RoleResponse]])
async def list_roles(
    tenant_id: Optional[uuid.UUID] = Depends(get_optional_tenant_id),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SuccessResponse[List[RoleResponse]]:
    """List standard roles and custom roles available for the current tenant."""
    service = RoleService(db)
    roles = await service.list_roles(tenant_id=tenant_id)
    return SuccessResponse(data=roles)


@router.get("/{role_id}", response_model=SuccessResponse[RoleResponse])
async def get_role(
    role_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SuccessResponse[RoleResponse]:
    """Retrieve role details and mapped permissions."""
    service = RoleService(db)
    role = await service.get_role(role_id)
    return SuccessResponse(data=role)


@router.post(
    "",
    response_model=SuccessResponse[RoleResponse],
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("users:manage_roles"))],
)
async def create_custom_role(
    req: CreateRoleRequest,
    tenant_id: uuid.UUID = Depends(require_tenant_id),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SuccessResponse[RoleResponse]:
    """Create a new custom tenant role with specified permission keys."""
    service = RoleService(db)
    role = await service.create_custom_role(req, tenant_id=tenant_id)
    return SuccessResponse(data=role, message="Custom role created successfully")


@router.put(
    "/{role_id}",
    response_model=SuccessResponse[RoleResponse],
    dependencies=[Depends(require_permission("users:manage_roles"))],
)
async def update_custom_role(
    role_id: uuid.UUID,
    req: UpdateRoleRequest,
    tenant_id: uuid.UUID = Depends(require_tenant_id),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SuccessResponse[RoleResponse]:
    """Update permissions or details of an existing custom tenant role."""
    service = RoleService(db)
    role = await service.update_role(role_id, req, tenant_id=tenant_id)
    return SuccessResponse(data=role, message="Role updated successfully")
