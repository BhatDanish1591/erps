from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# ── Dashboard Statistics ──────────────────────────────────────────────────────
class RevenuePoint(BaseModel):
    month: str
    revenue: float


class GrowthPoint(BaseModel):
    month: str
    count: int


class InstitutionSummary(BaseModel):
    id: uuid.UUID
    name: str
    slug: str
    institution_type: str
    status: str
    email: Optional[str] = None
    created_at: datetime


class RecentUserSummary(BaseModel):
    id: uuid.UUID
    email: str
    full_name: str
    is_superadmin: bool
    created_at: datetime


class SuperAdminDashboardStats(BaseModel):
    total_institutions: int
    active_institutions: int
    pending_institutions: int
    suspended_institutions: int
    total_students: int
    total_teachers: int
    total_subscriptions: int
    mrr: float
    arr: float
    subscription_renewals: int
    expired_subscriptions: int
    payment_failures: int
    recent_institutions: List[InstitutionSummary]
    recent_users: List[RecentUserSummary]
    revenue_trend: List[RevenuePoint]
    institution_growth: List[GrowthPoint]


# ── Institution Management ────────────────────────────────────────────────────
class InstitutionListQuery(BaseModel):
    search: Optional[str] = None
    status: Optional[str] = None
    institution_type: Optional[str] = None
    page: int = Field(default=1, ge=1)
    size: int = Field(default=10, ge=1, le=100)


class InstitutionStatusUpdateRequest(BaseModel):
    status: str = Field(..., description="PENDING, ACTIVE, SUSPENDED, REJECTED, INACTIVE")
    reason: Optional[str] = None


class InstitutionUserItem(BaseModel):
    membership_id: uuid.UUID
    user_id: uuid.UUID
    full_name: str
    email: str
    role_name: str
    status: str
    created_at: datetime


class InstitutionDetailResponse(BaseModel):
    id: uuid.UUID
    name: str
    slug: str
    institution_type: str
    status: str
    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: str
    postal_code: Optional[str] = None
    logo_url: Optional[str] = None
    currency: str
    timezone: str
    created_at: datetime
    domains: List[str]
    total_users: int
    current_plan: Optional[str] = None
    subscription_status: Optional[str] = None


# ── Subscription Plans & Features ─────────────────────────────────────────────
class PlanFeaturePayload(BaseModel):
    feature_key: str
    feature_value: Dict[str, Any] = Field(default_factory=dict)
    is_enabled: bool = True


class SubscriptionPlanCreate(BaseModel):
    name: str
    code: str
    description: Optional[str] = None
    institution_type: Optional[str] = None
    billing_cycle: str = "YEARLY"
    price: float = Field(..., ge=0)
    monthly_price: float = Field(0.0, ge=0)
    annual_price: float = Field(0.0, ge=0)
    currency: str = "INR"
    max_students: int = Field(300, ge=1)
    max_teachers: int = Field(20, ge=1)
    storage_limit_gb: int = Field(10, ge=1)
    notification_quota: int = Field(1000, ge=0)
    trial_days: int = Field(30, ge=0)
    is_active: bool = True
    features: List[PlanFeaturePayload] = Field(default_factory=list)


class SubscriptionPlanUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    institution_type: Optional[str] = None
    billing_cycle: Optional[str] = None
    price: Optional[float] = None
    monthly_price: Optional[float] = None
    annual_price: Optional[float] = None
    currency: Optional[str] = None
    max_students: Optional[int] = None
    max_teachers: Optional[int] = None
    storage_limit_gb: Optional[int] = None
    notification_quota: Optional[int] = None
    trial_days: Optional[int] = None
    is_active: Optional[bool] = None
    features: Optional[List[PlanFeaturePayload]] = None


class SubscriptionPlanResponse(BaseModel):
    id: uuid.UUID
    name: str
    code: str
    description: Optional[str] = None
    institution_type: Optional[str] = None
    billing_cycle: str
    price: float
    monthly_price: float
    annual_price: float
    currency: str
    max_students: int
    max_teachers: int
    storage_limit_gb: int
    notification_quota: int
    trial_days: int
    is_active: bool
    features: List[PlanFeaturePayload] = Field(default_factory=list)
    created_at: datetime


