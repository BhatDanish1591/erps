from __future__ import annotations

import uuid
from typing import Optional, Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tenant import Tenant, TenantDomain, TenantSetting
from app.repositories.base import BaseRepository, TenantBaseRepository


class TenantRepository(BaseRepository[Tenant]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(Tenant, session)

    async def get_by_slug(self, slug: str) -> Optional[Tenant]:
        stmt = select(Tenant).where(
            Tenant.slug == slug,
            Tenant.is_deleted.is_(False),
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()


class TenantDomainRepository(BaseRepository[TenantDomain]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(TenantDomain, session)

    async def get_by_domain(self, domain: str) -> Optional[TenantDomain]:
        stmt = select(TenantDomain).where(TenantDomain.domain == domain)
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def list_by_tenant(self, tenant_id: uuid.UUID) -> Sequence[TenantDomain]:
        stmt = select(TenantDomain).where(TenantDomain.tenant_id == tenant_id)
        result = await self.session.execute(stmt)
        return result.scalars().all()


class TenantSettingRepository(TenantBaseRepository[TenantSetting]):
    def __init__(self, session: AsyncSession, tenant_id: Optional[uuid.UUID] = None) -> None:
        super().__init__(TenantSetting, session, tenant_id)

    async def get_by_key(self, key: str) -> Optional[TenantSetting]:
        stmt = select(TenantSetting).where(
            TenantSetting.tenant_id == self.tenant_id,
            TenantSetting.key == key,
            TenantSetting.is_deleted.is_(False),
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()
