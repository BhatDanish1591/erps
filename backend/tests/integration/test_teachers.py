from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta, timezone

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token, hash_password
from app.models.academic import AcademicSession, Department, SchoolClass, Section, Subject, TeacherProfile
from app.models.auth import Membership, Role
from app.models.enums import BillingCycle, InstitutionType, MembershipStatus, RoleScope, SubscriptionStatus, TenantStatus
from app.models.subscription import Subscription, SubscriptionPlan
from app.models.tenant import Tenant
from app.models.user import User
from app.services.subscription_service import SubscriptionService


@pytest.mark.asyncio
@pytest.mark.parametrize("setup_teacher_test_data", [InstitutionType.COLLEGE], indirect=True)
async def test_staff_elevation_and_department_scope(client: AsyncClient, db_session: AsyncSession, setup_teacher_test_data):
    fixture = setup_teacher_test_data
    tenant_id = fixture["tenant"].id
    department = fixture["department"]
    other = Department(tenant_id=tenant_id, name="Humanities", code="HUM")
    db_session.add(other)
    await db_session.commit()

    admin_headers = {"Authorization": "Bearer " + fixture["admin_token"]}
    initial_password = "Faculty-Test-Password-2026!"

    async def make_teacher(name, department_id):
        result = await client.post("/api/v1/teachers", headers=admin_headers, json={
            "full_name": name, "email": f"{uuid.uuid4().hex}@faculty.example.com",
            "department_id": str(department_id), "bank_account_number": "12345678",
            "initial_password": initial_password,
        })
        assert result.status_code == 201, result.text
        return result.json()["data"]

    def headers(person, role):
        token = create_access_token(
            user_id=uuid.UUID(person["user_id"]), email=person["email"], tenant_id=tenant_id, role=role,
        )
        return {"Authorization": f"Bearer {token}"}

    hod = await make_teacher("Science lead", department.id)
    principal = await make_teacher("College principal", other.id)
    assigned = await make_teacher("Science teacher", department.id)
    unassigned = await make_teacher("Humanities teacher", other.id)

    stale = headers(hod, "TEACHER")
    missing = await client.put(f"/api/v1/teachers/{hod['id']}/access", headers=admin_headers, json={"role": "HOD"})
    assert missing.status_code == 422
    changed = await client.put(f"/api/v1/teachers/{hod['id']}/access", headers=admin_headers, json={"role": "HOD", "department_id": str(department.id)})
    assert changed.status_code == 200, changed.text
    changed = await client.put(f"/api/v1/teachers/{principal['id']}/access", headers=admin_headers, json={"role": "PRINCIPAL"})
    assert changed.status_code == 200, changed.text
    assert (await client.get("/api/v1/teachers/dashboard", headers=stale)).status_code == 401

    signed_in = await client.post("/api/v1/auth/login", json={
        "identifier": hod["email"], "password": initial_password, "tenant_id": str(tenant_id),
    })
    assert signed_in.status_code == 200, signed_in.text
    auth = signed_in.json()["data"]
    assert auth["user"]["current_role"] == "HOD"
    hod_headers = {"Authorization": "Bearer " + auth["access_token"]}
    principal_headers = headers(principal, "PRINCIPAL")
    cohort = await client.get("/api/v1/teachers", headers=hod_headers)
    assert cohort.status_code == 200, cohort.text
    assert {row["id"] for row in cohort.json()["data"]["items"]} == {hod["id"], assigned["id"]}
    assert (await client.get(f"/api/v1/teachers/{unassigned['id']}", headers=hod_headers)).status_code == 403
    assert (await client.get(f"/api/v1/teachers/{assigned['id']}", headers=headers(unassigned, "TEACHER"))).status_code == 403
    scoped = await client.get(f"/api/v1/teachers/{assigned['id']}", headers=hod_headers)
    assert scoped.status_code == 200 and scoped.json()["data"]["bank_account_number"] is None
    assert (await client.put(f"/api/v1/teachers/{assigned['id']}/access", headers=hod_headers, json={"role": "PRINCIPAL"})).status_code == 403
    catalog = await client.get("/api/v1/academics/staff-overview", headers=hod_headers)
    assert [row["id"] for row in catalog.json()["data"]] == [str(department.id)]
    catalog = await client.get("/api/v1/academics/staff-overview", headers=principal_headers)
    assert {row["id"] for row in catalog.json()["data"]} == {str(department.id), str(other.id)}

    leave_payload = {"leave_type": "CASUAL", "start_date": "2026-11-23", "end_date": "2026-11-23", "days_count": 1, "reason": "Appointment"}
    leave = await client.post(f"/api/v1/teachers/{assigned['id']}/leaves", headers=headers(assigned, "TEACHER"), json=leave_payload)
    assert leave.status_code == 201, leave.text
    foreign_leave = await client.post(f"/api/v1/teachers/{unassigned['id']}/leaves", headers=headers(unassigned, "TEACHER"), json=leave_payload)
    assert foreign_leave.status_code == 201, foreign_leave.text
    queue = await client.get("/api/v1/teachers/leaves", headers=hod_headers)
    assert [row["id"] for row in queue.json()["data"]] == [leave.json()["data"]["id"]]
    foreign_review = await client.put(f"/api/v1/teachers/leaves/{foreign_leave.json()['data']['id']}/review", headers=hod_headers, json={"status": "APPROVED"})
    assert foreign_review.status_code == 404
    reviewed = await client.put(f"/api/v1/teachers/leaves/{leave.json()['data']['id']}/review", headers=hod_headers, json={"status": "APPROVED"})
    assert reviewed.status_code == 200, reviewed.text
    assert reviewed.json()["data"]["status"] == "APPROVED"

    classroom = fixture["class"]
    section = fixture["section"]
    other_section = Section(tenant_id=tenant_id, class_id=classroom.id, name="B", capacity=30)
    db_session.add(other_section)
    await db_session.commit()
    assignment = await client.post(f"/api/v1/teachers/{assigned['id']}/assignments", headers=admin_headers, json={
        "class_id": str(classroom.id), "section_id": str(section.id),
    })
    assert assignment.status_code == 201, assignment.text
    student_ids = []
    for name, target_section in (("Assigned learner", section), ("Other learner", other_section)):
        student = await client.post("/api/v1/students", headers=admin_headers, json={
            "full_name": name, "email": f"{uuid.uuid4().hex}@student.example.com",
            "class_id": str(classroom.id), "section_id": str(target_section.id),
        })
        assert student.status_code == 201, student.text
        student_ids.append(student.json()["data"]["id"])
    teacher_headers = headers(assigned, "TEACHER")
    directory = await client.get("/api/v1/students", headers=teacher_headers)
    assert directory.status_code == 200, directory.text
    assert [row["id"] for row in directory.json()["data"]["items"]] == [student_ids[0]]
    assert (await client.get(f"/api/v1/students/{student_ids[1]}", headers=teacher_headers)).status_code == 403
    exported = await client.get("/api/v1/students/export", headers=teacher_headers)
    assert exported.status_code == 200
    assert "Assigned learner" in exported.text and "Other learner" not in exported.text


