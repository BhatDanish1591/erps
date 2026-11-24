from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.user import User
from app.permissions.rbac import get_active_tenant_id, get_current_user, require_any_role
from app.schemas.notification import (
    EmitNotificationEventRequest,
    NotificationLogResponse,
    NotificationOutboxResponse,
    NotificationTemplateCreate,
    NotificationTemplateResponse,
    NotificationTemplateUpdate,
    UserNotificationPreferenceResponse,
    UserNotificationPreferenceUpdate,
    UserNotificationResponse,
    WebhookResponse,
)
from app.services.notification_service import NotificationService

router = APIRouter(prefix="/notifications", tags=["Notifications & Outbox"])


def get_notification_service(session: AsyncSession = Depends(get_db)) -> NotificationService:
    return NotificationService(session)


# ─────────────────────────────────────────────────────────────────────────────
# 1. In-App Notifications (User Bell / Activity)
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/in-app",
    response_model=List[UserNotificationResponse],
    summary="List in-app notifications for authenticated user",
)
async def list_user_notifications(
    unread_only: bool = Query(False),
    limit: int = Query(50, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    service: NotificationService = Depends(get_notification_service),
):
    return await service.repo.list_user_notifications(
        tenant_id=tenant_id,
        user_id=current_user.id,
        unread_only=unread_only,
        limit=limit,
    )


@router.post(
    "/in-app/{notification_id}/read",
    response_model=Optional[UserNotificationResponse],
    summary="Mark single in-app notification as read",
)
async def mark_notification_read(
    notification_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    service: NotificationService = Depends(get_notification_service),
):
    notif = await service.repo.mark_user_notification_read(
        tenant_id=tenant_id, user_id=current_user.id, notification_id=notification_id
    )
    if not notif:
        raise HTTPException(status_code=404, detail="Notification not found")
    return notif


@router.post(
    "/in-app/mark-all-read",
    summary="Mark all in-app notifications as read for current user",
)
async def mark_all_notifications_read(
    current_user: User = Depends(get_current_user),
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    service: NotificationService = Depends(get_notification_service),
):
    count = await service.repo.mark_all_user_notifications_read(
        tenant_id=tenant_id, user_id=current_user.id
    )
    return {"message": "All notifications marked as read", "count": count}


# ─────────────────────────────────────────────────────────────────────────────
# 2. User Notification Preferences
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/preferences",
    response_model=UserNotificationPreferenceResponse,
    summary="Get notification channels and category preferences",
)
async def get_user_preferences(
    current_user: User = Depends(get_current_user),
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    service: NotificationService = Depends(get_notification_service),
):
    return await service.repo.get_or_create_user_preferences(
        tenant_id=tenant_id, user_id=current_user.id
    )


@router.put(
    "/preferences",
    response_model=UserNotificationPreferenceResponse,
    summary="Update notification preferences and quiet hours",
)
async def update_user_preferences(
    data: UserNotificationPreferenceUpdate,
    current_user: User = Depends(get_current_user),
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    service: NotificationService = Depends(get_notification_service),
):
    return await service.repo.update_user_preferences(
        tenant_id=tenant_id,
        user_id=current_user.id,
        updates=data.model_dump(exclude_unset=True),
    )


# ─────────────────────────────────────────────────────────────────────────────
# 3. Transactional Outbox & Non-blocking Emission
# ─────────────────────────────────────────────────────────────────────────────

@router.post(
    "/emit",
    response_model=NotificationOutboxResponse,
    summary="Non-blocking event emission into transactional outbox",
)
async def emit_notification_event(
    data: EmitNotificationEventRequest,
    current_user: User = Depends(get_current_user),
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    service: NotificationService = Depends(get_notification_service),
):
    """
    Enqueues a notification event into the outbox table.
    Core API requests never block on external providers.
    """
    outbox = await service.emit_event(
        tenant_id=tenant_id,
        event_type=data.event_type,
        payload=data.event_payload,
        idempotency_key=data.idempotency_key,
    )
    return outbox


@router.get(
    "/outbox",
    response_model=List[NotificationOutboxResponse],
    summary="List recent outbox entries (Institution Admin / Super Admin)",
    dependencies=[Depends(require_any_role(["INSTITUTION_ADMIN", "SUPER_ADMIN"]))],
)
async def list_outbox_entries(
    limit: int = Query(50, ge=1, le=100),
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    service: NotificationService = Depends(get_notification_service),
):
    return await service.repo.list_outbox_entries(tenant_id=tenant_id, limit=limit)


