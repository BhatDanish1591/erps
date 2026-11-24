from __future__ import annotations

import hashlib
import hmac
import uuid
from datetime import datetime, timezone
from typing import AsyncGenerator

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import create_access_token, hash_password
from app.models.auth import Membership, Role
from app.models.enums import BillingCycle, DiscountType, InstitutionType, MembershipStatus, RoleScope, SubscriptionStatus, TenantStatus
from app.models.subscription import Coupon, Subscription, SubscriptionInvoice, SubscriptionPlan
from app.models.tenant import Tenant
from app.models.user import User
from app.services.entitlement_service import EntitlementService, SubscriptionLimitExceeded
from app.services.subscription_service import SubscriptionService


@pytest.fixture
async def setup_test_data(db_session: AsyncSession):
    # 1. Tenant
    tenant = Tenant(
        name="Springdale Public School",
        slug=f"springdale-{uuid.uuid4().hex[:6]}",
        institution_type=InstitutionType.SCHOOL,
        status=TenantStatus.ACTIVE,
        email=f"admin_{uuid.uuid4().hex[:6]}@springdale.edu",
    )
    db_session.add(tenant)

    # 2. Admin User
    admin_user = User(
        email=f"admin_{uuid.uuid4().hex[:6]}@springdale.edu",
        password_hash=hash_password("Password123!"),
        full_name="Principal Skinner",
        is_superadmin=False,
        is_active=True,
    )
    db_session.add(admin_user)

    # 3. Super Admin User
    superadmin = User(
        email=f"superadmin_{uuid.uuid4().hex[:6]}@edusaas.com",
        password_hash=hash_password("SuperAdmin123!"),
        full_name="Platform Owner",
        is_superadmin=True,
        is_active=True,
    )
    db_session.add(superadmin)
    await db_session.flush()

    # 4. Role & Membership
    role = (await db_session.execute(select(Role).where(Role.code == "INSTITUTION_ADMIN"))).scalars().first()
    if not role:
        role = Role(name="Institution Admin", code="INSTITUTION_ADMIN", scope=RoleScope.TENANT, is_system_role=True)
        db_session.add(role)
        await db_session.flush()

    membership = Membership(
        user_id=admin_user.id,
        tenant_id=tenant.id,
        role_id=role.id,
        status=MembershipStatus.ACTIVE,
    )
    db_session.add(membership)

    # 5. Ensure subscription plans are seeded and tenant has trial subscription
    sub_service = SubscriptionService(db_session)
    await sub_service.seed_default_plans_if_needed()

    starter_plan = (await db_session.execute(
        select(SubscriptionPlan).where(SubscriptionPlan.code == "STARTER_SCHOOL")
    )).scalars().first()
    if starter_plan:
        now = datetime.now(timezone.utc)
        from datetime import timedelta
        sub = Subscription(
            tenant_id=tenant.id,
            plan_id=starter_plan.id,
            status=SubscriptionStatus.TRIAL,
            billing_cycle=BillingCycle.MONTHLY,
            current_period_start=now,
            current_period_end=now + timedelta(days=30),
            trial_ends_at=now + timedelta(days=30),
            is_auto_renew=False,
        )
        db_session.add(sub)

    await db_session.commit()

    admin_token = create_access_token(
        user_id=admin_user.id,
        email=admin_user.email,
        tenant_id=tenant.id,
        role="INSTITUTION_ADMIN",
        is_superadmin=False,
    )
    super_token = create_access_token(
        user_id=superadmin.id,
        email=superadmin.email,
        is_superadmin=True,
    )

    return {
        "tenant": tenant,
        "admin_user": admin_user,
        "superadmin": superadmin,
        "admin_headers": {"Authorization": f"Bearer {admin_token}"},
        "super_headers": {"Authorization": f"Bearer {super_token}"},
    }


