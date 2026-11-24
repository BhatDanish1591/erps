from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta, timezone

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token, hash_password
from app.models.academic import (
    AcademicSession,
    CollegeEnrollmentDetail,
    CollegeSemester,
    Course,
    Department,
    SchoolClass,
    SchoolEnrollmentDetail,
    Section,
    StudentAcademicEnrollment,
    StudentParent,
    StudentProfile,
    Subject,
    TeacherAssignment,
    TeacherProfile,
)
from app.models.attendance import (
    AttendanceCorrectionLog,
    AttendanceDeviceLog,
    StudentAttendanceEntry,
    StudentAttendanceSession,
)
from app.models.auth import Membership, Role
from app.models.notification import NotificationOutbox
from app.models.enums import BillingCycle, InstitutionType, MembershipStatus, RoleScope, SubscriptionStatus, TenantStatus
from app.models.subscription import Subscription, SubscriptionPlan
from app.models.tenant import Tenant
from app.models.user import User


@pytest.fixture
async def setup_attendance_data(db_session: AsyncSession):
    # Tenant
    tenant = Tenant(
        name="Apex Academy",
        slug=f"apex-{uuid.uuid4().hex[:6]}",
        institution_type=InstitutionType.SCHOOL,
        status=TenantStatus.ACTIVE,
        email=f"apex_{uuid.uuid4().hex[:6]}@apex.edu",
    )
    db_session.add(tenant)
    await db_session.flush()

    # Subscription
    plan = SubscriptionPlan(
        name="Professional School Plan",
        code=f"PRO-SCH-{uuid.uuid4().hex[:4]}",
        institution_type=InstitutionType.SCHOOL,
        billing_cycle=BillingCycle.MONTHLY,
        price=2499.0,
        max_students=1000,
        max_teachers=75,
        is_active=True,
    )
    db_session.add(plan)
    await db_session.flush()

    sub = Subscription(
        tenant_id=tenant.id,
        plan_id=plan.id,
        status=SubscriptionStatus.ACTIVE,
        current_period_start=datetime.now(timezone.utc),
        current_period_end=datetime.now(timezone.utc) + timedelta(days=30),
    )
    db_session.add(sub)

    # Roles
    admin_role = (await db_session.execute(select(Role).where(Role.code == "INSTITUTION_ADMIN"))).scalars().first()
    if not admin_role:
        admin_role = Role(name="Institution Admin", code="INSTITUTION_ADMIN", scope=RoleScope.TENANT, is_system_role=True)
        db_session.add(admin_role)
        await db_session.flush()

    teacher_role = (await db_session.execute(select(Role).where(Role.code == "TEACHER"))).scalars().first()
    if not teacher_role:
        teacher_role = Role(name="Teacher", code="TEACHER", scope=RoleScope.TENANT, is_system_role=True)
        db_session.add(teacher_role)
        await db_session.flush()

    student_role = (await db_session.execute(select(Role).where(Role.code == "STUDENT"))).scalars().first()
    if not student_role:
        student_role = Role(name="Student", code="STUDENT", scope=RoleScope.TENANT, is_system_role=True)
        db_session.add(student_role)
        await db_session.flush()

    # Admin User
    admin_user = User(
        email=f"admin_{uuid.uuid4().hex[:6]}@apex.edu",
        password_hash=hash_password("ApexAdmin123!"),
        full_name="Principal Skinner",
        is_active=True,
    )
    db_session.add(admin_user)
    await db_session.flush()
    db_session.add(Membership(user_id=admin_user.id, tenant_id=tenant.id, role_id=admin_role.id, status=MembershipStatus.ACTIVE))

    # Teacher User & Profile
    teacher_user = User(
        email=f"teacher_{uuid.uuid4().hex[:6]}@apex.edu",
        password_hash=hash_password("ApexTeacher123!"),
        full_name="Edna Krabappel",
        is_active=True,
    )
    db_session.add(teacher_user)
    await db_session.flush()
    db_session.add(Membership(user_id=teacher_user.id, tenant_id=tenant.id, role_id=teacher_role.id, status=MembershipStatus.ACTIVE))

    teacher_profile = TeacherProfile(
        tenant_id=tenant.id,
        user_id=teacher_user.id,
        employee_id=f"TCH-{uuid.uuid4().hex[:4].upper()}",
        rfid_tag="RFID-TCH-001",
        status="ACTIVE",
    )
    db_session.add(teacher_profile)

    # Student User & Profile
    student_user = User(
        email=f"student_{uuid.uuid4().hex[:6]}@apex.edu",
        password_hash=hash_password("ApexStudent123!"),
        full_name="Bart Simpson",
        is_active=True,
    )
    db_session.add(student_user)
    await db_session.flush()
    db_session.add(Membership(user_id=student_user.id, tenant_id=tenant.id, role_id=student_role.id, status=MembershipStatus.ACTIVE))

    student_profile = StudentProfile(
        tenant_id=tenant.id,
        user_id=student_user.id,
        admission_number=f"ADM-{uuid.uuid4().hex[:4].upper()}",
        gender="MALE",
        date_of_birth=date(2010, 4, 1),
        admission_date=date(2025, 4, 1),
        parent_name="Homer Simpson",
        parent_phone="+15551234567",
        rfid_tag="RFID-STU-001",
        status="ACTIVE",
    )
    db_session.add(student_profile)

    # Academic Session, Class, Section, Subject
    acad_session = AcademicSession(
        tenant_id=tenant.id,
        name="2026-2027",
        code=f"SESS-{uuid.uuid4().hex[:4]}",
        start_date=date(2026, 4, 1),
        end_date=date(2027, 3, 31),
        is_current=True,
    )
    db_session.add(acad_session)
    await db_session.flush()

    s_class = SchoolClass(
        tenant_id=tenant.id,
        name="Grade 4",
        code=f"G4-{uuid.uuid4().hex[:4]}",
        order_index=4,
    )
    db_session.add(s_class)
    await db_session.flush()

    section = Section(
        tenant_id=tenant.id,
        class_id=s_class.id,
        name="Section A",
    )
    db_session.add(section)
    await db_session.flush()

    subject = Subject(
        tenant_id=tenant.id,
        name="History",
        code=f"HIST-{uuid.uuid4().hex[:4]}",
        subject_type="THEORY",
    )
    db_session.add(subject)
    await db_session.flush()

    # Enroll Student
    enrollment = StudentAcademicEnrollment(
        tenant_id=tenant.id,
        student_id=student_profile.id,
        academic_session_id=acad_session.id,
        enrollment_type="SCHOOL",
        enrollment_number=f"ENR-{uuid.uuid4().hex[:6].upper()}",
        enrollment_date=date(2026, 4, 1),
        status="ACTIVE",
    )
    db_session.add(enrollment)
    await db_session.flush()

    sch_detail = SchoolEnrollmentDetail(
        tenant_id=tenant.id,
        enrollment_id=enrollment.id,
        class_id=s_class.id,
        section_id=section.id,
    )
    db_session.add(sch_detail)
    db_session.add(TeacherAssignment(
        tenant_id=tenant.id,
        teacher_id=teacher_profile.id,
        academic_session_id=acad_session.id,
        class_id=s_class.id,
        section_id=section.id,
        subject_id=subject.id,
    ))
    await db_session.commit()

    # JWT Tokens
    admin_token = create_access_token(
        user_id=admin_user.id,
        email=admin_user.email,
        tenant_id=tenant.id,
        role="INSTITUTION_ADMIN",
        permissions=["attendance.mark", "attendance.view", "attendance.correct"],
    )
    teacher_token = create_access_token(
        user_id=teacher_user.id,
        email=teacher_user.email,
        tenant_id=tenant.id,
        role="TEACHER",
        permissions=["attendance.mark", "attendance.view"],
    )
    student_token = create_access_token(
        user_id=student_user.id,
        email=student_user.email,
        tenant_id=tenant.id,
        role="STUDENT",
        permissions=["attendance.view"],
    )

    return {
        "tenant": tenant,
        "acad_session": acad_session,
        "school_class": s_class,
        "section": section,
        "subject": subject,
        "teacher_user": teacher_user,
        "teacher_profile": teacher_profile,
        "student_user": student_user,
        "student_profile": student_profile,
        "admin_token": admin_token,
        "teacher_token": teacher_token,
        "student_token": student_token,
    }


