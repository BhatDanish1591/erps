import logging
import uuid
from typing import Any, Dict, Optional

from app.core.config import settings
from app.services.channel_adapters.base import BaseChannelAdapter, ProviderDispatchResult

logger = logging.getLogger(__name__)


class PushChannelAdapter(BaseChannelAdapter):
    """
    Adapter for Push Notifications via Firebase Cloud Messaging (FCM)
    and Apple Push Notification service (APNs).
    """

    async def send(
        self,
        recipient: str,
        subject: Optional[str],
        content: str,
        template_meta: Optional[Dict[str, Any]] = None,
        tenant_config: Optional[Dict[str, Any]] = None,
    ) -> ProviderDispatchResult:
        tenant_config = tenant_config or {}
        template_meta = template_meta or {}

        # Recipient is the FCM Device Registration Token or APNs Device Token
        device_token = recipient.strip()
        if not device_token:
            return ProviderDispatchResult(
                success=False,
                status="FAILED",
                provider="FIREBASE",
                error_details="Empty device token for push notification",
            )

        provider_type = tenant_config.get("provider_type", "PUSH_FIREBASE")
        is_apns = "APNS" in provider_type

        if is_apns:
            # Apple Push Notification service
            apns_id = f"apns_{uuid.uuid4().hex}"
            logger.info(f"[PUSH:APNS] Dispatched to={device_token[:12]}... title={subject} id={apns_id}")
            return ProviderDispatchResult(
                success=True,
                status="DISPATCHED",
                provider="APNS",
                provider_message_id=apns_id,
                metadata={"token_prefix": device_token[:8], "simulated": True},
            )
        else:
            # Firebase Cloud Messaging
            fcm_id = f"projects/edusaas/messages/{uuid.uuid4().hex[:16]}"
            logger.info(f"[PUSH:FCM] Dispatched to={device_token[:12]}... title={subject} id={fcm_id}")
            return ProviderDispatchResult(
                success=True,
                status="DISPATCHED",
                provider="FIREBASE",
                provider_message_id=fcm_id,
                metadata={"token_prefix": device_token[:8], "simulated": True},
            )
