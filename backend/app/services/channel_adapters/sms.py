import logging
import uuid
from typing import Any, Dict, Optional
import httpx

from app.core.config import settings
from app.services.channel_adapters.base import BaseChannelAdapter, ProviderDispatchResult

logger = logging.getLogger(__name__)


class SMSChannelAdapter(BaseChannelAdapter):
    """
    Adapter for MSG91 SMS and OTP delivery.
    Supports Flow API, DLT-registered templates, and sender ID routing.
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
        template_meta = template_meta or {}

        # Strip non-digits
        phone = recipient.strip().replace("+", "").replace(" ", "").replace("-", "")
        if not phone.isdigit() or len(phone) < 10:
            return ProviderDispatchResult(
                success=False,
                status="FAILED",
                provider="MSG91",
                error_details=f"Invalid phone number for SMS: '{recipient}'",
            )

        # Prepend 91 if 10-digit Indian number
        if len(phone) == 10:
            phone = f"91{phone}"

        auth_key = credentials.get("auth_key") or settings.MSG91_AUTH_KEY
        sender_id = (
            custom_settings.get("sender_id")
            or credentials.get("sender_id")
            or settings.MSG91_SENDER_ID
            or "EDUSAS"
        )
        template_id = (
            template_meta.get("msg91_template_id")
            or custom_settings.get("template_id")
            or settings.MSG91_TEMPLATE_ID
        )

        if auth_key and template_id and not (settings.is_development or settings.is_test):
            try:
                url = "https://control.msg91.com/api/v5/flow/"
                headers = {
                    "authkey": auth_key,
                    "content-type": "application/json",
                }
                payload = {
                    "template_id": template_id,
                    "short_url": "0",
                    "sender": sender_id,
                    "recipients": [
                        {
                            "mobiles": phone,
                            **template_meta.get("variables", {"message": content[:160]}),
                        }
                    ],
                }

                async with httpx.AsyncClient(timeout=15.0) as client:
                    resp = await client.post(url, headers=headers, json=payload)
                    data = resp.json()
                    if resp.status_code == 200 and data.get("type") == "success":
                        request_id = data.get("message") or f"req_{uuid.uuid4().hex[:12]}"
                        return ProviderDispatchResult(
                            success=True,
                            status="DISPATCHED",
                            provider="MSG91",
                            provider_message_id=request_id,
                            metadata=data,
                        )
                    else:
                        error_msg = data.get("message") or resp.text
                        return ProviderDispatchResult(
                            success=False,
                            status="FAILED",
                            provider="MSG91",
                            error_details=error_msg,
                            metadata=data,
                        )
            except Exception as ex:
                logger.error(f"MSG91 SMS dispatch failed: {ex}")
                return ProviderDispatchResult(
                    success=False,
                    status="FAILED",
                    provider="MSG91",
                    error_details=str(ex),
                )
        else:
            # Simulated SMS dispatch (dev/test)
            request_id = f"msg91_{uuid.uuid4().hex[:16]}"
            logger.info(f"[SMS:MSG91] Dispatched to={phone} sender={sender_id} req_id={request_id}")
            return ProviderDispatchResult(
                success=True,
                status="DISPATCHED",
                provider="MSG91",
                provider_message_id=request_id,
                metadata={
                    "simulated": True,
                    "phone": phone,
                    "sender_id": sender_id,
                    "template_id": template_id,
                },
            )