# ── Coupons Management ────────────────────────────────────────────────────────
class CouponCreate(BaseModel):
    code: str = Field(..., min_length=2, max_length=50)
    description: Optional[str] = None
    discount_type: str = "PERCENTAGE"
    discount_value: float = Field(..., gt=0)
    max_redemptions: Optional[int] = None
    valid_from: Optional[datetime] = None
    valid_until: Optional[datetime] = None
    is_active: bool = True
    applicable_institution_type: Optional[str] = None


class CouponUpdate(BaseModel):
    description: Optional[str] = None
    discount_value: Optional[float] = None
    max_redemptions: Optional[int] = None
    valid_until: Optional[datetime] = None
    is_active: Optional[bool] = None


class CouponResponse(BaseModel):
    id: uuid.UUID
    code: str
    description: Optional[str] = None
    discount_type: str
    discount_value: float
    max_redemptions: Optional[int] = None
    times_redeemed: int
    valid_from: datetime
    valid_until: Optional[datetime] = None
    is_active: bool
    applicable_institution_type: Optional[str] = None
    created_at: datetime


# ── Global Announcements ──────────────────────────────────────────────────────
class GlobalAnnouncementCreate(BaseModel):
    title: str
    content: str
    target_role: Optional[str] = None
    priority: str = "NORMAL"
    expires_at: Optional[datetime] = None


class GlobalAnnouncementResponse(BaseModel):
    id: uuid.UUID
    title: str
    content: str
    target_role: Optional[str] = None
    priority: str
    is_active: bool
    expires_at: Optional[datetime] = None
    created_at: datetime


# ── Support Tickets ───────────────────────────────────────────────────────────
class SupportTicketCreate(BaseModel):
    tenant_id: Optional[uuid.UUID] = None
    subject: str
    description: str
    category: str = "GENERAL"
    priority: str = "MEDIUM"


class SupportTicketStatusUpdate(BaseModel):
    status: str  # OPEN, IN_PROGRESS, RESOLVED, CLOSED
    assigned_to_user_id: Optional[uuid.UUID] = None


class SupportTicketReplyCreate(BaseModel):
    message: str
    is_internal: bool = False


class SupportTicketReplyResponse(BaseModel):
    id: uuid.UUID
    ticket_id: uuid.UUID
    user_id: uuid.UUID
    user_name: str
    message: str
    is_internal: bool
    created_at: datetime


class SupportTicketResponse(BaseModel):
    id: uuid.UUID
    ticket_number: str
    tenant_id: Optional[uuid.UUID] = None
    tenant_name: Optional[str] = None
    user_id: uuid.UUID
    user_name: str
    user_email: str
    subject: str
    description: str
    category: str
    priority: str
    status: str
    assigned_to_user_id: Optional[uuid.UUID] = None
    assigned_to_name: Optional[str] = None
    created_at: datetime
    replies: List[SupportTicketReplyResponse] = Field(default_factory=list)


# ── Platform Settings & Integrations ──────────────────────────────────────────
class PlatformSettingUpdate(BaseModel):
    category: str = "GENERAL"
    key: str
    value: Dict[str, Any]
    description: Optional[str] = None
    is_secret: bool = False


class PlatformSettingResponse(BaseModel):
    id: uuid.UUID
    category: str
    key: str
    value: Dict[str, Any]
    description: Optional[str] = None
    is_secret: bool
    updated_at: datetime


class PlatformIntegrationUpdate(BaseModel):
    is_enabled: bool
    config: Dict[str, Any]
    status: Optional[str] = None


class PlatformIntegrationResponse(BaseModel):
    id: uuid.UUID
    provider: str
    name: str
    is_enabled: bool
    config: Dict[str, Any]
    status: str
    last_tested_at: Optional[datetime] = None
    updated_at: datetime


# ── Audit Logs ────────────────────────────────────────────────────────────────
class AuditLogResponse(BaseModel):
    id: uuid.UUID
    tenant_id: Optional[uuid.UUID] = None
    user_id: Optional[uuid.UUID] = None
    actor_email: Optional[str] = None
    action: str
    entity_type: str
    entity_id: Optional[str] = None
    ip_address: Optional[str] = None
    changes: Dict[str, Any]
    created_at: datetime
