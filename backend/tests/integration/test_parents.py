from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta, timezone

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token
from app.models.academic import (
    AcademicSession,
    SchoolClass,
    Section,
    StudentParent,
    StudentProfile,
    Subject,
    TeacherAssignment,
    TeacherProfile,
    TimetableEntry,
)
from app.models.attendance import StudentAttendanceEntry, StudentAttendanceSession
from app.models.auth import Membership, Role
from app.models.user import User
from app.models.examination import Examination
from app.models.fee import FeeInvoice
from app.models.tenant import Tenant


@pytest.mark.asyncio
async def test_parent_linking_request_and_anti_unverified_rule(
    client: AsyncClient,
    db_session: AsyncSession,
):
    session = db_session
    tenant = Tenant(name="Heritage Public School", slug=f"hps-{uuid.uuid4().hex[:6]}")
    session.add(tenant)
    await session.flush()

    # Roles
    admin_role = (await session.execute(select(Role).where(Role.code == "INSTITUTION_ADMIN"))).scalars().first()
    parent_role = (await session.execute(select(Role).where(Role.code == "PARENT"))).scalars().first()
    student_role = (await session.execute(select(Role).where(Role.code == "STUDENT"))).scalars().first()

    # Admin User
    admin_user = User(
        email=f"admin-{uuid.uuid4().hex[:6]}@hps.edu",
        password_hash="pw",
        full_name="Principal Sharma",
        is_active=True,
    )
    # Parent User
    parent_user = User(
        email=f"parent-{uuid.uuid4().hex[:6]}@gmail.com",
        password_hash="pw",
        full_name="Rajesh Gupta",
        phone="+919876543210",
        is_active=True,
    )
    # Student User
    student_user = User(
        email=f"student-{uuid.uuid4().hex[:6]}@hps.edu",
        password_hash="pw",
        full_name="Aryan Gupta",
        is_active=True,
    )
    session.add_all([admin_user, parent_user, student_user])
    await session.flush()

    session.add_all([
        Membership(tenant_id=tenant.id, user_id=admin_user.id, role_id=admin_role.id),
        Membership(tenant_id=tenant.id, user_id=parent_user.id, role_id=parent_role.id),
        Membership(tenant_id=tenant.id, user_id=student_user.id, role_id=student_role.id),
    ])

    acad_session = AcademicSession(
        tenant_id=tenant.id,
        name="AY 2026-27",
        code=f"AY-{uuid.uuid4().hex[:4]}",
        start_date=date(2026, 4, 1),
        end_date=date(2027, 3, 31),
        is_current=True,
    )
    session.add(acad_session)

    school_class = SchoolClass(
        tenant_id=tenant.id,
        name="Class 8",
        code=f"C8-{uuid.uuid4().hex[:4]}",
        order_index=8,
    )
    session.add(school_class)
    await session.flush()

    student = StudentProfile(
        tenant_id=tenant.id,
        user_id=student_user.id,
        admission_number="HPS-2026-0042",
        class_id=school_class.id,
        academic_session_id=acad_session.id,
    )
    session.add(student)
    await session.commit()

    admin_token = create_access_token(
        user_id=admin_user.id, email=admin_user.email, tenant_id=tenant.id, role="INSTITUTION_ADMIN"
    )
    parent_token = create_access_token(
        user_id=parent_user.id, email=parent_user.email, tenant_id=tenant.id, role="PARENT"
    )
    admin_headers = {"Authorization": f"Bearer {admin_token}", "X-Tenant-ID": str(tenant.id)}
    parent_headers = {"Authorization": f"Bearer {parent_token}", "X-Tenant-ID": str(tenant.id)}

    # 1. Parent submits linking request WITHOUT verification code (Requires admin verification)
    link_res = await client.post(
        "/api/v1/parents/link-requests",
        json={
            "admission_number": "HPS-2026-0042",
            "relation_type": "FATHER",
            "emergency_contact": True,
            "notes": "I am Aryan's father Rajesh Gupta.",
        },
        headers=parent_headers,
    )
    assert link_res.status_code == 201
    link_data = link_res.json()
    assert link_data["status"] == "PENDING_APPROVAL"
    link_id = link_data["link_id"]

    # 2. Crucial Security Rule: Parent CANNOT view student's attendance or results while PENDING_APPROVAL
    att_res = await client.get(f"/api/v1/parents/children/{student.id}/attendance", headers=parent_headers)
    assert att_res.status_code == 403
    assert "Access denied" in att_res.json()["error"]["message"]

    res_res = await client.get(f"/api/v1/parents/children/{student.id}/results", headers=parent_headers)
    assert res_res.status_code == 403

    # 3. Admin lists pending requests
    pending_res = await client.get("/api/v1/parents/admin/linking-requests", headers=admin_headers)
    assert pending_res.status_code == 200
    pending_list = pending_res.json()
    assert any(req["id"] == link_id and req["student_name"] == "Aryan Gupta" for req in pending_list)

    # 4. Admin approves linking request
    approve_res = await client.post(
        f"/api/v1/parents/admin/linking-requests/{link_id}/process",
        json={"action": "APPROVE", "approval_notes": "Verified against physical admission form"},
        headers=admin_headers,
    )
    assert approve_res.status_code == 200
    assert approve_res.json()["status"] == "VERIFIED"

    # 5. Parent can now access verified child profile
    prof_res = await client.get(f"/api/v1/parents/children/{student.id}/profile", headers=parent_headers)
    assert prof_res.status_code == 200
    prof_data = prof_res.json()
    assert prof_data["full_name"] == "Aryan Gupta"
    assert prof_data["relation_type"] == "FATHER"
    assert prof_data["emergency_contact"] is True


