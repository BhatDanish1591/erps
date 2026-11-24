from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from app.models.enums import BillingCycle, DiscountType, InstitutionType, InvoiceStatus, PaymentStatus, SubscriptionStatus


class PlanFeatureItem(BaseModel):
    feature_key: str
    feature_value: Dict[str, Any] = Field(default_factory=dict)
    is_enabled: bool = True


class SubscriptionPlanSchema(BaseModel):
    id: uuid.UUID
    name: str
    code: str
    description: Optional[str] = None
    institution_type: Optional[str] = None
    billing_cycle: str
    price: float
    monthly_price: float
    annual_price: float
    currency: str = "INR"
    max_students: int
    max_teachers: int
    storage_limit_gb: int
    notification_quota: int
    trial_days: int
    is_active: bool
    features: List[PlanFeatureItem] = Field(default_factory=list)
    created_at: datetime


class SubscriptionPlanCreateSchema(BaseModel):
    name: str
    code: str
    description: Optional[str] = None
    institution_type: Optional[InstitutionType] = None
    billing_cycle: BillingCycle = BillingCycle.YEARLY
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
    features: List[PlanFeatureItem] = Field(default_factory=list)


class SubscriptionPlanUpdateSchema(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    institution_type: Optional[InstitutionType] = None
    billing_cycle: Optional[BillingCycle] = None
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
    features: Optional[List[PlanFeatureItem]] = None


# ── Coupons ───────────────────────────────────────────────────────────────────
class CouponSchema(BaseModel):
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


class CouponCreateSchema(BaseModel):
    code: str = Field(..., min_length=2, max_length=50)
    description: Optional[str] = None
    discount_type: DiscountType = DiscountType.PERCENTAGE
    discount_value: float = Field(..., gt=0)
    max_redemptions: Optional[int] = None
    valid_from: Optional[datetime] = None
    valid_until: Optional[datetime] = None
    is_active: bool = True
    applicable_institution_type: Optional[InstitutionType] = None


class CouponUpdateSchema(BaseModel):
    description: Optional[str] = None
    discount_value: Optional[float] = None
    max_redemptions: Optional[int] = None
    valid_until: Optional[datetime] = None
    is_active: Optional[bool] = None


# ── Orders & Billing ──────────────────────────────────────────────────────────
class PreviewOrderRequest(BaseModel):
    plan_id: uuid.UUID
    billing_cycle: BillingCycle = BillingCycle.MONTHLY
    coupon_code: Optional[str] = None


class OrderPricingBreakdown(BaseModel):
    plan_name: str
    billing_cycle: str
    base_price: float
    discount_amount: float
    subtotal: float
    tax_rate_percent: float = 18.0
    tax_amount: float
    total_amount: float
    currency: str = "INR"
    coupon_applied: Optional[str] = None


class CreateOrderRequest(BaseModel):
    plan_id: uuid.UUID
    billing_cycle: BillingCycle = BillingCycle.MONTHLY
    coupon_code: Optional[str] = None
    billing_name: Optional[str] = None
    billing_address: Optional[str] = None


class CreateOrderResponse(BaseModel):
    order_id: str
    amount: float
    amount_paise: int
    currency: str
    key_id: str
    invoice_id: uuid.UUID
    plan_id: uuid.UUID
    plan_name: str
    billing_cycle: str


class VerifyPaymentRequest(BaseModel):
    razorpay_order_id: str
    razorpay_payment_id: str
    razorpay_signature: str
    invoice_id: uuid.UUID


class CancelSubscriptionRequest(BaseModel):
    immediate: bool = False
    reason: Optional[str] = None


class SubscriptionInvoiceSummary(BaseModel):
    id: uuid.UUID
    invoice_number: str
    billing_cycle: str
    subtotal: float
    discount_amount: float
    tax_amount: float
    total_amount: float
    currency: str
    status: str
    due_date: date
    paid_at: Optional[datetime] = None
    created_at: datetime


class SubscriptionInvoiceDetail(SubscriptionInvoiceSummary):
    billing_name: Optional[str] = None
    billing_address: Optional[str] = None
    line_items: List[Dict[str, Any]] = Field(default_factory=list)
    payments: List[Dict[str, Any]] = Field(default_factory=list)
