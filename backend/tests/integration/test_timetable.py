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
    SchoolClass,
    SchoolEnrollmentDetail,
    Section,
    StudentAcademicEnrollment,
    StudentProfile,
    Subject,
    TeacherProfile,
)
from app.models.auth import Membership, Role
from app.models.enums import BillingCycle, InstitutionType, MembershipStatus, RoleScope, TenantStatus
from app.models.subscription import Subscription, SubscriptionPlan
from app.models.tenant import Tenant
from app.models.user import User


@pytest.fixture
async def setup_timetable_data(db_session: AsyncSession):
    # 1. Tenant
    tenant = Tenant(
        name="Oakridge Model High School",
        slug=f"oakridge-tt-{uuid.uuid4().hex[:6]}",
        institution_type=InstitutionType.SCHOOL,
        status=TenantStatus.ACTIVE,
        email=f"oakridge_tt_{uuid.uuid4().hex[:6]}@school.edu",
    )
    db_session.add(tenant)
    await db_session.flush()

    # 2. Subscription
    plan = SubscriptionPlan(
        name="Enterprise Timetable Plan",
        code=f"ENT-TT-{uuid.uuid4().hex[:4]}",
        institution_type=InstitutionType.SCHOOL,
        billing_cycle=BillingCycle.MONTHLY,
        price=4999.0,
        max_students=3000,
        max_teachers=200,
        is_active=True,
    )
    db_session.add(plan)
    await db_session.flush()

    sub = Subscription(
        tenant_id=tenant.id,
        plan_id=plan.id,
        status="ACTIVE",
        billing_cycle=BillingCycle.MONTHLY,
        current_period_start=datetime.now(timezone.utc),
        current_period_end=datetime.now(timezone.utc) + timedelta(days=30),
    )
    db_session.add(sub)

    # 3. Roles
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

    # 4. Users
    admin_user = User(
        email=f"tt_admin_{uuid.uuid4().hex[:6]}@oakridge.edu",
        password_hash=hash_password("AdminPass123!"),
        full_name="Sister Principal",
        is_active=True,
    )
    db_session.add(admin_user)
    await db_session.flush()
    db_session.add(Membership(user_id=admin_user.id, tenant_id=tenant.id, role_id=admin_role.id, status=MembershipStatus.ACTIVE))

    # Teacher 1 (Physics)
    teacher1_user = User(
        email=f"tt_teacher1_{uuid.uuid4().hex[:6]}@oakridge.edu",
        password_hash=hash_password("TeacherPass123!"),
        full_name="Isaac Newton",
        is_active=True,
    )
    db_session.add(teacher1_user)
    await db_session.flush()
    db_session.add(Membership(user_id=teacher1_user.id, tenant_id=tenant.id, role_id=teacher_role.id, status=MembershipStatus.ACTIVE))

    teacher1_profile = TeacherProfile(
        tenant_id=tenant.id,
        user_id=teacher1_user.id,
        employee_id=f"TCH-{uuid.uuid4().hex[:4].upper()}",
        status="ACTIVE",
    )
    db_session.add(teacher1_profile)

    # Teacher 2 (Mathematics)
    teacher2_user = User(
        email=f"tt_teacher2_{uuid.uuid4().hex[:6]}@oakridge.edu",
        password_hash=hash_password("TeacherPass123!"),
        full_name="Leonhard Euler",
        is_active=True,
    )
    db_session.add(teacher2_user)
    await db_session.flush()
    db_session.add(Membership(user_id=teacher2_user.id, tenant_id=tenant.id, role_id=teacher_role.id, status=MembershipStatus.ACTIVE))

    teacher2_profile = TeacherProfile(
        tenant_id=tenant.id,
        user_id=teacher2_user.id,
        employee_id=f"TCH-{uuid.uuid4().hex[:4].upper()}",
        status="ACTIVE",
    )
    db_session.add(teacher2_profile)

    # Student
    student_user = User(
        email=f"tt_student_{uuid.uuid4().hex[:6]}@oakridge.edu",
        password_hash=hash_password("StudentPass123!"),
        full_name="Albert Einstein",
        is_active=True,
    )
    db_session.add(student_user)
    await db_session.flush()
    db_session.add(Membership(user_id=student_user.id, tenant_id=tenant.id, role_id=student_role.id, status=MembershipStatus.ACTIVE))

    student_profile = StudentProfile(
        tenant_id=tenant.id,
        user_id=student_user.id,
        admission_number=f"ADM-{uuid.uuid4().hex[:6].upper()}",
        gender="MALE",
        date_of_birth=date(2008, 3, 14),
        admission_date=date(2025, 4, 1),
        status="ACTIVE",
    )
    db_session.add(student_profile)

    # 5. Academic Structure
    session = AcademicSession(
        tenant_id=tenant.id,
        name="2026-2027",
        code=f"SESS-{uuid.uuid4().hex[:4].upper()}",
        start_date=date(2026, 4, 1),
        end_date=date(2027, 3, 31),
        is_current=True,
    )
    db_session.add(session)
    await db_session.flush()

    school_class1 = SchoolClass(
        tenant_id=tenant.id,
        name="Grade 10",
        code=f"G10-{uuid.uuid4().hex[:4]}",
    )
    school_class2 = SchoolClass(
        tenant_id=tenant.id,
        name="Grade 11",
        code=f"G11-{uuid.uuid4().hex[:4]}",
    )
    db_session.add_all([school_class1, school_class2])
    await db_session.flush()

    section1 = Section(tenant_id=tenant.id, class_id=school_class1.id, name="Section A", capacity=40)
    section2 = Section(tenant_id=tenant.id, class_id=school_class2.id, name="Section A", capacity=40)
    db_session.add_all([section1, section2])
    await db_session.flush()

    subject1 = Subject(tenant_id=tenant.id, name="Classical Physics", code="PHY-101", credits=4)
    subject2 = Subject(tenant_id=tenant.id, name="Pure Mathematics", code="MATH-101", credits=4)
    db_session.add_all([subject1, subject2])
    await db_session.flush()

    # Enroll student in Grade 10 Section A
    enrollment = StudentAcademicEnrollment(
        tenant_id=tenant.id,
        student_id=student_profile.id,
        academic_session_id=session.id,
        enrollment_type="SCHOOL",
        enrollment_number=f"ENR-{uuid.uuid4().hex[:6].upper()}",
        enrollment_date=date(2026, 4, 1),
        status="ACTIVE",
    )
    db_session.add(enrollment)
    await db_session.flush()

    school_detail = SchoolEnrollmentDetail(
        tenant_id=tenant.id,
        enrollment_id=enrollment.id,
        class_id=school_class1.id,
        section_id=section1.id,
    )
    db_session.add(school_detail)
    await db_session.commit()

    admin_token = create_access_token(
        user_id=admin_user.id,
        email=admin_user.email,
        tenant_id=tenant.id,
        role="INSTITUTION_ADMIN",
        permissions=["timetable.manage", "timetable.view"],
    )
    teacher1_token = create_access_token(
        user_id=teacher1_user.id,
        email=teacher1_user.email,
        tenant_id=tenant.id,
        role="TEACHER",
        permissions=["timetable.view"],
    )
    teacher2_token = create_access_token(
        user_id=teacher2_user.id,
        email=teacher2_user.email,
        tenant_id=tenant.id,
        role="TEACHER",
        permissions=["timetable.view"],
    )
    student_token = create_access_token(
        user_id=student_user.id,
        email=student_user.email,
        tenant_id=tenant.id,
        role="STUDENT",
        permissions=["timetable.view"],
    )

    return {
        "tenant": tenant,
        "session": session,
        "class1": school_class1,
        "class2": school_class2,
        "section1": section1,
        "section2": section2,
        "subject1": subject1,
        "subject2": subject2,
        "teacher1": teacher1_profile,
        "teacher2": teacher2_profile,
        "student": student_profile,
        "admin_headers": {"Authorization": f"Bearer {admin_token}", "X-Tenant-Id": str(tenant.id)},
        "teacher1_headers": {"Authorization": f"Bearer {teacher1_token}", "X-Tenant-Id": str(tenant.id)},
        "teacher2_headers": {"Authorization": f"Bearer {teacher2_token}", "X-Tenant-Id": str(tenant.id)},
        "student_headers": {"Authorization": f"Bearer {student_token}", "X-Tenant-Id": str(tenant.id)},
    }


