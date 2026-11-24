from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.user import User
from app.permissions.rbac import require_super_admin
from app.schemas.super_admin import (
    CouponCreate,
    CouponUpdate,
    GlobalAnnouncementCreate,
    InstitutionListQuery,
    InstitutionStatusUpdateRequest,
    PlatformIntegrationUpdate,
    PlatformSettingUpdate,
    SubscriptionPlanCreate,
    SubscriptionPlanUpdate,
    SupportTicketCreate,
    SupportTicketReplyCreate,
    SupportTicketStatusUpdate,
)
from app.services.super_admin_service import SuperAdminService

router = APIRouter(prefix="/super-admin", tags=["Super Admin"])


# ── Dashboard Statistics ──────────────────────────────────────────────────────
@router.get("/stats")
async def get_dashboard_stats(
    current_user: User = Depends(require_super_admin),
    session: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    service = SuperAdminService(session)
    data = await service.get_dashboard_stats()
    return {"success": True, "data": data}


# ── Institution Management ────────────────────────────────────────────────────
@router.get("/institutions")
async def list_institutions(
    search: Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    institution_type: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=100),
    current_user: User = Depends(require_super_admin),
    session: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    service = SuperAdminService(session)
    tenants, total = await service.list_institutions(search, status_filter, institution_type, page, size)

    items = [
        {
            "id": t.id,
            "name": t.name,
            "slug": t.slug,
            "institution_type": t.institution_type.value,
            "status": t.status.value,
            "email": t.email,
            "phone": t.phone,
            "city": t.city,
            "state": t.state,
            "country": t.country,
            "created_at": t.created_at,
        }
        for t in tenants
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


@router.get("/institutions/{tenant_id}")
async def get_institution_detail(
    tenant_id: uuid.UUID,
    current_user: User = Depends(require_super_admin),
    session: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    service = SuperAdminService(session)
    detail = await service.get_institution_detail(tenant_id)
    if not detail:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Institution not found")
    return {"success": True, "data": detail}


@router.post("/institutions/{tenant_id}/status")
async def update_institution_status(
    tenant_id: uuid.UUID,
    payload: InstitutionStatusUpdateRequest,
    request: Request,
    current_user: User = Depends(require_super_admin),
    session: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    service = SuperAdminService(session)
    try:
        tenant = await service.update_institution_status(
            tenant_id=tenant_id,
            new_status_str=payload.status,
            actor_user_id=current_user.id,
            reason=payload.reason,
            ip_address=request.client.host if request.client else None,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    return {
        "success": True,
        "data": {"id": tenant.id, "name": tenant.name, "status": tenant.status.value},
        "message": f"Institution status successfully updated to {payload.status}",
    }


@router.get("/institutions/{tenant_id}/users")
async def list_institution_users(
    tenant_id: uuid.UUID,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(require_super_admin),
    session: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    service = SuperAdminService(session)
    items, total = await service.list_institution_users(tenant_id, page, size)
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


# ── Subscription Plans Management ─────────────────────────────────────────────
@router.get("/plans")
async def list_plans(
    current_user: User = Depends(require_super_admin),
    session: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    from app.services.subscription_service import SubscriptionService
    sub_service = SubscriptionService(session)
    await sub_service.seed_default_plans_if_needed()

    service = SuperAdminService(session)
    plans = await service.list_plans()
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


@router.post("/plans")
async def create_plan(
    payload: SubscriptionPlanCreate,
    request: Request,
    current_user: User = Depends(require_super_admin),
    session: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    service = SuperAdminService(session)
    plan = await service.create_plan(
        payload=payload,
        actor_user_id=current_user.id,
        ip_address=request.client.host if request.client else None,
    )
    return {
        "success": True,
        "data": {"id": plan.id, "name": plan.name, "code": plan.code},
        "message": "Subscription plan created successfully",
    }


@router.put("/plans/{plan_id}")
async def update_plan(
    plan_id: uuid.UUID,
    payload: SubscriptionPlanUpdate,
    request: Request,
    current_user: User = Depends(require_super_admin),
    session: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    service = SuperAdminService(session)
    try:
        plan = await service.update_plan(
            plan_id=plan_id,
            payload=payload,
            actor_user_id=current_user.id,
            ip_address=request.client.host if request.client else None,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

    return {
        "success": True,
        "data": {"id": plan.id, "name": plan.name},
        "message": "Subscription plan updated successfully",
    }


@router.delete("/plans/{plan_id}")
async def delete_plan(
    plan_id: uuid.UUID,
    request: Request,
    current_user: User = Depends(require_super_admin),
    session: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    from app.models.subscription import SubscriptionPlan
    from sqlalchemy import select
    plan = (await session.execute(
        select(SubscriptionPlan).where(SubscriptionPlan.id == plan_id)
    )).scalar_one_or_none()
    if not plan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan not found")

    plan.is_active = False
    await session.commit()
    return {"success": True, "message": "Plan deactivated successfully"}


@router.post("/plans/seed")
async def seed_plans(
    current_user: User = Depends(require_super_admin),
    session: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    from app.services.subscription_service import SubscriptionService
    sub_service = SubscriptionService(session)
    await sub_service.seed_default_plans_if_needed()
    return {"success": True, "message": "Standardized School and College plans seeded"}


# ── Super Admin Coupon Management ─────────────────────────────────────────────
@router.get("/coupons")
async def list_coupons(
    current_user: User = Depends(require_super_admin),
    session: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    from app.repositories.subscription import SubscriptionRepository
    repo = SubscriptionRepository(session)
    coupons = await repo.list_coupons(only_active=False)
    items = [
        {
            "id": c.id,
            "code": c.code,
            "description": c.description,
            "discount_type": c.discount_type.value,
            "discount_value": float(c.discount_value),
            "max_redemptions": c.max_redemptions,
            "times_redeemed": c.times_redeemed,
            "valid_from": c.valid_from,
            "valid_until": c.valid_until,
            "is_active": c.is_active,
            "applicable_institution_type": c.applicable_institution_type.value if c.applicable_institution_type else None,
            "created_at": c.created_at,
        }
        for c in coupons
    ]
    return {"success": True, "data": items}


@router.post("/coupons")
async def create_coupon(
    payload: CouponCreate,
    current_user: User = Depends(require_super_admin),
    session: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    from app.models.enums import DiscountType, InstitutionType
    from app.models.subscription import Coupon
    from app.repositories.subscription import SubscriptionRepository
    from datetime import datetime, timezone

    repo = SubscriptionRepository(session)
    existing = await repo.get_coupon_by_code(payload.code)
    if existing:
        raise HTTPException(status_code=400, detail=f"Coupon '{payload.code}' already exists")

    coupon = Coupon(
        code=payload.code.strip().upper(),
        description=payload.description,
        discount_type=DiscountType(payload.discount_type),
        discount_value=payload.discount_value,
        max_redemptions=payload.max_redemptions,
        valid_from=payload.valid_from or datetime.now(timezone.utc),
        valid_until=payload.valid_until,
        is_active=payload.is_active,
        applicable_institution_type=InstitutionType(payload.applicable_institution_type) if payload.applicable_institution_type else None,
    )
    created = await repo.create_coupon(coupon)
    return {"success": True, "data": {"id": created.id, "code": created.code}, "message": "Coupon created successfully"}


@router.delete("/coupons/{coupon_id}")
async def deactivate_coupon(
    coupon_id: uuid.UUID,
    current_user: User = Depends(require_super_admin),
    session: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    from app.models.subscription import Coupon
    from sqlalchemy import select
    coupon = (await session.execute(select(Coupon).where(Coupon.id == coupon_id))).scalar_one_or_none()
    if not coupon:
        raise HTTPException(status_code=404, detail="Coupon not found")

    coupon.is_active = False
    await session.commit()
    return {"success": True, "message": "Coupon deactivated successfully"}


# ── Super Admin Subscription Lifecycle Controls ───────────────────────────────
@router.get("/subscriptions")
async def list_all_subscriptions(
    status: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(require_super_admin),
    session: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    from app.models.enums import SubscriptionStatus
    from app.repositories.subscription import SubscriptionRepository
    repo = SubscriptionRepository(session)
    sub_status = SubscriptionStatus(status) if status else None
    subs, total = await repo.list_all_subscriptions(status=sub_status, page=page, size=size)

    items = [
        {
            "id": s.id,
            "tenant_id": s.tenant_id,
            "tenant_name": s.tenant.name if s.tenant else "Unknown",
            "institution_type": s.tenant.institution_type.value if s.tenant and s.tenant.institution_type else "SCHOOL",
            "plan_name": s.plan.name if s.plan else "Unknown",
            "plan_code": s.plan.code if s.plan else "",
            "status": s.status.value,
            "billing_cycle": s.billing_cycle.value,
            "current_period_start": s.current_period_start,
            "current_period_end": s.current_period_end,
            "trial_ends_at": s.trial_ends_at,
            "is_auto_renew": s.is_auto_renew,
            "created_at": s.created_at,
        }
        for s in subs
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


@router.post("/subscriptions/{subscription_id}/suspend")
async def suspend_subscription(
    subscription_id: uuid.UUID,
    request: Request,
    reason: Optional[str] = None,
    current_user: User = Depends(require_super_admin),
    session: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    from app.services.subscription_service import SubscriptionService
    service = SubscriptionService(session)
    sub = await service.suspend_subscription(
        subscription_id=subscription_id,
        actor_user_id=current_user.id,
        reason=reason,
        ip_address=request.client.host if request.client else None,
    )
    return {"success": True, "message": "Subscription and tenant suspended successfully"}


@router.post("/subscriptions/{subscription_id}/reactivate")
async def reactivate_subscription(
    subscription_id: uuid.UUID,
    request: Request,
    current_user: User = Depends(require_super_admin),
    session: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    from app.services.subscription_service import SubscriptionService
    service = SubscriptionService(session)
    sub = await service.reactivate_subscription(
        subscription_id=subscription_id,
        actor_user_id=current_user.id,
        ip_address=request.client.host if request.client else None,
    )
    return {"success": True, "message": "Subscription and tenant reactivated successfully"}


@router.post("/subscriptions/{subscription_id}/extend-trial")
async def extend_trial(
    subscription_id: uuid.UUID,
    request: Request,
    days: int = Query(14, ge=1, le=90),
    current_user: User = Depends(require_super_admin),
    session: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    from app.services.subscription_service import SubscriptionService
    service = SubscriptionService(session)
    sub = await service.extend_trial(
        subscription_id=subscription_id,
        days=days,
        actor_user_id=current_user.id,
        ip_address=request.client.host if request.client else None,
    )
    return {"success": True, "message": f"Trial extended by {days} days successfully"}


# ── Global Announcements ──────────────────────────────────────────────────────
@router.get("/announcements")
async def list_announcements(
    current_user: User = Depends(require_super_admin),
    session: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    service = SuperAdminService(session)
    items = await service.list_announcements()
    return {
        "success": True,
        "data": [
            {
                "id": a.id,
                "title": a.title,
                "content": a.content,
                "target_role": a.target_role,
                "priority": a.priority,
                "is_active": a.is_active,
                "expires_at": a.expires_at,
                "created_at": a.created_at,
            }
            for a in items
        ],
    }


@router.post("/announcements")
async def create_announcement(
    payload: GlobalAnnouncementCreate,
    current_user: User = Depends(require_super_admin),
    session: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    service = SuperAdminService(session)
    ann = await service.create_announcement(payload, current_user.id)
    return {
        "success": True,
        "data": {"id": ann.id, "title": ann.title},
        "message": "Announcement published successfully",
    }


@router.delete("/announcements/{announcement_id}")
async def delete_announcement(
    announcement_id: uuid.UUID,
    current_user: User = Depends(require_super_admin),
    session: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    service = SuperAdminService(session)
    ok = await service.delete_announcement(announcement_id, current_user.id)
    if not ok:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Announcement not found")
    return {"success": True, "message": "Announcement deleted successfully"}


# ── Support Tickets ───────────────────────────────────────────────────────────
@router.get("/tickets")
async def list_tickets(
    status_filter: Optional[str] = Query(None, alias="status"),
    current_user: User = Depends(require_super_admin),
    session: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    service = SuperAdminService(session)
    tickets = await service.list_tickets(status_filter)
    return {"success": True, "data": tickets}


@router.post("/tickets")
async def create_ticket(
    payload: SupportTicketCreate,
    current_user: User = Depends(require_super_admin),
    session: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    service = SuperAdminService(session)
    ticket = await service.create_ticket(payload, current_user.id)
    return {"success": True, "data": {"id": ticket.id, "ticket_number": ticket.ticket_number}}


@router.put("/tickets/{ticket_id}/status")
async def update_ticket_status(
    ticket_id: uuid.UUID,
    payload: SupportTicketStatusUpdate,
    current_user: User = Depends(require_super_admin),
    session: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    service = SuperAdminService(session)
    ok = await service.update_ticket_status(ticket_id, payload.status, current_user.id, payload.assigned_to_user_id)
    if not ok:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found")
    return {"success": True, "message": "Ticket status updated successfully"}


@router.post("/tickets/{ticket_id}/replies")
async def reply_ticket(
    ticket_id: uuid.UUID,
    payload: SupportTicketReplyCreate,
    current_user: User = Depends(require_super_admin),
    session: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    service = SuperAdminService(session)
    reply = await service.reply_ticket(ticket_id, payload, current_user.id)
    return {
        "success": True,
        "data": {"id": reply.id, "ticket_id": reply.ticket_id, "message": reply.message},
        "message": "Reply recorded successfully",
    }


# ── Platform Settings & Integrations ──────────────────────────────────────────
@router.get("/settings")
async def get_platform_settings(
    current_user: User = Depends(require_super_admin),
    session: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    service = SuperAdminService(session)
    settings = await service.get_settings()
    return {
        "success": True,
        "data": [
            {
                "id": s.id,
                "category": s.category,
                "key": s.key,
                "value": s.value,
                "description": s.description,
                "is_secret": s.is_secret,
                "updated_at": s.updated_at,
            }
            for s in settings
        ],
    }


@router.post("/settings")
async def update_platform_setting(
    payload: PlatformSettingUpdate,
    request: Request,
    current_user: User = Depends(require_super_admin),
    session: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    service = SuperAdminService(session)
    s = await service.update_setting(
        payload=payload,
        actor_user_id=current_user.id,
        ip_address=request.client.host if request.client else None,
    )
    return {"success": True, "data": {"id": s.id, "key": s.key}, "message": "Platform setting updated"}


@router.get("/integrations")
async def list_integrations(
    current_user: User = Depends(require_super_admin),
    session: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    service = SuperAdminService(session)
    items = await service.list_integrations()
    return {
        "success": True,
        "data": [
            {
                "id": i.id,
                "provider": i.provider,
                "name": i.name,
                "is_enabled": i.is_enabled,
                "config": i.config,
                "status": i.status,
                "last_tested_at": i.last_tested_at,
                "updated_at": i.updated_at,
            }
            for i in items
        ],
    }


@router.put("/integrations/{provider}")
async def update_integration(
    provider: str,
    payload: PlatformIntegrationUpdate,
    current_user: User = Depends(require_super_admin),
    session: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    service = SuperAdminService(session)
    item = await service.update_integration(provider, payload, current_user.id)
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Integration provider not found")
    return {"success": True, "data": {"provider": item.provider, "is_enabled": item.is_enabled}}


# ── Platform Audit Logs ───────────────────────────────────────────────────────
@router.get("/audit-logs")
async def list_audit_logs(
    action: Optional[str] = Query(None),
    entity_type: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(require_super_admin),
    session: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    service = SuperAdminService(session)
    items, total = await service.list_audit_logs(action, entity_type, page, size)
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
