from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, Response, status
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import AppException
from app.models.enums import BillingCycle, InstitutionType
from app.models.user import User
from app.permissions.rbac import get_active_tenant_id, get_current_user, require_permission
from app.schemas.subscription import (
    CancelSubscriptionRequest,
    CreateOrderRequest,
    CreateOrderResponse,
    OrderPricingBreakdown,
    PreviewOrderRequest,
    SubscriptionInvoiceDetail,
    SubscriptionInvoiceSummary,
    SubscriptionPlanSchema,
    VerifyPaymentRequest,
)
from app.services.entitlement_service import EntitlementService
from app.services.subscription_service import SubscriptionService

router = APIRouter(prefix="/subscriptions", tags=["Subscriptions & Billing"])


# ── Current Subscription & Usage ──────────────────────────────────────────────
@router.get("/current")
async def get_current_subscription_and_usage(
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    entitlement_service = EntitlementService(session)
    data = await entitlement_service.get_tenant_usage_and_limits(tenant_id)
    return {"success": True, "data": data}


# ── Available Plans for Tenant ────────────────────────────────────────────────
@router.get("/plans")
async def list_available_plans(
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    institution_type: Optional[InstitutionType] = None,
    session: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    service = SubscriptionService(session)
    plans = await service.list_available_plans(institution_type=institution_type)
    items = [
        {
            "id": p.id,
            "name": p.name,
            "code": p.code,
            "description": p.description,
            "institution_type": p.institution_type.value if p.institution_type else None,
            "billing_cycle": p.billing_cycle.value,
            "price": float(p.price),
            "monthly_price": float(p.monthly_price),
            "annual_price": float(p.annual_price),
            "currency": p.currency,
            "max_students": p.max_students,
            "max_teachers": p.max_teachers,
            "storage_limit_gb": p.storage_limit_gb,
            "notification_quota": p.notification_quota,
            "trial_days": p.trial_days,
            "is_active": p.is_active,
            "features": [
                {
                    "feature_key": f.feature_key,
                    "feature_value": f.feature_value,
                    "is_enabled": f.is_enabled,
                }
                for f in p.features
            ],
            "created_at": p.created_at,
        }
        for p in plans
    ]
    return {"success": True, "data": items}


# ── Order Preview (Calculations & Coupon Check) ───────────────────────────────
@router.post("/preview-order")
async def preview_order(
    payload: PreviewOrderRequest,
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    session: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    service = SubscriptionService(session)
    pricing = await service.preview_order(
        tenant_id=tenant_id,
        plan_id=payload.plan_id,
        billing_cycle=payload.billing_cycle,
        coupon_code=payload.coupon_code,
    )
    return {"success": True, "data": pricing}


# ── Initiate Checkout (Server-Side Razorpay Order) ────────────────────────────
@router.post("/create-order")
async def create_subscription_order(
    payload: CreateOrderRequest,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    service = SubscriptionService(session)
    result = await service.create_subscription_order(
        tenant_id=tenant_id,
        plan_id=payload.plan_id,
        billing_cycle=payload.billing_cycle,
        coupon_code=payload.coupon_code,
        actor_user_id=current_user.id,
        billing_name=payload.billing_name or current_user.full_name,
        billing_address=payload.billing_address,
        ip_address=request.client.host if request.client else None,
    )
    return {"success": True, "data": result}


# ── Verify Payment (HMAC SHA-256 Server Verification) ─────────────────────────
@router.post("/verify-payment")
async def verify_subscription_payment(
    payload: VerifyPaymentRequest,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    service = SubscriptionService(session)
    result = await service.verify_payment(
        tenant_id=tenant_id,
        razorpay_order_id=payload.razorpay_order_id,
        razorpay_payment_id=payload.razorpay_payment_id,
        razorpay_signature=payload.razorpay_signature,
        invoice_id=payload.invoice_id,
        actor_user_id=current_user.id,
        ip_address=request.client.host if request.client else None,
    )
    return {
        "success": True,
        "data": result,
        "message": "Payment verified and subscription activated successfully",
    }


# ── Cancel / Disable Auto-Renew ───────────────────────────────────────────────
@router.post("/cancel")
async def cancel_subscription(
    payload: CancelSubscriptionRequest,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    service = SubscriptionService(session)
    result = await service.cancel_subscription(
        tenant_id=tenant_id,
        actor_user_id=current_user.id,
        immediate=payload.immediate,
        reason=payload.reason,
        ip_address=request.client.host if request.client else None,
    )
    return {"success": True, "data": result}


# ── Tenant Invoices ───────────────────────────────────────────────────────────
@router.get("/invoices")
async def list_invoices(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    session: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    service = SubscriptionService(session)
    invoices, total = await service.list_invoices(tenant_id, page, size)
    items = [
        {
            "id": inv.id,
            "invoice_number": inv.invoice_number,
            "billing_cycle": inv.billing_cycle.value,
            "subtotal": float(inv.subtotal),
            "discount_amount": float(inv.discount_amount),
            "tax_amount": float(inv.tax_amount),
            "total_amount": float(inv.total_amount),
            "currency": inv.currency,
            "status": inv.status.value,
            "due_date": inv.due_date,
            "paid_at": inv.paid_at,
            "created_at": inv.created_at,
        }
        for inv in invoices
    ]
    return {
        "success": True,
        "data": {
            "items": items,
            "total": total,
            "page": page,
            "size": size,
            "pages": (total + size - 1) // size if total > 0 else 0,
        },
    }


@router.get("/invoices/{invoice_id}")
async def get_invoice(
    invoice_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    session: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    service = SubscriptionService(session)
    inv = await service.get_invoice_detail(tenant_id, invoice_id)
    return {
        "success": True,
        "data": {
            "id": inv.id,
            "invoice_number": inv.invoice_number,
            "billing_cycle": inv.billing_cycle.value,
            "subtotal": float(inv.subtotal),
            "discount_amount": float(inv.discount_amount),
            "tax_amount": float(inv.tax_amount),
            "total_amount": float(inv.total_amount),
            "currency": inv.currency,
            "status": inv.status.value,
            "due_date": inv.due_date,
            "paid_at": inv.paid_at,
            "billing_name": inv.billing_name,
            "billing_address": inv.billing_address,
            "line_items": inv.line_items,
            "payments": [
                {
                    "id": p.id,
                    "amount": float(p.amount),
                    "gateway": p.gateway,
                    "transaction_reference": p.transaction_reference,
                    "status": p.status.value,
                    "paid_at": p.paid_at,
                }
                for p in inv.payments
            ],
            "created_at": inv.created_at,
        },
    }


@router.get("/invoices/{invoice_id}/html", response_class=HTMLResponse)
async def view_invoice_html(
    invoice_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    session: AsyncSession = Depends(get_db),
):
    service = SubscriptionService(session)
    html_content = await service.generate_invoice_html(tenant_id, invoice_id)
    return HTMLResponse(content=html_content)


# ── Razorpay Signed Webhook Endpoint (Public, Secured by HMAC SHA-256) ────────
@router.post("/razorpay-webhook")
async def razorpay_webhook(
    request: Request,
    x_razorpay_signature: Optional[str] = Header(None, alias="X-Razorpay-Signature"),
    session: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    if not x_razorpay_signature:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing X-Razorpay-Signature header",
        )

    raw_body = await request.body()
    service = SubscriptionService(session)
    result = await service.process_razorpay_webhook(raw_body, x_razorpay_signature)
    return {"success": True, "data": result}