@pytest.mark.asyncio
async def test_settings_periods_and_holidays(client: AsyncClient, setup_timetable_data: dict):
    data = setup_timetable_data
    headers = data["admin_headers"]
    sess_id = str(data["session"].id)

    # 1. Configure Timetable Settings (Working Days & Period Durations)
    settings_payload = {
        "academic_session_id": sess_id,
        "working_days": ["MONDAY", "TUESDAY", "WEDNESDAY", "THURSDAY", "FRIDAY"],
        "periods_per_day": 7,
        "period_duration_minutes": 50,
        "break_duration_minutes": 15,
        "lunch_duration_minutes": 40,
        "school_start_time": "08:15",
    }
    set_res = await client.put("/api/v1/timetable/settings", json=settings_payload, headers=headers)
    assert set_res.status_code == 200
    assert set_res.json()["data"]["periods_per_day"] == 7
    assert set_res.json()["data"]["school_start_time"] == "08:15"

    # 2. Configure Period Definitions
    period_payload = {
        "academic_session_id": sess_id,
        "period_number": 1,
        "name": "Period 1 - Morning Lecture",
        "period_type": "ACADEMIC",
        "start_time": "08:30",
        "end_time": "09:20",
        "is_break": False,
    }
    period_res = await client.post("/api/v1/timetable/periods", json=period_payload, headers=headers)
    assert period_res.status_code == 201
    assert period_res.json()["data"]["name"] == "Period 1 - Morning Lecture"

    # List periods
    list_p = await client.get(f"/api/v1/timetable/periods?academic_session_id={sess_id}", headers=headers)
    assert list_p.status_code == 200
    assert len(list_p.json()["data"]) >= 1

    # 3. Add Institutional Holiday
    holiday_payload = {
        "academic_session_id": sess_id,
        "title": "National Science Day Celebration",
        "holiday_date": "2026-02-28",
        "holiday_type": "INSTITUTIONAL",
        "description": "Exhibition and special academic seminars.",
        "is_half_day": False,
    }
    hol_res = await client.post("/api/v1/timetable/holidays", json=holiday_payload, headers=headers)
    assert hol_res.status_code == 201
    assert hol_res.json()["data"]["title"] == "National Science Day Celebration"

    # List holidays
    list_h = await client.get(f"/api/v1/timetable/holidays?academic_session_id={sess_id}", headers=headers)
    assert list_h.status_code == 200
    assert len(list_h.json()["data"]) >= 1