@pytest.mark.asyncio
async def test_attendance_roster_and_submit_session(client: AsyncClient, setup_attendance_data: dict, db_session: AsyncSession):
    data = setup_attendance_data
    tenant_id = str(data["tenant"].id)
    headers = {"Authorization": f"Bearer {data['teacher_token']}", "X-Tenant-ID": tenant_id}

    # 1. Fetch Roster
    res = await client.get(
        f"/api/v1/attendance/roster",
        headers=headers,
        params={
            "academic_session_id": str(data["acad_session"].id),
            "session_date": "2026-05-10",
            "class_id": str(data["school_class"].id),
            "section_id": str(data["section"].id),
            "subject_id": str(data["subject"].id),
            "period_number": 1,
            "session_type": "PERIOD_WISE",
        },
    )
    assert res.status_code == 200, res.text
    roster_data = res.json()["data"]
    assert len(roster_data["students"]) == 1
    assert roster_data["students"][0]["admission_number"] == data["student_profile"].admission_number
    assert roster_data["students"][0]["current_status"] is None
    outside = await client.get("/api/v1/attendance/roster", headers=headers, params={
        "academic_session_id": str(data["acad_session"].id), "session_date": "2026-05-10",
        "class_id": str(data["school_class"].id),
    })
    assert outside.status_code == 403

    # 2. Submit Attendance Session
    submit_payload = {
        "academic_session_id": str(data["acad_session"].id),
        "session_date": "2026-05-10",
        "session_type": "PERIOD_WISE",
        "class_id": str(data["school_class"].id),
        "section_id": str(data["section"].id),
        "subject_id": str(data["subject"].id),
        "period_number": 1,
        "remarks": "Period 1 History Roll Call",
        "entries": [
            {
                "student_id": str(data["student_profile"].id),
                "status": "PRESENT",
                "remarks": "On time",
                "marked_via": "WEB",
            }
        ],
        "notify_absent_parents": True,
    }

    res_post = await client.post("/api/v1/attendance/sessions", headers=headers, json=submit_payload)
    assert res_post.status_code == 201, res_post.text
    sess_res = res_post.json()["data"]
    assert sess_res["total_students"] == 1
    assert sess_res["present_count"] == 1
    assert sess_res["absent_count"] == 0
    assert sess_res["attendance_rate"] == 100.0

    # 3. Re-query Roster to verify current status is populated
    res_roster2 = await client.get(
        f"/api/v1/attendance/roster",
        headers=headers,
        params={
            "academic_session_id": str(data["acad_session"].id),
            "session_date": "2026-05-10",
            "class_id": str(data["school_class"].id),
            "section_id": str(data["section"].id),
            "subject_id": str(data["subject"].id),
            "period_number": 1,
            "session_type": "PERIOD_WISE",
        },
    )
    assert res_roster2.status_code == 200
    assert res_roster2.json()["data"]["is_submitted"] is True
    assert res_roster2.json()["data"]["students"][0]["current_status"] == "PRESENT"

    admin_headers = {"Authorization": f"Bearer {data['admin_token']}"}
    cohort = await client.get("/api/v1/attendance/cohort-report", headers=admin_headers, params={
        "academic_session_id": str(data["acad_session"].id),
        "class_id": str(data["school_class"].id),
    })
    assert cohort.status_code == 200, cohort.text
    report = cohort.json()["data"]
    assert report["overview"] == {"total": 1, "attended": 1, "percentage": 100.0}
    assert report["subjects"][0]["classes"] == 1
    assert report["students"][0]["id"] == str(data["student_profile"].id)

    parent = User(email=f"attendance-parent-{uuid.uuid4().hex}@example.com", password_hash="test", full_name="Parent")
    db_session.add(parent)
    await db_session.flush()
    db_session.add(StudentParent(
        tenant_id=data["tenant"].id, student_id=data["student_profile"].id, parent_user_id=parent.id, status="VERIFIED",
    ))
    await db_session.commit()
    absent_submission = {
        "academic_session_id": str(data["acad_session"].id), "session_date": "2026-05-11",
        "class_id": str(data["school_class"].id), "section_id": str(data["section"].id),
        "session_type": "DAILY", "notify_absent_parents": True,
        "entries": [{"student_id": str(data["student_profile"].id), "status": "ABSENT"}],
    }
    for _ in range(2):
        marked = await client.post("/api/v1/attendance/sessions", headers=admin_headers, json=absent_submission)
        assert marked.status_code == 201, marked.text
    notices = (await db_session.scalars(select(NotificationOutbox).where(
        NotificationOutbox.tenant_id == data["tenant"].id, NotificationOutbox.event_type == "STUDENT_ABSENT",
    ))).all()
    assert len(notices) == 1
    assert notices[0].event_payload["recipients"][0]["user_id"] == str(parent.id)


