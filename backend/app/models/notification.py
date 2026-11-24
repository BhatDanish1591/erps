import uuid
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel, SoftDeleteMixin, TenantBaseModel


class TenantIntegration(BaseModel, SoftDeleteMixin):
    """
    Tenant-specific configuration and credentials for external third-party service providers.
    Supports Amazon SES, Resend, Meta WhatsApp Cloud API, MSG91, Firebase Cloud Messaging,
    Apple Push Notification service, Razorpay, and AWS S3 / Cloudflare R2.
    """
    __tablename__ = "tenant_integrations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    provider_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # EMAIL_SES, EMAIL_RESEND, WHATSAPP_META, SMS_MSG91, PUSH_FIREBASE, PUSH_APNS, PAYMENT_RAZORPAY, STORAGE_S3, STORAGE_R2
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    credentials_encrypted: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    settings: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    webhook_secret: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(
        String(30), default="UNTESTED", nullable=False
    )  # ACTIVE, INACTIVE, ERROR, UNTESTED
    last_tested_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    last_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    tenant: Mapped["Tenant"] = relationship("Tenant")

    __table_args__ = (
        UniqueConstraint("tenant_id", "provider_type", name="uq_tenant_integrations_provider"),
        Index("ix_tenant_integrations_tenant_provider", "tenant_id", "provider_type"),
        Index("ix_tenant_integrations_status", "tenant_id", "status"),
    )


class NotificationTemplate(BaseModel, SoftDeleteMixin):
    """
    Customizable notification templates for each event and channel (Email, WhatsApp, SMS, Push, In-App).
    Supports placeholders e.g. {{student_name}}, {{amount}}, {{due_date}}, etc.
    Also references WhatsApp approved template names and MSG91 DLT template IDs.
    """
    __tablename__ = "notification_templates"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )  # NULL indicates system platform fallback default
    event_type: Mapped[str] = mapped_column(
        String(60), nullable=False, index=True
    )  # STUDENT_ABSENT, EXAM_SCHEDULED, RESULTS_PUBLISHED, STUDY_MATERIAL_UPLOADED, ASSIGNMENT_CREATED, ASSIGNMENT_DEADLINE_APPROACHING, FEE_REMINDER, PAYMENT_CONFIRMED, ANNOUNCEMENT_PUBLISHED, TIMETABLE_CHANGED
    channel: Mapped[str] = mapped_column(
        String(30), nullable=False
    )  # EMAIL, WHATSAPP, SMS, PUSH, IN_APP
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    subject_template: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    body_template: Mapped[str] = mapped_column(Text, nullable=False)
    whatsapp_template_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    whatsapp_template_namespace: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    whatsapp_language: Mapped[str] = mapped_column(String(20), default="en_US", nullable=False)
    msg91_template_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    tenant: Mapped[Optional["Tenant"]] = relationship("Tenant")

    __table_args__ = (
        Index("ix_notif_templates_event_channel", "event_type", "channel"),
        Index("ix_notif_templates_tenant_event", "tenant_id", "event_type"),
    )


class UserNotificationPreference(BaseModel):
    """
    User notification preferences, category opt-outs, and quiet hours schedule.
    """
    __tablename__ = "user_notification_preferences"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Channel consent
    channel_email: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    channel_whatsapp: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    channel_sms: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    channel_push: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    channel_in_app: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Category preferences
    category_attendance: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    category_academic: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    category_examinations: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    category_finance: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    category_announcements: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Quiet hours
    quiet_hours_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    quiet_hours_start: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)  # e.g. "22:00"
    quiet_hours_end: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)    # e.g. "07:00"

    user: Mapped["User"] = relationship("User")

    __table_args__ = (
        UniqueConstraint("tenant_id", "user_id", name="uq_user_notif_prefs_tenant_user"),
        Index("ix_user_notif_prefs_tenant_user", "tenant_id", "user_id"),
    )


class NotificationOutbox(BaseModel):
    """
    Transactional Outbox table. Core domain events write into this table within
    the same database transaction as business mutations, guaranteeing zero data loss
    and non-blocking asynchronous processing.
    """
    __tablename__ = "notification_outbox"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    event_type: Mapped[str] = mapped_column(String(60), nullable=False, index=True)
    event_payload: Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(120), nullable=False)
    status: Mapped[str] = mapped_column(
        String(30), default="PENDING", nullable=False, index=True
    )  # PENDING, PROCESSING, PROCESSED, FAILED, CANCELLED
    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    max_retries: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    scheduled_for: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    processed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    __table_args__ = (
        UniqueConstraint("tenant_id", "idempotency_key", name="uq_notif_outbox_tenant_idempotency"),
        Index("ix_notif_outbox_tenant_status", "tenant_id", "status"),
        Index("ix_notif_outbox_status_sched", "status", "scheduled_for"),
    )


class NotificationLog(BaseModel):
    """
    Comprehensive delivery and audit log for every dispatched message across all channels.
    Tracks external provider message IDs, delivery statuses, failure reasons, and webhooks.
    """
    __tablename__ = "notification_logs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    outbox_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("notification_outbox.id", ondelete="SET NULL"),
        nullable=True,
    )
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    recipient: Mapped[str] = mapped_column(String(255), nullable=False)
    channel: Mapped[str] = mapped_column(
        String(30), nullable=False
    )  # EMAIL, WHATSAPP, SMS, PUSH, IN_APP
    provider: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # SES, RESEND, META_WHATSAPP, MSG91, FIREBASE, APNS, IN_APP
    event_type: Mapped[str] = mapped_column(String(60), nullable=False)
    subject: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    provider_message_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    status: Mapped[str] = mapped_column(
        String(30), default="QUEUED", nullable=False
    )  # QUEUED, DISPATCHED, DELIVERED, FAILED, BOUNCED, READ
    attempt_count: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    error_details: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    delivered_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    read_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("ix_notif_logs_tenant_channel_status", "tenant_id", "channel", "status"),
        Index("ix_notif_logs_tenant_event", "tenant_id", "event_type"),
        Index("ix_notif_logs_provider_msg_id", "provider_message_id"),
    )


class UserNotification(BaseModel):
    """
    In-app notification entity displayed in user navigation notification bell / inbox.
    """
    __tablename__ = "user_notifications"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    event_type: Mapped[str] = mapped_column(String(60), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    action_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    read_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    user: Mapped["User"] = relationship("User")

    __table_args__ = (
        Index("ix_user_notifs_tenant_user_read", "tenant_id", "user_id", "is_read"),
        Index("ix_user_notifs_user_created", "user_id", "created_at"),
    )
