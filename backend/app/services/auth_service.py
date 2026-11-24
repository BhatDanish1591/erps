from __future__ import annotations

import re
import uuid
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import set_tenant_session_context
from app.core.exceptions import (
    AuthenticationException,
    ConflictException,
    NotFoundException,
    TenantException,
    ValidationException,
)
from app.core.security import (
    create_access_token,
    generate_secure_token,
    hash_password,
    hash_token,
    verify_password,
)
from app.models.enums import InstitutionType, LoginStatus, MembershipStatus, RoleScope, TenantStatus
from app.models.tenant import Tenant
from app.models.user import User
from app.repositories.role import RoleRepository
from app.repositories.tenant import TenantRepository
from app.repositories.user import UserRepository
from app.schemas.auth import (
    AuthUserResponse,
    LoginRequest,
    TokenResponse,
    UserInstitutionMembership,
    UserRegisterRequest,
)


class AuthService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.user_repo = UserRepository(db)
        self.tenant_repo = TenantRepository(db)
        self.role_repo = RoleRepository(db)

    async def register(
        self,
        req: UserRegisterRequest,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> TokenResponse:
        # Check if email is already registered
        existing_user = await self.user_repo.get_by_email(req.email)
        if existing_user:
            raise ConflictException(message="A user with this email address already exists")

        # Create user
        pwd_hash = hash_password(req.password)
        user = await self.user_repo.create(
            email=req.email.lower().strip(),
            password_hash=pwd_hash,
            full_name=req.full_name.strip(),
            phone=req.phone.strip() if req.phone else None,
            is_active=True,
            is_superadmin=False,
        )

        tenant_id: Optional[uuid.UUID] = None
        role_code: Optional[str] = None
        permissions: List[str] = []

        # If an institution was specified on signup, create it and make user the Institution Admin
        if req.institution_name:
            base_slug = re.sub(r"[^a-zA-Z0-9]+", "-", req.institution_name.lower()).strip("-")
            slug = f"{base_slug}-{uuid.uuid4().hex[:6]}"

            tenant = await self.tenant_repo.create(
                name=req.institution_name.strip(),
                slug=slug,
                institution_type=req.institution_type or InstitutionType.SCHOOL,
                status=TenantStatus.ACTIVE,
                email=req.email,
            )
            tenant_id = tenant.id
            await set_tenant_session_context(self.db, tenant_id)

            admin_role = await self.role_repo.get_by_code("INSTITUTION_ADMIN")
            if admin_role:
                await self.user_repo.create_membership(
                    tenant_id=tenant_id,
                    user_id=user.id,
                    role_id=admin_role.id,
                    status=MembershipStatus.ACTIVE,
                )
                role_code = admin_role.code
                permissions = [
                    rp.permission.code for rp in (admin_role.role_permissions or [])
                ]

        return await self._generate_auth_tokens(
            user=user,
            tenant_id=tenant_id,
            role_code=role_code,
            permissions=permissions,
            ip_address=ip_address,
            user_agent=user_agent,
        )

    async def login(
        self,
        req: LoginRequest,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> TokenResponse:
        user = await self.user_repo.get_by_identifier(req.identifier)

        if not user or not verify_password(req.password, user.password_hash):
            await self.user_repo.record_login_attempt(
                email=req.identifier,
                status=LoginStatus.FAILED,
                ip_address=ip_address,
                user_agent=user_agent,
                user_id=user.id if user else None,
                tenant_id=req.tenant_id,
                failure_reason="INVALID_CREDENTIALS",
            )
            raise AuthenticationException(message="Invalid credentials provided")

        if not user.is_active or user.is_deleted:
            await self.user_repo.record_login_attempt(
                email=req.identifier,
                status=LoginStatus.FAILED,
                ip_address=ip_address,
                user_agent=user_agent,
                user_id=user.id,
                failure_reason="ACCOUNT_INACTIVE",
            )
            raise AuthenticationException(message="Account has been disabled. Please contact support.")

        await self.user_repo.update_last_login(user.id)
        await self.user_repo.record_login_attempt(
            email=user.email,
            status=LoginStatus.SUCCESS,
            ip_address=ip_address,
            user_agent=user_agent,
            user_id=user.id,
            tenant_id=req.tenant_id,
        )

        # Multi-Institution Membership Resolution
        memberships = await self.user_repo.get_user_memberships(user.id)
        active_memberships = [m for m in memberships if m.status == MembershipStatus.ACTIVE and not m.tenant.is_deleted]

        target_tenant_id: Optional[uuid.UUID] = None
        target_role_code: Optional[str] = None
        target_permissions: List[str] = []

        if user.is_superadmin:
            target_role_code = "SUPER_ADMIN"
            target_permissions = ["*:*"]
            target_tenant_id = req.tenant_id
        elif req.tenant_id:
            membership = next((m for m in active_memberships if m.tenant_id == req.tenant_id), None)
            if not membership:
                raise TenantException(message="You do not have active membership in this institution")
            target_tenant_id = membership.tenant_id
            target_role_code = membership.role.code
            target_permissions = [rp.permission.code for rp in (membership.role.role_permissions or [])]
        elif len(active_memberships) == 1:
            m = active_memberships[0]
            target_tenant_id = m.tenant_id
            target_role_code = m.role.code
            target_permissions = [rp.permission.code for rp in (m.role.role_permissions or [])]

        return await self._generate_auth_tokens(
            user=user,
            tenant_id=target_tenant_id,
            role_code=target_role_code,
            permissions=target_permissions,
            ip_address=ip_address,
            user_agent=user_agent,
        )

    async def select_institution(
        self,
        user_id: uuid.UUID,
        tenant_id: uuid.UUID,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> TokenResponse:
        user = await self.user_repo.get_by_id(user_id)
        if not user or not user.is_active:
            raise AuthenticationException(message="User not found or inactive")

        if user.is_superadmin:
            return await self._generate_auth_tokens(
                user=user,
                tenant_id=tenant_id,
                role_code="SUPER_ADMIN",
                permissions=["*:*"],
                ip_address=ip_address,
                user_agent=user_agent,
            )

        membership = await self.user_repo.get_membership(user_id=user_id, tenant_id=tenant_id)
        if not membership or membership.status != MembershipStatus.ACTIVE:
            raise TenantException(message="You do not hold an active membership in this institution")

        role_code = membership.role.code
        permissions = [rp.permission.code for rp in (membership.role.role_permissions or [])]

        return await self._generate_auth_tokens(
            user=user,
            tenant_id=tenant_id,
            role_code=role_code,
            permissions=permissions,
            ip_address=ip_address,
            user_agent=user_agent,
        )

    async def refresh_token(
        self,
        token_str: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> TokenResponse:
        hashed = hash_token(token_str)
        token_record = await self.user_repo.get_refresh_token(hashed)

        if not token_record:
            raise AuthenticationException(message="Invalid refresh token")

        if token_record.is_revoked:
            # Token reuse detected! Revoke all tokens for this user as a security safeguard
            await self.user_repo.revoke_all_user_tokens(token_record.user_id)
            raise AuthenticationException(
                message="Refresh token has been revoked. Security alert: Please log in again."
            )

        now = datetime.now(timezone.utc)
        if token_record.expires_at <= now:
            raise AuthenticationException(message="Refresh token has expired. Please log in again.")

        user = await self.user_repo.get_by_id(token_record.user_id)
        if not user or not user.is_active:
            raise AuthenticationException(message="User account is inactive or not found")

        # Generate new replacement refresh token (rotation)
        new_token_str = generate_secure_token()
        new_token_hash = hash_token(new_token_str)
        expires_at = now + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

        # Mark old token revoked and reference successor
        await self.user_repo.revoke_refresh_token(hashed, replaced_by=new_token_hash)
        await self.user_repo.save_refresh_token(
            user_id=user.id,
            token_hash=new_token_hash,
            expires_at=expires_at,
            ip_address=ip_address,
            user_agent=user_agent,
        )

        # Build access token
        access_token = create_access_token(
            user_id=user.id,
            email=user.email,
            is_superadmin=user.is_superadmin,
        )

        user_resp = await self._build_auth_user_response(user, current_tenant_id=None)

        return TokenResponse(
            access_token=access_token,
            refresh_token=new_token_str,
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            user=user_resp,
        )

    async def logout(self, token_str: str) -> bool:
        hashed = hash_token(token_str)
        return await self.user_repo.revoke_refresh_token(hashed)

    async def _generate_auth_tokens(
        self,
        user: User,
        tenant_id: Optional[uuid.UUID] = None,
        role_code: Optional[str] = None,
        permissions: Optional[List[str]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> TokenResponse:
        access_token = create_access_token(
            user_id=user.id,
            email=user.email,
            tenant_id=tenant_id,
            role=role_code,
            permissions=permissions,
            is_superadmin=user.is_superadmin,
        )

        refresh_token_plain = generate_secure_token()
        refresh_token_hash = hash_token(refresh_token_plain)
        expires_at = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

        await self.user_repo.save_refresh_token(
            user_id=user.id,
            token_hash=refresh_token_hash,
            expires_at=expires_at,
            ip_address=ip_address,
            user_agent=user_agent,
        )

        user_resp = await self._build_auth_user_response(
            user=user,
            current_tenant_id=tenant_id,
            current_role=role_code,
            permissions=permissions or [],
        )

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token_plain,
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            user=user_resp,
        )

    async def _build_auth_user_response(
        self,
        user: User,
        current_tenant_id: Optional[uuid.UUID] = None,
        current_role: Optional[str] = None,
        permissions: Optional[List[str]] = None,
    ) -> AuthUserResponse:
        memberships = await self.user_repo.get_user_memberships(user.id)
        institutions: List[UserInstitutionMembership] = []

        for m in memberships:
            if m.status == MembershipStatus.ACTIVE and not m.tenant.is_deleted:
                m_perms = [rp.permission.code for rp in (m.role.role_permissions or [])]
                institutions.append(
                    UserInstitutionMembership(
                        tenant_id=m.tenant_id,
                        institution_name=m.tenant.name,
                        institution_slug=m.tenant.slug,
                        institution_type=m.tenant.institution_type,
                        role_code=m.role.code,
                        role_name=m.role.name,
                        status=m.status,
                        permissions=m_perms,
                    )
                )

        return AuthUserResponse(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            phone=user.phone,
            is_superadmin=user.is_superadmin,
            is_active=user.is_active,
            current_tenant_id=current_tenant_id,
            current_role=current_role,
            permissions=permissions or [],
            institutions=institutions,
        )