@pytest.mark.asyncio
async def test_verification_code_immediate_linking_and_duplication_guard(
    client: AsyncClient,
    db_session: AsyncSession,
):
    session = db_session
    tenant = Tenant(name="Global High", slug=f"gh-{uuid.uuid4().hex[:6]}")
    session.add(tenant)
    await session.flush()

    admin_role = (await session.execute(select(Role).where(Role.code == "INSTITUTION_ADMIN"))).scalars().first()
    parent_role = (await session.execute(select(Role).where(Role.code == "PARENT"))).scalars().first()

    admin_user = User(email=f"adm-{uuid.uuid4().hex[:6]}@gh.edu", password_hash="pw", full_name="Admin GH")
    parent_user = User(email=f"mom-{uuid.uuid4().hex[:6]}@gmail.com", password_hash="pw", full_name="Sunita Rao")
    student_user = User(email=f"stud-{uuid.uuid4().hex[:6]}@gh.edu", password_hash="pw", full_name="Rohan Rao")
    session.add_all([admin_user, parent_user, student_user])
    await session.flush()

    session.add_all([
        Membership(tenant_id=tenant.id, user_id=admin_user.id, role_id=admin_role.id),
        Membership(tenant_id=tenant.id, user_id=parent_user.id, role_id=parent_role.id),
    ])

    student = StudentProfile(
        tenant_id=tenant.id,
        user_id=student_user.id,
        admission_number="GH-2026-9999",
    )
    session.add(student)
    await session.commit()

    admin_token = create_access_token(
        user_id=admin_user.id, email=admin_user.email, tenant_id=tenant.id, role="INSTITUTION_ADMIN"
    )
    parent_token = create_access_token(
        user_id=parent_user.id, email=parent_user.email, tenant_id=tenant.id, role="PARENT"
    )
    admin_headers = {"Authorization": f"Bearer {admin_token}", "X-Tenant-ID": str(tenant.id)}
    parent_headers = {"Authorization": f"Bearer {parent_token}", "X-Tenant-ID": str(tenant.id)}

    # 1. Admin generates one-time verification code for student
    gen_res = await client.post(
        "/api/v1/parents/admin/verification-codes",
        json={"student_id": str(student.id), "valid_days": 5},
        headers=admin_headers,
    )
    assert gen_res.status_code == 201
    code_data = gen_res.json()
    valid_code = code_data["code"]
    assert valid_code.startswith("LNK-")

    # 2. Parent attempts with wrong code -> Rejected
    bad_res = await client.post(
        "/api/v1/parents/link-requests",
        json={
            "admission_number": "GH-2026-9999",
            "verification_code": "LNK-WRONG99",
            "relation_type": "MOTHER",
        },
        headers=parent_headers,
    )
    assert bad_res.status_code == 400
    assert "invalid or has expired" in bad_res.json()["error"]["message"]

    # 3. Parent enters correct code -> Immediately verified
    ok_res = await client.post(
        "/api/v1/parents/link-requests",
        json={
            "admission_number": "GH-2026-9999",
            "verification_code": valid_code,
            "relation_type": "MOTHER",
        },
        headers=parent_headers,
    )
    assert ok_res.status_code == 201
    assert ok_res.json()["status"] == "VERIFIED"

    # 4. Attempting to link already verified child again -> 400
    dup_res = await client.post(
        "/api/v1/parents/link-requests",
        json={"admission_number": "GH-2026-9999", "relation_type": "MOTHER"},
        headers=parent_headers,
    )
    assert dup_res.status_code == 400
    assert "already verified" in dup_res.json()["error"]["message"]


