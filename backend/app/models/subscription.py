from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import Boolean, Date, DateTime, Enum, ForeignKey, Index, Integer, Numeric, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel
from app.models.enums import BillingCycle, DiscountType, InstitutionType, InvoiceStatus, PaymentStatus, SubscriptionStatus

if TYPE_CHECKING:
    from app.models.tenant import Tenant


class SubscriptionPlan(BaseModel):
    """
    SaaS commercial tier defined at the platform level (e.g. Starter, Pro, Enterprise).
    """
    __tablename__ = "subscription_plans"

    name: Mapped[str] = mapped_column(String(100), nullable=False)
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    institution_type: Mapped[Optional[InstitutionType]] = mapped_column(
        Enum(InstitutionType, name="institution_type_enum", create_type=False),
        nullable=True,
    )
    billing_cycle: Mapped[BillingCycle] = mapped_column(
        Enum(BillingCycle, name="billing_cycle_enum", create_type=False),
        nullable=False,
        default=BillingCycle.YEARLY,
    )
    price: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0.0)
    monthly_price: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0.0)
    annual_price: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0.0)
    currency: Mapped[str] = mapped_column(String(10), nullable=False, default="INR")
    max_students: Mapped[int] = mapped_column(Integer, nullable=False, default=300)
    max_teachers: Mapped[int] = mapped_column(Integer, nullable=False, default=20)
    storage_limit_gb: Mapped[int] = mapped_column(Integer, nullable=False, default=10)
    notification_quota: Mapped[int] = mapped_column(Integer, nullable=False, default=1000)
    trial_days: Mapped[int] = mapped_column(Integer, nullable=False, default=30)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)

    # Relationships
    features: Mapped[List["PlanFeature"]] = relationship(
        "PlanFeature", back_populates="plan", cascade="all, delete-orphan"
    )
    subscriptions: Mapped[List["Subscription"]] = relationship("Subscription", back_populates="plan")


class PlanFeature(BaseModel):
    """
    Individual feature entitlement / quota associated with a subscription plan.
    e.g. key='advanced_analytics', value={"enabled": true}.
    """
    __tablename__ = "plan_features"

    plan_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("subscription_plans.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    feature_key: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    feature_value: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    plan: Mapped["SubscriptionPlan"] = relationship("SubscriptionPlan", back_populates="features")

    __table_args__ = (
        UniqueConstraint("plan_id", "feature_key", name="uq_plan_features_plan_key"),
    )


class Coupon(BaseModel):
    """
    Promotional discounts applicable to subscription plan purchases and renewals.
    """
    __tablename__ = "coupons"

    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    discount_type: Mapped[DiscountType] = mapped_column(
        Enum(DiscountType, name="discount_type_enum"),
        nullable=False,
        default=DiscountType.PERCENTAGE,
    )
    discount_value: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    max_redemptions: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    times_redeemed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    valid_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    valid_until: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)
    applicable_institution_type: Mapped[Optional[InstitutionType]] = mapped_column(
        Enum(InstitutionType, name="institution_type_enum", create_type=False),
        nullable=True,
    )


class Subscription(BaseModel):
    """
    Active or historical subscription held by a tenant institution.
    """
    __tablename__ = "subscriptions"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    plan_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("subscription_plans.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    status: Mapped[SubscriptionStatus] = mapped_column(
        Enum(SubscriptionStatus, name="subscription_status_enum", create_type=False),
        nullable=False,
        default=SubscriptionStatus.TRIAL,
        index=True,
    )
    billing_cycle: Mapped[BillingCycle] = mapped_column(
        Enum(BillingCycle, name="billing_cycle_enum", create_type=False),
        nullable=False,
        default=BillingCycle.YEARLY,
    )
    current_period_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    current_period_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    trial_ends_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    canceled_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    grace_period_ends_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    is_auto_renew: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    payment_method: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # Relationships
    tenant: Mapped["Tenant"] = relationship("Tenant", back_populates="subscriptions")
    plan: Mapped["SubscriptionPlan"] = relationship("SubscriptionPlan", back_populates="subscriptions")
    invoices: Mapped[List["SubscriptionInvoice"]] = relationship(
        "SubscriptionInvoice", back_populates="subscription", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_subscriptions_tenant_status", "tenant_id", "status"),
    )


class SubscriptionInvoice(BaseModel):
    """
    Billed invoice generated for a tenant's subscription plan.
    """
    __tablename__ = "subscription_invoices"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    subscription_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("subscriptions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    invoice_number: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    subtotal: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    tax_amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0.0)
    discount_amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0.0)
    total_amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(10), nullable=False, default="INR")
    coupon_code: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    billing_cycle: Mapped[BillingCycle] = mapped_column(
        Enum(BillingCycle, name="billing_cycle_enum", create_type=False),
        nullable=False,
        default=BillingCycle.YEARLY,
    )
    billing_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    billing_address: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    line_items: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    status: Mapped[InvoiceStatus] = mapped_column(
        Enum(InvoiceStatus, name="invoice_status_enum", create_type=False),
        nullable=False,
        default=InvoiceStatus.ISSUED,
        index=True,
    )
    due_date: Mapped[date] = mapped_column(Date, nullable=False)
    paid_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    invoice_url: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)

    # Relationships
    tenant: Mapped["Tenant"] = relationship("Tenant", back_populates="invoices")
    subscription: Mapped["Subscription"] = relationship("Subscription", back_populates="invoices")
    payments: Mapped[List["SubscriptionPayment"]] = relationship(
        "SubscriptionPayment", back_populates="invoice", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_subscription_invoices_tenant_status", "tenant_id", "status"),
    )


class SubscriptionPayment(BaseModel):
    """
    Payment transaction record for a subscription invoice (via Razorpay, Stripe, etc.).
    """
    __tablename__ = "subscription_payments"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    invoice_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("subscription_invoices.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(10), nullable=False, default="INR")
    payment_method: Mapped[str] = mapped_column(String(50), nullable=False, default="RAZORPAY")
    gateway: Mapped[str] = mapped_column(String(50), nullable=False, default="razorpay")
    gateway_order_id: Mapped[Optional[str]] = mapped_column(String(100), index=True, nullable=True)
    gateway_payment_id: Mapped[Optional[str]] = mapped_column(String(100), index=True, nullable=True)
    gateway_signature: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    idempotency_key: Mapped[Optional[str]] = mapped_column(String(100), unique=True, index=True, nullable=True)
    transaction_reference: Mapped[Optional[str]] = mapped_column(String(255), unique=True, nullable=True, index=True)
    status: Mapped[PaymentStatus] = mapped_column(
        Enum(PaymentStatus, name="payment_status_enum", create_type=False),
        nullable=False,
        default=PaymentStatus.PENDING,
        index=True,
    )
    paid_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    failure_reason: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    # Relationships
    tenant: Mapped["Tenant"] = relationship("Tenant", back_populates="payments")
    invoice: Mapped["SubscriptionInvoice"] = relationship("SubscriptionInvoice", back_populates="payments")

    __table_args__ = (
        Index("ix_subscription_payments_tenant_status", "tenant_id", "status"),
    )


class WebhookEvent(BaseModel):
    """
    Idempotent store for incoming payment gateway webhooks.
    """
    __tablename__ = "webhook_events"

    event_id: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    gateway: Mapped[str] = mapped_column(String(50), nullable=False, default="razorpay")
    event_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    is_processed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    processed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
