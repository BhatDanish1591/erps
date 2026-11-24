import hashlib
import json
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import delete, func, or_, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.notification import (
    NotificationLog,
    NotificationOutbox,
    NotificationTemplate,
    TenantIntegration,
    UserNotification,
    UserNotificationPreference,
)


class NotificationRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    # ─────────────────────────────────────────────────────────────────────────
    # 1. Tenant Integrations
    # ─────────────────────────────────────────────────────────────────────────

    async def get_integration(
        self, tenant_id: uuid.UUID, provider_type: str
    ) -> Optional[TenantIntegration]:
        stmt = select(TenantIntegration).where(
            TenantIntegration.tenant_id == tenant_id,
            TenantIntegration.provider_type == provider_type,
            TenantIntegration.is_deleted == False,
        )
        return (await self.session.execute(stmt)).scalars().first()

    async def get_integration_by_id(
        self, tenant_id: uuid.UUID, integration_id: uuid.UUID
    ) -> Optional[TenantIntegration]:
        stmt = select(TenantIntegration).where(
            TenantIntegration.tenant_id == tenant_id,
            TenantIntegration.id == integration_id,
            TenantIntegration.is_deleted == False,
        )
        return (await self.session.execute(stmt)).scalars().first()

    async def list_integrations(self, tenant_id: uuid.UUID) -> List[TenantIntegration]:
        stmt = (
            select(TenantIntegration)
            .where(
                TenantIntegration.tenant_id == tenant_id,
                TenantIntegration.is_deleted == False,
            )
            .order_by(TenantIntegration.provider_type)
        )
        return list((await self.session.execute(stmt)).scalars().all())

    async def upsert_integration(
        self,
        tenant_id: uuid.UUID,
        provider_type: str,
        is_enabled: bool = True,
        credentials: Optional[Dict[str, Any]] = None,
        settings: Optional[Dict[str, Any]] = None,
        webhook_secret: Optional[str] = None,
        status: str = "UNTESTED",
    ) -> TenantIntegration:
        integration = await self.get_integration(tenant_id, provider_type)
        if not integration:
            integration = TenantIntegration(
                tenant_id=tenant_id,
                provider_type=provider_type,
                is_enabled=is_enabled,
                credentials_encrypted=credentials or {},
                settings=settings or {},
                webhook_secret=webhook_secret,
                status=status,
            )
            self.session.add(integration)
        else:
            integration.is_enabled = is_enabled
            if credentials is not None:
                integration.credentials_encrypted = credentials
            if settings is not None:
                integration.settings = settings
            if webhook_secret is not None:
                integration.webhook_secret = webhook_secret
            integration.status = status
            integration.updated_at = datetime.now(timezone.utc)
        await self.session.flush()
        return integration

    # ─────────────────────────────────────────────────────────────────────────
    # 2. Notification Templates
    # ─────────────────────────────────────────────────────────────────────────

    async def get_template(
        self, tenant_id: Optional[uuid.UUID], event_type: str, channel: str
    ) -> Optional[NotificationTemplate]:
        # Try tenant-specific template first
        if tenant_id:
            stmt = select(NotificationTemplate).where(
                NotificationTemplate.tenant_id == tenant_id,
                NotificationTemplate.event_type == event_type,
                NotificationTemplate.channel == channel,
                NotificationTemplate.is_active == True,
                NotificationTemplate.is_deleted == False,
            )
            res = (await self.session.execute(stmt)).scalars().first()
            if res:
                return res

        # Fallback to system-wide default template (tenant_id IS NULL)
        fallback_stmt = select(NotificationTemplate).where(
            NotificationTemplate.tenant_id.is_(None),
            NotificationTemplate.event_type == event_type,
            NotificationTemplate.channel == channel,
            NotificationTemplate.is_active == True,
            NotificationTemplate.is_deleted == False,
        )
        return (await self.session.execute(fallback_stmt)).scalars().first()

    async def list_templates(
        self, tenant_id: uuid.UUID
    ) -> List[NotificationTemplate]:
        stmt = (
            select(NotificationTemplate)
            .where(
                or_(
                    NotificationTemplate.tenant_id == tenant_id,
                    NotificationTemplate.tenant_id.is_(None),
                ),
                NotificationTemplate.is_deleted == False,
            )
            .order_by(NotificationTemplate.event_type, NotificationTemplate.channel)
        )
        return list((await self.session.execute(stmt)).scalars().all())

    async def create_template(
        self,
        tenant_id: Optional[uuid.UUID],
        event_type: str,
        channel: str,
        name: str,
        body_template: str,
        subject_template: Optional[str] = None,
        whatsapp_template_name: Optional[str] = None,
        whatsapp_template_namespace: Optional[str] = None,
        whatsapp_language: str = "en_US",
        msg91_template_id: Optional[str] = None,
    ) -> NotificationTemplate:
        template = NotificationTemplate(
            tenant_id=tenant_id,
            event_type=event_type,
            channel=channel,
            name=name,
            subject_template=subject_template,
            body_template=body_template,
            whatsapp_template_name=whatsapp_template_name,
            whatsapp_template_namespace=whatsapp_template_namespace,
            whatsapp_language=whatsapp_language,
            msg91_template_id=msg91_template_id,
            is_active=True,
        )
        self.session.add(template)
        await self.session.flush()
        return template

    # ─────────────────────────────────────────────────────────────────────────
    # 3. User Notification Preferences
    # ─────────────────────────────────────────────────────────────────────────

    async def get_or_create_user_preferences(
        self, tenant_id: uuid.UUID, user_id: uuid.UUID
    ) -> UserNotificationPreference:
        stmt = select(UserNotificationPreference).where(
            UserNotificationPreference.tenant_id == tenant_id,
            UserNotificationPreference.user_id == user_id,
        )
        prefs = (await self.session.execute(stmt)).scalars().first()
        if not prefs:
            prefs = UserNotificationPreference(
                tenant_id=tenant_id,
                user_id=user_id,
                channel_email=True,
                channel_whatsapp=True,
                channel_sms=True,
                channel_push=True,
                channel_in_app=True,
                category_attendance=True,
                category_academic=True,
                category_examinations=True,
                category_finance=True,
                category_announcements=True,
                quiet_hours_enabled=False,
            )
            self.session.add(prefs)
            await self.session.flush()
        return prefs

    async def update_user_preferences(
        self,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID,
        updates: Dict[str, Any],
    ) -> UserNotificationPreference:
        prefs = await self.get_or_create_user_preferences(tenant_id, user_id)
        for field, val in updates.items():
            if hasattr(prefs, field) and val is not None:
                setattr(prefs, field, val)
        prefs.updated_at = datetime.now(timezone.utc)
        await self.session.flush()
        return prefs

    # ─────────────────────────────────────────────────────────────────────────
    # 4. Transactional Outbox
    # ─────────────────────────────────────────────────────────────────────────

    async def enqueue_outbox_event(
        self,
        tenant_id: uuid.UUID,
        event_type: str,
        payload: Dict[str, Any],
        idempotency_key: Optional[str] = None,
    ) -> NotificationOutbox:
        if not idempotency_key:
            # Deterministic hash of payload + tenant + event
            raw_hash = f"{tenant_id}:{event_type}:{json.dumps(payload, sort_keys=True)}"
            idempotency_key = hashlib.sha256(raw_hash.encode()).hexdigest()[:64]

        stmt = insert(NotificationOutbox).values(
            tenant_id=tenant_id,
            event_type=event_type,
            event_payload=payload,
            idempotency_key=idempotency_key,
            status="PENDING",
            scheduled_for=datetime.now(timezone.utc),
        ).on_conflict_do_nothing(index_elements=["tenant_id", "idempotency_key"]).returning(NotificationOutbox)
        outbox = await self.session.scalar(stmt)
        if outbox is not None:
            return outbox
        return (await self.session.execute(select(NotificationOutbox).where(
            NotificationOutbox.tenant_id == tenant_id,
            NotificationOutbox.idempotency_key == idempotency_key,
        ))).scalar_one()

    async def get_pending_outbox_items(
        self, limit: int = 50, tenant_id: Optional[uuid.UUID] = None
    ) -> List[NotificationOutbox]:
        stmt = (
            select(NotificationOutbox)
            .where(
                NotificationOutbox.status.in_(["PENDING", "FAILED"]),
                NotificationOutbox.retry_count < NotificationOutbox.max_retries,
                NotificationOutbox.scheduled_for <= datetime.now(timezone.utc),
            )
            .order_by(NotificationOutbox.scheduled_for.asc())
            .limit(limit)
        )
        if tenant_id is not None:
            stmt = stmt.where(NotificationOutbox.tenant_id == tenant_id)
        return list((await self.session.execute(stmt)).scalars().all())

    async def list_outbox_entries(
        self, tenant_id: uuid.UUID, limit: int = 50
    ) -> List[NotificationOutbox]:
        stmt = (
            select(NotificationOutbox)
            .where(NotificationOutbox.tenant_id == tenant_id)
            .order_by(NotificationOutbox.created_at.desc())
            .limit(limit)
        )
        return list((await self.session.execute(stmt)).scalars().all())

    # ─────────────────────────────────────────────────────────────────────────
    # 5. Notification Logs
    # ─────────────────────────────────────────────────────────────────────────

    async def create_log(
        self,
        tenant_id: uuid.UUID,
        recipient: str,
        channel: str,
        provider: str,
        event_type: str,
        status: str,
        outbox_id: Optional[uuid.UUID] = None,
        user_id: Optional[uuid.UUID] = None,
        subject: Optional[str] = None,
        content: Optional[str] = None,
        provider_message_id: Optional[str] = None,
        error_details: Optional[str] = None,
        metadata_json: Optional[Dict[str, Any]] = None,
    ) -> NotificationLog:
        now = datetime.now(timezone.utc)
        delivered_at = now if status == "DELIVERED" else None
        log = NotificationLog(
            tenant_id=tenant_id,
            outbox_id=outbox_id,
            user_id=user_id,
            recipient=recipient,
            channel=channel,
            provider=provider,
            event_type=event_type,
            subject=subject,
            content=content,
            provider_message_id=provider_message_id,
            status=status,
            error_details=error_details,
            metadata_json=metadata_json or {},
            delivered_at=delivered_at,
        )
        self.session.add(log)
        await self.session.flush()
        return log

    async def get_log_by_provider_message_id(
        self, provider_message_id: str
    ) -> Optional[NotificationLog]:
        stmt = select(NotificationLog).where(
            NotificationLog.provider_message_id == provider_message_id
        )
        return (await self.session.execute(stmt)).scalars().first()

    async def list_logs(
        self,
        tenant_id: uuid.UUID,
        channel: Optional[str] = None,
        status: Optional[str] = None,
        event_type: Optional[str] = None,
        limit: int = 50,
    ) -> List[NotificationLog]:
        stmt = select(NotificationLog).where(NotificationLog.tenant_id == tenant_id)
        if channel:
            stmt = stmt.where(NotificationLog.channel == channel)
        if status:
            stmt = stmt.where(NotificationLog.status == status)
        if event_type:
            stmt = stmt.where(NotificationLog.event_type == event_type)
        stmt = stmt.order_by(NotificationLog.created_at.desc()).limit(limit)
        return list((await self.session.execute(stmt)).scalars().all())

    # ─────────────────────────────────────────────────────────────────────────
    # 6. In-App User Notifications
    # ─────────────────────────────────────────────────────────────────────────

    async def create_user_notification(
        self,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID,
        event_type: str,
        title: str,
        message: str,
        action_url: Optional[str] = None,
    ) -> UserNotification:
        notif = UserNotification(
            tenant_id=tenant_id,
            user_id=user_id,
            event_type=event_type,
            title=title,
            message=message,
            action_url=action_url,
            is_read=False,
        )
        self.session.add(notif)
        await self.session.flush()
        return notif

    async def list_user_notifications(
        self,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID,
        unread_only: bool = False,
        limit: int = 50,
    ) -> List[UserNotification]:
        stmt = select(UserNotification).where(
            UserNotification.tenant_id == tenant_id,
            UserNotification.user_id == user_id,
        )
        if unread_only:
            stmt = stmt.where(UserNotification.is_read == False)
        stmt = stmt.order_by(UserNotification.created_at.desc()).limit(limit)
        return list((await self.session.execute(stmt)).scalars().all())

    async def mark_user_notification_read(
        self, tenant_id: uuid.UUID, user_id: uuid.UUID, notification_id: uuid.UUID
    ) -> Optional[UserNotification]:
        stmt = select(UserNotification).where(
            UserNotification.tenant_id == tenant_id,
            UserNotification.user_id == user_id,
            UserNotification.id == notification_id,
        )
        notif = (await self.session.execute(stmt)).scalars().first()
        if notif:
            notif.is_read = True
            notif.read_at = datetime.now(timezone.utc)
            await self.session.flush()
        return notif

    async def mark_all_user_notifications_read(
        self, tenant_id: uuid.UUID, user_id: uuid.UUID
    ) -> int:
        now = datetime.now(timezone.utc)
        stmt = (
            update(UserNotification)
            .where(
                UserNotification.tenant_id == tenant_id,
                UserNotification.user_id == user_id,
                UserNotification.is_read == False,
            )
            .values(is_read=True, read_at=now, updated_at=now)
        )
        res = await self.session.execute(stmt)
        return res.rowcount