@pytest.fixture
async def setup_teacher_test_data(db_session: AsyncSession, request: pytest.FixtureRequest):
    # 1. Tenant
    tenant = Tenant(
        name="St. Xavier's Academy",
        slug=f"xaviers-{uuid.uuid4().hex[:6]}",
        institution_type=getattr(request, "param", InstitutionType.SCHOOL),
        status=TenantStatus.ACTIVE,
        email=f"admin_{uuid.uuid4().hex[:6]}@xaviers.edu",
    )
    db_session.add(tenant)
    await db_session.flush()

    # 2. Academic Session, Class, Section & Subject
    session_obj = AcademicSession(
        tenant_id=tenant.id,
        name="2026-2027",
        code="AY-2026-27",
        start_date=date(2026, 4, 1),
        end_date=date(2027, 3, 31),
        is_current=True,
    )
    db_session.add(session_obj)

    department = Department(
        tenant_id=tenant.id,
        name="Science Department",
        code="SCI",
    )
    db_session.add(department)

    school_class = SchoolClass(
        tenant_id=tenant.id,
        name="Class 10",
        code="C10",
        order_index=10,
    )
    db_session.add(school_class)
    await db_session.flush()

    section = Section(
        tenant_id=tenant.id,
        class_id=school_class.id,
        name="A",
        capacity=40,
    )
    db_session.add(section)

    subject = Subject(
        tenant_id=tenant.id,
        name="Physics",
        code="PHY101",
        subject_type="THEORY",
    )
    db_session.add(subject)

    # 3. Admin User
    admin_user = User(
        email=f"admin_{uuid.uuid4().hex[:6]}@xaviers.edu",
        password_hash=hash_password("Password123!"),
        full_name="Principal Father Thomas",
        is_superadmin=False,
        is_active=True,
    )
    db_session.add(admin_user)
    await db_session.flush()

    # 4. Roles
    admin_role = (await db_session.execute(select(Role).where(Role.code == "INSTITUTION_ADMIN"))).scalars().first()
    if not admin_role:
        admin_role = Role(name="Institution Admin", code="INSTITUTION_ADMIN", scope=RoleScope.TENANT, is_system_role=True)
        db_session.add(admin_role)

    teacher_role = (await db_session.execute(select(Role).where(Role.code == "TEACHER"))).scalars().first()
    if not teacher_role:
        teacher_role = Role(name="Teacher", code="TEACHER", scope=RoleScope.TENANT, is_system_role=True)
        db_session.add(teacher_role)
    await db_session.flush()

    membership = Membership(
        user_id=admin_user.id,
        tenant_id=tenant.id,
        role_id=admin_role.id,
        status=MembershipStatus.ACTIVE,
    )
    db_session.add(membership)

    # 5. Plan & Active Subscription
    sub_service = SubscriptionService(db_session)
    await sub_service.seed_default_plans_if_needed()

    starter_plan = (await db_session.execute(
        select(SubscriptionPlan).where(SubscriptionPlan.code == "STARTER_SCHOOL")
    )).scalars().first()

    now = datetime.now(timezone.utc)
    sub = Subscription(
        tenant_id=tenant.id,
        plan_id=starter_plan.id,
        status=SubscriptionStatus.ACTIVE,
        billing_cycle=BillingCycle.MONTHLY,
        current_period_start=now,
        current_period_end=now + timedelta(days=30),
        is_auto_renew=True,
    )
    db_session.add(sub)
    await db_session.commit()

    admin_token = create_access_token(
        user_id=admin_user.id,
        email=admin_user.email,
        tenant_id=tenant.id,
        role="INSTITUTION_ADMIN",
        permissions=["*:*"],
    )

    return {
        "tenant": tenant,
        "admin": admin_user,
        "admin_token": admin_token,
        "session": session_obj,
        "department": department,
        "class": school_class,
        "section": section,
        "subject": subject,
        "plan": starter_plan,
    }


