from __future__ import annotations

import uuid
from typing import Any, Generic, List, Optional, Sequence, Type, TypeVar

from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundException
from app.core.tenant_context import get_current_tenant_id
from app.models.base import BaseModel, TenantBaseModel

ModelT = TypeVar("ModelT", bound=BaseModel)
TenantModelT = TypeVar("TenantModelT", bound=TenantBaseModel)


class BaseRepository(Generic[ModelT]):
    """
    Generic repository for non-tenant or platform-level entities (e.g. Tenant, User, Plan).
    """

    def __init__(self, model: Type[ModelT], session: AsyncSession) -> None:
        self.model = model
        self.session = session

    async def get_by_id(self, id: uuid.UUID) -> Optional[ModelT]:
        stmt = select(self.model).where(self.model.id == id)
        if hasattr(self.model, "is_deleted"):
            stmt = stmt.where(self.model.is_deleted.is_(False))
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def list(
        self,
        *,
        skip: int = 0,
        limit: int = 100,
        filters: Optional[dict[str, Any]] = None,
    ) -> Sequence[ModelT]:
        stmt = select(self.model)
        if hasattr(self.model, "is_deleted"):
            stmt = stmt.where(self.model.is_deleted.is_(False))
        if filters:
            for key, val in filters.items():
                if hasattr(self.model, key) and val is not None:
                    stmt = stmt.where(getattr(self.model, key) == val)
        stmt = stmt.offset(skip).limit(limit)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def count(self, filters: Optional[dict[str, Any]] = None) -> int:
        stmt = select(func.count(self.model.id))
        if hasattr(self.model, "is_deleted"):
            stmt = stmt.where(self.model.is_deleted.is_(False))
        if filters:
            for key, val in filters.items():
                if hasattr(self.model, key) and val is not None:
                    stmt = stmt.where(getattr(self.model, key) == val)
        result = await self.session.execute(stmt)
        return result.scalar_one()

    async def create(self, **kwargs: Any) -> ModelT:
        instance = self.model(**kwargs)
        self.session.add(instance)
        await self.session.flush()
        await self.session.refresh(instance)
        return instance

    async def update(self, id: uuid.UUID, **kwargs: Any) -> Optional[ModelT]:
        instance = await self.get_by_id(id)
        if not instance:
            return None
        for key, val in kwargs.items():
            if hasattr(instance, key):
                setattr(instance, key, val)
        await self.session.flush()
        await self.session.refresh(instance)
        return instance

    async def soft_delete(self, id: uuid.UUID) -> bool:
        instance = await self.get_by_id(id)
        if not instance:
            return False
        if hasattr(instance, "is_deleted"):
            instance.is_deleted = True
            await self.session.flush()
            return True
        await self.session.delete(instance)
        await self.session.flush()
        return True


class TenantBaseRepository(Generic[TenantModelT]):
    """
    Tenant-aware repository for all institution-scoped models.
    Enforces tenant isolation by always injecting tenant_id into SELECT,
    UPDATE, and DELETE statements.
    """

    def __init__(
        self,
        model: Type[TenantModelT],
        session: AsyncSession,
        tenant_id: Optional[uuid.UUID] = None,
    ) -> None:
        self.model = model
        self.session = session
        self._explicit_tenant_id = tenant_id

    @property
    def tenant_id(self) -> uuid.UUID:
        tid = self._explicit_tenant_id or get_current_tenant_id()
        if not tid:
            raise ValueError(f"Tenant ID is required for operations on {self.model.__name__}")
        return tid

    async def get_by_id(self, id: uuid.UUID) -> Optional[TenantModelT]:
        """Fetch a record by ID strictly within the current tenant context."""
        stmt = select(self.model).where(
            self.model.id == id,
            self.model.tenant_id == self.tenant_id,
            self.model.is_deleted.is_(False),
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def list(
        self,
        *,
        skip: int = 0,
        limit: int = 100,
        filters: Optional[dict[str, Any]] = None,
    ) -> Sequence[TenantModelT]:
        """List records strictly bounded by the current tenant ID."""
        stmt = select(self.model).where(
            self.model.tenant_id == self.tenant_id,
            self.model.is_deleted.is_(False),
        )
        if filters:
            for key, val in filters.items():
                if hasattr(self.model, key) and val is not None:
                    stmt = stmt.where(getattr(self.model, key) == val)
        stmt = stmt.offset(skip).limit(limit)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def count(self, filters: Optional[dict[str, Any]] = None) -> int:
        stmt = select(func.count(self.model.id)).where(
            self.model.tenant_id == self.tenant_id,
            self.model.is_deleted.is_(False),
        )
        if filters:
            for key, val in filters.items():
                if hasattr(self.model, key) and val is not None:
                    stmt = stmt.where(getattr(self.model, key) == val)
        result = await self.session.execute(stmt)
        return result.scalar_one()

    async def create(self, **kwargs: Any) -> TenantModelT:
        """Create a record, guaranteeing tenant_id is set to the authenticated tenant."""
        kwargs["tenant_id"] = self.tenant_id
        instance = self.model(**kwargs)
        self.session.add(instance)
        await self.session.flush()
        await self.session.refresh(instance)
        return instance

    async def update(self, id: uuid.UUID, **kwargs: Any) -> Optional[TenantModelT]:
        """Update a record strictly within the authenticated tenant context."""
        instance = await self.get_by_id(id)
        if not instance:
            return None
        # Disallow tampering with tenant_id
        kwargs.pop("tenant_id", None)
        for key, val in kwargs.items():
            if hasattr(instance, key):
                setattr(instance, key, val)
        await self.session.flush()
        await self.session.refresh(instance)
        return instance

    async def soft_delete(self, id: uuid.UUID) -> bool:
        """Soft-delete a record strictly within the authenticated tenant context."""
        instance = await self.get_by_id(id)
        if not instance:
            return False
        instance.is_deleted = True
        await self.session.flush()
        return True
