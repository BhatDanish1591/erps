from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import Boolean, Enum, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel, TenantBaseModel
from app.models.enums import InstitutionType, TenantStatus

if TYPE_CHECKING:
    from app.models.academic import AcademicSession
    from app.models.auth import Membership, Role
    from app.models.subscription import Subscription, SubscriptionInvoice, SubscriptionPayment


class Tenant(BaseModel):
    """
    Core institution record. Represents a single school or college tenant on the platform.
    """
    __tablename__ = "tenants"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    institution_type: Mapped[InstitutionType] = mapped_column(
        Enum(InstitutionType, name="institution_type_enum"),
        nullable=False,
        default=InstitutionType.SCHOOL,
    )
    status: Mapped[TenantStatus] = mapped_column(
        Enum(TenantStatus, name="tenant_status_enum"),
        nullable=False,
        default=TenantStatus.TRIAL,
        index=True,
    )
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    phone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    address: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    city: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    state: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    country: Mapped[str] = mapped_column(String(100), nullable=False, default="India")
    postal_code: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    logo_url: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    timezone: Mapped[str] = mapped_column(String(50), nullable=False, default="Asia/Kolkata")
    currency: Mapped[str] = mapped_column(String(10), nullable=False, default="INR")
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)

    # Relationships
    domains: Mapped[List["TenantDomain"]] = relationship(
        "TenantDomain", back_populates="tenant", cascade="all, delete-orphan"
    )
    settings: Mapped[List["TenantSetting"]] = relationship(
        "TenantSetting", back_populates="tenant", cascade="all, delete-orphan"
    )
    memberships: Mapped[List["Membership"]] = relationship(
        "Membership", back_populates="tenant", cascade="all, delete-orphan"
    )
    roles: Mapped[List["Role"]] = relationship(
        "Role", back_populates="tenant", cascade="all, delete-orphan"
    )
    academic_sessions: Mapped[List["AcademicSession"]] = relationship(
        "AcademicSession", back_populates="tenant", cascade="all, delete-orphan"
    )
    subscriptions: Mapped[List["Subscription"]] = relationship(
        "Subscription", back_populates="tenant", cascade="all, delete-orphan"
    )
    invoices: Mapped[List["SubscriptionInvoice"]] = relationship(
        "SubscriptionInvoice", back_populates="tenant", cascade="all, delete-orphan"
    )
    payments: Mapped[List["SubscriptionPayment"]] = relationship(
        "SubscriptionPayment", back_populates="tenant", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_tenants_type_status", "institution_type", "status"),
    )


class TenantDomain(BaseModel):
    """
    Subdomains and custom domains linked to an institution tenant.
    e.g., 'springdale.edusaas.com' or 'portal.springdale.edu'.
    """
    __tablename__ = "tenant_domains"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    domain: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    tenant: Mapped["Tenant"] = relationship("Tenant", back_populates="domains")

    __table_args__ = (
        UniqueConstraint("domain", name="uq_tenant_domains_domain"),
        Index("ix_tenant_domains_tenant_primary", "tenant_id", "is_primary"),
    )


class TenantSetting(TenantBaseModel):
    """
    Configuration key-value pairs stored per tenant (e.g. branding, notification flags).
    """
    __tablename__ = "tenant_settings"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    key: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    value: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    is_public: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    tenant: Mapped["Tenant"] = relationship("Tenant", back_populates="settings")

    __table_args__ = (
        UniqueConstraint("tenant_id", "key", name="uq_tenant_settings_tenant_key"),
        Index("ix_tenant_settings_tenant_public", "tenant_id", "is_public"),
    )
