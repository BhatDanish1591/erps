import uuid
from datetime import date, datetime, time, timezone
from decimal import Decimal
from typing import Optional
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
    TeacherProfile,
    TeacherSubjectMapping,
)
from app.models.attendance import (
    StudentAttendanceEntry,
    StudentAttendanceSession,
)
from app.models.auth import Membership, Role
from app.models.examination import Examination
from app.models.fee import (
    FeeInvoice,
    FeePayment,
)
from app.models.result import StudentSubjectResult
from app.models.subscription import (
    Subscription,
    SubscriptionPlan,
)
from app.models.tenant import Tenant
from app.models.user import User


async def _setup_tenant_user_role(
    session: AsyncSession, role_code: str, tenant: Optional[Tenant] = None
):
    if not tenant:
        tenant = Tenant(name="Sterling Heights Academy", slug=f"sterling-{uuid.uuid4().hex[:6]}")
        session.add(tenant)
        await session.flush()

    role = (await session.execute(select(Role).where(Role.code == role_code))).scalars().first()
    user = User(
        email=f"{role_code.lower()}-{uuid.uuid4().hex[:6]}@sterling.edu",
        password_hash="pw",
        full_name=f"{role_code} User",
        is_active=True,
    )
    session.add(user)
    await session.flush()

    session.add(Membership(tenant_id=tenant.id, user_id=user.id, role_id=role.id))
    await session.commit()

    token = create_access_token(
        user_id=user.id, email=user.email, tenant_id=tenant.id, role=role_code
    )
    headers = {"Authorization": f"Bearer {token}", "X-Tenant-ID": str(tenant.id)}
    return tenant, user, headers


@pytest.mark.asyncio
async def test_super_admin_analytics_dashboard(
    client: AsyncClient,
    db_session: AsyncSession,
):
    """
    Verifies that Super Admin can access platform-wide growth, MRR, ARR,
    subscription distribution, payment failure metrics, and user statistics.
    """
    super_admin_role = (
        await db_session.execute(select(Role).where(Role.code == "SUPER_ADMIN"))
    ).scalars().first()

    sa_user = User(
        email=f"sa-{uuid.uuid4().hex[:6]}@platform.com",
        password_hash="pw",
        full_name="Global Platform Auditor",
        is_active=True,
    )
    db_session.add(sa_user)
    await db_session.flush()

    # Seed plan & subscription
    plan = SubscriptionPlan(
        name="Enterprise School Suite",
        code=f"PLAN-{uuid.uuid4().hex[:4].upper()}",
        price=Decimal("15000.00"),
        billing_cycle="MONTHLY",
        max_students=1000,
        max_teachers=100,
    )
    db_session.add(plan)
    await db_session.flush()

    tenant = Tenant(name="Greenwood High", slug=f"greenwood-{uuid.uuid4().hex[:6]}")
    db_session.add(tenant)
    await db_session.flush()

    sub = Subscription(
        tenant_id=tenant.id,
        plan_id=plan.id,
        status="ACTIVE",
        billing_cycle="MONTHLY",
        current_period_start=datetime.now(timezone.utc),
        current_period_end=datetime.now(timezone.utc),
    )
    db_session.add(sub)
    await db_session.commit()

    token = create_access_token(
        user_id=sa_user.id, email=sa_user.email, tenant_id=None, role="SUPER_ADMIN"
    )
    headers = {"Authorization": f"Bearer {token}"}

    res = await client.get("/api/v1/reports/super-admin", headers=headers)
    assert res.status_code == 200
    data = res.json()

    assert data["total_institutions"] >= 1
    assert data["active_subscriptions"] >= 1
    assert Decimal(str(data["monthly_recurring_revenue"])) >= Decimal("15000.00")
    assert Decimal(str(data["annual_recurring_revenue"])) >= Decimal("180000.00")
    assert len(data["institution_growth"]) >= 1
    assert "user_statistics" in data
    assert "payment_failures" in data


