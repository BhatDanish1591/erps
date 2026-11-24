from __future__ import annotations

import uuid
from datetime import datetime
from typing import List, Optional

from pydantic import EmailStr, Field

from app.models.enums import InstitutionType, MembershipStatus
from app.schemas.common import AppBaseModel


class UserRegisterRequest(AppBaseModel):
    email: EmailStr
    password: str = Field(min_length=8, description="Password at least 8 characters")
    full_name: str = Field(min_length=2, max_length=255)
    phone: Optional[str] = Field(default=None, max_length=50)
    institution_name: Optional[str] = Field(default=None, description="Optional institution to create on signup")
    institution_type: Optional[InstitutionType] = Field(default=InstitutionType.SCHOOL)


class LoginRequest(AppBaseModel):
    identifier: str = Field(description="Email or phone number")
    password: str
    tenant_id: Optional[uuid.UUID] = Field(default=None, description="Target institution context")


class RefreshTokenRequest(AppBaseModel):
    refresh_token: str


class SelectInstitutionRequest(AppBaseModel):
    tenant_id: uuid.UUID


class ForgotPasswordRequest(AppBaseModel):
    email: EmailStr


class ResetPasswordRequest(AppBaseModel):
    token: str
    new_password: str = Field(min_length=8)


class VerifyEmailRequest(AppBaseModel):
    token: str


class VerifyOTPRequest(AppBaseModel):
    phone: str
    otp: str


class MFASetupResponse(AppBaseModel):
    secret: str
    otpauth_url: str


class MFAVerifyRequest(AppBaseModel):
    code: str


class UserInstitutionMembership(AppBaseModel):
    tenant_id: uuid.UUID
    institution_name: str
    institution_slug: str
    institution_type: InstitutionType
    role_code: str
    role_name: str
    status: MembershipStatus
    permissions: List[str]


class AuthUserResponse(AppBaseModel):
    id: uuid.UUID
    email: str
    full_name: str
    phone: Optional[str] = None
    is_superadmin: bool
    is_active: bool
    current_tenant_id: Optional[uuid.UUID] = None
    current_role: Optional[str] = None
    permissions: List[str] = []
    institutions: List[UserInstitutionMembership] = []


class TokenResponse(AppBaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: AuthUserResponse


class SessionInfo(AppBaseModel):
    id: uuid.UUID
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    created_at: datetime
    expires_at: datetime
    is_current: bool = False


class LoginHistoryItem(AppBaseModel):
    id: uuid.UUID
    email: str
    status: str
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    failure_reason: Optional[str] = None
    created_at: datetime
