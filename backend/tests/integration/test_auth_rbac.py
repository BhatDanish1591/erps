from __future__ import annotations

import uuid
import pytest
from httpx import AsyncClient

from app.core.security import hash_password
from app.models.enums import InstitutionType, MembershipStatus, RoleScope, TenantStatus
from app.models.tenant import Tenant
from app.models.user import User
from app.repositories.role import RoleRepository
from app.repositories.tenant import TenantRepository
from app.repositories.user import UserRepository


@pytest.mark.asyncio
async def test_auth_registration_and_login_flow(client: AsyncClient):
    # ── 1. Register a new user with an initial institution ───────────────────
    reg_payload = {
        "email": f"principal_{uuid.uuid4().hex[:6]}@greenwood.edu",
        "password": "StrongPassword123!",
        "full_name": "Dr. Eleanor Vance",
        "phone": "+919876543210",
        "institution_name": "Greenwood High School",
        "institution_type": "SCHOOL",
    }
    reg_res = await client.post("/api/v1/auth/register", json=reg_payload)
    assert reg_res.status_code == 201, reg_res.text
    reg_body = reg_res.json()
    assert reg_body["success"] is True
    assert "access_token" in reg_body["data"]
    assert "refresh_token" in reg_body["data"]
    user_data = reg_body["data"]["user"]
    assert user_data["email"] == reg_payload["email"]
    assert len(user_data["institutions"]) == 1
    assert user_data["institutions"][0]["role_code"] == "INSTITUTION_ADMIN"

    # ── 2. Login with email ──────────────────────────────────────────────────
    login_payload = {
        "identifier": reg_payload["email"],
        "password": "StrongPassword123!",
    }
    login_res = await client.post("/api/v1/auth/login", json=login_payload)
    assert login_res.status_code == 200
    login_body = login_res.json()
    assert login_body["success"] is True
    access_token = login_body["data"]["access_token"]
    refresh_token = login_body["data"]["refresh_token"]

    # ── 3. Access protected /auth/me endpoint ────────────────────────────────
    me_res = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert me_res.status_code == 200
    me_data = me_res.json()["data"]
    assert me_data["email"] == reg_payload["email"]

    # ── 4. Rotate refresh token ──────────────────────────────────────────────
    refresh_res = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    assert refresh_res.status_code == 200
    new_refresh_token = refresh_res.json()["data"]["refresh_token"]
    assert new_refresh_token != refresh_token

    # ── 5. Logout using new refresh token ────────────────────────────────────
    logout_res = await client.post(
        "/api/v1/auth/logout",
        json={"refresh_token": new_refresh_token},
    )
    assert logout_res.status_code == 200