@pytest.mark.asyncio
async def test_conflict_detection_engine(client: AsyncClient, setup_timetable_data: dict):
    data = setup_timetable_data
    headers = data["admin_headers"]
    sess_id = str(data["session"].id)

    # 1. Create a Timetable Schedule container
    sched_payload = {
        "name": "Term 1 Master Schedule 2026-27",
        "academic_session_id": sess_id,
        "institution_type": "SCHOOL",
        "effective_from": "2026-06-01",
        "effective_to": "2026-10-31",
        "description": "Standard school weekly lecture schedule.",
    }
    blocked = await client.post(
        "/api/v1/timetable/schedules", json={**sched_payload, "institution_type": "COLLEGE"}, headers=headers,
    )
    assert blocked.status_code == 400
    sched_res = await client.post("/api/v1/timetable/schedules", json=sched_payload, headers=headers)
    assert sched_res.status_code == 201
    schedule_id = sched_res.json()["data"]["id"]

    # 2. Create Entry 1: Teacher 1 teaches Physics in Grade 10 Section A on Monday 09:00 - 09:45 in Room 101
    entry1_payload = {
        "schedule_id": schedule_id,
        "academic_session_id": sess_id,
        "teacher_id": str(data["teacher1"].id),
        "subject_id": str(data["subject1"].id),
        "class_id": str(data["class1"].id),
        "section_id": str(data["section1"].id),
        "day_of_week": "MONDAY",
        "period_number": 1,
        "start_time": "09:00",
        "end_time": "09:45",
        "room_number": "Room 101",
        "entry_type": "THEORY",
        "is_practical": False,
    }
    e1_res = await client.post("/api/v1/timetable/entries", json=entry1_payload, headers=headers)
    assert e1_res.status_code == 201
    entry1_id = e1_res.json()["data"]["id"]

    # 3. Test Teacher Conflict: Attempting to assign Teacher 1 to Grade 11 on Monday 09:30 - 10:15 (overlapping 09:00-09:45)
    conflict_teacher_payload = {
        "schedule_id": schedule_id,
        "academic_session_id": sess_id,
        "teacher_id": str(data["teacher1"].id),
        "subject_id": str(data["subject1"].id),
        "class_id": str(data["class2"].id),
        "section_id": str(data["section2"].id),
        "day_of_week": "MONDAY",
        "period_number": 2,
        "start_time": "09:30",
        "end_time": "10:15",
        "room_number": "Room 202",
        "entry_type": "THEORY",
    }
    t_conf_res = await client.post("/api/v1/timetable/entries", json=conflict_teacher_payload, headers=headers)
    assert t_conf_res.status_code == 400
    assert "Scheduling conflict detected" in t_conf_res.json()["error"]["message"]
    assert "Isaac Newton" in t_conf_res.json()["error"]["message"]

    # 4. Test Classroom Conflict: Teacher 2 tries to use Room 101 on Monday 09:15 - 10:00 (overlapping 09:00-09:45)
    conflict_room_payload = {
        "schedule_id": schedule_id,
        "academic_session_id": sess_id,
        "teacher_id": str(data["teacher2"].id),
        "subject_id": str(data["subject2"].id),
        "class_id": str(data["class2"].id),
        "section_id": str(data["section2"].id),
        "day_of_week": "MONDAY",
        "period_number": 1,
        "start_time": "09:15",
        "end_time": "10:00",
        "room_number": "Room 101",  # Same room!
        "entry_type": "THEORY",
    }
    r_conf_res = await client.post("/api/v1/timetable/entries", json=conflict_room_payload, headers=headers)
    assert r_conf_res.status_code == 400
    assert "Room 101 is already occupied" in r_conf_res.json()["error"]["message"]

    # 5. Test Class Conflict: Scheduling another lecture for Grade 10 Section A on Monday 09:00 - 09:45
    conflict_class_payload = {
        "schedule_id": schedule_id,
        "academic_session_id": sess_id,
        "teacher_id": str(data["teacher2"].id),
        "subject_id": str(data["subject2"].id),
        "class_id": str(data["class1"].id),  # Same class!
        "section_id": str(data["section1"].id),  # Same section!
        "day_of_week": "MONDAY",
        "period_number": 1,
        "start_time": "09:00",
        "end_time": "09:45",
        "room_number": "Room 105",
        "entry_type": "THEORY",
    }
    c_conf_res = await client.post("/api/v1/timetable/entries", json=conflict_class_payload, headers=headers)
    assert c_conf_res.status_code == 400
    assert "already has a scheduled class" in c_conf_res.json()["error"]["message"]

    # 6. Check conflicts API endpoint directly
    check_res = await client.get(
        f"/api/v1/timetable/check-conflicts?day_of_week=MONDAY&start_time=09:15&end_time=10:00&teacher_id={data['teacher1'].id}",
        headers=headers,
    )
    assert check_res.status_code == 200
    assert check_res.json()["data"]["has_conflicts"] is True
    assert check_res.json()["data"]["total_conflicts"] >= 1

    # 7. Audit schedule conflicts before publishing
    audit_res = await client.get(f"/api/v1/timetable/schedules/{schedule_id}/conflicts", headers=headers)
    assert audit_res.status_code == 200
    assert audit_res.json()["data"]["has_conflicts"] is False  # Currently only 1 clean entry exists

    # 8. Publish the schedule
    pub_res = await client.post(f"/api/v1/timetable/schedules/{schedule_id}/publish", headers=headers)
    assert pub_res.status_code == 200
    assert pub_res.json()["data"]["status"] == "PUBLISHED"