@pytest.mark.asyncio
async def test_create_teacher_success(client: AsyncClient, setup_teacher_test_data):
    data = setup_teacher_test_data
    token = data["admin_token"]

    payload = {
        "full_name": "Dr. Sarah Paulson",
        "email": f"sarah_{uuid.uuid4().hex[:6]}@xaviers.edu",
        "phone": "+919876500001",
        "designation": "Senior Physics Faculty",
        "qualification": "Ph.D. in Physics",
        "specialization": "Quantum Mechanics",
        "experience_years": 8,
        "department_id": str(data["department"].id),
        "joining_date": "2024-06-01",
        "employment_type": "FULL_TIME",
        "city": "Kolkata",
        "state": "West Bengal",
        "postal_code": "700016",
    }

    res = await client.post(
        "/api/v1/teachers",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )

    assert res.status_code == 201
    body = res.json()
    assert body["success"] is True
    teacher = body["data"]
    assert teacher["full_name"] == "Dr. Sarah Paulson"
    assert teacher["employee_id"].startswith("EMP-")
    assert teacher["designation"] == "Senior Physics Faculty"
    assert teacher["experience_years"] == 8
    assert teacher["status"] == "ACTIVE"


@pytest.mark.asyncio
async def test_duplicate_employee_id_rejected(client: AsyncClient, setup_teacher_test_data):
    data = setup_teacher_test_data
    token = data["admin_token"]

    payload1 = {
        "full_name": "Marcus Vance",
        "employee_id": "EMP-2026-CUSTOM-99",
        "designation": "Mathematics Lecturer",
    }
    res1 = await client.post(
        "/api/v1/teachers",
        json=payload1,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res1.status_code == 201

    payload2 = {
        "full_name": "Elena Rostova",
        "employee_id": "EMP-2026-CUSTOM-99",
        "designation": "Chemistry Lecturer",
    }
    res2 = await client.post(
        "/api/v1/teachers",
        json=payload2,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res2.status_code == 409
    body2 = res2.json()
    assert body2["error"]["code"] == "DUPLICATE_EMPLOYEE_ID"


@pytest.mark.asyncio
async def test_assign_academic_resources_and_timetable(client: AsyncClient, setup_teacher_test_data):
    data = setup_teacher_test_data
    token = data["admin_token"]

    # 1. Create Teacher
    create_res = await client.post(
        "/api/v1/teachers",
        json={"full_name": "Prof. Albus Dumbledore", "designation": "Headmaster"},
        headers={"Authorization": f"Bearer {token}"},
    )
    teacher_id = create_res.json()["data"]["id"]

    # 2. Assign Class, Section, and Subject
    assign_payload = {
        "academic_session_id": str(data["session"].id),
        "class_id": str(data["class"].id),
        "section_id": str(data["section"].id),
        "subject_id": str(data["subject"].id),
        "is_class_teacher": True,
    }
    assign_res = await client.post(
        f"/api/v1/teachers/{teacher_id}/assignments",
        json=assign_payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert assign_res.status_code == 201
    assert assign_res.json()["success"] is True

    # 3. Add Timetable Slot
    tt_payload = {
        "academic_session_id": str(data["session"].id),
        "class_id": str(data["class"].id),
        "section_id": str(data["section"].id),
        "subject_id": str(data["subject"].id),
        "day_of_week": "MONDAY",
        "period_number": 1,
        "start_time": "09:00",
        "end_time": "09:45",
        "room_number": "Lab 101",
    }
    tt_res = await client.post(
        f"/api/v1/teachers/{teacher_id}/timetable",
        json=tt_payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert tt_res.status_code == 201

    # 4. Query Timetable
    get_tt_res = await client.get(
        f"/api/v1/teachers/{teacher_id}/timetable?day_of_week=MONDAY",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert get_tt_res.status_code == 200
    tt_data = get_tt_res.json()["data"]
    assert len(tt_data) == 1
    assert tt_data[0]["period_number"] == 1
    assert tt_data[0]["room_number"] == "Lab 101"

    # 5. Verify Workload
    detail_res = await client.get(
        f"/api/v1/teachers/{teacher_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    workload = detail_res.json()["data"]["workload"]
    assert workload["total_classes_assigned"] == 1
    assert workload["total_subjects_assigned"] == 1
    assert workload["weekly_periods_count"] == 1
    assert "Class 10 - Sec A" in workload["is_class_teacher_of"]


@pytest.mark.asyncio
async def test_teacher_attendance_and_leave_workflow(client: AsyncClient, setup_teacher_test_data):
    data = setup_teacher_test_data
    token = data["admin_token"]

    create_res = await client.post(
        "/api/v1/teachers",
        json={"full_name": "Severus Snape", "designation": "Potions Master"},
        headers={"Authorization": f"Bearer {token}"},
    )
    teacher_id = create_res.json()["data"]["id"]

    # 1. Record Attendance Punch
    att_res = await client.post(
        f"/api/v1/teachers/{teacher_id}/attendance",
        json={
            "attendance_date": "2026-08-10",
            "status": "PRESENT",
            "check_in_time": "08:45",
            "check_out_time": "16:15",
            "remarks": "On time",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert att_res.status_code == 200
    assert att_res.json()["data"]["status"] == "PRESENT"

    # 2. Apply for Leave
    leave_res = await client.post(
        f"/api/v1/teachers/{teacher_id}/leaves",
        json={
            "leave_type": "CASUAL",
            "start_date": "2026-08-15",
            "end_date": "2026-08-16",
            "days_count": 2.0,
            "reason": "Family engagement",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert leave_res.status_code == 201
    leave_data = leave_res.json()["data"]
    assert leave_data["status"] == "PENDING"
    leave_id = leave_data["id"]

    # 3. Review Leave (Approve)
    review_res = await client.put(
        f"/api/v1/teachers/leaves/{leave_id}/review",
        json={"status": "APPROVED"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert review_res.status_code == 200
    assert review_res.json()["data"]["status"] == "APPROVED"


@pytest.mark.asyncio
async def test_teacher_dedicated_dashboard(client: AsyncClient, setup_teacher_test_data):
    data = setup_teacher_test_data
    admin_token = data["admin_token"]

    # Create teacher
    teacher_email = f"minerva_{uuid.uuid4().hex[:6]}@xaviers.edu"
    create_res = await client.post(
        "/api/v1/teachers",
        json={
            "full_name": "Minerva McGonagall",
            "email": teacher_email,
            "designation": "Deputy Headmistress",
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    teacher_data = create_res.json()["data"]
    teacher_user_id = teacher_data["user_id"]
    teacher_id = teacher_data["id"]

    # Assign a class
    await client.post(
        f"/api/v1/teachers/{teacher_id}/assignments",
        json={
            "class_id": str(data["class"].id),
            "section_id": str(data["section"].id),
            "subject_id": str(data["subject"].id),
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    # Generate teacher JWT token
    teacher_token = create_access_token(
        user_id=uuid.UUID(teacher_user_id),
        email=teacher_email,
        tenant_id=data["tenant"].id,
        role="TEACHER",
        permissions=["academic:session:read"],
    )

    # Call /api/v1/teachers/dashboard as the teacher
    dash_res = await client.get(
        "/api/v1/teachers/dashboard",
        headers={"Authorization": f"Bearer {teacher_token}"},
    )
    assert dash_res.status_code == 200
    dash_data = dash_res.json()["data"]
    assert dash_data["teacher"]["full_name"] == "Minerva McGonagall"
    assert len(dash_data["assigned_classes"]) >= 1
    assert dash_data["attendance_tasks"] == []
    assert "upcoming_examinations" in dash_data
    assert "assignments_to_evaluate" in dash_data


@pytest.mark.asyncio
async def test_teacher_status_toggle(client: AsyncClient, setup_teacher_test_data):
    data = setup_teacher_test_data
    token = data["admin_token"]

    create_res = await client.post(
        "/api/v1/teachers",
        json={"full_name": "Gilderoy Lockhart", "designation": "Defense Against the Dark Arts"},
        headers={"Authorization": f"Bearer {token}"},
    )
    teacher_id = create_res.json()["data"]["id"]

    # Deactivate
    deact_res = await client.post(
        f"/api/v1/teachers/{teacher_id}/status?status=INACTIVE",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert deact_res.status_code == 200
    assert deact_res.json()["status"] == "INACTIVE"

    # Reactivate
    act_res = await client.post(
        f"/api/v1/teachers/{teacher_id}/status?status=ACTIVE",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert act_res.status_code == 200
    assert act_res.json()["status"] == "ACTIVE"

async def test_admin_removes_faculty_and_revokes_staff_membership(client: AsyncClient, setup_teacher_test_data):
    data = setup_teacher_test_data
    headers = {"Authorization": "Bearer " + data["admin_token"]}
    response = await client.post("/api/v1/teachers", headers=headers, json={
        "full_name": "Faculty Removal Test",
        "email": f"{uuid.uuid4().hex}@faculty.example.com",
        "department_id": str(data["department"].id),
        "initial_password": "Faculty-Test-Password-2026!",
    })
    assert response.status_code == 201, response.text
    teacher = response.json()["data"]
    teacher_token = create_access_token(user_id=uuid.UUID(teacher["user_id"]), email=teacher["email"], tenant_id=data["tenant"].id, role="TEACHER")
    teacher_headers = {"Authorization": f"Bearer {teacher_token}"}
    forbidden = await client.delete(f"/api/v1/teachers/{teacher['id']}", headers=teacher_headers)
    assert forbidden.status_code == 403
    removed = await client.delete(f"/api/v1/teachers/{teacher['id']}", headers=headers)
    assert removed.status_code == 200, removed.text
    assert (await client.get(f"/api/v1/teachers/{teacher['id']}", headers=headers)).status_code == 404
    assert (await client.get("/api/v1/teachers/dashboard", headers=teacher_headers)).status_code in (401, 403)