@pytest.mark.asyncio
async def test_college_cohort_report_counts_subject_attendance(client: AsyncClient, db_session: AsyncSession, setup_attendance_data: dict):
    data = setup_attendance_data
    tenant = data["tenant"]
    tenant.institution_type = InstitutionType.COLLEGE
    department = Department(tenant_id=tenant.id, name="Computing", code="CS")
    db_session.add(department)
    await db_session.flush()
    course = Course(tenant_id=tenant.id, department_id=department.id, name="Computer Science", code="BSC-CS")
    db_session.add(course)
    await db_session.flush()
    semester = CollegeSemester(tenant_id=tenant.id, course_id=course.id, name="Semester 1", semester_number=1)
    db_session.add(semester)
    await db_session.flush()
    enrollment = await db_session.scalar(select(StudentAcademicEnrollment).where(
        StudentAcademicEnrollment.student_id == data["student_profile"].id,
    ))
    enrollment.enrollment_type = "COLLEGE"
    db_session.add(CollegeEnrollmentDetail(
        tenant_id=tenant.id, enrollment_id=enrollment.id, course_id=course.id, semester_id=semester.id,
    ))
    await db_session.commit()

    filters = {
        "academic_session_id": str(data["acad_session"].id),
        "department_id": str(department.id), "course_id": str(course.id), "semester_id": str(semester.id),
    }
    headers = {"Authorization": f"Bearer {data['admin_token']}"}
    admission = await client.post("/api/v1/students", headers=headers, json={
        "full_name": "Newly Admitted Student",
        "academic_session_id": filters["academic_session_id"],
        "department_id": filters["department_id"],
        "course_id": filters["course_id"],
        "semester": 1,
    })
    assert admission.status_code == 201, admission.text
    before = await client.get("/api/v1/attendance/cohort-report", headers=headers, params=filters)
    assert before.status_code == 200, before.text
    report_students = before.json()["data"]["students"]
    assert any(student["id"] == admission.json()["data"]["id"] for student in report_students)
    assert all(student["percentage"] is None for student in report_students)
    assert before.json()["data"]["overview"]["percentage"] is None

    recorded = await client.post("/api/v1/attendance/sessions", headers=headers, json={
        "academic_session_id": filters["academic_session_id"], "session_date": "2026-05-10",
        "course_id": filters["course_id"], "semester_id": filters["semester_id"],
        "session_type": "SUBJECT_WISE", "subject_id": str(data["subject"].id),
        "entries": [
            {"student_id": str(data["student_profile"].id), "status": "LATE"},
            {"student_id": admission.json()["data"]["id"], "status": "PRESENT"},
        ],
    })
    assert recorded.status_code == 201, recorded.text
    response = await client.get("/api/v1/attendance/cohort-report", headers=headers, params=filters)
    assert response.status_code == 200, response.text
    subject = response.json()["data"]["subjects"][0]
    assert (subject["name"], subject["classes"], subject["percentage"]) == ("History", 1, 100.0)


