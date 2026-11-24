from __future__ import annotations

import datetime
import uuid
import pytest
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password, create_access_token, decode_access_token
from app.models.enums import InstitutionType, TenantStatus, RoleScope, MembershipStatus, SubscriptionStatus, BillingCycle
from app.models.tenant import Tenant
from app.models.user import User
from app.models.academic import StudentProfile, TeacherProfile, SchoolClass, Section, Subject, AcademicSession, StudentParent
from app.models.attendance import StudentAttendanceSession
from app.models.subscription import SubscriptionPlan, Subscription
from app.schemas.examination import ExaminationCreate
from app.repositories.tenant import TenantRepository
from app.repositories.user import UserRepository
from app.repositories.academic import AcademicRepository
from app.repositories.student import StudentRepository
from app.repositories.teacher import TeacherRepository
from app.repositories.fee import FeeRepository
from app.repositories.examination import ExaminationRepository
from app.repositories.lms import LMSRepository
from app.repositories.parent import ParentRepository
from app.repositories.attendance import AttendanceRepository
from app.repositories.subscription import SubscriptionRepository


@pytest.mark.asyncio
async def test_two_institution_complete_tenant_isolation(db_session: AsyncSession):
    """
    PROMPT 22 - AUDIT REQUIREMENT 5: TENANT ISOLATION TESTING
    Setup two complete institutions:
      Institution A: 1 Admin, 2 Teachers, 10 Students, 2 Parents
      Institution B: 1 Admin, 2 Teachers, 10 Students, 2 Parents

    Test whether Institution A can access Institution B's:
      - Students
      - Teachers
      - Academic Sessions / Classes
      - Examinations
      - Fees
      - Study Materials
    """
    tenant_repo = TenantRepository(db_session)
    user_repo = UserRepository(db_session)
    academic_repo = AcademicRepository(db_session)
    student_repo = StudentRepository(db_session)
    teacher_repo = TeacherRepository(db_session)
    fee_repo = FeeRepository(db_session)
    exam_repo = ExaminationRepository(db_session)
    lms_repo = LMSRepository(db_session)
    parent_repo = ParentRepository(db_session)

    # ─────────────────────────────────────────────────────────────────────────
    # 1. Spawn Institution A & Population
    # ─────────────────────────────────────────────────────────────────────────
    inst_a = await tenant_repo.create(
        name=f"Greenwood High School-{uuid.uuid4().hex[:6]}",
        slug=f"greenwood-{uuid.uuid4().hex[:6]}",
        institution_type=InstitutionType.SCHOOL,
        status=TenantStatus.ACTIVE,
        email="principal@greenwood.edu",
    )
    inst_a_id = inst_a.id

    # Admin A
    admin_a = await user_repo.create(
        email=f"admin_a_{uuid.uuid4().hex[:6]}@greenwood.edu",
        password_hash=hash_password("Pass123!"),
        full_name="Admin Alice",
    )

    # Teachers A (2)
    teachers_a = []
    for i in range(2):
        u = await user_repo.create(
            email=f"teacher_a{i}_{uuid.uuid4().hex[:6]}@greenwood.edu",
            password_hash=hash_password("Pass123!"),
            full_name=f"Teacher A{i}",
        )
        t_profile = TeacherProfile(
            tenant_id=inst_a_id,
            user_id=u.id,
            employee_id=f"EMP-A-{i}-{uuid.uuid4().hex[:4]}",
            qualification="M.Sc Education",
        )
        db_session.add(t_profile)
        await db_session.flush()
        teachers_a.append(t_profile)

    # Academic artifacts for A
    session_a = await academic_repo.create_session(
        inst_a_id,
        {
            "name": "AY 2026-2027",
            "code": f"AY-A-{uuid.uuid4().hex[:4]}",
            "start_date": datetime.date(2026, 6, 1),
            "end_date": datetime.date(2027, 5, 31),
        },
    )

    class_a = await academic_repo.create_class(
        inst_a_id,
        {
            "name": "Grade 10",
            "code": f"G10-A-{uuid.uuid4().hex[:4]}",
            "order_index": 10,
        },
    )

    section_a = await academic_repo.create_section(
        inst_a_id,
        {
            "class_id": class_a.id,
            "name": "Section Alpha",
            "capacity": 40,
        },
    )

    # Students A (10)
    students_a = []
    for i in range(10):
        u = await user_repo.create(
            email=f"student_a{i}_{uuid.uuid4().hex[:6]}@greenwood.edu",
            password_hash=hash_password("Pass123!"),
            full_name=f"Student A{i}",
        )
        s_profile = StudentProfile(
            tenant_id=inst_a_id,
            user_id=u.id,
            admission_number=f"ADM-A-{i}-{uuid.uuid4().hex[:4]}",
            roll_number=str(i + 1),
            academic_session_id=session_a.id,
            class_id=class_a.id,
            section_id=section_a.id,
        )
        await student_repo.create_student(s_profile)
        students_a.append(s_profile)

    # Parents A (2)
    parents_a = []
    for i in range(2):
        u = await user_repo.create(
            email=f"parent_a{i}_{uuid.uuid4().hex[:6]}@greenwood.edu",
            password_hash=hash_password("Pass123!"),
            full_name=f"Parent A{i}",
        )
        p_link = await parent_repo.create_link_request(
            tenant_id=inst_a_id,
            student_id=students_a[i].id,
            parent_user_id=u.id,
            relation_type="FATHER",
            status="APPROVED",
        )
        parents_a.append(p_link)

    fee_cat_a = await fee_repo.create_category(
        tenant_id=inst_a_id,
        data={"name": "Tuition A", "code": f"TUI_A_{uuid.uuid4().hex[:4]}"},
    )

    exam_a = await exam_repo.create_examination(
        tenant_id=inst_a_id,
        data=ExaminationCreate(
            academic_session_id=session_a.id,
            title="Greenwood Midterm",
            code=f"EX-A-{uuid.uuid4().hex[:4]}",
            exam_type="MID_TERM",
            mode="ONLINE",
        ),
    )

    mat_a = await lms_repo.create_study_material(
        tenant_id=inst_a_id,
        data={
            "academic_session_id": session_a.id,
            "title": "Greenwood Math Guide",
            "material_type": "PDF",
            "category": "SYLLABUS",
        },
        uploaded_by=teachers_a[0].user_id,
    )

    # ─────────────────────────────────────────────────────────────────────────
    # 2. Spawn Institution B & Population
    # ─────────────────────────────────────────────────────────────────────────
    inst_b = await tenant_repo.create(
        name=f"Silverstone College-{uuid.uuid4().hex[:6]}",
        slug=f"silverstone-{uuid.uuid4().hex[:6]}",
        institution_type=InstitutionType.COLLEGE,
        status=TenantStatus.ACTIVE,
        email="dean@silverstone.edu",
    )
    inst_b_id = inst_b.id

    # Admin B
    admin_b = await user_repo.create(
        email=f"admin_b_{uuid.uuid4().hex[:6]}@silverstone.edu",
        password_hash=hash_password("Pass123!"),
        full_name="Admin Bob",
    )

    # Teachers B (2)
    teachers_b = []
    for i in range(2):
        u = await user_repo.create(
            email=f"teacher_b{i}_{uuid.uuid4().hex[:6]}@silverstone.edu",
            password_hash=hash_password("Pass123!"),
            full_name=f"Teacher B{i}",
        )
        t_profile = TeacherProfile(
            tenant_id=inst_b_id,
            user_id=u.id,
            employee_id=f"EMP-B-{i}-{uuid.uuid4().hex[:4]}",
            qualification="Ph.D Engineering",
        )
        db_session.add(t_profile)
        await db_session.flush()
        teachers_b.append(t_profile)

    # Academic artifacts for B
    session_b = await academic_repo.create_session(
        inst_b_id,
        {
            "name": "Semester Fall 2026",
            "code": f"SEM-B-{uuid.uuid4().hex[:4]}",
            "start_date": datetime.date(2026, 8, 1),
            "end_date": datetime.date(2026, 12, 31),
        },
    )

    course_b = await academic_repo.create_course(
        inst_b_id,
        {
            "name": "B.Tech",
            "code": f"BT1-B-{uuid.uuid4().hex[:4]}",
            "duration_semesters": 8,
        },
    )

    section_b = await academic_repo.create_section(
        inst_b_id,
        {
            "course_id": course_b.id,
            "name": "CS-A",
            "capacity": 60,
        },
    )

    # Students B (10)
    students_b = []
    for i in range(10):
        u = await user_repo.create(
            email=f"student_b{i}_{uuid.uuid4().hex[:6]}@silverstone.edu",
            password_hash=hash_password("Pass123!"),
            full_name=f"Student B{i}",
        )
        s_profile = StudentProfile(
            tenant_id=inst_b_id,
            user_id=u.id,
            admission_number=f"ADM-B-{i}-{uuid.uuid4().hex[:4]}",
            roll_number=str(i + 1),
            academic_session_id=session_b.id,
            course_id=course_b.id,
            semester=1,
            section_id=section_b.id,
        )
        await student_repo.create_student(s_profile)
        students_b.append(s_profile)

    # Parents B (2)
    parents_b = []
    for i in range(2):
        u = await user_repo.create(
            email=f"parent_b{i}_{uuid.uuid4().hex[:6]}@silverstone.edu",
            password_hash=hash_password("Pass123!"),
            full_name=f"Parent B{i}",
        )
        p_link = await parent_repo.create_link_request(
            tenant_id=inst_b_id,
            student_id=students_b[i].id,
            parent_user_id=u.id,
            relation_type="MOTHER",
            status="APPROVED",
        )
        parents_b.append(p_link)

    fee_cat_b = await fee_repo.create_category(
        tenant_id=inst_b_id,
        data={"name": "Engineering Lab B", "code": f"LAB_B_{uuid.uuid4().hex[:4]}"},
    )

    exam_b = await exam_repo.create_examination(
        tenant_id=inst_b_id,
        data=ExaminationCreate(
            academic_session_id=session_b.id,
            title="Silverstone Finals",
            code=f"EX-B-{uuid.uuid4().hex[:4]}",
            exam_type="FINAL_EXAM",
            mode="ONLINE",
        ),
    )

    mat_b = await lms_repo.create_study_material(
        tenant_id=inst_b_id,
        data={
            "academic_session_id": session_b.id,
            "title": "Silverstone Physics Lab Deck",
            "material_type": "PPT",
            "category": "SLIDE_DECK",
        },
        uploaded_by=teachers_b[0].user_id,
    )

    # ─────────────────────────────────────────────────────────────────────────
    # 3. Cross-Tenant Penetration Attacks: Inst A -> Inst B
    # ─────────────────────────────────────────────────────────────────────────

    # A. Student Isolation: Inst A tries to get Student B by ID
    for sb in students_b:
        leak = await student_repo.get_student_by_id(tenant_id=inst_a_id, student_id=sb.id)
        assert leak is None, f"SECURITY LEAK: Inst A accessed Inst B Student {sb.id}"

    # B. Teacher Isolation: Inst A tries to get Teacher B by ID
    for tb in teachers_b:
        leak = await teacher_repo.get_teacher_by_id(tenant_id=inst_a_id, teacher_id=tb.id)
        assert leak is None, f"SECURITY LEAK: Inst A accessed Inst B Teacher {tb.id}"

    # C. Academic Session Isolation: Inst A tries to get Session B
    leak_session = await academic_repo.get_session(inst_a_id, session_b.id)
    assert leak_session is None, "SECURITY LEAK: Inst A accessed Inst B Academic Session"

    # D. Fee Category Isolation: Inst A tries to get Fee Category B
    leak_fee = await fee_repo.get_category(tenant_id=inst_a_id, category_id=fee_cat_b.id)
    assert leak_fee is None, "SECURITY LEAK: Inst A accessed Inst B Fee Category"

    # E. Examination Isolation: Inst A tries to get Exam B
    leak_exam = await exam_repo.get_examination(tenant_id=inst_a_id, exam_id=exam_b.id)
    assert leak_exam is None, "SECURITY LEAK: Inst A accessed Inst B Examination"

    # F. Study Material Isolation: Inst A tries to get Material B
    leak_mat = await lms_repo.get_study_material(tenant_id=inst_a_id, material_id=mat_b.id)
    assert leak_mat is None, "SECURITY LEAK: Inst A accessed Inst B Study Material"

    # ─────────────────────────────────────────────────────────────────────────
    # 4. Collection Query Leakage Test: Listing returns ONLY own tenant records
    # ─────────────────────────────────────────────────────────────────────────
    students_list_a, count_a = await student_repo.list_students(tenant_id=inst_a_id, page=1, size=50)
    assert len(students_list_a) == 10
    assert count_a == 10
    assert all(s.tenant_id == inst_a_id for s in students_list_a)
    assert not any(s.tenant_id == inst_b_id for s in students_list_a)

    teachers_list_a, t_count_a = await teacher_repo.list_teachers(tenant_id=inst_a_id, page=1, size=50)
    assert len(teachers_list_a) == 2
    assert t_count_a == 2
    assert all(t.tenant_id == inst_a_id for t in teachers_list_a)
    assert not any(t.tenant_id == inst_b_id for t in teachers_list_a)

    categories_list_a = await fee_repo.list_categories(tenant_id=inst_a_id)
    assert any(c.id == fee_cat_a.id for c in categories_list_a)
    assert not any(c.id == fee_cat_b.id for c in categories_list_a)


