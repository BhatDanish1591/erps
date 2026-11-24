from __future__ import annotations

import uuid
from typing import List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictException, NotFoundException, ValidationException
from app.models.auth import Role
from app.models.enums import RoleScope
from app.repositories.role import RoleRepository
from app.schemas.role import CreateRoleRequest, PermissionResponse, RoleResponse, UpdateRoleRequest


class RoleService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.role_repo = RoleRepository(db)

    async def list_permissions(self) -> List[PermissionResponse]:
        perms = await self.role_repo.list_permissions()
        return [
            PermissionResponse(
                id=p.id,
                code=p.code,
                module=p.module,
                description=p.description,
            )
            for p in perms
        ]

    async def list_roles(self, tenant_id: Optional[uuid.UUID] = None) -> List[RoleResponse]:
        roles = await self.role_repo.list_available_roles(tenant_id=tenant_id)
        return [self._format_role(r) for r in roles]

    async def get_role(self, role_id: uuid.UUID) -> RoleResponse:
        role = await self.role_repo.get_role_with_permissions(role_id)
        if not role:
            raise NotFoundException(message="Role not found")
        return self._format_role(role)

    async def create_custom_role(
        self, req: CreateRoleRequest, tenant_id: uuid.UUID
    ) -> RoleResponse:
        existing = await self.role_repo.get_by_code(req.code, tenant_id=tenant_id)
        if existing and existing.tenant_id == tenant_id:
            raise ConflictException(message=f"Role code '{req.code}' already exists in this institution")

        role = await self.role_repo.create(
            name=req.name,
            code=req.code,
            tenant_id=tenant_id,
            scope=RoleScope.TENANT,
            description=req.description,
            is_system_role=False,
        )

        if req.permission_codes:
            perms = await self.role_repo.get_permissions_by_codes(req.permission_codes)
            await self.role_repo.set_role_permissions(
                role.id, [p.id for p in perms]
            )

        refreshed = await self.role_repo.get_role_with_permissions(role.id)
        return self._format_role(refreshed or role)

    async def update_role(
        self, role_id: uuid.UUID, req: UpdateRoleRequest, tenant_id: Optional[uuid.UUID] = None
    ) -> RoleResponse:
        role = await self.role_repo.get_role_with_permissions(role_id)
        if not role:
            raise NotFoundException(message="Role not found")

        if role.is_system_role:
            raise ValidationException(message="System template roles cannot be modified directly")

        if tenant_id and role.tenant_id != tenant_id:
            raise NotFoundException(message="Role not found in this institution")

        if req.name is not None:
            role.name = req.name
        if req.description is not None:
            role.description = req.description

        if req.permission_codes is not None:
            perms = await self.role_repo.get_permissions_by_codes(req.permission_codes)
            await self.role_repo.set_role_permissions(
                role.id, [p.id for p in perms]
            )

        await self.db.flush()
        refreshed = await self.role_repo.get_role_with_permissions(role.id)
        return self._format_role(refreshed or role)

    @staticmethod
    def _format_role(role: Role) -> RoleResponse:
        perms = [rp.permission.code for rp in (role.role_permissions or [])]
        return RoleResponse(
            id=role.id,
            tenant_id=role.tenant_id,
            name=role.name,
            code=role.code,
            scope=role.scope,
            description=role.description,
            is_system_role=role.is_system_role,
            permissions=perms,
        )