@pytest.mark.asyncio
async def test_attendance_correction_audit_log(client: AsyncClient, setup_attendance_data: dict):
    data = setup_attendance_data
    tenant_id = str(data["tenant"].id)
    admin_headers = {"Authorization": f"Bearer {data['admin_token']}", "X-Tenant-ID": tenant_id}

    # First submit attendance as ABSENT
    submit_payload = {
        "academic_session_id": str(data["acad_session"].id),
        "session_date": "2026-05-11",
        "session_type": "DAILY",
        "class_id": str(data["school_class"].id),
        "section_id": str(data["section"].id),
        "entries": [
            {
                "student_id": str(data["student_profile"].id),
                "status": "ABSENT",
                "remarks": "Not present in morning roll call",
            }
        ],
    }
    res_submit = await client.post("/api/v1/attendance/sessions", headers=admin_headers, json=submit_payload)
    assert res_submit.status_code == 201
    entry_id = res_submit.json()["data"]["entries"][0]["id"]
    assert res_submit.json()["data"]["absent_count"] == 1

    # Perform Attendance Correction
    correct_payload = {
        "entry_id": entry_id,
        "new_status": "PRESENT",
        "reason": "Student arrived late with principal permission slip",
    }
    res_correct = await client.post("/api/v1/attendance/entries/correct", headers=admin_headers, json=correct_payload)
    assert res_correct.status_code == 200, res_correct.text
    assert res_correct.json()["data"]["status"] == "PRESENT"
    assert res_correct.json()["data"]["is_corrected"] is True

    # Verify Correction Audit Log
    res_logs = await client.get(f"/api/v1/attendance/corrections?entry_id={entry_id}", headers=admin_headers)
    assert res_logs.status_code == 200
    logs = res_logs.json()["data"]
    assert len(logs) >= 1
    assert logs[0]["previous_status"] == "ABSENT"
    assert logs[0]["new_status"] == "PRESENT"
    assert "principal permission slip" in logs[0]["reason"]