@pytest.mark.asyncio
async def test_multi_child_cross_institution_support_and_academic_views(
    client: AsyncClient,
    db_session: AsyncSession,
):
    session = db_session
    # Tenant 1: School
    t1 = Tenant(name="St. Mary's School", slug=f"sms-{uuid.uuid4().hex[:6]}")
    # Tenant 2: College
    t2 = Tenant(name="Trinity College of Tech", slug=f"tct-{uuid.uuid4().hex[:6]}")
    session.add_all([t1, t2])
    await session.flush()

    parent_role = (await session.execute(select(Role).where(Role.code == "PARENT"))).scalars().first()

    parent = User(email=f"multi-{uuid.uuid4().hex[:6]}@family.com", password_hash="pw", full_name="Vikram Singh")
    child1_user = User(email=f"c1-{uuid.uuid4().hex[:6]}@sms.edu", password_hash="pw", full_name="Simran Singh")
    child2_user = User(email=f"c2-{uuid.uuid4().hex[:6]}@tct.edu", password_hash="pw", full_name="Karan Singh")
    session.add_all([parent, child1_user, child2_user])
    await session.flush()

    session.add_all([
        Membership(tenant_id=t1.id, user_id=parent.id, role_id=parent_role.id),
        Membership(tenant_id=t2.id, user_id=parent.id, role_id=parent_role.id),
    ])

    # School setup for Child 1
    acad_sess1 = AcademicSession(
        tenant_id=t1.id, name="AY 2026-27", code=f"AY1-{uuid.uuid4().hex[:4]}",
        start_date=date(2026, 4, 1), end_date=date(2027, 3, 31), is_current=True
    )
    session.add(acad_sess1)
    await session.flush()

    c1_class = SchoolClass(tenant_id=t1.id, name="Grade 10", code="G10", order_index=10)
    c1_subject = Subject(tenant_id=t1.id, name="Mathematics", code="MATH10")
    session.add_all([c1_class, c1_subject])
    await session.flush()

    c1_student = StudentProfile(tenant_id=t1.id, user_id=child1_user.id, admission_number="SMS-2026-01", class_id=c1_class.id, academic_session_id=acad_sess1.id)
    c2_student = StudentProfile(tenant_id=t2.id, user_id=child2_user.id, admission_number="TCT-2026-99")
    session.add_all([c1_student, c2_student])
    await session.flush()

    # Pre-link both children as VERIFIED
    link1 = StudentParent(
        tenant_id=t1.id, student_id=c1_student.id, parent_user_id=parent.id,
        relation_type="FATHER", status="VERIFIED", can_view_grades=True, can_pay_fees=True
    )
    link2 = StudentParent(
        tenant_id=t2.id, student_id=c2_student.id, parent_user_id=parent.id,
        relation_type="FATHER", status="VERIFIED", can_view_grades=True, can_pay_fees=True
    )
    session.add_all([link1, link2])

    # Add Attendance Entry for Child 1
    att_sess = StudentAttendanceSession(
        tenant_id=t1.id,
        academic_session_id=acad_sess1.id,
        session_date=date.today(),
        session_type="DAILY",
        class_id=c1_class.id,
    )
    session.add(att_sess)
    await session.flush()

    session.add(StudentAttendanceEntry(
        tenant_id=t1.id,
        session_id=att_sess.id,
        student_id=c1_student.id,
        status="PRESENT",
    ))

    # Add Fee Invoice for Child 1
    session.add(FeeInvoice(
        tenant_id=t1.id,
        student_id=c1_student.id,
        academic_session_id=acad_sess1.id,
        invoice_number="INV-2026-P001",
        title="Term 1 School Fee",
        issue_date=date(2026, 7, 1),
        due_date=date(2026, 7, 31),
        subtotal=15000.0,
        total_amount=15000.0,
        paid_amount=5000.0,
        balance_amount=10000.0,
        status="PARTIALLY_PAID",
    ))
    await session.commit()

    token = create_access_token(user_id=parent.id, email=parent.email, tenant_id=t1.id, role="PARENT")
    headers_t1 = {"Authorization": f"Bearer {token}", "X-Tenant-ID": str(t1.id)}

    # 1. Multi-Child switcher: returns both children across both institutions!
    children_res = await client.get("/api/v1/parents/children", headers=headers_t1)
    assert children_res.status_code == 200
    children = children_res.json()
    assert len(children) == 2
    names = [c["student_name"] for c in children]
    assert "Simran Singh" in names
    assert "Karan Singh" in names

    # 2. View Child 1 Attendance
    c1_att = await client.get(f"/api/v1/parents/children/{c1_student.id}/attendance", headers=headers_t1)
    assert c1_att.status_code == 200
    assert c1_att.json()["present_days"] == 1
    assert c1_att.json()["overall_percentage"] == 100.0

    # 3. View Child 1 Fees
    c1_fees = await client.get(f"/api/v1/parents/children/{c1_student.id}/fees", headers=headers_t1)
    assert c1_fees.status_code == 200
    fee_data = c1_fees.json()
    assert fee_data["total_due"] == 10000.0
    assert len(fee_data["invoices"]) == 1

    for endpoint in ("timetable", "examinations", "results", "assignments", "materials", "teachers"):
        response = await client.get(f"/api/v1/parents/children/{c1_student.id}/{endpoint}", headers=headers_t1)
        assert response.status_code == 200, response.text


