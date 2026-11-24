from __future__ import annotations

import asyncio
import hashlib
import hmac
import uuid
from typing import Any, Dict, Optional

from app.core.config import settings
from app.core.exceptions import AppException
from app.core.logging import get_logger

logger = get_logger(__name__)

try:
    import razorpay
except ImportError:
    razorpay = None


class PaymentGatewayError(AppException):
    def __init__(self, message: str, details: Optional[list] = None):
        super().__init__(
            status_code=400,
            error_code="PAYMENT_GATEWAY_ERROR",
            message=message,
            details=details,
        )


class RazorpayGateway:
    """
    Enterprise Razorpay Payment Gateway integration supporting:
    - Server-side order creation
    - Cryptographic HMAC-SHA256 signature verification for payments
    - Signed webhook verification
    - Graceful test/sandbox fallback when live credentials are not set
    """

    def __init__(self) -> None:
        self.key_id = settings.RAZORPAY_KEY_ID
        self.key_secret = settings.RAZORPAY_KEY_SECRET
        self.webhook_secret = settings.RAZORPAY_WEBHOOK_SECRET

        if self.key_id and self.key_secret and razorpay:
            self._client = razorpay.Client(auth=(self.key_id, self.key_secret))
        else:
            self._client = None

    @property
    def is_live_configured(self) -> bool:
        return bool(self.key_id and self.key_secret and self._client)

    def create_order(
        self,
        amount_in_rupees: float,
        receipt: str,
        currency: str = "INR",
        notes: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Creates a Razorpay order. Amount is converted to paise (integer).
        """
        amount_paise = int(round(amount_in_rupees * 100))
        if amount_paise <= 0:
            raise PaymentGatewayError("Order amount must be greater than zero")

        if self.is_live_configured:
            try:
                order_data = {
                    "amount": amount_paise,
                    "currency": currency,
                    "receipt": receipt[:40],
                    "notes": notes or {},
                    "payment_capture": 1,
                }
                order = self._client.order.create(data=order_data)
                return {
                    "order_id": order["id"],
                    "amount": amount_in_rupees,
                    "amount_paise": amount_paise,
                    "currency": currency,
                    "key_id": self.key_id,
                    "status": order.get("status", "created"),
                }
            except Exception as e:
                logger.error("Razorpay order creation failed", error=str(e), receipt=receipt)
                raise PaymentGatewayError(f"Razorpay order generation failed: {str(e)}")

        if not settings.is_test:
            raise PaymentGatewayError("Online payments are unavailable. Razorpay is not configured.")

        # Local and automated test orders never reach the provider.
        mock_order_id = f"order_mock_{uuid.uuid4().hex[:16]}"
        logger.info(
            "Created sandbox/mock Razorpay order",
            order_id=mock_order_id,
            amount=amount_in_rupees,
            receipt=receipt,
        )
        return {
            "order_id": mock_order_id,
            "amount": amount_in_rupees,
            "amount_paise": amount_paise,
            "currency": currency,
            "key_id": self.key_id or "rzp_test_mock_key",
            "status": "created",
        }

    def verify_payment_signature(
        self,
        order_id: str,
        payment_id: str,
        signature: str,
    ) -> bool:
        """
        Verifies Razorpay payment signature using HMAC-SHA256:
        hash = hmac_sha256(order_id + "|" + payment_id, secret)
        """
        if not order_id or not payment_id or not signature:
            return False

        if not self.is_live_configured:
            if not settings.is_test or not order_id.startswith("order_mock_"):
                return False
            if hmac.compare_digest(signature, f"mock_sig_{payment_id}"):
                return True

        message = f"{order_id}|{payment_id}"
        expected_signature = hmac.new(
            (self.key_secret or "mock_secret").encode("utf-8"),
            message.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

        return hmac.compare_digest(expected_signature, signature)

    def verify_webhook_signature(
        self,
        raw_body: bytes,
        signature: str,
    ) -> bool:
        """
        Verifies signed webhook payload using RAZORPAY_WEBHOOK_SECRET.
        """
        if not signature or not self.webhook_secret:
            return False

        expected_signature = hmac.new(
            self.webhook_secret.encode("utf-8"),
            raw_body,
            hashlib.sha256,
        ).hexdigest()

        return hmac.compare_digest(expected_signature, signature)

    async def require_captured_payment(
        self, order_id: str, payment_id: str, amount: float, currency: str
    ) -> None:
        if settings.is_test and not self.is_live_configured and order_id.startswith("order_mock_"):
            return
        if not self._client:
            raise PaymentGatewayError("Razorpay is not configured.")
        try:
            payment = await asyncio.to_thread(self._client.payment.fetch, payment_id)
        except Exception as error:
            logger.warning("Razorpay payment lookup failed", payment_id=payment_id)
            raise PaymentGatewayError("Razorpay could not confirm the payment. Check your invoice before paying again.") from error
        if (
            payment.get("order_id") != order_id
            or payment.get("amount") != round(amount * 100)
            or payment.get("currency") != currency
        ):
            raise PaymentGatewayError("The Razorpay payment details do not match this order.")
        if payment.get("status") != "captured":
            raise PaymentGatewayError("Payment is awaiting capture. Check your invoice before paying again.")


razorpay_gateway = RazorpayGateway()