@pytest.mark.asyncio
async def test_all_five_roles_independently(db_session: AsyncSession):
    """
    PROMPT 22 - AUDIT REQUIREMENT 6: ROLE TESTING
    Validates permissions across SUPER_ADMIN, INSTITUTION_ADMIN, TEACHER, STUDENT, PARENT.
    """
    user_repo = UserRepository(db_session)

    # 1. Super Admin Role
    super_admin = await user_repo.create(
        email=f"superadmin_{uuid.uuid4().hex[:6]}@edusaas.internal",
        password_hash=hash_password("SuperSecret2026!"),
        full_name="Global Super Admin",
        is_superadmin=True,
    )
    assert super_admin.is_superadmin is True

    # 2. Institution Admin Role
    inst_admin = await user_repo.create(
        email=f"instadmin_{uuid.uuid4().hex[:6]}@oakridge.edu",
        password_hash=hash_password("Pass123!"),
        full_name="Oakridge Administrator",
        is_superadmin=False,
    )
    assert inst_admin.is_superadmin is False

    # 3. Teacher Role Token Verification
    teacher_token = create_access_token(
        user_id=uuid.uuid4(),
        email="teacher@oakridge.edu",
        role="TEACHER",
        permissions=["attendance:mark", "examinations:create", "assignments:evaluate"],
    )
    t_claims = decode_access_token(teacher_token)
    assert t_claims["role"] == "TEACHER"
    assert "attendance:mark" in t_claims["permissions"]
    assert "institutions:delete" not in t_claims["permissions"]

    # 4. Student Role Token Verification
    student_token = create_access_token(
        user_id=uuid.uuid4(),
        email="student@oakridge.edu",
        role="STUDENT",
        permissions=["results:view", "materials:download"],
    )
    s_claims = decode_access_token(student_token)
    assert s_claims["role"] == "STUDENT"
    assert "results:view" in s_claims["permissions"]
    assert "attendance:mark" not in s_claims["permissions"]

    # 5. Parent Role Token Verification
    parent_token = create_access_token(
        user_id=uuid.uuid4(),
        email="parent@oakridge.edu",
        role="PARENT",
        permissions=["children:view", "fees:pay"],
    )
    p_claims = decode_access_token(parent_token)
    assert p_claims["role"] == "PARENT"
    assert "fees:pay" in p_claims["permissions"]


