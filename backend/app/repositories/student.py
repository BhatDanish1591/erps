from __future__ import annotations

import csv
import io
import uuid
from datetime import date, datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import and_, desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import AppException
from app.core.logging import get_logger
from app.models.academic import (
    AcademicSession,
    Course,
    Department,
    SchoolClass,
    Section,
    StudentDocument,
    StudentEnrollmentHistory,
    StudentParent,
    StudentProfile,
    TeacherAssignment,
    TeacherProfile,
)
from app.models.audit import AuditLog
from app.models.auth import Membership, Role
from app.models.enums import MembershipStatus, RoleScope
from app.models.tenant import Tenant
from app.models.user import User

logger = get_logger(__name__)


def teacher_student_scope(tenant_id: uuid.UUID, teacher_user_id: uuid.UUID):
    return (
        select(TeacherAssignment.id)
        .join(TeacherProfile, TeacherProfile.id == TeacherAssignment.teacher_id)
        .where(
            TeacherProfile.tenant_id == tenant_id,
            TeacherProfile.user_id == teacher_user_id,
            TeacherProfile.is_deleted.is_(False),
            TeacherProfile.status == "ACTIVE",
            TeacherAssignment.tenant_id == tenant_id,
            TeacherAssignment.is_deleted.is_(False),
            or_(
                TeacherAssignment.class_id == StudentProfile.class_id,
                TeacherAssignment.course_id == StudentProfile.course_id,
                TeacherAssignment.section_id == StudentProfile.section_id,
            ),
            or_(TeacherAssignment.section_id.is_(None), TeacherAssignment.section_id == StudentProfile.section_id),
            or_(TeacherAssignment.semester.is_(None), TeacherAssignment.semester == StudentProfile.semester),
            or_(
                TeacherAssignment.academic_session_id.is_(None),
                TeacherAssignment.academic_session_id == StudentProfile.academic_session_id,
            ),
        )
        .exists()
    )


class StudentRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def generate_admission_number(self, tenant_id: uuid.UUID) -> str:
        """
        Generates next sequential admission number for tenant: e.g. ADM-2026-0001
        """
        year = datetime.now(timezone.utc).year
        prefix = f"ADM-{year}-"

        stmt = (
            select(StudentProfile.admission_number)
            .where(
                StudentProfile.tenant_id == tenant_id,
                StudentProfile.admission_number.like(f"{prefix}%"),
            )
        )
        res = await self.session.execute(stmt)
        all_numbers = res.scalars().all()

        max_seq = 0
        for num in all_numbers:
            suffix = num[len(prefix):]
            if suffix.isdigit():
                val = int(suffix)
                if val > max_seq:
                    max_seq = val

        next_seq = max_seq + 1
        return f"{prefix}{next_seq:04d}"

    async def get_student_by_id(
        self, tenant_id: uuid.UUID, student_id: uuid.UUID
    ) -> Optional[StudentProfile]:
        stmt = (
            select(StudentProfile)
            .options(
                selectinload(StudentProfile.user),
                selectinload(StudentProfile.academic_session),
                selectinload(StudentProfile.school_class),
                selectinload(StudentProfile.section),
                selectinload(StudentProfile.department),
                selectinload(StudentProfile.course),
                selectinload(StudentProfile.documents),
                selectinload(StudentProfile.enrollments).selectinload(StudentEnrollmentHistory.academic_session),
            )
            .where(
                StudentProfile.tenant_id == tenant_id,
                StudentProfile.id == student_id,
                StudentProfile.is_deleted == False,
            )
        )
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def get_student_by_admission_number(
        self, tenant_id: uuid.UUID, admission_number: str
    ) -> Optional[StudentProfile]:
        stmt = select(StudentProfile).where(
            StudentProfile.tenant_id == tenant_id,
            StudentProfile.admission_number == admission_number.strip(),
            StudentProfile.is_deleted == False,
        )
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def list_students(
        self,
        tenant_id: uuid.UUID,
        search: Optional[str] = None,
        class_id: Optional[uuid.UUID] = None,
        section_id: Optional[uuid.UUID] = None,
        department_id: Optional[uuid.UUID] = None,
        course_id: Optional[uuid.UUID] = None,
        semester: Optional[int] = None,
        academic_session_id: Optional[uuid.UUID] = None,
        status: Optional[str] = None,
        gender: Optional[str] = None,
        page: int = 1,
        size: int = 20,
        teacher_user_id: Optional[uuid.UUID] = None,
    ) -> Tuple[List[StudentProfile], int]:
        base_query = (
            select(StudentProfile)
            .join(StudentProfile.user)
            .options(
                selectinload(StudentProfile.user),
                selectinload(StudentProfile.academic_session),
                selectinload(StudentProfile.school_class),
                selectinload(StudentProfile.section),
                selectinload(StudentProfile.department),
                selectinload(StudentProfile.course),
            )
            .where(
                StudentProfile.tenant_id == tenant_id,
                StudentProfile.is_deleted == False,
            )
        )
        count_query = (
            select(func.count(StudentProfile.id))
            .join(StudentProfile.user)
            .where(
                StudentProfile.tenant_id == tenant_id,
                StudentProfile.is_deleted == False,
            )
        )

        if teacher_user_id is not None:
            teacher_scope = teacher_student_scope(tenant_id, teacher_user_id)
            base_query = base_query.where(teacher_scope)
            count_query = count_query.where(teacher_scope)

        if search:
            s = f"%{search.strip()}%"
            filter_cond = or_(
                User.full_name.ilike(s),
                User.email.ilike(s),
                StudentProfile.admission_number.ilike(s),
                StudentProfile.roll_number.ilike(s),
                StudentProfile.parent_phone.ilike(s),
            )
            base_query = base_query.where(filter_cond)
            count_query = count_query.where(filter_cond)

        if class_id:
            base_query = base_query.where(StudentProfile.class_id == class_id)
            count_query = count_query.where(StudentProfile.class_id == class_id)

        if section_id:
            base_query = base_query.where(StudentProfile.section_id == section_id)
            count_query = count_query.where(StudentProfile.section_id == section_id)

        if department_id:
            base_query = base_query.where(StudentProfile.department_id == department_id)
            count_query = count_query.where(StudentProfile.department_id == department_id)

        if course_id:
            base_query = base_query.where(StudentProfile.course_id == course_id)
            count_query = count_query.where(StudentProfile.course_id == course_id)

        if semester:
            base_query = base_query.where(StudentProfile.semester == semester)
            count_query = count_query.where(StudentProfile.semester == semester)

        if academic_session_id:
            base_query = base_query.where(StudentProfile.academic_session_id == academic_session_id)
            count_query = count_query.where(StudentProfile.academic_session_id == academic_session_id)

        if status:
            base_query = base_query.where(StudentProfile.status == status)
            count_query = count_query.where(StudentProfile.status == status)

        if gender:
            base_query = base_query.where(StudentProfile.gender == gender)
            count_query = count_query.where(StudentProfile.gender == gender)

        total = (await self.session.execute(count_query)).scalar() or 0
        paginated_query = (
            base_query.order_by(desc(StudentProfile.created_at))
            .offset((page - 1) * size)
            .limit(size)
        )
        result = await self.session.execute(paginated_query)
        return list(result.scalars().all()), total

    async def get_or_create_user_and_membership(
        self,
        tenant_id: uuid.UUID,
        email: str,
        full_name: str,
        phone: Optional[str],
        role_code: str = "STUDENT",
    ) -> Tuple[User, Membership]:
        # Check user
        user = (await self.session.execute(select(User).where(User.email == email.strip().lower()))).scalar_one_or_none()
        if not user:
            from app.core.security import hash_password
            user = User(
                email=email.strip().lower(),
                password_hash=hash_password(f"Edu@{uuid.uuid4().hex[:8]}!"),
                full_name=full_name.strip(),
                phone=phone,
                is_active=True,
                is_superadmin=False,
            )
            self.session.add(user)
            await self.session.flush()

        # Check role
        role = (await self.session.execute(select(Role).where(Role.code == role_code))).scalars().first()
        if not role:
            role = Role(name=role_code.replace("_", " ").title(), code=role_code, scope=RoleScope.TENANT, is_system_role=True)
            self.session.add(role)
            await self.session.flush()

        # Check membership
        membership = (await self.session.execute(
            select(Membership).where(
                Membership.user_id == user.id,
                Membership.tenant_id == tenant_id,
            )
        )).scalar_one_or_none()

        if not membership:
            membership = Membership(
                user_id=user.id,
                tenant_id=tenant_id,
                role_id=role.id,
                status=MembershipStatus.ACTIVE,
            )
            self.session.add(membership)
            await self.session.flush()

        return user, membership

    async def create_student(
        self,
        profile: StudentProfile,
        enrollment: Optional[StudentEnrollmentHistory] = None,
    ) -> StudentProfile:
        self.session.add(profile)
        await self.session.flush()
        if enrollment:
            enrollment.student_id = profile.id
            self.session.add(enrollment)
        return profile

    async def log_audit(
        self,
        tenant_id: uuid.UUID,
        user_id: Optional[uuid.UUID],
        action: str,
        entity_id: str,
        changes: Optional[dict] = None,
    ) -> None:
        log = AuditLog(
            tenant_id=tenant_id,
            user_id=user_id,
            action=action,
            entity_type="STUDENT",
            entity_id=entity_id,
            changes=changes or {},
        )
        self.session.add(log)
