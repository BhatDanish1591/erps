from __future__ import annotations

import uuid
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token, hash_password
from app.main import app
from app.models.auth import Role
from app.models.user import User
from app.models.enums import RoleScope, TenantStatus
from app.models.tenant import Tenant


@pytest.mark.asyncio
async def test_super_admin_authorization_enforcement(client: AsyncClient, db_session: AsyncSession):
    # Create normal teacher user
    normal_user = User(
        email=f"teacher_{uuid.uuid4().hex[:6]}@example.com",
        password_hash=hash_password("Password123!"),
        full_name="Jane Doe",
        is_superadmin=False,
        is_active=True,
    )
    db_session.add(normal_user)
    await db_session.commit()

    normal_token = create_access_token(
        user_id=normal_user.id,
        email=normal_user.email,
        role="TEACHER",
        is_superadmin=False,
    )

    # Non-superadmin should receive 403 Forbidden
    res = await client.get(
        "/api/v1/super-admin/stats",
        headers={"Authorization": f"Bearer {normal_token}"},
    )
    assert res.status_code == 403
    data = res.json()
    assert data["success"] is False


@pytest.mark.asyncio
async def test_super_admin_dashboard_stats_and_institution_lifecycle(client: AsyncClient, db_session: AsyncSession):
    # Create super admin user
    super_admin = User(
        email=f"superadmin_{uuid.uuid4().hex[:6]}@edusaas.com",
        password_hash=hash_password("SuperSecret123!"),
        full_name="Platform Admin",
        is_superadmin=True,
        is_active=True,
    )
    # Create test institution
    tenant = Tenant(
        name="Oakridge International",
        slug=f"oakridge-{uuid.uuid4().hex[:6]}",
        status=TenantStatus.PENDING,
        email="info@oakridge.edu",
    )
    db_session.add(super_admin)
    db_session.add(tenant)
    await db_session.commit()

    admin_token = create_access_token(
        user_id=super_admin.id,
        email=super_admin.email,
        role="SUPER_ADMIN",
        is_superadmin=True,
    )

    headers = {"Authorization": f"Bearer {admin_token}"}

    # 1. Fetch dashboard stats
    res = await client.get("/api/v1/super-admin/stats", headers=headers)
    assert res.status_code == 200
    stats = res.json()["data"]
    assert stats["total_institutions"] >= 1
    assert "mrr" in stats
    assert "arr" in stats
    assert "recent_institutions" in stats

    # 2. List institutions
    res = await client.get("/api/v1/super-admin/institutions", headers=headers)
    assert res.status_code == 200
    institutions = res.json()["data"]["items"]
    assert len(institutions) >= 1
    found = any(i["id"] == str(tenant.id) for i in institutions)
    assert found is True

    # 3. Get institution detail
    res = await client.get(f"/api/v1/super-admin/institutions/{tenant.id}", headers=headers)
    assert res.status_code == 200
    detail = res.json()["data"]
    assert detail["name"] == "Oakridge International"
    assert detail["status"] == "PENDING"

    # 4. Approve institution (PENDING -> ACTIVE)
    res = await client.post(
        f"/api/v1/super-admin/institutions/{tenant.id}/status",
        headers=headers,
        json={"status": "ACTIVE", "reason": "Documents verified by platform admin"},
    )
    assert res.status_code == 200
    assert res.json()["data"]["status"] == "ACTIVE"

    # 5. Suspend institution (ACTIVE -> SUSPENDED)
    res = await client.post(
        f"/api/v1/super-admin/institutions/{tenant.id}/status",
        headers=headers,
        json={"status": "SUSPENDED", "reason": "Billing dispute"},
    )
    assert res.status_code == 200
    assert res.json()["data"]["status"] == "SUSPENDED"

    # 6. Verify audit logs record this transition
    res = await client.get("/api/v1/super-admin/audit-logs", headers=headers)
    assert res.status_code == 200
    audit_items = res.json()["data"]["items"]
    assert len(audit_items) >= 2
    suspend_logged = any("INSTITUTION_SUSPENDED" in a["action"] for a in audit_items)
    assert suspend_logged is True


@pytest.mark.asyncio
async def test_super_admin_plans_and_announcements(client: AsyncClient, db_session: AsyncSession):
    super_admin = User(
        email=f"admin_plans_{uuid.uuid4().hex[:6]}@edusaas.com",
        password_hash=hash_password("SuperSecret123!"),
        full_name="Plan Manager",
        is_superadmin=True,
        is_active=True,
    )
    db_session.add(super_admin)
    await db_session.commit()

    admin_token = create_access_token(
        user_id=super_admin.id,
        email=super_admin.email,
        role="SUPER_ADMIN",
        is_superadmin=True,
    )
    headers = {"Authorization": f"Bearer {admin_token}"}

    # 1. Create a subscription plan
    plan_code = f"tier_pro_{uuid.uuid4().hex[:4]}"
    res = await client.post(
        "/api/v1/super-admin/plans",
        headers=headers,
        json={
            "name": "Enterprise Pro Tier",
            "code": plan_code,
            "description": "Full access for large campuses",
            "billing_cycle": "YEARLY",
            "price": 49999.00,
            "currency": "INR",
            "features": [
                {"feature_key": "max_students", "feature_value": {"limit": 5000}, "is_enabled": True},
                {"feature_key": "sms_alerts", "feature_value": {"enabled": True}, "is_enabled": True},
            ],
        },
    )
    assert res.status_code == 200
    plan_id = res.json()["data"]["id"]

    # 2. List plans and verify newly created plan
    res = await client.get("/api/v1/super-admin/plans", headers=headers)
    assert res.status_code == 200
    plans = res.json()["data"]
    matching = [p for p in plans if p["id"] == plan_id]
    assert len(matching) == 1
    assert len(matching[0]["features"]) == 2

    # 3. Create global announcement
    res = await client.post(
        "/api/v1/super-admin/announcements",
        headers=headers,
        json={
            "title": "Scheduled Platform Maintenance",
            "content": "Platform maintenance on Sunday midnight for 30 minutes.",
            "priority": "HIGH",
        },
    )
    assert res.status_code == 200
    ann_id = res.json()["data"]["id"]

    # 4. List announcements
    res = await client.get("/api/v1/super-admin/announcements", headers=headers)
    assert res.status_code == 200
    anns = res.json()["data"]
    assert any(a["id"] == ann_id for a in anns)

    # 5. Delete announcement
    res = await client.delete(f"/api/v1/super-admin/announcements/{ann_id}", headers=headers)
    assert res.status_code == 200