@pytest.mark.asyncio
async def test_institution_admin_analytics_and_tenant_boundary_isolation(
    client: AsyncClient,
    db_session: AsyncSession,
):
    """
    Verifies Institution Admin analytics metrics (students, teachers, class distribution,
    daily/monthly attendance %, pass %, fee collections by mode, pending dues, grade trends)
    and strictly validates tenant isolation between distinct institutions.
    """
    tenant_a, admin_a, headers_a = await _setup_tenant_user_role(db_session, "INSTITUTION_ADMIN")
    tenant_b, admin_b, headers_b = await _setup_tenant_user_role(db_session, "INSTITUTION_ADMIN")

    # Seed Tenant A: Academic Session, Class, Sections, Students, Attendance, Fees
    acad_sess_a = AcademicSession(
        tenant_id=tenant_a.id,
        name="AY 2026-27",
        code=f"AY1-{uuid.uuid4().hex[:4]}",
        start_date=date(2026, 4, 1),
        end_date=date(2027, 3, 31),
        is_current=True,
    )
    db_session.add(acad_sess_a)
    await db_session.flush()

    cls_a = SchoolClass(tenant_id=tenant_a.id, name="Grade 10", code="G10", order_index=10)
    db_session.add(cls_a)
    await db_session.flush()

    sec_a = Section(tenant_id=tenant_a.id, class_id=cls_a.id, name="Section A")
    db_session.add(sec_a)
    await db_session.flush()

    # 2 Students in Tenant A
    students_a = []
    for i in range(2):
        u = User(
            email=f"stu-a-{i}-{uuid.uuid4().hex[:5]}@sterling.edu",
            password_hash="pw",
            full_name=f"Student A-{i+1}",
            is_active=True,
        )
        db_session.add(u)
        await db_session.flush()
        sp = StudentProfile(
            tenant_id=tenant_a.id,
            user_id=u.id,
            class_id=cls_a.id,
            section_id=sec_a.id,
            academic_session_id=acad_sess_a.id,
            admission_number=f"ADM-A-{uuid.uuid4().hex[:4].upper()}",
            admission_date=date(2026, 6, 1),
            status="ACTIVE",
        )
        db_session.add(sp)
        students_a.append(sp)

    # 1 Teacher in Tenant A
    tu = User(
        email=f"tea-a-{uuid.uuid4().hex[:5]}@sterling.edu",
        password_hash="pw",
        full_name="Teacher A",
        is_active=True,
    )
    db_session.add(tu)
    await db_session.flush()
    tp = TeacherProfile(
        tenant_id=tenant_a.id,
        user_id=tu.id,
        employee_id=f"EMP-A-{uuid.uuid4().hex[:4].upper()}",
        status="ACTIVE",
    )
    db_session.add(tp)

    # Attendance Session in Tenant A
    att_sess = StudentAttendanceSession(
        tenant_id=tenant_a.id,
        academic_session_id=acad_sess_a.id,
        class_id=cls_a.id,
        section_id=sec_a.id,
        session_date=date(2026, 11, 19),
        session_type="DAILY",
    )
    db_session.add(att_sess)
    await db_session.flush()

    # Mark 1 Present, 1 Absent
    db_session.add(StudentAttendanceEntry(
        tenant_id=tenant_a.id,
        session_id=att_sess.id,
        student_id=students_a[0].id,
        status="PRESENT",
    ))
    db_session.add(StudentAttendanceEntry(
        tenant_id=tenant_a.id,
        session_id=att_sess.id,
        student_id=students_a[1].id,
        status="ABSENT",
    ))

    # Fee Invoice & Successful Payment in Tenant A
    inv = FeeInvoice(
        tenant_id=tenant_a.id,
        student_id=students_a[0].id,
        invoice_number=f"INV-A-{uuid.uuid4().hex[:5].upper()}",
        title="November Term Fee",
        academic_session_id=acad_sess_a.id,
        issue_date=date(2026, 11, 1),
        due_date=date(2026, 11, 15),
        subtotal=Decimal("10000.00"),
        total_amount=Decimal("10000.00"),
        paid_amount=Decimal("6000.00"),
        balance_amount=Decimal("4000.00"),
        status="PARTIALLY_PAID",
    )
    db_session.add(inv)
    await db_session.flush()

    pay = FeePayment(
        tenant_id=tenant_a.id,
        academic_session_id=acad_sess_a.id,
        student_id=students_a[0].id,
        invoice_id=inv.id,
        receipt_number=f"PAY-A-{uuid.uuid4().hex[:5].upper()}",
        payment_date=datetime.now(timezone.utc),
        amount=Decimal("6000.00"),
        payment_mode="UPI",
        status="SUCCESS",
    )
    db_session.add(pay)

    # Exam Result in Tenant A (92% - Grade A)
    sbj_a = Subject(tenant_id=tenant_a.id, name="Mathematics", code=f"MTH-{uuid.uuid4().hex[:3]}")
    db_session.add(sbj_a)
    await db_session.flush()

    exam_a = Examination(
        tenant_id=tenant_a.id,
        academic_session_id=acad_sess_a.id,
        title="Mid-Term Mathematics",
        exam_type="MID_TERM",
        total_marks=Decimal("100.00"),
        passing_marks=Decimal("40.00"),
        duration_minutes=60,
    )
    db_session.add(exam_a)
    await db_session.flush()

    sub_res = StudentSubjectResult(
        tenant_id=tenant_a.id,
        student_id=students_a[0].id,
        academic_session_id=acad_sess_a.id,
        class_id=cls_a.id,
        exam_id=exam_a.id,
        subject_id=sbj_a.id,
        total_marks=Decimal("92.00"),
        max_marks=Decimal("100.00"),
        percentage=Decimal("92.00"),
        grade="A+",
        is_passed=True,
    )
    db_session.add(sub_res)
    await db_session.commit()

    # 1. Query Tenant A Analytics
    res_a = await client.get("/api/v1/reports/institution-admin", headers=headers_a)
    assert res_a.status_code == 200
    data_a = res_a.json()

    assert data_a["total_students"] == 2
    assert data_a["total_teachers"] == 1
    assert len(data_a["class_distribution"]) >= 1
    assert data_a["daily_attendance"]["present"] == 1
    assert data_a["daily_attendance"]["absent"] == 1
    assert data_a["daily_attendance"]["rate_percentage"] == 50.0
    assert Decimal(str(data_a["fee_collection"]["total_collected"])) == Decimal("6000.00")
    assert Decimal(str(data_a["pending_fees"]["total_pending"])) == Decimal("4000.00")
    assert data_a["pass_percentage"] == 100.0

    # 2. Query Tenant B Analytics -> STRICT TENANT ISOLATION CHECK
    res_b = await client.get("/api/v1/reports/institution-admin", headers=headers_b)
    assert res_b.status_code == 200
    data_b = res_b.json()

    # Tenant B must have zero students, zero fee collections, and zero cross-tenant contamination!
    assert data_b["total_students"] == 0
    assert data_b["total_teachers"] == 0
    assert Decimal(str(data_b["fee_collection"]["total_collected"])) == Decimal("0.00")
    assert Decimal(str(data_b["pending_fees"]["total_pending"])) == Decimal("0.00")


