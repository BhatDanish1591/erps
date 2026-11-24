from __future__ import annotations

import uuid
from typing import Callable, List, Optional

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db, set_database_context, set_tenant_session_context
from app.core.exceptions import AuthenticationException, AuthorizationException
from app.core.security import decode_access_token
from app.core.tenant_context import set_current_tenant_id
from app.models.tenant import Tenant
from app.models.auth import Membership, Role
from app.models.enums import MembershipStatus
from app.models.user import User
from app.repositories.user import UserRepository

security = HTTPBearer(auto_error=False)
ACADEMIC_STAFF_ROLES = ("PRINCIPAL", "HOD", "TEACHER")


async def get_current_user_claims(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> dict:
    """Extract and validate the raw JWT claims from the Authorization header."""
    if not credentials:
        raise AuthenticationException(message="Authentication required: No Bearer token provided")

    try:
        claims = decode_access_token(credentials.credentials)
        return claims
    except JWTError as exc:
        raise AuthenticationException(message=f"Invalid or expired token: {str(exc)}")


async def get_current_user(
    claims: dict = Depends(get_current_user_claims),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Fetch the authenticated user from the database."""
    user_id_str = claims.get("sub")
    if not user_id_str:
        raise AuthenticationException(message="Token missing subject identifier")

    try:
        user_id = uuid.UUID(user_id_str)
    except ValueError:
        raise AuthenticationException(message="Invalid user ID in token")

    repo = UserRepository(db)
    user = await repo.get_by_id(user_id)
    if not user or not user.is_active or user.is_deleted:
        raise AuthenticationException(message="User account is inactive or not found")

    if claims.get("tenant_id"):
        try:
            tenant_id = uuid.UUID(str(claims["tenant_id"]))
        except ValueError as exc:
            raise AuthenticationException(message="Invalid institution ID in token") from exc
        await set_tenant_session_context(db, tenant_id)
        set_current_tenant_id(tenant_id)
        if not user.is_superadmin and claims.get("role") in ACADEMIC_STAFF_ROLES:
            active_role = await db.scalar(
                select(Role.code)
                .join(Membership, Membership.role_id == Role.id)
                .where(
                    Membership.tenant_id == tenant_id,
                    Membership.user_id == user.id,
                    Membership.status == MembershipStatus.ACTIVE,
                    Membership.is_deleted.is_(False),
                )
            )
            if active_role != claims["role"]:
                raise AuthenticationException(message="Staff access changed. Sign in again to continue.")
    elif not user.is_superadmin:
        set_current_tenant_id(None)
    if user.is_superadmin:
        await set_database_context(db, is_superadmin=True)
    return user


async def require_super_admin(
    user: User = Depends(get_current_user),
) -> User:
    """Authorize only platform-level Super Administrators."""
    if not user.is_superadmin:
        raise AuthorizationException(message="Platform Super Administrator privileges required")
    return user


async def get_teacher_scope_user(
    user: User = Depends(get_current_user),
    claims: dict = Depends(get_current_user_claims),
) -> Optional[uuid.UUID]:
    return user.id if not user.is_superadmin and claims.get("role") == "TEACHER" else None


async def get_active_tenant_id(
    request: Request,
    claims: dict = Depends(get_current_user_claims),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> uuid.UUID:
    """Use the signed tenant claim, or let platform administrators select a tenant."""
    if claims.get("tenant_id"):
        return uuid.UUID(str(claims["tenant_id"]))
    if user.is_superadmin:
        for requested in (request.headers.get("X-Tenant-ID"), request.query_params.get("tenant_id")):
            if not requested:
                continue
            try:
                tenant_id = uuid.UUID(requested)
            except ValueError:
                continue
            await set_tenant_session_context(db, tenant_id)
            set_current_tenant_id(tenant_id)
            return tenant_id
        tenant_id = await db.scalar(
            select(Tenant.id).where(Tenant.is_deleted.is_(False)).order_by(Tenant.created_at).limit(1)
        )
        if tenant_id:
            await set_tenant_session_context(db, tenant_id)
            set_current_tenant_id(tenant_id)
            return tenant_id

    raise AuthorizationException(message="Active institution tenancy context required")


def require_permission(permission_code: str) -> Callable:
    """
    Dependency factory: validates that the authenticated caller has the specified permission
    in their active tenant context. Super Admins bypass permission checks.
    """
    async def permission_checker(
        claims: dict = Depends(get_current_user_claims),
        user: User = Depends(get_current_user),
    ) -> User:
        # Platform Super Admins have unrestricted system access
        if user.is_superadmin:
            return user

        user_permissions: List[str] = claims.get("permissions", [])
        if permission_code not in user_permissions and "*:*" not in user_permissions:
            raise AuthorizationException(
                message=f"Missing required permission: '{permission_code}'"
            )

        return user

    return permission_checker


def require_any_role(allowed_roles: List[str]) -> Callable:
    """
    Dependency factory: validates that the authenticated user possesses one of the allowed roles
    in the active tenant context.
    """
    async def role_checker(
        claims: dict = Depends(get_current_user_claims),
        user: User = Depends(get_current_user),
    ) -> User:
        if user.is_superadmin:
            return user

        user_role = claims.get("role")
        if not user_role or user_role not in allowed_roles:
            raise AuthorizationException(
                message=f"Access denied: Requires one of roles {allowed_roles}"
            )

        return user

    return role_checker