@pytest.mark.asyncio
async def test_multi_institution_user_and_context_switching(client: AsyncClient, db_session):
    tenant_repo = TenantRepository(db_session)
    user_repo = UserRepository(db_session)
    role_repo = RoleRepository(db_session)

    # Create two institutions
    inst_1 = await tenant_repo.create(
        name="St. Xavier High School",
        slug=f"st-xavier-{uuid.uuid4().hex[:6]}",
        institution_type=InstitutionType.SCHOOL,
        status=TenantStatus.ACTIVE,
    )
    inst_2 = await tenant_repo.create(
        name="Loyola College of Arts",
        slug=f"loyola-{uuid.uuid4().hex[:6]}",
        institution_type=InstitutionType.COLLEGE,
        status=TenantStatus.ACTIVE,
    )

    # Fetch roles
    teacher_role = await role_repo.get_by_code("TEACHER")
    parent_role = await role_repo.get_by_code("PARENT")

    # Create user belonging to BOTH institutions with different roles
    test_email = f"multi_user_{uuid.uuid4().hex[:6]}@example.com"
    user = await user_repo.create(
        email=test_email,
        password_hash=hash_password("UserPass123!"),
        full_name="Rajesh Sharma",
        phone="+919999988888",
        is_active=True,
    )

    # Membership 1: TEACHER in St. Xavier
    await user_repo.create_membership(
        tenant_id=inst_1.id,
        user_id=user.id,
        role_id=teacher_role.id,
        status=MembershipStatus.ACTIVE,
    )

    # Membership 2: PARENT in Loyola College
    await user_repo.create_membership(
        tenant_id=inst_2.id,
        user_id=user.id,
        role_id=parent_role.id,
        status=MembershipStatus.ACTIVE,
    )
    await db_session.commit()

    # Login without specifying institution -> user sees both available
    login_res = await client.post(
        "/api/v1/auth/login",
        json={"identifier": test_email, "password": "UserPass123!"},
    )
    assert login_res.status_code == 200
    data = login_res.json()["data"]
    assert len(data["user"]["institutions"]) == 2
    token = data["access_token"]

    # Select Institution 1 (Teacher role)
    select_res_1 = await client.post(
        "/api/v1/auth/select-institution",
        json={"tenant_id": str(inst_1.id)},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert select_res_1.status_code == 200
    token_inst_1 = select_res_1.json()["data"]["access_token"]
    user_inst_1 = select_res_1.json()["data"]["user"]
    assert user_inst_1["current_tenant_id"] == str(inst_1.id)
    assert user_inst_1["current_role"] == "TEACHER"

    # Select Institution 2 (Parent role)
    select_res_2 = await client.post(
        "/api/v1/auth/select-institution",
        json={"tenant_id": str(inst_2.id)},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert select_res_2.status_code == 200
    user_inst_2 = select_res_2.json()["data"]["user"]
    assert user_inst_2["current_tenant_id"] == str(inst_2.id)
    assert user_inst_2["current_role"] == "PARENT"


@pytest.mark.asyncio
async def test_permission_based_authorization_enforcement(client: AsyncClient, db_session):
    tenant_repo = TenantRepository(db_session)
    user_repo = UserRepository(db_session)
    role_repo = RoleRepository(db_session)

    # Setup institution
    inst = await tenant_repo.create(
        name="Delhi Public Academy",
        slug=f"dpa-{uuid.uuid4().hex[:6]}",
        institution_type=InstitutionType.SCHOOL,
        status=TenantStatus.ACTIVE,
    )

    admin_role = await role_repo.get_by_code("INSTITUTION_ADMIN")
    teacher_role = await role_repo.get_by_code("TEACHER")

    # User A: Admin
    admin_user = await user_repo.create(
        email=f"admin_{uuid.uuid4().hex[:6]}@dpa.edu",
        password_hash=hash_password("AdminPass123!"),
        full_name="Admin User",
        is_active=True,
    )
    await user_repo.create_membership(inst.id, admin_user.id, admin_role.id)

    # User B: Teacher
    teacher_user = await user_repo.create(
        email=f"teacher_{uuid.uuid4().hex[:6]}@dpa.edu",
        password_hash=hash_password("TeacherPass123!"),
        full_name="Teacher User",
        is_active=True,
    )
    await user_repo.create_membership(inst.id, teacher_user.id, teacher_role.id)
    await db_session.commit()

    # Login Admin
    res_admin = await client.post(
        "/api/v1/auth/login",
        json={"identifier": admin_user.email, "password": "AdminPass123!", "tenant_id": str(inst.id)},
    )
    admin_token = res_admin.json()["data"]["access_token"]

    # Login Teacher
    res_teacher = await client.post(
        "/api/v1/auth/login",
        json={"identifier": teacher_user.email, "password": "TeacherPass123!", "tenant_id": str(inst.id)},
    )
    teacher_token = res_teacher.json()["data"]["access_token"]

    # 1. Admin CAN create a custom role (requires users:manage_roles)
    create_role_res = await client.post(
        "/api/v1/roles",
        json={
            "name": "Head of Mathematics",
            "code": f"MATH_HEAD_{uuid.uuid4().hex[:4]}",
            "description": "Department Head",
            "permission_codes": ["academic:session:read", "exams:read"],
        },
        headers={
            "Authorization": f"Bearer {admin_token}",
            "X-Tenant-ID": str(inst.id),
        },
    )
    assert create_role_res.status_code == 201, create_role_res.text

    # 2. Teacher CANNOT create a custom role (Forbidden 403: missing required permission)
    teacher_attempt = await client.post(
        "/api/v1/roles",
        json={
            "name": "Unauthorized Role",
            "code": "UNAUTH_ROLE",
            "permission_codes": [],
        },
        headers={
            "Authorization": f"Bearer {teacher_token}",
            "X-Tenant-ID": str(inst.id),
        },
    )
    assert teacher_attempt.status_code == 403
    assert teacher_attempt.json()["error"]["code"] == "AUTHORIZATION_ERROR"
