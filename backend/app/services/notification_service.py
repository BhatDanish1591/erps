import json
import logging
import uuid
from datetime import datetime, time, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy import select

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundException, ValidationException
from app.models.notification import (
    NotificationLog,
    NotificationOutbox,
    NotificationTemplate,
    TenantIntegration,
    UserNotification,
    UserNotificationPreference,
)
from app.repositories.notification import NotificationRepository
from app.services.channel_adapters.email import EmailChannelAdapter
from app.services.channel_adapters.push import PushChannelAdapter
from app.services.channel_adapters.sms import SMSChannelAdapter
from app.services.channel_adapters.whatsapp import WhatsAppChannelAdapter

logger = logging.getLogger(__name__)

# Event Category Mapping
EVENT_CATEGORY_MAP = {
    "STUDENT_ABSENT": "category_attendance",
    "EXAM_SCHEDULED": "category_examinations",
    "RESULTS_PUBLISHED": "category_examinations",
    "STUDY_MATERIAL_UPLOADED": "category_academic",
    "ASSIGNMENT_CREATED": "category_academic",
    "ASSIGNMENT_DEADLINE_APPROACHING": "category_academic",
    "FEE_REMINDER": "category_finance",
    "PAYMENT_CONFIRMED": "category_finance",
    "ANNOUNCEMENT_PUBLISHED": "category_announcements",
    "TIMETABLE_CHANGED": "category_academic",
}

# Standard Default Templates
DEFAULT_TEMPLATES = [
    {
        "event_type": "STUDENT_ABSENT",
        "channel": "SMS",
        "name": "Student Absence SMS",
        "body_template": "Dear Parent, your ward {{student_name}} was marked ABSENT on {{date}}. Please contact institution admin if this is an error.",
        "msg91_template_id": "absent_sms_01",
    },
    {
        "event_type": "STUDENT_ABSENT",
        "channel": "WHATSAPP",
        "name": "Student Absence WhatsApp",
        "body_template": "Dear Parent, your ward {{student_name}} was marked ABSENT on {{date}}. For questions, please contact the institution.",
        "whatsapp_template_name": "student_absence_alert_v1",
    },
    {
        "event_type": "EXAM_SCHEDULED",
        "channel": "EMAIL",
        "name": "Examination Scheduled Email",
        "subject_template": "Exam Scheduled: {{exam_title}}",
        "body_template": "<p>Dear Student/Parent,</p><p>An examination <strong>{{exam_title}}</strong> has been scheduled starting on <strong>{{start_time}}</strong>.</p><p>Please review the exam timetable on your dashboard.</p>",
    },
    {
        "event_type": "RESULTS_PUBLISHED",
        "channel": "EMAIL",
        "name": "Results Published Email",
        "subject_template": "Report Card Published: {{term_name}}",
        "body_template": "<p>Dear Student/Parent,</p><p>Examination results for <strong>{{term_name}}</strong> have been approved and published. Score: {{total_marks}} ({{percentage}}%).</p>",
    },
    {
        "event_type": "FEE_REMINDER",
        "channel": "WHATSAPP",
        "name": "Fee Due Reminder WhatsApp",
        "body_template": "Dear Parent, fee invoice {{invoice_number}} of INR {{amount}} for {{student_name}} is due on {{due_date}}. Pay online via your Parent Portal.",
        "whatsapp_template_name": "fee_payment_reminder_v1",
    },
    {
        "event_type": "PAYMENT_CONFIRMED",
        "channel": "EMAIL",
        "name": "Fee Payment Confirmation Email",
        "subject_template": "Fee Payment Receipt: {{receipt_number}}",
        "body_template": "<p>Dear Parent,</p><p>We have successfully received payment of <strong>INR {{amount}}</strong> for {{student_name}}. Receipt #{{receipt_number}} has been generated.</p>",
    },
    {
        "event_type": "ANNOUNCEMENT_PUBLISHED",
        "channel": "IN_APP",
        "name": "Institution Announcement In-App",
        "body_template": "{{title}}: {{message}}",
    },
]