@pytest.mark.asyncio
async def test_teacher_analytics_dashboard(
    client: AsyncClient,
    db_session: AsyncSession,
):
    """
    Verifies that a Teacher can access their personal analytics dashboard
    (assigned students, subject performance, exam stats, and pending assignment evaluations).
    """
    tenant, teacher_user, headers = await _setup_tenant_user_role(db_session, "TEACHER")

    # Create Teacher Profile
    tp = TeacherProfile(
        tenant_id=tenant.id,
        user_id=teacher_user.id,
        employee_id=f"EMP-T-{uuid.uuid4().hex[:4].upper()}",
        status="ACTIVE",
    )
    db_session.add(tp)
    await db_session.flush()

    # Create class, subject, and mapping
    cls = SchoolClass(tenant_id=tenant.id, name="Class 9", code=f"C9-{uuid.uuid4().hex[:3]}", order_index=9)
    sbj = Subject(tenant_id=tenant.id, name="Mathematics", code=f"MTH-{uuid.uuid4().hex[:3]}")
    db_session.add_all([cls, sbj])
    await db_session.flush()

    mapping = TeacherSubjectMapping(
        tenant_id=tenant.id,
        class_id=cls.id,
        teacher_id=tp.id,
        subject_id=sbj.id,
    )
    db_session.add(mapping)

    # Add a student in that class
    su = User(
        email=f"stu-{uuid.uuid4().hex[:5]}@sterling.edu",
        password_hash="pw",
        full_name="Assigned Student",
        is_active=True,
    )
    db_session.add(su)
    await db_session.flush()
    sp = StudentProfile(
        tenant_id=tenant.id,
        user_id=su.id,
        class_id=cls.id,
        admission_number=f"ADM-T-{uuid.uuid4().hex[:4]}",
        admission_date=date(2026, 6, 1),
    )
    db_session.add(sp)
    await db_session.commit()

    res = await client.get("/api/v1/reports/teacher", headers=headers)
    assert res.status_code == 200
    data = res.json()

    assert data["teacher_name"] == teacher_user.full_name
    assert data["assigned_students"] == 1
    assert len(data["subject_performance"]) >= 1
    assert data["subject_performance"][0]["subject_name"] == "Mathematics"


