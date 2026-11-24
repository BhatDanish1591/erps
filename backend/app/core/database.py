from __future__ import annotations

import uuid
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional

import sqlalchemy
from sqlalchemy import event, text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.logging import get_logger
from app.core.tenant_context import get_current_tenant_id

logger = get_logger(__name__)


def create_engine() -> AsyncEngine:
    return create_async_engine(
        settings.DATABASE_URL,
        pool_size=settings.DATABASE_POOL_SIZE,
        max_overflow=settings.DATABASE_MAX_OVERFLOW,
        pool_timeout=settings.DATABASE_POOL_TIMEOUT,
        pool_recycle=settings.DATABASE_POOL_RECYCLE,
        pool_pre_ping=True,
        echo=settings.DEBUG,
    )


engine: AsyncEngine = create_engine()

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


@event.listens_for(Session, "after_begin")
def apply_database_context(session, transaction, connection) -> None:
    # PostgreSQL clears SET LOCAL at commit, including commits inside services.
    for key, value in session.info.get("database_context", {}).items():
        connection.execute(
            text("SELECT set_config(:key, :value, true)"),
            {"key": key, "value": value},
        )


async def set_database_context(session: AsyncSession, **values: object) -> None:
    context = session.info.setdefault("database_context", {})
    for name, value in values.items():
        key = f"app.{name}"
        if isinstance(value, bool):
            value = str(value).lower()
        value = "" if value is None else str(value)
        if context.get(key) != value:
            await session.execute(
                text("SELECT set_config(:key, :value, true)"),
                {"key": key, "value": value},
            )
            context[key] = value


async def set_tenant_session_context(session: AsyncSession, tenant_id: Optional[uuid.UUID]) -> None:
    await set_database_context(session, current_tenant_id=tenant_id)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Standard database session dependency.
    Authorization dependencies set the validated scope for authenticated requests.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


@asynccontextmanager
async def get_db_context(
    tenant_id: Optional[uuid.UUID] = None, *, system: bool = False
) -> AsyncGenerator[AsyncSession, None]:
    """
    Context manager for use outside of FastAPI (e.g. Celery workers, background jobs, test suites).
    Allows explicitly binding a tenant_id to the database session.
    """
    async with AsyncSessionLocal() as session:
        try:
            target_tenant = tenant_id or get_current_tenant_id()
            if target_tenant:
                await set_tenant_session_context(session, target_tenant)
            if system:
                await set_database_context(session, is_superadmin=True)
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def check_db_connection() -> bool:
    """Health-check: verify the database is reachable."""
    try:
        async with engine.connect() as conn:
            await conn.execute(sqlalchemy.text("SELECT 1"))
        return True
    except Exception as exc:
        logger.error("Database connection failed", error=str(exc))
        return False


async def check_tenant_isolation() -> bool:
    try:
        async with engine.connect() as conn:
            return bool(await conn.scalar(text("""
                SELECT count(*) > 0 AND bool_and(row_security_active(oid))
                FROM pg_class
                WHERE relnamespace = 'public'::regnamespace AND relrowsecurity
            """)))
    except Exception as exc:
        logger.error("Database role check failed", error=str(exc))
        return False