@pytest.mark.asyncio
async def test_subscription_plans_and_pricing(
    client: AsyncClient,
    setup_test_data: dict,
):
    auth_headers = setup_test_data["admin_headers"]

    # 1. Fetch available plans as tenant
    resp = await client.get("/api/v1/subscriptions/plans", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert len(data) >= 6

    # Verify standard School plans per Prompt 5 spec
    starter_school = next((p for p in data if p["code"] == "STARTER_SCHOOL"), None)
    assert starter_school is not None
    assert starter_school["monthly_price"] == 999.00
    assert starter_school["max_students"] == 300
    assert starter_school["max_teachers"] == 20

    pro_school = next((p for p in data if p["code"] == "PRO_SCHOOL"), None)
    assert pro_school is not None
    assert pro_school["monthly_price"] == 2499.00
    assert pro_school["max_students"] == 1000
    assert pro_school["max_teachers"] == 75

    enterprise_school = next((p for p in data if p["code"] == "ENTERPRISE_SCHOOL"), None)
    assert enterprise_school is not None
    assert enterprise_school["monthly_price"] == 4999.00
    assert enterprise_school["max_students"] == 3000
    assert enterprise_school["max_teachers"] == 200

    # Verify standard College plans per Prompt 5 spec
    basic_college = next((p for p in data if p["code"] == "BASIC_COLLEGE"), None)
    assert basic_college is not None
    assert basic_college["monthly_price"] == 2499.00
    assert basic_college["max_students"] == 500

    pro_college = next((p for p in data if p["code"] == "PRO_COLLEGE"), None)
    assert pro_college is not None
    assert pro_college["monthly_price"] == 5999.00
    assert pro_college["max_students"] == 2000

    enterprise_college = next((p for p in data if p["code"] == "ENTERPRISE_COLLEGE"), None)
    assert enterprise_college is not None
    assert enterprise_college["monthly_price"] == 9999.00
    assert enterprise_college["max_students"] == 5000


@pytest.mark.asyncio
async def test_coupon_validation_and_preview_order(
    client: AsyncClient,
    setup_test_data: dict,
):
    auth_headers = setup_test_data["admin_headers"]
    superadmin_headers = setup_test_data["super_headers"]

    # 1. Super Admin creates a promotional coupon
    coupon_code = f"DISC20_{uuid.uuid4().hex[:4].upper()}"
    coupon_resp = await client.post(
        "/api/v1/super-admin/coupons",
        headers=superadmin_headers,
        json={
            "code": coupon_code,
            "description": "20% off launch discount",
            "discount_type": "PERCENTAGE",
            "discount_value": 20.0,
            "max_redemptions": 100,
            "is_active": True,
        },
    )
    assert coupon_resp.status_code == 200

    # 2. Find Starter School plan
    plans_resp = await client.get("/api/v1/subscriptions/plans", headers=auth_headers)
    starter = next(p for p in plans_resp.json()["data"] if p["code"] == "STARTER_SCHOOL")

    # 3. Preview order with coupon
    preview_resp = await client.post(
        "/api/v1/subscriptions/preview-order",
        headers=auth_headers,
        json={
            "plan_id": starter["id"],
            "billing_cycle": "MONTHLY",
            "coupon_code": coupon_code,
        },
    )
    assert preview_resp.status_code == 200
    pricing = preview_resp.json()["data"]
    assert pricing["base_price"] == 999.0
    assert pricing["discount_amount"] == 199.80  # 20% of 999
    assert pricing["subtotal"] == 799.20
    assert pricing["tax_amount"] == 143.86  # 18% GST on 799.20
    assert pricing["total_amount"] == 943.06
    assert pricing["coupon_applied"] == coupon_code


@pytest.mark.asyncio
async def test_order_creation_and_payment_verification_lifecycle(
    client: AsyncClient,
    setup_test_data: dict,
):
    auth_headers = setup_test_data["admin_headers"]

    # 1. Get plan
    plans_resp = await client.get("/api/v1/subscriptions/plans", headers=auth_headers)
    starter = next(p for p in plans_resp.json()["data"] if p["code"] == "STARTER_SCHOOL")

    # 2. Create order
    order_resp = await client.post(
        "/api/v1/subscriptions/create-order",
        headers=auth_headers,
        json={
            "plan_id": starter["id"],
            "billing_cycle": "MONTHLY",
            "billing_name": "Springdale Public School",
            "billing_address": "123 Education Lane",
        },
    )
    assert order_resp.status_code == 200
    order_data = order_resp.json()["data"]
    assert "order_id" in order_data
    assert "invoice_id" in order_data
    assert order_data["amount"] > 0

    order_id = order_data["order_id"]
    invoice_id = order_data["invoice_id"]
    payment_id = f"pay_{uuid.uuid4().hex[:14]}"

    # 3. Verify payment with fraudulent signature -> MUST FAIL (400)
    fraud_resp = await client.post(
        "/api/v1/subscriptions/verify-payment",
        headers=auth_headers,
        json={
            "razorpay_order_id": order_id,
            "razorpay_payment_id": payment_id,
            "razorpay_signature": "invalid_fraudulent_signature",
            "invoice_id": invoice_id,
        },
    )
    assert fraud_resp.status_code == 400
    assert fraud_resp.json()["error"]["code"] == "PAYMENT_VERIFICATION_FAILED"

    # 4. Verify payment with valid mock signature -> MUST SUCCEED (200)
    valid_mock_sig = f"mock_sig_{payment_id}"
    success_resp = await client.post(
        "/api/v1/subscriptions/verify-payment",
        headers=auth_headers,
        json={
            "razorpay_order_id": order_id,
            "razorpay_payment_id": payment_id,
            "razorpay_signature": valid_mock_sig,
            "invoice_id": invoice_id,
        },
    )
    assert success_resp.status_code == 200
    result = success_resp.json()["data"]
    assert result["status"] == "ACTIVE"

    # 5. Check current subscription & usage stats
    current_resp = await client.get("/api/v1/subscriptions/current", headers=auth_headers)
    assert current_resp.status_code == 200
    usage_data = current_resp.json()["data"]
    assert usage_data["status"] == "ACTIVE"
    assert usage_data["usage"]["students"]["limit"] == 300
    assert usage_data["usage"]["teachers"]["limit"] == 20

    # 6. Check invoice list & HTML receipt
    inv_list_resp = await client.get("/api/v1/subscriptions/invoices", headers=auth_headers)
    assert inv_list_resp.status_code == 200
    assert inv_list_resp.json()["data"]["total"] >= 1

    html_resp = await client.get(f"/api/v1/subscriptions/invoices/{invoice_id}/html", headers=auth_headers)
    assert html_resp.status_code == 200
    assert "TAX INVOICE" in html_resp.text
    assert "PAID" in html_resp.text


@pytest.mark.asyncio
async def test_dynamic_entitlement_service(
    db_session: AsyncSession,
    setup_test_data: dict,
):
    tenant = setup_test_data["tenant"]
    entitlement_service = EntitlementService(db_session)

    # 1. Usage report
    usage = await entitlement_service.get_tenant_usage_and_limits(tenant.id)
    assert "students" in usage["usage"]
    assert "teachers" in usage["usage"]

    # 2. Check within quota
    await entitlement_service.check_quota(tenant.id, "students", increment=1)

    # 3. Check exceeding quota -> Raises SubscriptionLimitExceeded
    with pytest.raises(SubscriptionLimitExceeded) as exc_info:
        await entitlement_service.check_quota(tenant.id, "students", increment=10000)
    assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_super_admin_subscription_lifecycle_controls(
    client: AsyncClient,
    setup_test_data: dict,
):
    superadmin_headers = setup_test_data["super_headers"]

    # 1. Super Admin lists all subscriptions
    subs_resp = await client.get("/api/v1/super-admin/subscriptions", headers=superadmin_headers)
    assert subs_resp.status_code == 200
    items = subs_resp.json()["data"]["items"]
    assert len(items) >= 1

    target_sub = items[0]
    sub_id = target_sub["id"]

    # 2. Suspend subscription
    suspend_resp = await client.post(
        f"/api/v1/super-admin/subscriptions/{sub_id}/suspend",
        headers=superadmin_headers,
        json={"reason": "Non-payment of platform invoice"},
    )
    assert suspend_resp.status_code == 200

    # 3. Reactivate subscription
    reactivate_resp = await client.post(
        f"/api/v1/super-admin/subscriptions/{sub_id}/reactivate",
        headers=superadmin_headers,
    )
    assert reactivate_resp.status_code == 200

    # 4. Extend trial
    extend_resp = await client.post(
        f"/api/v1/super-admin/subscriptions/{sub_id}/extend-trial?days=15",
        headers=superadmin_headers,
    )
    assert extend_resp.status_code == 200