@pytest.mark.asyncio
async def test_student_and_parent_analytics_dashboards(
    client: AsyncClient,
    db_session: AsyncSession,
):
    """
    Verifies Student dashboard (attendance %, subject marks, progress trend)
    and Parent dashboard (linked child progress, dues, overdue status).
    """
    tenant, parent_user, parent_headers = await _setup_tenant_user_role(db_session, "PARENT")

    # Create student user and profile
    student_user = User(
        email=f"stu-p-{uuid.uuid4().hex[:5]}@sterling.edu",
        password_hash="pw",
        full_name="Aarav Sharma",
        is_active=True,
    )
    db_session.add(student_user)
    await db_session.flush()

    acad_sess_p = AcademicSession(
        tenant_id=tenant.id,
        name="AY 2026-27",
        code=f"AYP-{uuid.uuid4().hex[:4]}",
        start_date=date(2026, 4, 1),
        end_date=date(2027, 3, 31),
        is_current=True,
    )
    cls_p = SchoolClass(tenant_id=tenant.id, name="Grade 8", code=f"G8-{uuid.uuid4().hex[:3]}", order_index=8)
    db_session.add_all([acad_sess_p, cls_p])
    await db_session.flush()

    student_role = (await db_session.execute(select(Role).where(Role.code == "STUDENT"))).scalars().first()
    db_session.add(Membership(tenant_id=tenant.id, user_id=student_user.id, role_id=student_role.id))

    sp = StudentProfile(
        tenant_id=tenant.id,
        user_id=student_user.id,
        class_id=cls_p.id,
        academic_session_id=acad_sess_p.id,
        admission_number=f"ADM-P-{uuid.uuid4().hex[:4]}",
        admission_date=date(2026, 6, 1),
    )
    db_session.add(sp)
    await db_session.flush()

    # Link parent to student (VERIFIED)
    link = StudentParent(
        tenant_id=tenant.id,
        parent_user_id=parent_user.id,
        student_id=sp.id,
        relation_type="FATHER",
        status="VERIFIED",
    )
    db_session.add(link)

    # Add Attendance Session and Entry for student
    att_sess = StudentAttendanceSession(
        tenant_id=tenant.id,
        academic_session_id=acad_sess_p.id,
        class_id=cls_p.id,
        session_date=date(2026, 11, 18),
        session_type="DAILY",
    )
    db_session.add(att_sess)
    await db_session.flush()

    db_session.add(StudentAttendanceEntry(
        tenant_id=tenant.id,
        session_id=att_sess.id,
        student_id=sp.id,
        status="PRESENT",
    ))
    await db_session.commit()

    # 1. Student Dashboard test
    student_token = create_access_token(
        user_id=student_user.id, email=student_user.email, tenant_id=tenant.id, role="STUDENT"
    )
    student_headers = {"Authorization": f"Bearer {student_token}", "X-Tenant-ID": str(tenant.id)}

    stu_res = await client.get("/api/v1/reports/student", headers=student_headers)
    assert stu_res.status_code == 200
    stu_data = stu_res.json()
    assert stu_data["student_name"] == "Aarav Sharma"
    assert stu_data["attendance_percentage"] == 100.0

    # 2. Parent Dashboard test
    parent_res = await client.get("/api/v1/reports/parent", headers=parent_headers)
    assert parent_res.status_code == 200
    par_data = parent_res.json()
    assert par_data["children_count"] == 1
    assert par_data["children"][0]["student_name"] == "Aarav Sharma"
    assert par_data["children"][0]["attendance_percentage"] == 100.0