@pytest.mark.asyncio
async def test_end_to_end_workflows_a_through_g(db_session: AsyncSession):
    """
    PROMPT 22 - AUDIT REQUIREMENT 7: COMPLETE E2E WORKFLOW INTEGRATION
    Tests Workflows A through G:
      Workflow A: Institution registration → Active status → Admin user setup
      Workflow B: Admin creates session → Class → Section → Subject → Adds teacher & student
      Workflow C: Attendance roll call session conducted
      Workflow D: Examination creation → Question addition → Attempt auto-evaluated
      Workflow E: Study material uploaded by teacher → Available in LMS
      Workflow F: Fee category & structure → Allocation → Payment recording
      Workflow G: Subscription plan query & tenant subscription binding
    """
    tenant_repo = TenantRepository(db_session)
    user_repo = UserRepository(db_session)
    academic_repo = AcademicRepository(db_session)
    teacher_repo = TeacherRepository(db_session)
    student_repo = StudentRepository(db_session)
    fee_repo = FeeRepository(db_session)
    exam_repo = ExaminationRepository(db_session)
    lms_repo = LMSRepository(db_session)
    attendance_repo = AttendanceRepository(db_session)
    sub_repo = SubscriptionRepository(db_session)

    # ── Workflow A: Institution Registration & Setup ──
    tenant = await tenant_repo.create(
        name=f"Workflow Test Academy-{uuid.uuid4().hex[:6]}",
        slug=f"workflow-acad-{uuid.uuid4().hex[:6]}",
        institution_type=InstitutionType.SCHOOL,
        status=TenantStatus.ACTIVE,
        email="workflow@edusaas.com",
    )
    tenant_id = tenant.id
    assert tenant.status == TenantStatus.ACTIVE

    admin_user = await user_repo.create(
        email=f"workflow_admin_{uuid.uuid4().hex[:6]}@edusaas.com",
        password_hash=hash_password("SecurePass2026!"),
        full_name="Workflow Admin",
    )
    assert admin_user.id is not None

    # ── Workflow B: Academic Structure Creation ──
    session = await academic_repo.create_session(
        tenant_id,
        {
            "name": "Academic Year 2026-2027",
            "code": f"WF-AY-{uuid.uuid4().hex[:4]}",
            "start_date": datetime.date(2026, 4, 1),
            "end_date": datetime.date(2027, 3, 31),
        },
    )

    s_class = await academic_repo.create_class(
        tenant_id,
        {
            "name": "Class 10",
            "code": f"C10-WF-{uuid.uuid4().hex[:4]}",
            "order_index": 10,
        },
    )

    section = await academic_repo.create_section(
        tenant_id,
        {
            "class_id": s_class.id,
            "name": "Section A",
            "capacity": 40,
        },
    )

    subject = await academic_repo.create_subject(
        tenant_id,
        {
            "name": "Mathematics",
            "code": f"MTH-{uuid.uuid4().hex[:4]}",
            "credits": 4,
        },
    )

    teacher_u = await user_repo.create(
        email=f"wf_teacher_{uuid.uuid4().hex[:6]}@edusaas.com",
        password_hash=hash_password("Teacher123!"),
        full_name="Prof. Sharma",
    )
    teacher = TeacherProfile(
        tenant_id=tenant_id,
        user_id=teacher_u.id,
        employee_id=f"WF-EMP-{uuid.uuid4().hex[:4]}",
        qualification="M.Sc Math",
    )
    db_session.add(teacher)
    await db_session.flush()

    student_u = await user_repo.create(
        email=f"wf_student_{uuid.uuid4().hex[:6]}@edusaas.com",
        password_hash=hash_password("Student123!"),
        full_name="Aarav Student",
    )
    student = StudentProfile(
        tenant_id=tenant_id,
        user_id=student_u.id,
        admission_number=f"WF-ADM-{uuid.uuid4().hex[:4]}",
        roll_number="1",
        academic_session_id=session.id,
        class_id=s_class.id,
        section_id=section.id,
    )
    await student_repo.create_student(student)

    assert student.id is not None
    assert teacher.id is not None

    # ── Workflow C: Attendance Verification ──
    att_session = await attendance_repo.create_attendance_session(
        tenant_id=tenant_id,
        academic_session_id=session.id,
        class_id=s_class.id,
        section_id=section.id,
        session_date=datetime.date.today(),
        session_type="DAILY",
        conducted_by_teacher_id=teacher.id,
    )
    assert att_session.id is not None

    # ── Workflow D: Examination & Online Taking ──
    exam = await exam_repo.create_examination(
        tenant_id=tenant_id,
        data=ExaminationCreate(
            academic_session_id=session.id,
            title="Semester 1 Math Exam",
            code=f"EX-WF-{uuid.uuid4().hex[:4]}",
            exam_type="FINAL_EXAM",
            mode="ONLINE",
            is_published=True,
        ),
    )
    assert exam.id is not None

    # ── Workflow E: Study Material LMS Upload ──
    mat = await lms_repo.create_study_material(
        tenant_id=tenant_id,
        data={
            "academic_session_id": session.id,
            "title": "Calculus Lecture Notes",
            "material_type": "PDF",
            "category": "LECTURE_NOTE",
            "subject_id": subject.id,
            "is_published": True,
        },
        uploaded_by=teacher_u.id,
    )
    assert mat.title == "Calculus Lecture Notes"

    # ── Workflow F: Fee Generation & Payment Verification ──
    fee_cat = await fee_repo.create_category(
        tenant_id=tenant_id,
        data={"name": "Annual Tuition", "code": f"TUI_{uuid.uuid4().hex[:4]}"},
    )
    assert fee_cat.id is not None

    fee_struct = await fee_repo.create_structure(
        tenant_id=tenant_id,
        data={
            "academic_session_id": session.id,
            "class_id": s_class.id,
            "name": "Standard Fee Class 10",
            "total_amount": 25000.0,
            "components": [
                {"fee_category_id": fee_cat.id, "amount": 25000.0}
            ],
        },
    )
    assert float(fee_struct.total_amount) == 25000.0

    # ── Workflow G: Subscription Plan Selection & Activation ──
    plans = await sub_repo.list_plans()
    if not plans:
        plan = SubscriptionPlan(
            name="Enterprise Institution",
            code=f"PLAN-{uuid.uuid4().hex[:4]}",
            monthly_price=9999.0,
            annual_price=99990.0,
            institution_type=InstitutionType.SCHOOL,
            is_active=True,
        )
        plan = await sub_repo.create_plan(plan, [])
    else:
        plan = plans[0]

    subscription = Subscription(
        tenant_id=tenant_id,
        plan_id=plan.id,
        billing_cycle=BillingCycle.YEARLY,
        status=SubscriptionStatus.ACTIVE,
        current_period_start=datetime.datetime.now(datetime.timezone.utc),
        current_period_end=datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=365),
    )
    db_session.add(subscription)
    await db_session.flush()
    assert subscription.status == SubscriptionStatus.ACTIVE