@pytest.mark.asyncio
async def test_parent_teacher_communications(
    client: AsyncClient,
    db_session: AsyncSession,
):
    session = db_session
    tenant = Tenant(name="City High", slug=f"ch-{uuid.uuid4().hex[:6]}")
    session.add(tenant)
    await session.flush()

    parent_role = (await session.execute(select(Role).where(Role.code == "PARENT"))).scalars().first()
    teacher_role = (await session.execute(select(Role).where(Role.code == "TEACHER"))).scalars().first()

    parent = User(email=f"p-{uuid.uuid4().hex[:6]}@city.edu", password_hash="pw", full_name="Parent Verma")
    teacher = User(email=f"t-{uuid.uuid4().hex[:6]}@city.edu", password_hash="pw", full_name="Mr. Roy (Science Teacher)")
    student_user = User(email=f"s-{uuid.uuid4().hex[:6]}@city.edu", password_hash="pw", full_name="Ananya Verma")
    session.add_all([parent, teacher, student_user])
    await session.flush()

    session.add_all([
        Membership(tenant_id=tenant.id, user_id=parent.id, role_id=parent_role.id),
        Membership(tenant_id=tenant.id, user_id=teacher.id, role_id=teacher_role.id),
    ])

    student = StudentProfile(tenant_id=tenant.id, user_id=student_user.id, admission_number="CH-2026-555")
    session.add(student)
    await session.flush()

    link = StudentParent(
        tenant_id=tenant.id, student_id=student.id, parent_user_id=parent.id,
        relation_type="FATHER", status="VERIFIED"
    )
    session.add(link)
    await session.commit()

    p_token = create_access_token(user_id=parent.id, email=parent.email, tenant_id=tenant.id, role="PARENT")
    t_token = create_access_token(user_id=teacher.id, email=teacher.email, tenant_id=tenant.id, role="TEACHER")
    p_headers = {"Authorization": f"Bearer {p_token}", "X-Tenant-ID": str(tenant.id)}
    t_headers = {"Authorization": f"Bearer {t_token}", "X-Tenant-ID": str(tenant.id)}

    # 1. Parent sends message to teacher
    send_res = await client.post(
        "/api/v1/parents/communications",
        json={
            "student_id": str(student.id),
            "teacher_user_id": str(teacher.id),
            "subject": "Regarding Ananya's Science Project",
            "message": "Dear Mr. Roy, could you please clarify the deadline for the physics project?",
        },
        headers=p_headers,
    )
    assert send_res.status_code == 201
    thread_id = send_res.json()["id"]

    # 2. Teacher reads message
    t_inbox = await client.get("/api/v1/parents/communications", headers=t_headers)
    assert t_inbox.status_code == 200
    msgs = t_inbox.json()
    assert len(msgs) == 1
    assert msgs[0]["subject"] == "Regarding Ananya's Science Project"

    # 3. Teacher sends reply
    reply_res = await client.post(
        "/api/v1/parents/communications",
        json={
            "student_id": str(student.id),
            "teacher_user_id": str(parent.id),  # In reply, target is parent
            "subject": "Re: Regarding Ananya's Science Project",
            "message": "Hello Mr. Verma, the project is due next Friday on the 28th.",
            "parent_message_id": thread_id,
        },
        headers=t_headers,
    )
    assert reply_res.status_code == 201

    # 4. Parent views threaded communication
    p_inbox = await client.get("/api/v1/parents/communications", headers=p_headers)
    assert p_inbox.status_code == 200
    p_threads = p_inbox.json()
    assert len(p_threads) == 1
    assert len(p_threads[0]["replies"]) == 1
    assert "due next Friday" in p_threads[0]["replies"][0]["message"]
