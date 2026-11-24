from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.academic import StudentProfile, TeacherProfile
from app.models.audit import AuditLog
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
    WebhookEvent,
)
from app.models.tenant import Tenant


class SubscriptionRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    # ── Plan Management ───────────────────────────────────────────────────────
    async def list_plans(
        self,
        institution_type: Optional[InstitutionType] = None,
        only_active: bool = True,
    ) -> List[SubscriptionPlan]:
        query = select(SubscriptionPlan).options(selectinload(SubscriptionPlan.features))
        if only_active:
            query = query.where(SubscriptionPlan.is_active == True)
        if institution_type:
            query = query.where(
                or_(
                    SubscriptionPlan.institution_type == institution_type,
                    SubscriptionPlan.institution_type.is_(None),
                )
            )
        query = query.order_by(SubscriptionPlan.monthly_price.asc())
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_plan_by_id(self, plan_id: uuid.UUID) -> Optional[SubscriptionPlan]:
        query = (
            select(SubscriptionPlan)
            .options(selectinload(SubscriptionPlan.features))
            .where(SubscriptionPlan.id == plan_id)
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_plan_by_code(self, code: str) -> Optional[SubscriptionPlan]:
        query = (
            select(SubscriptionPlan)
            .options(selectinload(SubscriptionPlan.features))
            .where(SubscriptionPlan.code == code)
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def create_plan(self, plan: SubscriptionPlan, features: List[PlanFeature]) -> SubscriptionPlan:
        self.session.add(plan)
        await self.session.flush()
        for f in features:
            f.plan_id = plan.id
            self.session.add(f)
        await self.session.commit()
        await self.session.refresh(plan)
        return plan

    async def update_plan(self, plan: SubscriptionPlan) -> SubscriptionPlan:
        await self.session.commit()
        await self.session.refresh(plan)
        return plan

    # ── Coupon Management ─────────────────────────────────────────────────────
    async def list_coupons(self, only_active: bool = False) -> List[Coupon]:
        query = select(Coupon)
        if only_active:
            now = datetime.now(timezone.utc)
            query = query.where(
                Coupon.is_active == True,
                Coupon.valid_from <= now,
                or_(Coupon.valid_until.is_(None), Coupon.valid_until >= now),
            )
        query = query.order_by(Coupon.created_at.desc())
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_coupon_by_code(self, code: str) -> Optional[Coupon]:
        clean_code = code.strip().upper()
        query = select(Coupon).where(Coupon.code == clean_code)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def create_coupon(self, coupon: Coupon) -> Coupon:
        coupon.code = coupon.code.strip().upper()
        self.session.add(coupon)
        await self.session.commit()
        await self.session.refresh(coupon)
        return coupon

    # ── Tenant Subscriptions ──────────────────────────────────────────────────
    async def get_tenant_subscription(self, tenant_id: uuid.UUID) -> Optional[Subscription]:
        query = (
            select(Subscription)
            .options(selectinload(Subscription.plan).selectinload(SubscriptionPlan.features))
            .where(Subscription.tenant_id == tenant_id)
            .order_by(Subscription.created_at.desc())
        )
        result = await self.session.execute(query)
        return result.scalars().first()

    async def list_all_subscriptions(
        self,
        status: Optional[SubscriptionStatus] = None,
        page: int = 1,
        size: int = 20,
    ) -> Tuple[List[Subscription], int]:
        base_query = select(Subscription).options(
            selectinload(Subscription.plan),
            selectinload(Subscription.tenant),
        )
        count_query = select(func.count(Subscription.id))

        if status:
            base_query = base_query.where(Subscription.status == status)
            count_query = count_query.where(Subscription.status == status)

        total = (await self.session.execute(count_query)).scalar() or 0
        paginated_query = (
            base_query.order_by(Subscription.created_at.desc())
            .offset((page - 1) * size)
            .limit(size)
        )
        result = await self.session.execute(paginated_query)
        return list(result.scalars().all()), total

    # ── Invoices & Payments ───────────────────────────────────────────────────
    async def create_invoice(self, invoice: SubscriptionInvoice) -> SubscriptionInvoice:
        self.session.add(invoice)
        await self.session.flush()
        return invoice

    async def create_payment(self, payment: SubscriptionPayment) -> SubscriptionPayment:
        self.session.add(payment)
        await self.session.flush()
        return payment

    async def get_invoice_by_id(
        self, invoice_id: uuid.UUID, tenant_id: Optional[uuid.UUID] = None, *, for_update: bool = False
    ) -> Optional[SubscriptionInvoice]:
        query = (
            select(SubscriptionInvoice)
            .options(
                selectinload(SubscriptionInvoice.payments),
                selectinload(SubscriptionInvoice.subscription),
                selectinload(SubscriptionInvoice.tenant),
            )
            .where(SubscriptionInvoice.id == invoice_id)
        )
        if tenant_id:
            query = query.where(SubscriptionInvoice.tenant_id == tenant_id)
        if for_update:
            query = query.with_for_update().execution_options(populate_existing=True)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_payment_by_order_id(self, gateway_order_id: str) -> Optional[SubscriptionPayment]:
        query = (
            select(SubscriptionPayment)
            .options(
                selectinload(SubscriptionPayment.invoice).selectinload(SubscriptionInvoice.subscription),
                selectinload(SubscriptionPayment.tenant),
            )
            .where(SubscriptionPayment.gateway_order_id == gateway_order_id)
            .order_by(SubscriptionPayment.created_at.desc())
        )
        result = await self.session.execute(query)
        return result.scalars().first()

    async def list_tenant_invoices(
        self,
        tenant_id: uuid.UUID,
        page: int = 1,
        size: int = 20,
    ) -> Tuple[List[SubscriptionInvoice], int]:
        base_query = select(SubscriptionInvoice).where(SubscriptionInvoice.tenant_id == tenant_id)
        count_query = select(func.count(SubscriptionInvoice.id)).where(
            SubscriptionInvoice.tenant_id == tenant_id
        )

        total = (await self.session.execute(count_query)).scalar() or 0
        paginated_query = (
            base_query.order_by(SubscriptionInvoice.created_at.desc())
            .offset((page - 1) * size)
            .limit(size)
        )
        result = await self.session.execute(paginated_query)
        return list(result.scalars().all()), total

    # ── Webhook Idempotency ───────────────────────────────────────────────────
    async def get_webhook_event(self, event_id: str) -> Optional[WebhookEvent]:
        query = select(WebhookEvent).where(WebhookEvent.event_id == event_id)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def record_webhook_event(
        self,
        event_id: str,
        event_type: str,
        payload: dict,
        gateway: str = "razorpay",
    ) -> WebhookEvent:
        event = WebhookEvent(
            event_id=event_id,
            gateway=gateway,
            event_type=event_type,
            payload=payload,
            is_processed=False,
        )
        self.session.add(event)
        await self.session.flush()
        return event

    async def log_audit(
        self,
        tenant_id: Optional[uuid.UUID],
        actor_user_id: Optional[uuid.UUID],
        action: str,
        resource: str,
        resource_id: Optional[str] = None,
        changes: Optional[dict] = None,
        ip_address: Optional[str] = None,
    ) -> None:
        log = AuditLog(
            tenant_id=tenant_id,
            user_id=actor_user_id,
            action=action,
            entity_type=resource,
            entity_id=resource_id,
            changes=changes or {},
            ip_address=ip_address,
        )
        self.session.add(log)