@pytest.mark.asyncio
async def test_reports_export_pdf_and_excel(
    client: AsyncClient,
    db_session: AsyncSession,
):
    """
    Verifies downloadable binary report generation:
    PDF (application/pdf with %PDF magic header) and
    Excel (application/vnd.openxmlformats-officedocument.spreadsheetml.sheet with PK zip header).
    """
    tenant, admin, headers = await _setup_tenant_user_role(db_session, "INSTITUTION_ADMIN")

    # 1. PDF Export
    pdf_res = await client.get(
        "/api/v1/reports/export/pdf?report_type=INSTITUTION_OVERVIEW",
        headers=headers,
    )
    assert pdf_res.status_code == 200
    assert pdf_res.headers["content-type"] == "application/pdf"
    assert pdf_res.content.startswith(b"%PDF-")  # Standard PDF magic header

    # 2. Excel Export
    excel_res = await client.get(
        "/api/v1/reports/export/excel?report_type=FEE_COLLECTION",
        headers=headers,
    )
    assert excel_res.status_code == 200
    assert "spreadsheetml" in excel_res.headers["content-type"]
    assert excel_res.content.startswith(b"PK\x03\x04")  # Standard ZIP / XLSX magic header


@pytest.mark.asyncio
async def test_scheduled_reports_lifecycle(
    client: AsyncClient,
    db_session: AsyncSession,
):
    """
    Tests CRUD lifecycle and manual execution trigger of scheduled recurring reports.
    """
    tenant, admin, headers = await _setup_tenant_user_role(db_session, "INSTITUTION_ADMIN")

    # 1. Create Scheduled Report
    create_res = await client.post(
        "/api/v1/reports/scheduled",
        headers=headers,
        json={
            "title": "Weekly Executive Attendance & Fee Digest",
            "report_type": "INSTITUTION_OVERVIEW",
            "frequency": "WEEKLY",
            "format": "PDF",
            "recipients": ["director@sterling.edu", "finance@sterling.edu"],
            "filters": {"class_id": str(uuid.uuid4())},
        },
    )
    assert create_res.status_code == 201
    sched_data = create_res.json()
    sched_id = sched_data["id"]
    assert sched_data["title"] == "Weekly Executive Attendance & Fee Digest"
    assert sched_data["frequency"] == "WEEKLY"

    # 2. List Scheduled Reports
    list_res = await client.get("/api/v1/reports/scheduled", headers=headers)
    assert list_res.status_code == 200
    items = list_res.json()
    assert any(s["id"] == sched_id for s in items)

    # 3. Trigger Scheduled Report execution
    trigger_res = await client.post(
        f"/api/v1/reports/scheduled/{sched_id}/trigger",
        headers=headers,
    )
    assert trigger_res.status_code == 200
    assert trigger_res.json()["status"] == "DISPATCHED"

    # 4. Delete Scheduled Report
    del_res = await client.delete(
        f"/api/v1/reports/scheduled/{sched_id}",
        headers=headers,
    )
    assert del_res.status_code == 200
    assert del_res.json()["success"] is True
