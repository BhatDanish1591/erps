from __future__ import annotations

import asyncio
import json
import uuid
from datetime import date, datetime, timedelta, timezone
from html import escape
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import set_database_context
from app.core.exceptions import AppException
from app.core.logging import get_logger
from app.models.academic import StudentProfile, TeacherProfile
from app.models.enums import (
    BillingCycle,
    DiscountType,
    InstitutionType,
    InvoiceStatus,
    PaymentStatus,
    SubscriptionStatus,
    TenantStatus,
)
from app.models.subscription import (
    Coupon,
    PlanFeature,
    Subscription,
    SubscriptionInvoice,
    SubscriptionPayment,
    SubscriptionPlan,
)
from app.models.tenant import Tenant
from app.repositories.subscription import SubscriptionRepository
from app.services.payment_gateway import razorpay_gateway

logger = get_logger(__name__)


DEFAULT_SEEDED_PLANS = [
    # ── School Plans ──────────────────────────────────────────────────────────
    {
        "name": "Starter School",
        "code": "STARTER_SCHOOL",
        "description": "Essential CRM features for emerging and medium-sized primary/secondary schools.",
        "institution_type": InstitutionType.SCHOOL,
        "billing_cycle": BillingCycle.MONTHLY,
        "monthly_price": 999.00,
        "annual_price": 9990.00,
        "price": 999.00,
        "max_students": 300,
        "max_teachers": 20,
        "storage_limit_gb": 10,
        "notification_quota": 1000,
        "trial_days": 30,
        "features": [
            ("custom_domain", {"enabled": False}),
            ("bulk_import_export", {"enabled": True}),
            ("basic_analytics", {"enabled": True}),
            ("sms_notifications", {"enabled": False}),
            ("whatsapp_notifications", {"enabled": False}),
        ],
    },
    {
        "name": "Professional School",
        "code": "PRO_SCHOOL",
        "description": "Comprehensive school automation with communications, exams, and expanded capacity.",
        "institution_type": InstitutionType.SCHOOL,
        "billing_cycle": BillingCycle.MONTHLY,
        "monthly_price": 2499.00,
        "annual_price": 24990.00,
        "price": 2499.00,
        "max_students": 1000,
        "max_teachers": 75,
        "storage_limit_gb": 50,
        "notification_quota": 5000,
        "trial_days": 30,
        "features": [
            ("custom_domain", {"enabled": True}),
            ("bulk_import_export", {"enabled": True}),
            ("advanced_analytics", {"enabled": True}),
            ("sms_notifications", {"enabled": True}),
            ("whatsapp_notifications", {"enabled": False}),
            ("priority_support", {"enabled": True}),
        ],
    },
    {
        "name": "Enterprise School",
        "code": "ENTERPRISE_SCHOOL",
        "description": "High-volume multi-branch institutional suite with full communications & priority support.",
        "institution_type": InstitutionType.SCHOOL,
        "billing_cycle": BillingCycle.MONTHLY,
        "monthly_price": 4999.00,
        "annual_price": 49990.00,
        "price": 4999.00,
        "max_students": 3000,
        "max_teachers": 200,
        "storage_limit_gb": 250,
        "notification_quota": 20000,
        "trial_days": 30,
        "features": [
            ("custom_domain", {"enabled": True}),
            ("bulk_import_export", {"enabled": True}),
            ("advanced_analytics", {"enabled": True}),
            ("sms_notifications", {"enabled": True}),
            ("whatsapp_notifications", {"enabled": True}),
            ("priority_support", {"enabled": True}),
            ("api_access", {"enabled": True}),
            ("multi_branch", {"enabled": True}),
        ],
    },
    # ── College Plans ─────────────────────────────────────────────────────────
    {
        "name": "Basic College",
        "code": "BASIC_COLLEGE",
        "description": "Streamlined academic and department management for degree programs and junior colleges.",
        "institution_type": InstitutionType.COLLEGE,
        "billing_cycle": BillingCycle.MONTHLY,
        "monthly_price": 2499.00,
        "annual_price": 24990.00,
        "price": 2499.00,
        "max_students": 500,
        "max_teachers": 40,
        "storage_limit_gb": 20,
        "notification_quota": 2000,
        "trial_days": 30,
        "features": [
            ("custom_domain", {"enabled": False}),
            ("bulk_import_export", {"enabled": True}),
            ("basic_analytics", {"enabled": True}),
            ("sms_notifications", {"enabled": False}),
            ("whatsapp_notifications", {"enabled": False}),
        ],
    },
    {
        "name": "Professional College",
        "code": "PRO_COLLEGE",
        "description": "Multi-department and course management with semester evaluations and faculty workflows.",
        "institution_type": InstitutionType.COLLEGE,
        "billing_cycle": BillingCycle.MONTHLY,
        "monthly_price": 5999.00,
        "annual_price": 59990.00,
        "price": 5999.00,
        "max_students": 2000,
        "max_teachers": 150,
        "storage_limit_gb": 100,
        "notification_quota": 10000,
        "trial_days": 30,
        "features": [
            ("custom_domain", {"enabled": True}),
            ("bulk_import_export", {"enabled": True}),
            ("advanced_analytics", {"enabled": True}),
            ("sms_notifications", {"enabled": True}),
            ("whatsapp_notifications", {"enabled": False}),
            ("priority_support", {"enabled": True}),
        ],
    },
    {
        "name": "Enterprise College",
        "code": "ENTERPRISE_COLLEGE",
        "description": "Enterprise university platform with high concurrency, custom domain, and dedicated support.",
        "institution_type": InstitutionType.COLLEGE,
        "billing_cycle": BillingCycle.MONTHLY,
        "monthly_price": 9999.00,
        "annual_price": 99990.00,
        "price": 9999.00,
        "max_students": 5000,
        "max_teachers": 400,
        "storage_limit_gb": 500,
        "notification_quota": 50000,
        "trial_days": 30,
        "features": [
            ("custom_domain", {"enabled": True}),
            ("bulk_import_export", {"enabled": True}),
            ("advanced_analytics", {"enabled": True}),
            ("sms_notifications", {"enabled": True}),
            ("whatsapp_notifications", {"enabled": True}),
            ("priority_support", {"enabled": True}),
            ("api_access", {"enabled": True}),
            ("multi_branch", {"enabled": True}),
        ],
    },
]