@pytest.mark.asyncio
async def test_student_attendance_summary_and_low_attendance_alerts(client: AsyncClient, setup_attendance_data: dict):
    data = setup_attendance_data
    tenant_id = str(data["tenant"].id)
    admin_headers = {"Authorization": f"Bearer {data['admin_token']}", "X-Tenant-ID": tenant_id}

    # Submit 2 days: Day 1 ABSENT, Day 2 PRESENT (attendance rate: 50%)
    await client.post(
        "/api/v1/attendance/sessions",
        headers=admin_headers,
        json={
            "academic_session_id": str(data["acad_session"].id),
            "session_date": "2026-05-01",
            "class_id": str(data["school_class"].id),
            "section_id": str(data["section"].id),
            "entries": [{"student_id": str(data["student_profile"].id), "status": "ABSENT"}],
        },
    )
    await client.post(
        "/api/v1/attendance/sessions",
        headers=admin_headers,
        json={
            "academic_session_id": str(data["acad_session"].id),
            "session_date": "2026-05-02",
            "class_id": str(data["school_class"].id),
            "section_id": str(data["section"].id),
            "entries": [{"student_id": str(data["student_profile"].id), "status": "PRESENT"}],
        },
    )

    # Check Student Summary
    res_summary = await client.get(
        f"/api/v1/attendance/students/{data['student_profile'].id}/summary",
        headers=admin_headers,
    )
    assert res_summary.status_code == 200
    sum_data = res_summary.json()["data"]
    assert sum_data["total_conducted"] >= 2
    assert sum_data["attendance_percentage"] <= 75.0
    assert sum_data["is_low_attendance"] is True

    # Check Low Attendance Alert Endpoint
    res_alerts = await client.get("/api/v1/attendance/low-attendance?threshold=75.0", headers=admin_headers)
    assert res_alerts.status_code == 200
    alert_list = res_alerts.json()["data"]
    found = any(a["student_id"] == str(data["student_profile"].id) for a in alert_list)
    assert found is True

    # Check Monthly Report
    res_monthly = await client.get(
        f"/api/v1/attendance/students/{data['student_profile'].id}/monthly?year=2026&month=5",
        headers=admin_headers,
    )
    assert res_monthly.status_code == 200
    monthly_data = res_monthly.json()["data"]
    assert monthly_data["conducted_days"] >= 2
    assert len(monthly_data["records"]) >= 2

    # Check Admin Overview
    res_overview = await client.get("/api/v1/attendance/overview?target_date=2026-05-02", headers=admin_headers)
    assert res_overview.status_code == 200
    ov_data = res_overview.json()["data"]
    assert ov_data["total_students_enrolled"] >= 1
    assert ov_data["low_attendance_students_count"] >= 1


