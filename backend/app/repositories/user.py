from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import List, Optional, Sequence

from sqlalchemy import delete, desc, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import set_database_context
from app.models.auth import Membership, Role, RolePermission, Permission
from app.models.enums import LoginStatus, MembershipStatus
from app.models.tenant import Tenant
from app.models.user import LoginHistory, RefreshToken, User
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(User, session)

    async def get_by_email(self, email: str) -> Optional[User]:
        stmt = select(User).where(
            User.email == email.lower().strip(),
            User.is_deleted.is_(False),
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def get_by_phone(self, phone: str) -> Optional[User]:
        stmt = select(User).where(
            User.phone == phone.strip(),
            User.is_deleted.is_(False),
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def get_by_identifier(self, identifier: str) -> Optional[User]:
        clean = identifier.strip().lower()
        if "@" in clean:
            return await self.get_by_email(clean)
        return await self.get_by_phone(clean)

    async def update_last_login(self, user_id: uuid.UUID) -> None:
        stmt = (
            update(User)
            .where(User.id == user_id)
            .values(last_login_at=datetime.now(timezone.utc))
        )
        await self.session.execute(stmt)

    # ── Refresh Tokens & Sessions ─────────────────────────────────────────────
    async def save_refresh_token(
        self,
        user_id: uuid.UUID,
        token_hash: str,
        expires_at: datetime,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> RefreshToken:
        token = RefreshToken(
            user_id=user_id,
            token_hash=token_hash,
            expires_at=expires_at,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        self.session.add(token)
        await self.session.flush()
        return token

    async def get_refresh_token(self, token_hash: str) -> Optional[RefreshToken]:
        stmt = select(RefreshToken).where(RefreshToken.token_hash == token_hash)
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def revoke_refresh_token(
        self, token_hash: str, replaced_by: Optional[str] = None
    ) -> bool:
        stmt = (
            update(RefreshToken)
            .where(RefreshToken.token_hash == token_hash)
            .values(
                is_revoked=True,
                revoked_at=datetime.now(timezone.utc),
                replaced_by_token_hash=replaced_by,
            )
        )
        result = await self.session.execute(stmt)
        return result.rowcount > 0

    async def revoke_all_user_tokens(self, user_id: uuid.UUID) -> int:
        stmt = (
            update(RefreshToken)
            .where(
                RefreshToken.user_id == user_id,
                RefreshToken.is_revoked.is_(False),
            )
            .values(
                is_revoked=True,
                revoked_at=datetime.now(timezone.utc),
            )
        )
        result = await self.session.execute(stmt)
        return result.rowcount

    async def list_active_sessions(self, user_id: uuid.UUID) -> Sequence[RefreshToken]:
        now = datetime.now(timezone.utc)
        stmt = (
            select(RefreshToken)
            .where(
                RefreshToken.user_id == user_id,
                RefreshToken.is_revoked.is_(False),
                RefreshToken.expires_at > now,
            )
            .order_by(desc(RefreshToken.created_at))
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    # ── Login History ─────────────────────────────────────────────────────────
    async def record_login_attempt(
        self,
        email: str,
        status: LoginStatus,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        user_id: Optional[uuid.UUID] = None,
        tenant_id: Optional[uuid.UUID] = None,
        failure_reason: Optional[str] = None,
    ) -> LoginHistory:
        record = LoginHistory(
            user_id=user_id,
            tenant_id=tenant_id,
            email=email,
            status=status,
            ip_address=ip_address,
            user_agent=user_agent,
            failure_reason=failure_reason,
        )
        self.session.add(record)
        await self.session.flush()
        return record

    async def list_user_login_history(
        self, user_id: uuid.UUID, limit: int = 20
    ) -> Sequence[LoginHistory]:
        stmt = (
            select(LoginHistory)
            .where(LoginHistory.user_id == user_id)
            .order_by(desc(LoginHistory.created_at))
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    # ── Memberships ───────────────────────────────────────────────────────────
    async def get_user_memberships(self, user_id: uuid.UUID) -> Sequence[Membership]:
        await set_database_context(self.session, membership_user_id=user_id)
        stmt = (
            select(Membership)
            .where(
                Membership.user_id == user_id,
                Membership.is_deleted.is_(False),
            )
            .options(
                selectinload(Membership.tenant),
                selectinload(Membership.role).selectinload(Role.role_permissions).selectinload(RolePermission.permission),
            )
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_membership(
        self, user_id: uuid.UUID, tenant_id: uuid.UUID
    ) -> Optional[Membership]:
        await set_database_context(self.session, membership_user_id=user_id)
        stmt = (
            select(Membership)
            .where(
                Membership.user_id == user_id,
                Membership.tenant_id == tenant_id,
                Membership.is_deleted.is_(False),
            )
            .options(
                selectinload(Membership.tenant),
                selectinload(Membership.role).selectinload(Role.role_permissions).selectinload(RolePermission.permission),
            )
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def create_membership(
        self,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID,
        role_id: uuid.UUID,
        status: MembershipStatus = MembershipStatus.ACTIVE,
    ) -> Membership:
        membership = Membership(
            tenant_id=tenant_id,
            user_id=user_id,
            role_id=role_id,
            status=status,
        )
        self.session.add(membership)
        await self.session.flush()
        return membership