class SubscriptionService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = SubscriptionRepository(session)

    # ── Plan Seeding ──────────────────────────────────────────────────────────
    async def seed_default_plans_if_needed(self) -> None:
        """
        Idempotently seeds the 6 standardized School & College plans.
        """
        for item in DEFAULT_SEEDED_PLANS:
            existing = await self.repo.get_plan_by_code(item["code"])
            if not existing:
                plan = SubscriptionPlan(
                    name=item["name"],
                    code=item["code"],
                    description=item["description"],
                    institution_type=item["institution_type"],
                    billing_cycle=item["billing_cycle"],
                    price=item["price"],
                    monthly_price=item["monthly_price"],
                    annual_price=item["annual_price"],
                    currency="INR",
                    max_students=item["max_students"],
                    max_teachers=item["max_teachers"],
                    storage_limit_gb=item["storage_limit_gb"],
                    notification_quota=item["notification_quota"],
                    trial_days=item["trial_days"],
                    is_active=True,
                )
                features = [
                    PlanFeature(
                        feature_key=k,
                        feature_value=v,
                        is_enabled=v.get("enabled", True),
                    )
                    for k, v in item["features"]
                ]
                await self.repo.create_plan(plan, features)
                logger.info("Seeded subscription plan", code=item["code"])

    async def list_available_plans(
        self, institution_type: Optional[InstitutionType] = None
    ) -> List[SubscriptionPlan]:
        await self.seed_default_plans_if_needed()
        return await self.repo.list_plans(institution_type=institution_type, only_active=True)

    # ── Coupon Validation ─────────────────────────────────────────────────────
    async def validate_coupon(
        self,
        coupon_code: str,
        base_amount: float,
        institution_type: Optional[InstitutionType] = None,
    ) -> Tuple[bool, Optional[Coupon], float, str]:
        """
        Validates coupon rules and returns (is_valid, coupon, discount_amount, message).
        """
        if not coupon_code:
            return False, None, 0.0, "No coupon provided"

        coupon = await self.repo.get_coupon_by_code(coupon_code)
        if not coupon:
            return False, None, 0.0, f"Coupon code '{coupon_code}' is invalid."

        if not coupon.is_active:
            return False, None, 0.0, f"Coupon '{coupon.code}' is no longer active."

        now = datetime.now(timezone.utc)
        if coupon.valid_from > now:
            return False, None, 0.0, f"Coupon '{coupon.code}' is not yet valid."

        if coupon.valid_until and coupon.valid_until < now:
            return False, None, 0.0, f"Coupon '{coupon.code}' has expired."

        if coupon.max_redemptions and coupon.times_redeemed >= coupon.max_redemptions:
            return False, None, 0.0, f"Coupon '{coupon.code}' redemption limit reached."

        if (
            coupon.applicable_institution_type
            and institution_type
            and coupon.applicable_institution_type != institution_type
        ):
            return (
                False,
                None,
                0.0,
                f"Coupon '{coupon.code}' is only valid for {coupon.applicable_institution_type.value} institutions.",
            )

        # Calculate discount
        if coupon.discount_type == DiscountType.PERCENTAGE:
            discount_amount = round(base_amount * (float(coupon.discount_value) / 100.0), 2)
        else:
            discount_amount = min(base_amount, float(coupon.discount_value))

        return True, coupon, discount_amount, "Coupon applied successfully"

    # ── Pricing Calculations ──────────────────────────────────────────────────
    async def preview_order(
        self,
        tenant_id: uuid.UUID,
        plan_id: uuid.UUID,
        billing_cycle: BillingCycle,
        coupon_code: Optional[str] = None,
    ) -> Dict[str, Any]:
        plan = await self.repo.get_plan_by_id(plan_id)
        if not plan:
            raise AppException(404, "PLAN_NOT_FOUND", "Subscription plan not found")

        tenant = (await self.session.execute(select(Tenant).where(Tenant.id == tenant_id))).scalar_one_or_none()
        institution_type = tenant.institution_type if tenant else None

        base_price = float(plan.monthly_price if billing_cycle == BillingCycle.MONTHLY else plan.annual_price)
        discount_amount = 0.0
        coupon_applied = None

        if coupon_code:
            is_valid, coupon, disc, msg = await self.validate_coupon(
                coupon_code, base_price, institution_type
            )
            if is_valid and coupon:
                discount_amount = disc
                coupon_applied = coupon.code

        subtotal = max(0.0, base_price - discount_amount)
        tax_amount = round(subtotal * 0.18, 2)  # 18% GST standard
        total_amount = round(subtotal + tax_amount, 2)

        return {
            "plan_id": plan.id,
            "plan_name": plan.name,
            "plan_code": plan.code,
            "billing_cycle": billing_cycle.value,
            "base_price": base_price,
            "discount_amount": discount_amount,
            "subtotal": subtotal,
            "tax_rate_percent": 18.0,
            "tax_amount": tax_amount,
            "total_amount": total_amount,
            "currency": plan.currency,
            "coupon_applied": coupon_applied,
        }

    # ── Order Creation ────────────────────────────────────────────────────────
    async def create_subscription_order(
        self,
        tenant_id: uuid.UUID,
        plan_id: uuid.UUID,
        billing_cycle: BillingCycle,
        coupon_code: Optional[str] = None,
        actor_user_id: Optional[uuid.UUID] = None,
        billing_name: Optional[str] = None,
        billing_address: Optional[str] = None,
        ip_address: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Creates a pending invoice, initiates Razorpay Order server-side,
        and returns order payload for the frontend checkout.
        """
        plan = await self.repo.get_plan_by_id(plan_id)
        if not plan:
            raise AppException(404, "PLAN_NOT_FOUND", "Subscription plan not found")

        # Downgrade safety check: verify current active resources fit in target plan
        student_count = (await self.session.execute(
            select(func.count(StudentProfile.id)).where(
                StudentProfile.tenant_id == tenant_id,
                StudentProfile.is_deleted == False,
            )
        )).scalar() or 0
        if student_count > plan.max_students:
            raise AppException(
                400,
                "DOWNGRADE_LIMIT_EXCEEDED",
                f"Cannot switch to {plan.name}: institution currently has {student_count} active students, exceeding the plan limit of {plan.max_students}.",
            )

        teacher_count = (await self.session.execute(
            select(func.count(TeacherProfile.id)).where(
                TeacherProfile.tenant_id == tenant_id,
                TeacherProfile.is_deleted == False,
            )
        )).scalar() or 0
        if teacher_count > plan.max_teachers:
            raise AppException(
                400,
                "DOWNGRADE_LIMIT_EXCEEDED",
                f"Cannot switch to {plan.name}: institution currently has {teacher_count} active teachers, exceeding the plan limit of {plan.max_teachers}.",
            )

        pricing = await self.preview_order(
            tenant_id=tenant_id,
            plan_id=plan_id,
            billing_cycle=billing_cycle,
            coupon_code=coupon_code,
        )

        sub = await self.repo.get_tenant_subscription(tenant_id)
        if not sub:
            now = datetime.now(timezone.utc)
            sub = Subscription(
                tenant_id=tenant_id,
                plan_id=plan.id,
                status=SubscriptionStatus.TRIAL,
                billing_cycle=billing_cycle,
                current_period_start=now,
                current_period_end=now + timedelta(days=30),
            )
            self.session.add(sub)
            await self.session.flush()

        invoice_number = f"INV-{datetime.now().strftime('%Y%m')}-{uuid.uuid4().hex[:6].upper()}"
        line_items = [
            {
                "description": f"{plan.name} ({billing_cycle.value})",
                "quantity": 1,
                "rate": pricing["base_price"],
                "discount": pricing["discount_amount"],
                "amount": pricing["subtotal"],
            }
        ]

        invoice = SubscriptionInvoice(
            tenant_id=tenant_id,
            subscription_id=sub.id,
            invoice_number=invoice_number,
            subtotal=pricing["subtotal"],
            discount_amount=pricing["discount_amount"],
            tax_amount=pricing["tax_amount"],
            total_amount=pricing["total_amount"],
            currency=pricing["currency"],
            coupon_code=pricing["coupon_applied"],
            billing_cycle=billing_cycle,
            billing_name=billing_name,
            billing_address=billing_address,
            line_items=line_items,
            status=InvoiceStatus.ISSUED,
            due_date=date.today(),
        )
        await self.repo.create_invoice(invoice)

        # If 100% discount or free order, activate immediately
        if pricing["total_amount"] <= 0:
            return await self._activate_free_order(
                invoice=invoice,
                sub=sub,
                plan=plan,
                billing_cycle=billing_cycle,
                actor_user_id=actor_user_id,
                ip_address=ip_address,
            )

        # Server-side Razorpay Order creation
        rzp_order = await asyncio.to_thread(
            razorpay_gateway.create_order,
            amount_in_rupees=pricing["total_amount"],
            receipt=invoice.invoice_number,
            currency=pricing["currency"],
            notes={
                "tenant_id": str(tenant_id),
                "invoice_id": str(invoice.id),
                "plan_code": plan.code,
                "billing_cycle": billing_cycle.value,
            },
        )

        payment = SubscriptionPayment(
            tenant_id=tenant_id,
            invoice_id=invoice.id,
            amount=pricing["total_amount"],
            currency=pricing["currency"],
            payment_method="RAZORPAY",
            gateway="razorpay",
            gateway_order_id=rzp_order["order_id"],
            status=PaymentStatus.PENDING,
            payload={**rzp_order, "plan_id": str(plan.id)},
        )
        await self.repo.create_payment(payment)
        await self.session.commit()

        return {
            "order_id": rzp_order["order_id"],
            "amount": pricing["total_amount"],
            "amount_paise": rzp_order["amount_paise"],
            "currency": pricing["currency"],
            "key_id": rzp_order["key_id"],
            "invoice_id": invoice.id,
            "plan_id": plan.id,
            "plan_name": plan.name,
            "billing_cycle": billing_cycle.value,
        }

    async def _activate_free_order(
        self,
        invoice: SubscriptionInvoice,
        sub: Subscription,
        plan: SubscriptionPlan,
        billing_cycle: BillingCycle,
        actor_user_id: Optional[uuid.UUID],
        ip_address: Optional[str],
    ) -> Dict[str, Any]:
        now = datetime.now(timezone.utc)
        invoice.status = InvoiceStatus.PAID
        invoice.paid_at = now

        sub.plan_id = plan.id
        sub.status = SubscriptionStatus.ACTIVE
        sub.billing_cycle = billing_cycle
        sub.current_period_start = now
        sub.current_period_end = now + timedelta(days=30 if billing_cycle == BillingCycle.MONTHLY else 365)
        sub.trial_ends_at = None
        sub.canceled_at = None
        sub.is_auto_renew = True

        payment = SubscriptionPayment(
            tenant_id=invoice.tenant_id,
            invoice_id=invoice.id,
            amount=0.0,
            currency="INR",
            payment_method="COUPON_100",
            gateway="internal",
            status=PaymentStatus.SUCCESS,
            paid_at=now,
            transaction_reference=f"FREE-{invoice.invoice_number}",
        )
        await self.repo.create_payment(payment)

        # Update tenant status
        tenant = (await self.session.execute(select(Tenant).where(Tenant.id == invoice.tenant_id))).scalar_one_or_none()
        if tenant and tenant.status in [TenantStatus.PENDING, TenantStatus.TRIAL, TenantStatus.SUSPENDED]:
            tenant.status = TenantStatus.ACTIVE

        await self.repo.log_audit(
            tenant_id=invoice.tenant_id,
            actor_user_id=actor_user_id,
            action="SUBSCRIPTION_ACTIVATED_FREE",
            resource="subscriptions",
            resource_id=str(sub.id),
            changes={"plan": plan.name, "amount": 0.0},
            ip_address=ip_address,
        )
        await self.session.commit()

        return {
            "order_id": "free_activation",
            "amount": 0.0,
            "amount_paise": 0,
            "currency": "INR",
            "key_id": "free",
            "invoice_id": invoice.id,
            "plan_id": plan.id,
            "plan_name": plan.name,
            "billing_cycle": billing_cycle.value,
        }

    # ── Payment Verification (Strict Backend Verification) ────────────────────
    async def verify_payment(
        self,
        tenant_id: uuid.UUID,
        razorpay_order_id: str,
        razorpay_payment_id: str,
        razorpay_signature: str,
        invoice_id: uuid.UUID,
        actor_user_id: Optional[uuid.UUID] = None,
        ip_address: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Verifies Razorpay HMAC signature. Never trusts frontend payment confirmation.
        """
        invoice = await self.repo.get_invoice_by_id(invoice_id, tenant_id=tenant_id, for_update=True)
        if not invoice:
            raise AppException(404, "INVOICE_NOT_FOUND", "Invoice not found")

        payment = await self.repo.get_payment_by_order_id(razorpay_order_id)
        if not payment or payment.invoice_id != invoice.id:
            raise AppException(400, "PAYMENT_ORDER_MISMATCH", "The Razorpay order does not match this invoice.")

        # Cryptographic verification
        is_valid = razorpay_gateway.verify_payment_signature(
            order_id=razorpay_order_id,
            payment_id=razorpay_payment_id,
            signature=razorpay_signature,
        )

        if not is_valid:
            raise AppException(
                400,
                "PAYMENT_VERIFICATION_FAILED",
                "Razorpay signature verification failed. Untrusted transaction.",
            )

        if invoice.status == InvoiceStatus.PAID:
            return {
                "success": True,
                "status": "ACTIVE",
                "invoice_id": invoice.id,
                "invoice_number": invoice.invoice_number,
                "amount_paid": float(invoice.total_amount),
                "current_period_end": invoice.subscription.current_period_end,
            }

        await razorpay_gateway.require_captured_payment(
            razorpay_order_id, razorpay_payment_id, float(payment.amount), payment.currency,
        )
        payment.gateway_signature = razorpay_signature
        await self._activate_paid_order(invoice, payment, razorpay_payment_id, actor_user_id, ip_address)
        await self.session.commit()

        return {
            "success": True,
            "status": "ACTIVE",
            "invoice_id": invoice.id,
            "invoice_number": invoice.invoice_number,
            "amount_paid": float(invoice.total_amount),
            "current_period_end": invoice.subscription.current_period_end,
        }

    async def _activate_paid_order(
        self,
        invoice: SubscriptionInvoice,
        payment: SubscriptionPayment,
        provider_payment_id: str,
        actor_user_id: Optional[uuid.UUID] = None,
        ip_address: Optional[str] = None,
    ) -> None:
        if invoice.status != InvoiceStatus.ISSUED:
            raise AppException(409, "INVOICE_NOT_PAYABLE", "This subscription invoice cannot be activated.")
        plan_id = (payment.payload or {}).get("plan_id")
        if plan_id:
            plan = await self.repo.get_plan_by_id(uuid.UUID(plan_id))
        else:
            # Older orders recorded the plan name in the invoice line item.
            descriptions = {item.get("description") for item in invoice.line_items or []}
            plans = await self.repo.list_plans(only_active=False)
            matches = [plan for plan in plans if f"{plan.name} ({invoice.billing_cycle.value})" in descriptions]
            plan = matches[0] if len(matches) == 1 else None
        if plan is None:
            raise AppException(409, "PAYMENT_PLAN_NOT_FOUND", "The plan associated with this invoice could not be identified.")

        now = datetime.now(timezone.utc)
        payment.status = PaymentStatus.SUCCESS
        payment.gateway_payment_id = provider_payment_id
        payment.transaction_reference = provider_payment_id
        payment.paid_at = now
        invoice.status = InvoiceStatus.PAID
        invoice.paid_at = now
        if invoice.coupon_code:
            coupon = await self.repo.get_coupon_by_code(invoice.coupon_code)
            if coupon:
                coupon.times_redeemed += 1

        # Activate subscription
        sub = invoice.subscription
        sub.plan_id = plan.id
        sub.billing_cycle = invoice.billing_cycle
        sub.status = SubscriptionStatus.ACTIVE
        sub.current_period_start = now
        sub.current_period_end = now + timedelta(
            days=30 if invoice.billing_cycle == BillingCycle.MONTHLY else 365
        )
        sub.grace_period_ends_at = None
        sub.trial_ends_at = None
        sub.canceled_at = None
        sub.is_auto_renew = True
        sub.payment_method = "RAZORPAY"

        # Update tenant status
        tenant = (await self.session.execute(select(Tenant).where(Tenant.id == invoice.tenant_id))).scalar_one_or_none()
        if tenant and tenant.status in [TenantStatus.PENDING, TenantStatus.TRIAL, TenantStatus.SUSPENDED]:
            tenant.status = TenantStatus.ACTIVE

        await self.repo.log_audit(
            tenant_id=invoice.tenant_id,
            actor_user_id=actor_user_id,
            action="SUBSCRIPTION_ACTIVATED",
            resource="subscriptions",
            resource_id=str(sub.id),
            changes={
                "order_id": payment.gateway_order_id,
                "payment_id": provider_payment_id,
                "amount": float(invoice.total_amount),
            },
            ip_address=ip_address,
        )

    # ── Webhook Handler ───────────────────────────────────────────────────────
    async def process_razorpay_webhook(
        self,
        raw_body: bytes,
        signature: str,
    ) -> Dict[str, Any]:
        """
        Idempotent server-side webhook handler for signed Razorpay events.
        """
        if not razorpay_gateway.verify_webhook_signature(raw_body, signature):
            raise AppException(400, "INVALID_WEBHOOK_SIGNATURE", "Webhook signature mismatch")

        try:
            payload = json.loads(raw_body.decode("utf-8"))
        except Exception:
            raise AppException(400, "INVALID_PAYLOAD", "Cannot parse JSON webhook body")

        await set_database_context(self.session, is_superadmin=True)
        event_type = payload.get("event", "unknown")
        event_id = payload.get("id") or uuid.uuid4().hex

        # Idempotency check
        existing_event = await self.repo.get_webhook_event(event_id)
        if existing_event and existing_event.is_processed:
            logger.info("Ignoring duplicate webhook event", event_id=event_id)
            return {"status": "already_processed", "event_id": event_id}

        webhook_event = await self.repo.record_webhook_event(
            event_id=event_id,
            event_type=event_type,
            payload=payload,
        )

        # Process payment / order events
        now = datetime.now(timezone.utc)
        if event_type in ["order.paid", "payment.captured"]:
            entity = payload.get("payload", {}).get("payment", {}).get("entity", {})
            order_id = entity.get("order_id")
            payment_id = entity.get("id")

            if order_id and payment_id and entity.get("status") == "captured":
                payment = await self.repo.get_payment_by_order_id(order_id)
                if payment and entity.get("amount") == round(float(payment.amount) * 100) and entity.get("currency") == payment.currency:
                    invoice = await self.repo.get_invoice_by_id(payment.invoice_id, tenant_id=payment.tenant_id, for_update=True)
                    if invoice and invoice.status == InvoiceStatus.ISSUED:
                        await self._activate_paid_order(invoice, payment, payment_id)

        elif event_type == "payment.failed":
            entity = payload.get("payload", {}).get("payment", {}).get("entity", {})
            order_id = entity.get("order_id")
            reason = entity.get("error_description", "Payment transaction failed")

            if order_id:
                payment = await self.repo.get_payment_by_order_id(order_id)
                if payment and payment.status == PaymentStatus.PENDING:
                    payment.status = PaymentStatus.FAILED
                    payment.failure_reason = reason

        webhook_event.is_processed = True
        webhook_event.processed_at = now
        await self.session.commit()

        return {"status": "processed", "event_id": event_id}

    # ── Subscription Cancellation & Renewal ───────────────────────────────────
    async def cancel_subscription(
        self,
        tenant_id: uuid.UUID,
        actor_user_id: Optional[uuid.UUID] = None,
        immediate: bool = False,
        reason: Optional[str] = None,
        ip_address: Optional[str] = None,
    ) -> Dict[str, Any]:
        sub = await self.repo.get_tenant_subscription(tenant_id)
        if not sub:
            raise AppException(404, "SUBSCRIPTION_NOT_FOUND", "Active subscription not found")

        now = datetime.now(timezone.utc)
        sub.is_auto_renew = False
        if immediate:
            sub.status = SubscriptionStatus.CANCELED
            sub.canceled_at = now

        await self.repo.log_audit(
            tenant_id=tenant_id,
            actor_user_id=actor_user_id,
            action="SUBSCRIPTION_CANCELED" if immediate else "AUTO_RENEW_DISABLED",
            resource="subscriptions",
            resource_id=str(sub.id),
            changes={"immediate": immediate, "reason": reason},
            ip_address=ip_address,
        )
        await self.session.commit()

        return {
            "success": True,
            "status": sub.status.value,
            "is_auto_renew": sub.is_auto_renew,
            "message": "Subscription canceled immediately" if immediate else "Auto-renewal disabled. Access continues until end of billing cycle.",
        }

    # ── Invoices & HTML Receipt Generation ────────────────────────────────────
    async def list_invoices(
        self, tenant_id: uuid.UUID, page: int = 1, size: int = 20
    ) -> Tuple[List[SubscriptionInvoice], int]:
        return await self.repo.list_tenant_invoices(tenant_id, page, size)

    async def get_invoice_detail(
        self, tenant_id: uuid.UUID, invoice_id: uuid.UUID
    ) -> SubscriptionInvoice:
        invoice = await self.repo.get_invoice_by_id(invoice_id, tenant_id=tenant_id)
        if not invoice:
            raise AppException(404, "INVOICE_NOT_FOUND", "Invoice not found")
        return invoice

    async def generate_invoice_html(self, tenant_id: uuid.UUID, invoice_id: uuid.UUID) -> str:
        invoice = await self.get_invoice_detail(tenant_id, invoice_id)
        tenant = invoice.tenant
        payments = invoice.payments
        tx_ref = payments[0].transaction_reference if payments else "N/A"

        items_html = ""
        for item in invoice.line_items:
            items_html += f"""
            <tr>
                <td style="padding: 12px; border-bottom: 1px solid #e2e8f0;">{escape(str(item.get('description', 'Subscription Plan')))}</td>
                <td style="padding: 12px; border-bottom: 1px solid #e2e8f0; text-align: center;">{escape(str(item.get('quantity', 1)))}</td>
                <td style="padding: 12px; border-bottom: 1px solid #e2e8f0; text-align: right;">₹{float(item.get('rate', 0)):,.2f}</td>
                <td style="padding: 12px; border-bottom: 1px solid #e2e8f0; text-align: right;">₹{float(item.get('amount', 0)):,.2f}</td>
            </tr>
            """

        status_color = "#10b981" if invoice.status == InvoiceStatus.PAID else "#f59e0b"

        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>Tax Invoice - {invoice.invoice_number}</title>
            <style>
                body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; color: #1e293b; margin: 0; padding: 40px; }}
                .invoice-box {{ max-width: 800px; margin: auto; padding: 30px; border: 1px solid #e2e8f0; border-radius: 8px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05); }}
                .badge {{ display: inline-block; padding: 4px 12px; border-radius: 9999px; font-size: 12px; font-weight: 700; color: white; background-color: {status_color}; }}
                table {{ width: 100%; border-collapse: collapse; text-align: left; }}
                th {{ background-color: #f8fafc; padding: 12px; border-bottom: 2px solid #cbd5e1; font-weight: 600; font-size: 13px; text-transform: uppercase; }}
            </style>
        </head>
        <body>
            <div class="invoice-box">
                <table style="margin-bottom: 30px;">
                    <tr>
                        <td>
                            <h2 style="margin: 0; color: #0284c7;">EduSaaS CRM</h2>
                            <p style="margin: 4px 0; color: #64748b; font-size: 13px;">Cloud Educational Institution ERP</p>
                            <p style="margin: 2px 0; font-size: 13px;">GSTIN: 29ABCDE1234F1Z5</p>
                        </td>
                        <td style="text-align: right;">
                            <h1 style="margin: 0; font-size: 24px; color: #0f172a;">TAX INVOICE</h1>
                            <p style="margin: 4px 0; font-weight: bold;">{invoice.invoice_number}</p>
                            <span class="badge">{invoice.status.value}</span>
                        </td>
                    </tr>
                </table>

                <table style="margin-bottom: 30px; border-top: 1px solid #e2e8f0; padding-top: 20px;">
                    <tr>
                        <td style="width: 50%; vertical-align: top;">
                            <strong style="color: #64748b; font-size: 12px; text-transform: uppercase;">Billed To:</strong>
                            <h4 style="margin: 4px 0;">{escape(tenant.name if tenant else 'Institution')}</h4>
                            <p style="margin: 2px 0; color: #475569; font-size: 13px;">{escape(invoice.billing_name or (tenant.email if tenant else None) or '')}</p>
                            <p style="margin: 2px 0; color: #475569; font-size: 13px;">{escape(invoice.billing_address or '')}</p>
                        </td>
                        <td style="width: 50%; text-align: right; vertical-align: top;">
                            <p style="margin: 4px 0; font-size: 13px;"><strong>Invoice Date:</strong> {invoice.created_at.strftime('%d %b %Y')}</p>
                            <p style="margin: 4px 0; font-size: 13px;"><strong>Due Date:</strong> {invoice.due_date.strftime('%d %b %Y')}</p>
                            <p style="margin: 4px 0; font-size: 13px;"><strong>Transaction Ref:</strong> {escape(tx_ref or 'N/A')}</p>
                        </td>
                    </tr>
                </table>

                <table>
                    <thead>
                        <tr>
                            <th>Description</th>
                            <th style="text-align: center;">Qty</th>
                            <th style="text-align: right;">Rate</th>
                            <th style="text-align: right;">Amount</th>
                        </tr>
                    </thead>
                    <tbody>
                        {items_html}
                    </tbody>
                </table>

                <table style="margin-top: 20px; width: 350px; margin-left: auto;">
                    <tr>
                        <td style="padding: 6px 12px; color: #64748b;">Subtotal:</td>
                        <td style="padding: 6px 12px; text-align: right;">₹{float(invoice.subtotal):,.2f}</td>
                    </tr>
                    <tr>
                        <td style="padding: 6px 12px; color: #64748b;">Discount:</td>
                        <td style="padding: 6px 12px; text-align: right; color: #16a34a;">-₹{float(invoice.discount_amount):,.2f}</td>
                    </tr>
                    <tr>
                        <td style="padding: 6px 12px; color: #64748b;">GST (18%):</td>
                        <td style="padding: 6px 12px; text-align: right;">₹{float(invoice.tax_amount):,.2f}</td>
                    </tr>
                    <tr style="border-top: 2px solid #0f172a; font-weight: bold; font-size: 16px;">
                        <td style="padding: 10px 12px;">Total:</td>
                        <td style="padding: 10px 12px; text-align: right; color: #0284c7;">₹{float(invoice.total_amount):,.2f}</td>
                    </tr>
                </table>

                <div style="margin-top: 40px; padding-top: 20px; border-top: 1px solid #e2e8f0; font-size: 12px; color: #94a3b8; text-align: center;">
                    Thank you for choosing EduSaaS CRM. This is an electronically generated tax invoice.
                </div>
            </div>
        </body>
        </html>
        """

    # ── Super Admin Controls ──────────────────────────────────────────────────
    async def suspend_subscription(
        self,
        subscription_id: uuid.UUID,
        actor_user_id: uuid.UUID,
        reason: Optional[str] = None,
        ip_address: Optional[str] = None,
    ) -> Subscription:
        sub = (await self.session.execute(
            select(Subscription).where(Subscription.id == subscription_id)
        )).scalar_one_or_none()
        if not sub:
            raise AppException(404, "SUBSCRIPTION_NOT_FOUND", "Subscription not found")

        sub.status = SubscriptionStatus.SUSPENDED
        tenant = (await self.session.execute(select(Tenant).where(Tenant.id == sub.tenant_id))).scalar_one_or_none()
        if tenant:
            tenant.status = TenantStatus.SUSPENDED

        await self.repo.log_audit(
            tenant_id=sub.tenant_id,
            actor_user_id=actor_user_id,
            action="SUBSCRIPTION_SUSPENDED",
            resource="subscriptions",
            resource_id=str(sub.id),
            changes={"reason": reason},
            ip_address=ip_address,
        )
        await self.session.commit()
        return sub

    async def reactivate_subscription(
        self,
        subscription_id: uuid.UUID,
        actor_user_id: uuid.UUID,
        ip_address: Optional[str] = None,
    ) -> Subscription:
        sub = (await self.session.execute(
            select(Subscription).where(Subscription.id == subscription_id)
        )).scalar_one_or_none()
        if not sub:
            raise AppException(404, "SUBSCRIPTION_NOT_FOUND", "Subscription not found")

        sub.status = SubscriptionStatus.ACTIVE
        tenant = (await self.session.execute(select(Tenant).where(Tenant.id == sub.tenant_id))).scalar_one_or_none()
        if tenant:
            tenant.status = TenantStatus.ACTIVE

        await self.repo.log_audit(
            tenant_id=sub.tenant_id,
            actor_user_id=actor_user_id,
            action="SUBSCRIPTION_REACTIVATED",
            resource="subscriptions",
            resource_id=str(sub.id),
            changes={},
            ip_address=ip_address,
        )
        await self.session.commit()
        return sub

    async def extend_trial(
        self,
        subscription_id: uuid.UUID,
        days: int,
        actor_user_id: uuid.UUID,
        ip_address: Optional[str] = None,
    ) -> Subscription:
        sub = (await self.session.execute(
            select(Subscription).where(Subscription.id == subscription_id)
        )).scalar_one_or_none()
        if not sub:
            raise AppException(404, "SUBSCRIPTION_NOT_FOUND", "Subscription not found")

        now = datetime.now(timezone.utc)
        base_date = sub.trial_ends_at or now
        if base_date < now:
            base_date = now

        new_end = base_date + timedelta(days=days)
        sub.trial_ends_at = new_end
        sub.current_period_end = new_end
        sub.status = SubscriptionStatus.TRIAL

        await self.repo.log_audit(
            tenant_id=sub.tenant_id,
            actor_user_id=actor_user_id,
            action="TRIAL_EXTENDED",
            resource="subscriptions",
            resource_id=str(sub.id),
            changes={"extended_days": days, "new_trial_ends_at": new_end.isoformat()},
            ip_address=ip_address,
        )
        await self.session.commit()
        return sub
