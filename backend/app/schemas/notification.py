import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


# ─────────────────────────────────────────────────────────────────────────────
# 1. Tenant Integrations
# ─────────────────────────────────────────────────────────────────────────────

class TenantIntegrationBase(BaseModel):
    provider_type: str = Field(..., description="EMAIL_SES, EMAIL_RESEND, WHATSAPP_META, SMS_MSG91, PUSH_FIREBASE, PUSH_APNS, PAYMENT_RAZORPAY, STORAGE_S3, STORAGE_R2")
    is_enabled: bool = True
    credentials: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Sensitive credentials (API keys, secrets, tokens)")
    settings: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Non-sensitive settings (region, bucket, sender ID, etc.)")
    webhook_secret: Optional[str] = None


class TenantIntegrationCreate(TenantIntegrationBase):
    pass


class TenantIntegrationUpdate(BaseModel):
    is_enabled: Optional[bool] = None
    credentials: Optional[Dict[str, Any]] = None
    settings: Optional[Dict[str, Any]] = None
    webhook_secret: Optional[str] = None


class TenantIntegrationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    provider_type: str
    is_enabled: bool
    masked_credentials: Optional[Dict[str, str]] = None
    settings: Optional[Dict[str, Any]] = None
    status: str
    last_tested_at: Optional[datetime] = None
    last_error: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class TestIntegrationRequest(BaseModel):
    provider_type: str
    recipient: Optional[str] = Field(None, description="Test destination email, phone number, or token")


class TestIntegrationResponse(BaseModel):
    success: bool
    provider_type: str
    message: str
    details: Optional[Dict[str, Any]] = None


# ─────────────────────────────────────────────────────────────────────────────
# 2. Notification Templates
# ─────────────────────────────────────────────────────────────────────────────

class NotificationTemplateBase(BaseModel):
    event_type: str = Field(..., description="STUDENT_ABSENT, EXAM_SCHEDULED, RESULTS_PUBLISHED, etc.")
    channel: str = Field(..., description="EMAIL, WHATSAPP, SMS, PUSH, IN_APP")
    name: str = Field(..., max_length=150)
    subject_template: Optional[str] = Field(None, max_length=255)
    body_template: str
    whatsapp_template_name: Optional[str] = None
    whatsapp_template_namespace: Optional[str] = None
    whatsapp_language: str = "en_US"
    msg91_template_id: Optional[str] = None
    is_active: bool = True


class NotificationTemplateCreate(NotificationTemplateBase):
    pass


class NotificationTemplateUpdate(BaseModel):
    name: Optional[str] = None
    subject_template: Optional[str] = None
    body_template: Optional[str] = None
    whatsapp_template_name: Optional[str] = None
    whatsapp_template_namespace: Optional[str] = None
    whatsapp_language: Optional[str] = None
    msg91_template_id: Optional[str] = None
    is_active: Optional[bool] = None


class NotificationTemplateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: Optional[uuid.UUID] = None
    event_type: str
    channel: str
    name: str
    subject_template: Optional[str] = None
    body_template: str
    whatsapp_template_name: Optional[str] = None
    whatsapp_template_namespace: Optional[str] = None
    whatsapp_language: str
    msg91_template_id: Optional[str] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime


# ─────────────────────────────────────────────────────────────────────────────
# 3. User Notification Preferences
# ─────────────────────────────────────────────────────────────────────────────

class UserNotificationPreferenceUpdate(BaseModel):
    channel_email: Optional[bool] = None
    channel_whatsapp: Optional[bool] = None
    channel_sms: Optional[bool] = None
    channel_push: Optional[bool] = None
    channel_in_app: Optional[bool] = None
    category_attendance: Optional[bool] = None
    category_academic: Optional[bool] = None
    category_examinations: Optional[bool] = None
    category_finance: Optional[bool] = None
    category_announcements: Optional[bool] = None
    quiet_hours_enabled: Optional[bool] = None
    quiet_hours_start: Optional[str] = None
    quiet_hours_end: Optional[str] = None


class UserNotificationPreferenceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    user_id: uuid.UUID
    channel_email: bool
    channel_whatsapp: bool
    channel_sms: bool
    channel_push: bool
    channel_in_app: bool
    category_attendance: bool
    category_academic: bool
    category_examinations: bool
    category_finance: bool
    category_announcements: bool
    quiet_hours_enabled: bool
    quiet_hours_start: Optional[str] = None
    quiet_hours_end: Optional[str] = None


# ─────────────────────────────────────────────────────────────────────────────
# 4. Outbox & Notification Dispatch
# ─────────────────────────────────────────────────────────────────────────────

class EmitNotificationEventRequest(BaseModel):
    event_type: str
    event_payload: Dict[str, Any]
    idempotency_key: Optional[str] = None


class NotificationOutboxResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    event_type: str
    event_payload: Dict[str, Any]
    idempotency_key: str
    status: str
    retry_count: int
    max_retries: int
    scheduled_for: datetime
    processed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    created_at: datetime


# ─────────────────────────────────────────────────────────────────────────────
# 5. Delivery Logs & In-App Notifications
# ─────────────────────────────────────────────────────────────────────────────

class NotificationLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    outbox_id: Optional[uuid.UUID] = None
    user_id: Optional[uuid.UUID] = None
    recipient: str
    channel: str
    provider: str
    event_type: str
    subject: Optional[str] = None
    content: Optional[str] = None
    provider_message_id: Optional[str] = None
    status: str
    attempt_count: int
    error_details: Optional[str] = None
    metadata_json: Optional[Dict[str, Any]] = None
    delivered_at: Optional[datetime] = None
    read_at: Optional[datetime] = None
    created_at: datetime


class UserNotificationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    user_id: uuid.UUID
    event_type: str
    title: str
    message: str
    action_url: Optional[str] = None
    is_read: bool
    read_at: Optional[datetime] = None
    created_at: datetime


# ─────────────────────────────────────────────────────────────────────────────
# 6. Webhooks
# ─────────────────────────────────────────────────────────────────────────────

class WebhookResponse(BaseModel):
    status: str = "received"
    processed: bool = True
    message: str