@router.post(
    "/outbox/process-batch",
    summary="Trigger immediate processing of pending outbox items (Worker/Admin)",
    dependencies=[Depends(require_any_role(["INSTITUTION_ADMIN", "SUPER_ADMIN"]))],
)
async def process_outbox_batch(
    limit: int = Query(50, ge=1, le=100),
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    service: NotificationService = Depends(get_notification_service),
):
    processed = await service.process_pending_outbox_batch(limit=limit, tenant_id=tenant_id)
    return {"message": "Outbox batch processed", "processed_count": processed}


# ─────────────────────────────────────────────────────────────────────────────
# 4. Delivery Logs & Auditing
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/logs",
    response_model=List[NotificationLogResponse],
    summary="List notification delivery logs across all channels",
    dependencies=[Depends(require_any_role(["INSTITUTION_ADMIN", "SUPER_ADMIN"]))],
)
async def list_notification_logs(
    channel: Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    event_type: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=100),
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    service: NotificationService = Depends(get_notification_service),
):
    return await service.repo.list_logs(
        tenant_id=tenant_id,
        channel=channel,
        status=status_filter,
        event_type=event_type,
        limit=limit,
    )


# ─────────────────────────────────────────────────────────────────────────────
# 5. Templates Management
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/templates",
    response_model=List[NotificationTemplateResponse],
    summary="List notification templates for institution",
    dependencies=[Depends(require_any_role(["INSTITUTION_ADMIN", "SUPER_ADMIN"]))],
)
async def list_templates(
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    service: NotificationService = Depends(get_notification_service),
):
    return await service.repo.list_templates(tenant_id=tenant_id)


@router.post(
    "/templates",
    response_model=NotificationTemplateResponse,
    summary="Create or customize institution notification template",
    dependencies=[Depends(require_any_role(["INSTITUTION_ADMIN", "SUPER_ADMIN"]))],
)
async def create_template(
    data: NotificationTemplateCreate,
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    service: NotificationService = Depends(get_notification_service),
):
    return await service.repo.create_template(
        tenant_id=tenant_id,
        event_type=data.event_type,
        channel=data.channel,
        name=data.name,
        subject_template=data.subject_template,
        body_template=data.body_template,
        whatsapp_template_name=data.whatsapp_template_name,
        whatsapp_template_namespace=data.whatsapp_template_namespace,
        whatsapp_language=data.whatsapp_language,
        msg91_template_id=data.msg91_template_id,
    )


# ─────────────────────────────────────────────────────────────────────────────
# 6. Provider Webhooks (Secure External Endpoints)
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/webhooks/whatsapp", summary="Meta WhatsApp Webhook Verification")
async def verify_whatsapp_webhook(
    hub_mode: Optional[str] = Query(None, alias="hub.mode"),
    hub_challenge: Optional[str] = Query(None, alias="hub.challenge"),
    hub_verify_token: Optional[str] = Query(None, alias="hub.verify_token"),
):
    if hub_mode == "subscribe" and hub_challenge:
        return Response(content=hub_challenge, media_type="text/plain")
    return Response(content="Verification failed", status_code=403)


@router.post("/webhooks/whatsapp", response_model=WebhookResponse, summary="Meta WhatsApp Delivery Status Webhook")
async def receive_whatsapp_webhook(
    payload: Dict[str, Any],
    service: NotificationService = Depends(get_notification_service),
):
    res = await service.handle_whatsapp_webhook(payload)
    return WebhookResponse(
        status="success",
        processed=True,
        message=f"WhatsApp webhook processed: {res.get('updated', 0)} statuses updated",
    )


@router.post("/webhooks/ses", response_model=WebhookResponse, summary="Amazon SES SNS Event Webhook")
async def receive_ses_webhook(
    payload: Dict[str, Any],
    service: NotificationService = Depends(get_notification_service),
):
    res = await service.handle_ses_webhook(payload)
    return WebhookResponse(
        status="success",
        processed=res.get("updated", False),
        message=f"SES webhook event processed for message {res.get('message_id')}",
    )


@router.post("/webhooks/msg91", response_model=WebhookResponse, summary="MSG91 SMS DLR Webhook")
async def receive_msg91_webhook(
    payload: Dict[str, Any],
    service: NotificationService = Depends(get_notification_service),
):
    res = await service.handle_msg91_webhook(payload)
    return WebhookResponse(
        status="success",
        processed=res.get("updated", False),
        message=f"MSG91 DLR processed for request {res.get('request_id')}",
    )
