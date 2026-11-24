from __future__ import annotations

from typing import AsyncGenerator
from urllib.parse import urlparse, urlunparse

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.pool import NullPool
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings
from app.core.database import get_db
from app.main import app

def _get_test_db_url() -> str:
    parsed = urlparse(settings.DATABASE_URL)
    test_parsed = parsed._replace(path="/edusaas_test")
    return urlunparse(test_parsed)

TEST_DATABASE_URL = _get_test_db_url()


@pytest_asyncio.fixture(scope="session")
async def test_engine():
    engine = create_async_engine(TEST_DATABASE_URL, echo=False, poolclass=NullPool)
    # Seed default roles and permissions for tests
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        from app.models.auth import Role, Permission, RolePermission
        from app.models.enums import RoleScope
        from sqlalchemy import select

        existing_role = await session.execute(select(Role).where(Role.code == "INSTITUTION_ADMIN"))
        if not existing_role.scalars().first():
            roles = [
                Role(name="Super Admin", code="SUPER_ADMIN", scope=RoleScope.PLATFORM, is_system_role=True),
                Role(name="Institution Admin", code="INSTITUTION_ADMIN", scope=RoleScope.TENANT, is_system_role=True),
                Role(name="Teacher", code="TEACHER", scope=RoleScope.TENANT, is_system_role=True),
                Role(name="Student", code="STUDENT", scope=RoleScope.TENANT, is_system_role=True),
                Role(name="Parent", code="PARENT", scope=RoleScope.TENANT, is_system_role=True),
            ]
            for r in roles:
                session.add(r)
            
            perms = [
                Permission(code="users:manage_roles", module="users", description="Manage roles"),
                Permission(code="academic:session:read", module="academic", description="Read sessions"),
                Permission(code="exams:read", module="exams", description="Read exams"),
                Permission(code="attendance:mark", module="attendance", description="Mark attendance"),
            ]
            for p in perms:
                session.add(p)
            await session.flush()

            admin_role = next(r for r in roles if r.code == "INSTITUTION_ADMIN")
            for p in perms:
                session.add(RolePermission(role_id=admin_role.id, permission_id=p.id))
            await session.commit()

    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    session_factory = async_sessionmaker(test_engine, expire_on_commit=False)
    async with session_factory() as session:
        try:
            yield session
        finally:
            try:
                await session.rollback()
                await session.close()
            except Exception:
                pass


@pytest_asyncio.fixture
async def client(test_engine) -> AsyncGenerator[AsyncClient, None]:
    session_factory = async_sessionmaker(test_engine, expire_on_commit=False)

    async def override_get_db():
        async with session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac
    app.dependency_overrides.clear()
