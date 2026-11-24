from __future__ import annotations

import uuid
from typing import List, Optional, Sequence

from sqlalchemy import delete, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.auth import Permission, Role, RolePermission
from app.models.enums import RoleScope
from app.repositories.base import BaseRepository


class RoleRepository(BaseRepository[Role]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(Role, session)

    async def get_by_code(
        self, code: str, tenant_id: Optional[uuid.UUID] = None
    ) -> Optional[Role]:
        """
        Fetch role by code. Prioritizes tenant-custom role, then platform/system role.
        """
        stmt = (
            select(Role)
            .where(
                Role.code == code,
                or_(Role.tenant_id == tenant_id, Role.tenant_id.is_(None)),
            )
            .options(
                selectinload(Role.role_permissions).selectinload(RolePermission.permission)
            )
            .order_by(Role.tenant_id.desc().nullslast())
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def list_available_roles(
        self, tenant_id: Optional[uuid.UUID] = None
    ) -> Sequence[Role]:
        """
        List roles visible to the tenant (system templates + custom tenant roles).
        """
        stmt = (
            select(Role)
            .where(or_(Role.tenant_id == tenant_id, Role.tenant_id.is_(None)))
            .options(
                selectinload(Role.role_permissions).selectinload(RolePermission.permission)
            )
            .order_by(Role.name)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_role_with_permissions(self, role_id: uuid.UUID) -> Optional[Role]:
        stmt = (
            select(Role)
            .where(Role.id == role_id)
            .options(
                selectinload(Role.role_permissions).selectinload(RolePermission.permission)
            )
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def list_permissions(self) -> Sequence[Permission]:
        stmt = select(Permission).order_by(Permission.module, Permission.code)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_permissions_by_codes(
        self, codes: List[str]
    ) -> Sequence[Permission]:
        stmt = select(Permission).where(Permission.code.in_(codes))
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def set_role_permissions(
        self, role_id: uuid.UUID, permission_ids: List[uuid.UUID]
    ) -> None:
        # Clear existing
        await self.session.execute(
            delete(RolePermission).where(RolePermission.role_id == role_id)
        )
        # Re-assign
        for pid in permission_ids:
            rp = RolePermission(role_id=role_id, permission_id=pid)
            self.session.add(rp)
        await self.session.flush()
