import logging
import uuid
from typing import Any, Dict, Optional
import httpx

from app.core.config import settings
from app.services.channel_adapters.base import BaseChannelAdapter, ProviderDispatchResult

logger = logging.getLogger(__name__)


class WhatsAppChannelAdapter(BaseChannelAdapter):
    """
    Adapter for Meta WhatsApp Cloud API.
    Dispatches notifications using registered and approved WhatsApp Business templates
    or session messages within customer support 24hr windows.
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

        # Format recipient phone number (must be international without leading + or 00)
        phone = recipient.strip().replace("+", "").replace(" ", "").replace("-", "")
        if not phone.isdigit() or len(phone) < 10:
            return ProviderDispatchResult(
                success=False,
                status="FAILED",
                provider="META_WHATSAPP",
                error_details=f"Invalid recipient phone number format for WhatsApp: '{recipient}'",
            )

        token = credentials.get("access_token") or settings.META_WHATSAPP_TOKEN
        phone_number_id = (
            credentials.get("phone_number_id")
            or custom_settings.get("phone_number_id")
            or settings.META_PHONE_NUMBER_ID
        )

        template_name = template_meta.get("whatsapp_template_name")
        language_code = template_meta.get("whatsapp_language", "en_US")

        # If live Meta credentials exist and not in dev/test, make outbound HTTP call
        if token and phone_number_id and not (settings.is_development or settings.is_test):
            try:
                url = f"https://graph.facebook.com/v21.0/{phone_number_id}/messages"
                headers = {
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                }

                if template_name:
                    payload = {
                        "messaging_product": "whatsapp",
                        "to": phone,
                        "type": "template",
                        "template": {
                            "name": template_name,
                            "language": {"code": language_code},
                            "components": [
                                {
                                    "type": "body",
                                    "parameters": [
                                        {"type": "text", "text": str(v)}
                                        for v in template_meta.get("parameters", [content[:60]])
                                    ],
                                }
                            ],
                        },
                    }
                else:
                    payload = {
                        "messaging_product": "whatsapp",
                        "to": phone,
                        "type": "text",
                        "text": {"body": content},
                    }

                async with httpx.AsyncClient(timeout=15.0) as client:
                    resp = await client.post(url, headers=headers, json=payload)
                    data = resp.json()
                    if resp.status_code == 200 and "messages" in data:
                        wamid = data["messages"][0].get("id")
                        return ProviderDispatchResult(
                            success=True,
                            status="DISPATCHED",
                            provider="META_WHATSAPP",
                            provider_message_id=wamid,
                            metadata=data,
                        )
                    else:
                        error_msg = data.get("error", {}).get("message") or resp.text
                        return ProviderDispatchResult(
                            success=False,
                            status="FAILED",
                            provider="META_WHATSAPP",
                            error_details=error_msg,
                            metadata=data,
                        )
            except Exception as ex:
                logger.error(f"Meta WhatsApp API call failed: {ex}")
                return ProviderDispatchResult(
                    success=False,
                    status="FAILED",
                    provider="META_WHATSAPP",
                    error_details=str(ex),
                )
        else:
            # Simulated Meta WhatsApp dispatch (tests and dev)
            wamid = f"wamid.HBgL{uuid.uuid4().hex[:20]}="
            logger.info(f"[WHATSAPP:META] Dispatched to={phone} template={template_name} msg_id={wamid}")
            return ProviderDispatchResult(
                success=True,
                status="DISPATCHED",
                provider="META_WHATSAPP",
                provider_message_id=wamid,
                metadata={
                    "simulated": True,
                    "phone": phone,
                    "template": template_name,
                    "language": language_code,
                },
            )
