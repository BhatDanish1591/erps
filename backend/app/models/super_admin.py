from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.tenant import Tenant
    from app.models.user import User


class GlobalAnnouncement(BaseModel):
    """
    Platform-wide announcements published by Super Admin to institutions and users.
    """
    __tablename__ = "global_announcements"

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    target_role: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # None = ALL
    priority: Mapped[str] = mapped_column(String(20), nullable=False, default="NORMAL")  # LOW, NORMAL, HIGH, URGENT
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_by_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    created_by: Mapped[Optional["User"]] = relationship("User", foreign_keys=[created_by_user_id])


class SupportTicket(BaseModel):
    """
    Tenant support requests and inquiries managed centrally by Super Admin.
    """
    __tablename__ = "support_tickets"

    ticket_number: Mapped[str] = mapped_column(String(32), unique=True, nullable=False, index=True)
    tenant_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    subject: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(String(50), nullable=False, default="GENERAL")
    priority: Mapped[str] = mapped_column(String(20), nullable=False, default="MEDIUM")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="OPEN", index=True)
    assigned_to_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    tenant: Mapped[Optional["Tenant"]] = relationship("Tenant")
    user: Mapped["User"] = relationship("User", foreign_keys=[user_id])
    assigned_to: Mapped[Optional["User"]] = relationship("User", foreign_keys=[assigned_to_user_id])
    replies: Mapped[List["SupportTicketReply"]] = relationship(
        "SupportTicketReply", back_populates="ticket", cascade="all, delete-orphan", order_by="SupportTicketReply.created_at"
    )


class SupportTicketReply(BaseModel):
    """
    Threaded replies and internal staff notes on support tickets.
    """
    __tablename__ = "support_ticket_replies"

    ticket_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("support_tickets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    message: Mapped[str] = mapped_column(Text, nullable=False)
    is_internal: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    ticket: Mapped["SupportTicket"] = relationship("SupportTicket", back_populates="replies")
    user: Mapped["User"] = relationship("User")


class PlatformSetting(BaseModel):
    """
    Global platform configuration key-value store for Super Admin.
    """
    __tablename__ = "platform_settings"

    category: Mapped[str] = mapped_column(String(50), nullable=False, default="GENERAL", index=True)
    key: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    value: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    description: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    is_secret: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class PlatformIntegration(BaseModel):
    """
    SaaS third-party provider status and configuration (Razorpay, WhatsApp, SES, MSG91, FCM, S3).
    """
    __tablename__ = "platform_integrations"

    provider: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    config: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="NOT_CONFIGURED")
    last_tested_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