@pytest.mark.asyncio
async def test_qr_attendance_and_rfid_integration(client: AsyncClient, setup_attendance_data: dict):
    data = setup_attendance_data
    tenant_id = str(data["tenant"].id)
    teacher_headers = {"Authorization": f"Bearer {data['teacher_token']}", "X-Tenant-ID": tenant_id}
    student_headers = {"Authorization": f"Bearer {data['student_token']}", "X-Tenant-ID": tenant_id}

    # 1. Teacher generates QR code
    res_qr = await client.post(
        f"/api/v1/attendance/qr/generate?academic_session_id={data['acad_session'].id}",
        headers=teacher_headers,
        json={
            "class_id": str(data["school_class"].id),
            "section_id": str(data["section"].id),
            "validity_minutes": 15,
        },
    )
    assert res_qr.status_code == 200, res_qr.text
    qr_token = res_qr.json()["data"]["qr_token"]
    assert qr_token.startswith("QR-ATT-")

    # 2. Student scans QR code
    res_scan = await client.post(
        "/api/v1/attendance/qr/scan",
        headers=student_headers,
        json={"qr_token": qr_token},
    )
    assert res_scan.status_code == 200, res_scan.text
    assert res_scan.json()["data"]["status"] == "PRESENT"
    assert res_scan.json()["data"]["marked_via"] == "QR"

    # 3. RFID Swipe Webhook
    res_rfid = await client.post(
        "/api/v1/attendance/hardware/rfid-swipe",
        headers={"Authorization": f"Bearer {data['admin_token']}", "X-Tenant-ID": tenant_id},
        json={
            "device_id": "GATE-READER-01",
            "rfid_tag": "RFID-STU-001",
            "event_type": "SWIPE",
        },
    )
    assert res_rfid.status_code == 200, res_rfid.text
    rfid_res = res_rfid.json()["data"]
    assert rfid_res["status"] == "SUCCESS"
    assert rfid_res["user_type"] == "STUDENT"
    assert rfid_res["matched_id"] == str(data["student_profile"].id)


@pytest.mark.asyncio
async def test_teacher_checkin_checkout_and_leave(client: AsyncClient, setup_attendance_data: dict):
    data = setup_attendance_data
    tenant_id = str(data["tenant"].id)
    teacher_headers = {"Authorization": f"Bearer {data['teacher_token']}", "X-Tenant-ID": tenant_id}
    admin_headers = {"Authorization": f"Bearer {data['admin_token']}", "X-Tenant-ID": tenant_id}

    # 1. Teacher Check-in
    res_in = await client.post(
        "/api/v1/attendance/teacher/check-in",
        headers=teacher_headers,
        json={
            "check_in_method": "WEB",
            "latitude": 28.6139,
            "longitude": 77.2090,
            "notes": "Arrived on campus",
        },
    )
    assert res_in.status_code == 200, res_in.text
    assert res_in.json()["data"]["status"] == "PRESENT"
    assert res_in.json()["data"]["check_in_time"] is not None

    # 2. Teacher Check-out
    res_out = await client.post(
        "/api/v1/attendance/teacher/check-out",
        headers=teacher_headers,
        json={"notes": "Completed end-of-day tasks"},
    )
    assert res_out.status_code == 200, res_out.text
    assert res_out.json()["data"]["check_out_time"] is not None

    # 3. Teacher applies for leave
    res_leave = await client.post(
        "/api/v1/attendance/teacher/leaves",
        headers=teacher_headers,
        json={
            "leave_type": "CASUAL",
            "start_date": "2026-06-01",
            "end_date": "2026-06-02",
            "reason": "Family function attending out of town",
        },
    )
    assert res_leave.status_code == 201, res_leave.text
    leave_id = res_leave.json()["data"]["id"]
    assert res_leave.json()["data"]["status"] == "PENDING"
    assert res_leave.json()["data"]["total_days"] == 2

    # 4. Admin approves leave
    res_app = await client.put(
        f"/api/v1/attendance/teacher/leaves/{leave_id}",
        headers=admin_headers,
        json={"action": "APPROVE"},
    )
    assert res_app.status_code == 200, res_app.text
    assert res_app.json()["data"]["status"] == "APPROVED"