@pytest.mark.asyncio
async def test_substitute_assignment_and_my_timetable(client: AsyncClient, setup_timetable_data: dict):
    data = setup_timetable_data
    admin_headers = data["admin_headers"]
    teacher1_headers = data["teacher1_headers"]
    teacher2_headers = data["teacher2_headers"]
    student_headers = data["student_headers"]
    sess_id = str(data["session"].id)

    # 1. Create a schedule and an entry for Teacher 1
    sched_res = await client.post(
        "/api/v1/timetable/schedules",
        json={
            "name": "Weekly Schedule",
            "academic_session_id": sess_id,
            "effective_from": "2026-06-01",
            "effective_to": "2026-12-31",
        },
        headers=admin_headers,
    )
    schedule_id = sched_res.json()["data"]["id"]

    entry_res = await client.post(
        "/api/v1/timetable/entries",
        json={
            "schedule_id": schedule_id,
            "academic_session_id": sess_id,
            "teacher_id": str(data["teacher1"].id),
            "subject_id": str(data["subject1"].id),
            "class_id": str(data["class1"].id),
            "section_id": str(data["section1"].id),
            "day_of_week": "WEDNESDAY",
            "period_number": 2,
            "start_time": "10:00",
            "end_time": "10:45",
            "room_number": "Lab 3",
            "entry_type": "PRACTICAL",
            "is_practical": True,
        },
        headers=admin_headers,
    )
    assert entry_res.status_code == 201
    entry_id = entry_res.json()["data"]["id"]

    # Publish schedule
    await client.post(f"/api/v1/timetable/schedules/{schedule_id}/publish", headers=admin_headers)

    # 2. Teacher 1 goes on leave. Assign Teacher 2 as substitute for next Wednesday
    next_wed = (date.today() + timedelta(days=(2 - date.today().weekday()) % 7)).isoformat()
    sub_payload = {
        "timetable_entry_id": entry_id,
        "assignment_date": next_wed,
        "substitute_teacher_id": str(data["teacher2"].id),
        "reason": "Teacher 1 attending academic conference.",
    }
    sub_res = await client.post("/api/v1/timetable/substitutes", json=sub_payload, headers=admin_headers)
    assert sub_res.status_code == 201
    sub_data = sub_res.json()["data"]
    assert sub_data["status"] == "ASSIGNED"
    assert sub_data["substitute_teacher_name"] == "Leonhard Euler"

    # 3. Test Teacher 1 My Timetable: views their weekly schedule
    t1_tt = await client.get("/api/v1/timetable/my-timetable", headers=teacher1_headers)
    assert t1_tt.status_code == 200
    t1_days = t1_tt.json()["data"]["days"]
    wed_day = next(d for d in t1_days if d["day_of_week"] == "WEDNESDAY")
    assert len(wed_day["entries"]) >= 1
    assert wed_day["entries"][0]["room_number"] == "Lab 3"

    # 4. Test Student My Timetable: student in Grade 10 Section A views their weekly schedule
    s_tt = await client.get("/api/v1/timetable/my-timetable", headers=student_headers)
    assert s_tt.status_code == 200
    s_days = s_tt.json()["data"]["days"]
    s_wed = next(d for d in s_days if d["day_of_week"] == "WEDNESDAY")
    assert len(s_wed["entries"]) >= 1
    assert s_wed["entries"][0]["subject_name"] == "Classical Physics"
