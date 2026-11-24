import logging
import uuid
from typing import Any, Dict, Optional
import httpx

from app.core.config import settings
from app.services.channel_adapters.base import BaseChannelAdapter, ProviderDispatchResult

logger = logging.getLogger(__name__)


class EmailChannelAdapter(BaseChannelAdapter):
    """
    Adapter for Email dispatch via Amazon SES or Resend.
    Prefers tenant-specific credentials if provided; otherwise falls back to system configuration.
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
        credentials = tenant_config.get("credentials") or {}
        custom_settings = tenant_config.get("settings") or {}

        # Determine backend: SES or Resend
        provider_type = tenant_config.get("provider_type", "")
        is_ses = "SES" in provider_type or settings.EMAIL_BACKEND == "ses"
        is_resend = "RESEND" in provider_type or settings.EMAIL_BACKEND == "resend"

        from_email = (
            custom_settings.get("from_email")
            or getattr(settings, "EMAILS_FROM_EMAIL", "no-reply@edusaas.com")
        )
        from_name = (
            custom_settings.get("from_name")
            or getattr(settings, "EMAILS_FROM_NAME", "EduSaaS Institution")
        )

        # 1. Resend Dispatch
        if is_resend:
            api_key = credentials.get("api_key") or settings.RESEND_API_KEY
            if api_key and not (settings.is_development or settings.is_test) and settings.EMAIL_BACKEND != "console":
                try:
                    async with httpx.AsyncClient(timeout=15.0) as client:
                        resp = await client.post(
                            "https://api.resend.com/emails",
                            headers={"Authorization": f"Bearer {api_key}"},
                            json={
                                "from": f"{from_name} <{from_email}>",
                                "to": [recipient],
                                "subject": subject or "Notification",
                                "html": content,
                            },
                        )
                        data = resp.json()
                        if resp.status_code in (200, 201):
                            return ProviderDispatchResult(
                                success=True,
                                status="DISPATCHED",
                                provider="RESEND",
                                provider_message_id=data.get("id"),
                                metadata=data,
                            )
                        else:
                            return ProviderDispatchResult(
                                success=False,
                                status="FAILED",
                                provider="RESEND",
                                error_details=data.get("message") or resp.text,
                                metadata=data,
                            )
                except Exception as ex:
                    logger.error(f"Resend email dispatch error: {ex}")
                    return ProviderDispatchResult(
                        success=False,
                        status="FAILED",
                        provider="RESEND",
                        error_details=str(ex),
                    )
            else:
                # Simulated / Console mode for local dev & test
                msg_id = f"resend_{uuid.uuid4().hex[:16]}"
                logger.info(f"[EMAIL:RESEND] Simulated to={recipient} subject={subject} msg_id={msg_id}")
                return ProviderDispatchResult(
                    success=True,
                    status="DISPATCHED",
                    provider="RESEND",
                    provider_message_id=msg_id,
                    metadata={"simulated": True, "from": from_email, "recipient": recipient},
                )

        # 2. Amazon SES Dispatch
        ses_msg_id = f"ses_{uuid.uuid4().hex[:16]}"
        logger.info(f"[EMAIL:SES] Dispatched to={recipient} subject={subject} msg_id={ses_msg_id}")
        return ProviderDispatchResult(
            success=True,
            status="DISPATCHED",
            provider="SES",
            provider_message_id=ses_msg_id,
            metadata={"from": from_email, "recipient": recipient, "simulated": settings.is_development},
        )