class NotificationService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = NotificationRepository(session)
        self.email_adapter = EmailChannelAdapter()
        self.whatsapp_adapter = WhatsAppChannelAdapter()
        self.sms_adapter = SMSChannelAdapter()
        self.push_adapter = PushChannelAdapter()

    # ─────────────────────────────────────────────────────────────────────────
    # 1. Outbox Event Enqueueing (Non-blocking domain emission)
    # ─────────────────────────────────────────────────────────────────────────

    async def emit_event(
        self,
        tenant_id: uuid.UUID,
        event_type: str,
        payload: Dict[str, Any],
        idempotency_key: Optional[str] = None,
    ) -> NotificationOutbox:
        """
        Enqueues an event into the transactional outbox table.
        Does NOT block on external HTTP calls.
        """
        outbox = await self.repo.enqueue_outbox_event(
            tenant_id=tenant_id,
            event_type=event_type,
            payload=payload,
            idempotency_key=idempotency_key,
        )
        return outbox

    # ─────────────────────────────────────────────────────────────────────────
    # 2. Outbox Processor (Worker Execution)
    # ─────────────────────────────────────────────────────────────────────────

    async def process_outbox_item(self, outbox_id: uuid.UUID) -> bool:
        outbox = await self.session.scalar(
            select(NotificationOutbox).where(NotificationOutbox.id == outbox_id)
            .with_for_update(skip_locked=True).execution_options(populate_existing=True)
        )
        if outbox is None:
            return False
        if outbox.status == "PROCESSED":
            await self.session.commit()
            return True

        outbox.status = "PROCESSING"
        await self.session.flush()

        try:
            payload = outbox.event_payload or {}
            event_type = outbox.event_type
            tenant_id = outbox.tenant_id

            # Extract recipients from payload
            # Format: recipients = [{"user_id": ..., "email": ..., "phone": ..., "push_token": ...}]
            recipients = payload.get("recipients", [])
            if not recipients and payload.get("user_id"):
                recipients = [{
                    "user_id": payload.get("user_id"),
                    "email": payload.get("email"),
                    "phone": payload.get("phone"),
                    "push_token": payload.get("push_token"),
                    "name": payload.get("student_name") or payload.get("user_name"),
                }]

            category_field = EVENT_CATEGORY_MAP.get(event_type, "category_announcements")

            # Load integrations for this tenant
            integrations = await self.repo.list_integrations(tenant_id)
            integration_map = {i.provider_type: i for i in integrations if i.is_enabled}

            for rec in recipients:
                user_id_raw = rec.get("user_id")
                user_id = uuid.UUID(str(user_id_raw)) if user_id_raw else None

                # Check user preferences
                prefs = None
                if user_id:
                    prefs = await self.repo.get_or_create_user_preferences(tenant_id, user_id)
                    # Check if category is enabled
                    if hasattr(prefs, category_field) and not getattr(prefs, category_field):
                        logger.info(f"User {user_id} opted out of event category {category_field}")
                        continue

                # 1. Dispatch IN_APP notification
                if (not prefs or prefs.channel_in_app) and user_id:
                    title = payload.get("title") or event_type.replace("_", " ").title()
                    message = payload.get("message") or f"Notification for {event_type}"
                    await self.repo.create_user_notification(
                        tenant_id=tenant_id,
                        user_id=user_id,
                        event_type=event_type,
                        title=title,
                        message=message,
                        action_url=payload.get("action_url"),
                    )
                    await self.repo.create_log(
                        tenant_id=tenant_id,
                        outbox_id=outbox.id,
                        user_id=user_id,
                        recipient=str(user_id),
                        channel="IN_APP",
                        provider="INTERNAL",
                        event_type=event_type,
                        status="DELIVERED",
                        subject=title,
                        content=message,
                    )

                # 2. Dispatch EMAIL
                email_address = rec.get("email")
                if email_address and (not prefs or prefs.channel_email):
                    template = await self.repo.get_template(tenant_id, event_type, "EMAIL")
                    subject = template.subject_template if template and template.subject_template else f"Update: {event_type}"
                    body = template.body_template if template else payload.get("message", "New notification received.")
                    # Render variables
                    subject = self._render_template(subject, payload)
                    body = self._render_template(body, payload)

                    email_config = (
                        integration_map.get("EMAIL_RESEND")
                        or integration_map.get("EMAIL_SES")
                    )
                    cfg_dict = {
                        "provider_type": email_config.provider_type if email_config else "EMAIL_RESEND",
                        "credentials": email_config.credentials_encrypted if email_config else {},
                        "settings": email_config.settings if email_config else {},
                    }

                    result = await self.email_adapter.send(
                        recipient=email_address,
                        subject=subject,
                        content=body,
                        tenant_config=cfg_dict,
                    )
                    await self.repo.create_log(
                        tenant_id=tenant_id,
                        outbox_id=outbox.id,
                        user_id=user_id,
                        recipient=email_address,
                        channel="EMAIL",
                        provider=result.provider,
                        event_type=event_type,
                        status=result.status,
                        subject=subject,
                        content=body,
                        provider_message_id=result.provider_message_id,
                        error_details=result.error_details,
                        metadata_json=result.metadata,
                    )

                # 3. Dispatch WHATSAPP
                phone = rec.get("phone")
                if phone and (not prefs or prefs.channel_whatsapp):
                    template = await self.repo.get_template(tenant_id, event_type, "WHATSAPP")
                    body = template.body_template if template else payload.get("message", "Notice from your institution.")
                    body = self._render_template(body, payload)

                    wa_config = integration_map.get("WHATSAPP_META")
                    cfg_dict = {
                        "provider_type": "WHATSAPP_META",
                        "credentials": wa_config.credentials_encrypted if wa_config else {},
                        "settings": wa_config.settings if wa_config else {},
                    }
                    tmpl_meta = {
                        "whatsapp_template_name": template.whatsapp_template_name if template else None,
                        "whatsapp_language": template.whatsapp_language if template else "en_US",
                        "parameters": [payload.get("student_name", "Student"), payload.get("date", "Today")],
                    }

                    result = await self.whatsapp_adapter.send(
                        recipient=phone,
                        subject=None,
                        content=body,
                        template_meta=tmpl_meta,
                        tenant_config=cfg_dict,
                    )
                    await self.repo.create_log(
                        tenant_id=tenant_id,
                        outbox_id=outbox.id,
                        user_id=user_id,
                        recipient=phone,
                        channel="WHATSAPP",
                        provider=result.provider,
                        event_type=event_type,
                        status=result.status,
                        content=body,
                        provider_message_id=result.provider_message_id,
                        error_details=result.error_details,
                        metadata_json=result.metadata,
                    )

                # 4. Dispatch SMS
                if phone and (not prefs or prefs.channel_sms):
                    template = await self.repo.get_template(tenant_id, event_type, "SMS")
                    body = template.body_template if template else payload.get("message", "Notice from your institution.")
                    body = self._render_template(body, payload)

                    sms_config = integration_map.get("SMS_MSG91")
                    cfg_dict = {
                        "provider_type": "SMS_MSG91",
                        "credentials": sms_config.credentials_encrypted if sms_config else {},
                        "settings": sms_config.settings if sms_config else {},
                    }
                    tmpl_meta = {
                        "msg91_template_id": template.msg91_template_id if template else None,
                        "variables": {k: str(v) for k, v in payload.items() if isinstance(v, (str, int, float))},
                    }

                    result = await self.sms_adapter.send(
                        recipient=phone,
                        subject=None,
                        content=body,
                        template_meta=tmpl_meta,
                        tenant_config=cfg_dict,
                    )
                    await self.repo.create_log(
                        tenant_id=tenant_id,
                        outbox_id=outbox.id,
                        user_id=user_id,
                        recipient=phone,
                        channel="SMS",
                        provider=result.provider,
                        event_type=event_type,
                        status=result.status,
                        content=body,
                        provider_message_id=result.provider_message_id,
                        error_details=result.error_details,
                        metadata_json=result.metadata,
                    )

                # 5. Dispatch PUSH
                push_token = rec.get("push_token")
                if push_token and (not prefs or prefs.channel_push):
                    title = payload.get("title") or event_type.replace("_", " ").title()
                    body = payload.get("message", "New notification")
                    push_config = integration_map.get("PUSH_FIREBASE") or integration_map.get("PUSH_APNS")
                    cfg_dict = {
                        "provider_type": push_config.provider_type if push_config else "PUSH_FIREBASE",
                        "credentials": push_config.credentials_encrypted if push_config else {},
                        "settings": push_config.settings if push_config else {},
                    }
                    result = await self.push_adapter.send(
                        recipient=push_token,
                        subject=title,
                        content=body,
                        tenant_config=cfg_dict,
                    )
                    await self.repo.create_log(
                        tenant_id=tenant_id,
                        outbox_id=outbox.id,
                        user_id=user_id,
                        recipient=push_token[:30],
                        channel="PUSH",
                        provider=result.provider,
                        event_type=event_type,
                        status=result.status,
                        subject=title,
                        content=body,
                        provider_message_id=result.provider_message_id,
                        error_details=result.error_details,
                    )

            outbox.status = "PROCESSED"
            outbox.processed_at = datetime.now(timezone.utc)
            await self.session.commit()
            return True

        except Exception as ex:
            logger.error(f"Failed to process outbox item {outbox_id}: {ex}")
            outbox.retry_count += 1
            outbox.error_message = str(ex)
            if outbox.retry_count >= outbox.max_retries:
                outbox.status = "FAILED"
            else:
                outbox.status = "PENDING"
            await self.session.commit()
            return False

    async def process_pending_outbox_batch(self, limit: int = 50, tenant_id: Optional[uuid.UUID] = None) -> int:
        items = await self.repo.get_pending_outbox_items(limit=limit, tenant_id=tenant_id)
        processed_count = 0
        for item in items:
            success = await self.process_outbox_item(item.id)
            if success:
                processed_count += 1
        return processed_count

    # ─────────────────────────────────────────────────────────────────────────
    # 3. Webhook Handling
    # ─────────────────────────────────────────────────────────────────────────

    async def handle_whatsapp_webhook(self, body: Dict[str, Any]) -> Dict[str, Any]:
        """
        Processes Meta WhatsApp Cloud API status webhook callbacks:
        sent, delivered, read, failed.
        """
        entries = body.get("entry", [])
        updated = 0
        for entry in entries:
            for change in entry.get("changes", []):
                val = change.get("value", {})
                statuses = val.get("statuses", [])
                for st in statuses:
                    wamid = st.get("id")
                    status_str = st.get("status")  # sent, delivered, read, failed
                    if wamid and status_str:
                        log = await self.repo.get_log_by_provider_message_id(wamid)
                        if log:
                            if status_str == "delivered":
                                log.status = "DELIVERED"
                                log.delivered_at = datetime.now(timezone.utc)
                            elif status_str == "read":
                                log.status = "READ"
                                log.read_at = datetime.now(timezone.utc)
                            elif status_str == "failed":
                                log.status = "FAILED"
                                errors = st.get("errors", [])
                                log.error_details = json.dumps(errors) if errors else "WhatsApp delivery failure"
                            updated += 1
        await self.session.commit()
        return {"updated": updated}

    async def handle_ses_webhook(self, body: Dict[str, Any]) -> Dict[str, Any]:
        """
        Processes Amazon SES SNS notification payload (Delivery, Bounce, Complaint).
        """
        notification_type = body.get("notificationType") or body.get("eventType")
        mail = body.get("mail", {})
        msg_id = mail.get("messageId")

        if msg_id:
            log = await self.repo.get_log_by_provider_message_id(msg_id)
            if log:
                if notification_type in ("Delivery", "delivered"):
                    log.status = "DELIVERED"
                    log.delivered_at = datetime.now(timezone.utc)
                elif notification_type in ("Bounce", "bounce"):
                    log.status = "BOUNCED"
                    log.error_details = json.dumps(body.get("bounce", {}))
                await self.session.commit()
                return {"updated": True, "message_id": msg_id, "status": log.status}
        return {"updated": False}

    async def handle_msg91_webhook(self, body: Dict[str, Any]) -> Dict[str, Any]:
        """
        Processes MSG91 DLR delivery reports.
        """
        request_id = body.get("requestId") or body.get("request_id")
        desc = body.get("description") or body.get("status")
        if request_id:
            log = await self.repo.get_log_by_provider_message_id(request_id)
            if log:
                if desc and "deliver" in desc.lower():
                    log.status = "DELIVERED"
                    log.delivered_at = datetime.now(timezone.utc)
                else:
                    log.status = "FAILED"
                    log.error_details = desc
                await self.session.commit()
                return {"updated": True, "request_id": request_id}
        return {"updated": False}

    # ─────────────────────────────────────────────────────────────────────────
    # 4. Tenant Integration Testing
    # ─────────────────────────────────────────────────────────────────────────

    async def test_integration(
        self, tenant_id: uuid.UUID, provider_type: str, recipient: Optional[str] = None
    ) -> Dict[str, Any]:
        integration = await self.repo.get_integration(tenant_id, provider_type)
        if not integration or not integration.is_enabled:
            return {
                "success": False,
                "provider_type": provider_type,
                "message": f"Integration {provider_type} is not configured or disabled.",
            }

        cfg_dict = {
            "provider_type": provider_type,
            "credentials": integration.credentials_encrypted or {},
            "settings": integration.settings or {},
        }

        try:
            if "EMAIL" in provider_type:
                target = recipient or "test@example.com"
                result = await self.email_adapter.send(
                    recipient=target,
                    subject="EduSaaS Integration Connection Test",
                    content="<p>This is a test notification verifying your institution email integration.</p>",
                    tenant_config=cfg_dict,
                )
            elif "WHATSAPP" in provider_type:
                target = recipient or "919876543210"
                result = await self.whatsapp_adapter.send(
                    recipient=target,
                    subject=None,
                    content="EduSaaS WhatsApp Integration Connection Test",
                    tenant_config=cfg_dict,
                )
            elif "SMS" in provider_type:
                target = recipient or "919876543210"
                result = await self.sms_adapter.send(
                    recipient=target,
                    subject=None,
                    content="EduSaaS SMS Connection Test",
                    tenant_config=cfg_dict,
                )
            elif "PUSH" in provider_type:
                target = recipient or "sample_device_fcm_token_12345678"
                result = await self.push_adapter.send(
                    recipient=target,
                    subject="Connection Test",
                    content="EduSaaS Push Integration Test",
                    tenant_config=cfg_dict,
                )
            else:
                result = None

            if result and result.success:
                integration.status = "ACTIVE"
                integration.last_tested_at = datetime.now(timezone.utc)
                integration.last_error = None
                await self.session.commit()
                return {
                    "success": True,
                    "provider_type": provider_type,
                    "message": f"{provider_type} integration test succeeded.",
                    "details": result.metadata,
                }
            else:
                err = result.error_details if result else "Unsupported test provider"
                integration.status = "ERROR"
                integration.last_tested_at = datetime.now(timezone.utc)
                integration.last_error = err
                await self.session.commit()
                return {
                    "success": False,
                    "provider_type": provider_type,
                    "message": f"{provider_type} integration test failed: {err}",
                }
        except Exception as ex:
            integration.status = "ERROR"
            integration.last_tested_at = datetime.now(timezone.utc)
            integration.last_error = str(ex)
            await self.session.commit()
            return {
                "success": False,
                "provider_type": provider_type,
                "message": f"Connection test exception: {ex}",
            }

    # ─────────────────────────────────────────────────────────────────────────
    # 5. Helpers
    # ─────────────────────────────────────────────────────────────────────────

    def _render_template(self, text: str, payload: Dict[str, Any]) -> str:
        for k, v in payload.items():
            if isinstance(v, (str, int, float)):
                text = text.replace(f"{{{{{k}}}}}", str(v))
        return text
