"""
Seed script to create clean, idempotent test demo credentials for all roles:
- Platform Super Admin
- Institution Admin (College - Apex Institute of Technology)
- Institution Admin (School - Greenwood High)
- Teacher / Faculty
- Student
- Parent
"""
import asyncio
import datetime
import uuid
from sqlalchemy import select, text
from sqlalchemy.orm import selectinload

from app.core.database import AsyncSessionLocal
from app.core.security import hash_password
from app.models.auth import Role, Permission, RolePermission, Membership
from app.models.enums import (
    InstitutionType,
    TenantStatus,
    MembershipStatus,
    RoleScope,
    SessionStatus,
    SubscriptionStatus,
    BillingCycle,
)
from app.models.tenant import Tenant
from app.models.user import User
from app.models.academic import (
    AcademicSession,
    Department,
    SchoolClass,
    Section,
    Subject,
    TeacherProfile,
    StudentProfile,
    StudentParent,
)

COMMON_PASSWORD = "Password123!"

async def seed_data():
    async with AsyncSessionLocal() as session:
        print("[1/6] Ensuring core roles exist...")
        role_codes = ["SUPER_ADMIN", "INSTITUTION_ADMIN", "TEACHER", "STUDENT", "PARENT"]
        role_map = {}
        for code in role_codes:
            stmt = select(Role).where(Role.code == code)
            r = (await session.execute(stmt)).scalars().first()
            if not r:
                r = Role(
                    name=code.replace("_", " ").title(),
                    code=code,
                    scope=RoleScope.PLATFORM if code == "SUPER_ADMIN" else RoleScope.TENANT,
                    is_system_role=True,
                )
                session.add(r)
                await session.flush()
            role_map[code] = r

        print("[2/6] Seeding or retrieving Institutions (Tenants)...")
        # 1. College Tenant
        stmt = select(Tenant).where(Tenant.slug == "apex-college")
        apex_tenant = (await session.execute(stmt)).scalars().first()
        if not apex_tenant:
            apex_tenant = Tenant(
                name="Apex Institute of Technology & Science",
                slug="apex-college",
                institution_type=InstitutionType.COLLEGE,
                status=TenantStatus.ACTIVE,
                email="contact@apex.edu",
                phone="+919876500001",
                city="Bangalore",
                state="Karnataka",
                country="India",
                timezone="Asia/Kolkata",
                currency="INR",
            )
            session.add(apex_tenant)
            await session.flush()

        # 2. School Tenant
        stmt = select(Tenant).where(Tenant.slug == "greenwood-school")
        greenwood_tenant = (await session.execute(stmt)).scalars().first()
        if not greenwood_tenant:
            greenwood_tenant = Tenant(
                name="Greenwood World School",
                slug="greenwood-school",
                institution_type=InstitutionType.SCHOOL,
                status=TenantStatus.ACTIVE,
                email="contact@greenwood.edu",
                phone="+919876500002",
                city="New Delhi",
                state="Delhi",
                country="India",
                timezone="Asia/Kolkata",
                currency="INR",
            )
            session.add(greenwood_tenant)
            await session.flush()

        print("[3/6] Seeding Academic Sessions and Structure for Apex College...")
        # Academic session
        stmt = select(AcademicSession).where(
            AcademicSession.tenant_id == apex_tenant.id,
            AcademicSession.code == "AY-2026-27"
        )
        academic_session = (await session.execute(stmt)).scalars().first()
        if not academic_session:
            academic_session = AcademicSession(
                tenant_id=apex_tenant.id,
                name="Academic Year 2026-2027",
                code="AY-2026-27",
                start_date=datetime.date(2026, 7, 1),
                end_date=datetime.date(2027, 6, 30),
                is_current=True,
                status=SessionStatus.ACTIVE,
            )
            session.add(academic_session)
            await session.flush()

        # Department
        stmt = select(Department).where(
            Department.tenant_id == apex_tenant.id,
            Department.code == "CSE"
        )
        cse_dept = (await session.execute(stmt)).scalars().first()
        if not cse_dept:
            cse_dept = Department(
                tenant_id=apex_tenant.id,
                name="Computer Science & Engineering",
                code="CSE",
            )
            session.add(cse_dept)
            await session.flush()

        # Class / Course
        stmt = select(SchoolClass).where(
            SchoolClass.tenant_id == apex_tenant.id,
            SchoolClass.name == "B.Tech Computer Science"
        )
        btech_class = (await session.execute(stmt)).scalars().first()
        if not btech_class:
            btech_class = SchoolClass(
                tenant_id=apex_tenant.id,
                name="B.Tech Computer Science",
                code="CS-SEM-5",
            )
            session.add(btech_class)
            await session.flush()

        # Section
        stmt = select(Section).where(
            Section.tenant_id == apex_tenant.id,
            Section.name == "Section A",
            Section.class_id == btech_class.id
        )
        section_a = (await session.execute(stmt)).scalars().first()
        if not section_a:
            section_a = Section(
                tenant_id=apex_tenant.id,
                class_id=btech_class.id,
                name="Section A",
                capacity=60,
            )
            session.add(section_a)
            await session.flush()

        print("[4/6] Creating or updating test users for all roles...")

        async def get_or_create_user(email, full_name, phone=None, is_superadmin=False):
            stmt = select(User).where(User.email == email)
            u = (await session.execute(stmt)).scalars().first()
            if not u:
                u = User(
                    email=email,
                    password_hash=hash_password(COMMON_PASSWORD),
                    full_name=full_name,
                    phone=phone,
                    is_active=True,
                    is_superadmin=is_superadmin,
                    email_verified_at=datetime.datetime.now(datetime.timezone.utc),
                )
                session.add(u)
                await session.flush()
            else:
                u.password_hash = hash_password(COMMON_PASSWORD)
                u.is_active = True
                u.is_superadmin = is_superadmin
                await session.flush()
            return u

        async def ensure_membership(user, tenant, role):
            stmt = select(Membership).where(
                Membership.user_id == user.id,
                Membership.tenant_id == tenant.id
            )
            m = (await session.execute(stmt)).scalars().first()
            if not m:
                m = Membership(
                    tenant_id=tenant.id,
                    user_id=user.id,
                    role_id=role.id,
                    status=MembershipStatus.ACTIVE,
                )
                session.add(m)
                await session.flush()
            else:
                m.role_id = role.id
                m.status = MembershipStatus.ACTIVE
                await session.flush()
            return m

        # 1. Super Admin
        super_admin = await get_or_create_user(
            email="superadmin@edusaas.com",
            full_name="Global Super Admin",
            phone="+919999000001",
            is_superadmin=True,
        )

        # 2. College Admin
        college_admin = await get_or_create_user(
            email="college.admin@apex.edu",
            full_name="Dr. Rajesh Sharma (College Director)",
            phone="+919999000002",
        )
        await ensure_membership(college_admin, apex_tenant, role_map["INSTITUTION_ADMIN"])

        # 3. School Admin
        school_admin = await get_or_create_user(
            email="school.admin@greenwood.edu",
            full_name="Principal Eleanor Vance",
            phone="+919999000003",
        )
        await ensure_membership(school_admin, greenwood_tenant, role_map["INSTITUTION_ADMIN"])

        # 4. Teacher / Faculty
        teacher_user = await get_or_create_user(
            email="teacher@apex.edu",
            full_name="Prof. Ananya Verma",
            phone="+919999000004",
        )
        await ensure_membership(teacher_user, apex_tenant, role_map["TEACHER"])

        # Check teacher profile
        stmt = select(TeacherProfile).where(
            TeacherProfile.tenant_id == apex_tenant.id,
            TeacherProfile.user_id == teacher_user.id
        )
        t_profile = (await session.execute(stmt)).scalars().first()
        if not t_profile:
            t_profile = TeacherProfile(
                tenant_id=apex_tenant.id,
                user_id=teacher_user.id,
                employee_id="FAC-CS-101",
                designation="Associate Professor",
                qualification="Ph.D Computer Science",
                specialization="Data Structures & Algorithms",
                experience_years=8,
                department_id=cse_dept.id,
                status="ACTIVE",
            )
            session.add(t_profile)
            await session.flush()

        # 5. Student
        student_user = await get_or_create_user(
            email="student@apex.edu",
            full_name="Aarav Patel",
            phone="+919999000005",
        )
        await ensure_membership(student_user, apex_tenant, role_map["STUDENT"])

        # Check student profile
        stmt = select(StudentProfile).where(
            StudentProfile.tenant_id == apex_tenant.id,
            StudentProfile.user_id == student_user.id
        )
        s_profile = (await session.execute(stmt)).scalars().first()
        if not s_profile:
            s_profile = StudentProfile(
                tenant_id=apex_tenant.id,
                user_id=student_user.id,
                admission_number="ADM-2026-101",
                roll_number="CS26-042",
                admission_date=datetime.date(2026, 7, 15),
                academic_session_id=academic_session.id,
                class_id=btech_class.id,
                section_id=section_a.id,
                department_id=cse_dept.id,
                gender="MALE",
                date_of_birth=datetime.date(2005, 4, 12),
                blood_group="O+",
                city="Bangalore",
                state="Karnataka",
                country="India",
                parent_name="Suresh Patel",
                parent_phone="+919999000006",
                parent_email="parent@apex.edu",
                status="ACTIVE",
            )
            session.add(s_profile)
            await session.flush()

        # 6. Parent
        parent_user = await get_or_create_user(
            email="parent@apex.edu",
            full_name="Suresh Patel",
            phone="+919999000006",
        )
        await ensure_membership(parent_user, apex_tenant, role_map["PARENT"])

        # Link parent to student
        stmt = select(StudentParent).where(
            StudentParent.tenant_id == apex_tenant.id,
            StudentParent.student_id == s_profile.id,
            StudentParent.parent_user_id == parent_user.id
        )
        sp_link = (await session.execute(stmt)).scalars().first()
        if not sp_link:
            sp_link = StudentParent(
                tenant_id=apex_tenant.id,
                student_id=s_profile.id,
                parent_user_id=parent_user.id,
                relation_type="FATHER",
                is_primary=True,
                can_view_grades=True,
                can_pay_fees=True,
                status="VERIFIED",
            )
            session.add(sp_link)
            await session.flush()

        await session.commit()
        print("[5/6] Database transaction committed successfully!")
        print("\n" + "="*60)
        print("SEEDING COMPLETE! ALL TEST CREDENTIALS READY:")
        print("="*60)
        print(f"Common Password for all accounts: {COMMON_PASSWORD}\n")
        print("1. SUPER ADMIN:")
        print("   Email: superadmin@edusaas.com")
        print("   Role:  SUPER_ADMIN (Platform-level)")
        print("\n2. COLLEGE ADMIN:")
        print("   Email: college.admin@apex.edu")
        print("   Institution: Apex Institute of Technology & Science (College)")
        print("   Role:  INSTITUTION_ADMIN")
        print("\n3. SCHOOL ADMIN:")
        print("   Email: school.admin@greenwood.edu")
        print("   Institution: Greenwood World School (School)")
        print("   Role:  INSTITUTION_ADMIN")
        print("\n4. TEACHER / FACULTY:")
        print("   Email: teacher@apex.edu")
        print("   Institution: Apex Institute of Technology & Science")
        print("   Role:  TEACHER")
        print("\n5. STUDENT:")
        print("   Email: student@apex.edu")
        print("   Institution: Apex Institute of Technology & Science")
        print("   Role:  STUDENT")
        print("\n6. PARENT:")
        print("   Email: parent@apex.edu")
        print("   Child: Aarav Patel (student@apex.edu)")
        print("   Institution: Apex Institute of Technology & Science")
        print("   Role:  PARENT")
        print("="*60)

if __name__ == "__main__":
    asyncio.run(seed_data())
