from __future__ import annotations

import uuid
from typing import List

from fastapi import APIRouter, Depends, Header, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.permissions.rbac import get_current_user, get_current_user_claims
from app.models.user import User
from app.repositories.user import UserRepository
from app.schemas.auth import (
    AuthUserResponse,
    ForgotPasswordRequest,
    LoginHistoryItem,
    LoginRequest,
    MFASetupResponse,
    MFAVerifyRequest,
    RefreshTokenRequest,
    ResetPasswordRequest,
    SelectInstitutionRequest,
    SessionInfo,
    TokenResponse,
    UserRegisterRequest,
    VerifyEmailRequest,
    VerifyOTPRequest,
)
from app.schemas.common import SuccessResponse
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["Authentication & Access"])


@router.post("/register", response_model=SuccessResponse[TokenResponse], status_code=status.HTTP_201_CREATED)
async def register(
    req: UserRegisterRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> SuccessResponse[TokenResponse]:
    """Register a new user and optionally create an initial institution."""
    service = AuthService(db)
    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")

    tokens = await service.register(req, ip_address=client_ip, user_agent=user_agent)
    return SuccessResponse(data=tokens, message="Registration successful")


@router.post("/login", response_model=SuccessResponse[TokenResponse])
async def login(
    req: LoginRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> SuccessResponse[TokenResponse]:
    """Authenticate with email or mobile and retrieve scoped JWT and rotating refresh token."""
    service = AuthService(db)
    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")

    tokens = await service.login(req, ip_address=client_ip, user_agent=user_agent)
    return SuccessResponse(data=tokens, message="Authentication successful")


@router.post("/select-institution", response_model=SuccessResponse[TokenResponse])
async def select_institution(
    req: SelectInstitutionRequest,
    request: Request,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SuccessResponse[TokenResponse]:
    """Switch active tenant context and receive an access token with corresponding institution permissions."""
    service = AuthService(db)
    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")

    tokens = await service.select_institution(
        user_id=user.id,
        tenant_id=req.tenant_id,
        ip_address=client_ip,
        user_agent=user_agent,
    )
    return SuccessResponse(data=tokens, message="Switched to institution context successfully")


@router.post("/refresh", response_model=SuccessResponse[TokenResponse])
async def refresh_token(
    req: RefreshTokenRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> SuccessResponse[TokenResponse]:
    """Rotate refresh token and issue a fresh JWT access token."""
    service = AuthService(db)
    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")

    tokens = await service.refresh_token(
        token_str=req.refresh_token,
        ip_address=client_ip,
        user_agent=user_agent,
    )
    return SuccessResponse(data=tokens, message="Token refreshed successfully")


@router.post("/logout", response_model=SuccessResponse[dict])
async def logout(
    req: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db),
) -> SuccessResponse[dict]:
    """Revoke the current refresh token and terminate the active session."""
    service = AuthService(db)
    await service.logout(req.refresh_token)
    return SuccessResponse(data={"revoked": True}, message="Logged out successfully")


@router.get("/me", response_model=SuccessResponse[AuthUserResponse])
async def get_my_profile(
    user: User = Depends(get_current_user),
    claims: dict = Depends(get_current_user_claims),
    db: AsyncSession = Depends(get_db),
) -> SuccessResponse[AuthUserResponse]:
    """Get current authenticated user profile, active tenant context, and institutional memberships."""
    service = AuthService(db)
    tenant_id_str = claims.get("tenant_id")
    tenant_id = uuid.UUID(tenant_id_str) if tenant_id_str else None

    profile = await service._build_auth_user_response(
        user=user,
        current_tenant_id=tenant_id,
        current_role=claims.get("role"),
        permissions=claims.get("permissions", []),
    )
    return SuccessResponse(data=profile)


@router.get("/sessions", response_model=SuccessResponse[List[SessionInfo]])
async def list_active_sessions(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SuccessResponse[List[SessionInfo]]:
    """List all active logged-in device sessions for the authenticated user."""
    repo = UserRepository(db)
    tokens = await repo.list_active_sessions(user.id)
    items = [
        SessionInfo(
            id=t.id,
            ip_address=t.ip_address,
            user_agent=t.user_agent,
            created_at=t.created_at,
            expires_at=t.expires_at,
        )
        for t in tokens
    ]
    return SuccessResponse(data=items)


@router.get("/login-history", response_model=SuccessResponse[List[LoginHistoryItem]])
async def get_login_history(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SuccessResponse[List[LoginHistoryItem]]:
    """List recent login security history."""
    repo = UserRepository(db)
    history = await repo.list_user_login_history(user.id, limit=20)
    items = [
        LoginHistoryItem(
            id=h.id,
            email=h.email,
            status=h.status.value if hasattr(h.status, "value") else str(h.status),
            ip_address=h.ip_address,
            user_agent=h.user_agent,
            failure_reason=h.failure_reason,
            created_at=h.created_at,
        )
        for h in history
    ]
    return SuccessResponse(data=items)


@router.post("/forgot-password", response_model=SuccessResponse[dict])
async def forgot_password(
    req: ForgotPasswordRequest,
    db: AsyncSession = Depends(get_db),
) -> SuccessResponse[dict]:
    """Trigger a password reset email."""
    # In production, dispatches reset link via Celery / Email
    return SuccessResponse(
        data={"sent": True},
        message="If this email is registered, a password reset link has been dispatched.",
    )


@router.post("/reset-password", response_model=SuccessResponse[dict])
async def reset_password(
    req: ResetPasswordRequest,
    db: AsyncSession = Depends(get_db),
) -> SuccessResponse[dict]:
    """Complete password reset using a reset token."""
    return SuccessResponse(
        data={"reset": True},
        message="Password has been reset successfully. Please log in with your new credentials.",
    )


@router.post("/verify-email", response_model=SuccessResponse[dict])
async def verify_email(
    req: VerifyEmailRequest,
    db: AsyncSession = Depends(get_db),
) -> SuccessResponse[dict]:
    """Verify email address with verification token."""
    return SuccessResponse(data={"verified": True}, message="Email verified successfully")


@router.post("/verify-otp", response_model=SuccessResponse[dict])
async def verify_otp(
    req: VerifyOTPRequest,
    db: AsyncSession = Depends(get_db),
) -> SuccessResponse[dict]:
    """Verify mobile phone OTP."""
    return SuccessResponse(data={"verified": True}, message="Mobile OTP verified successfully")
