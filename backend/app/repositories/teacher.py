from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import and_, desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.logging import get_logger
from app.models.academic import (
    AcademicSession,
    Course,
    Department,
    SchoolClass,
    Section,
    Subject,
    TeacherAssignment,
    TeacherAttendance,
    TeacherDocument,
    TeacherLeave,
    TeacherProfile,
    TimetableEntry,
)
from app.models.audit import AuditLog
from app.models.auth import Membership, Role
from app.models.enums import MembershipStatus, RoleScope
from app.models.tenant import Tenant
from app.models.user import User

logger = get_logger(__name__)


class TeacherRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def generate_employee_id(self, tenant_id: uuid.UUID) -> str:
        """
        Generates next sequential employee ID for tenant: e.g. EMP-2026-0001
        """
        year = datetime.now(timezone.utc).year
        prefix = f"EMP-{year}-"

        stmt = (
            select(TeacherProfile.employee_id)
            .where(
                TeacherProfile.tenant_id == tenant_id,
                TeacherProfile.employee_id.like(f"{prefix}%"),
            )
        )
        res = await self.session.execute(stmt)
        all_ids = res.scalars().all()

        max_seq = 0
        for emp_id in all_ids:
            suffix = emp_id[len(prefix):]
            if suffix.isdigit():
                val = int(suffix)
                if val > max_seq:
                    max_seq = val

        next_seq = max_seq + 1
        return f"{prefix}{next_seq:04d}"

    async def get_teacher_by_id(
        self, tenant_id: uuid.UUID, teacher_id: uuid.UUID
    ) -> Optional[TeacherProfile]:
        stmt = (
            select(TeacherProfile)
            .options(
                selectinload(TeacherProfile.user),
                selectinload(TeacherProfile.department),
                selectinload(TeacherProfile.assignments).selectinload(TeacherAssignment.school_class),
                selectinload(TeacherProfile.assignments).selectinload(TeacherAssignment.section),
                selectinload(TeacherProfile.assignments).selectinload(TeacherAssignment.department),
                selectinload(TeacherProfile.assignments).selectinload(TeacherAssignment.course),
                selectinload(TeacherProfile.assignments).selectinload(TeacherAssignment.subject),
                selectinload(TeacherProfile.timetable_entries).selectinload(TimetableEntry.subject),
                selectinload(TeacherProfile.timetable_entries).selectinload(TimetableEntry.school_class),
                selectinload(TeacherProfile.timetable_entries).selectinload(TimetableEntry.section),
                selectinload(TeacherProfile.attendances),
                selectinload(TeacherProfile.leaves),
                selectinload(TeacherProfile.documents),
            )
            .where(
                TeacherProfile.tenant_id == tenant_id,
                TeacherProfile.id == teacher_id,
                TeacherProfile.is_deleted == False,
            )
        )
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def get_teacher_by_user_id(
        self, tenant_id: uuid.UUID, user_id: uuid.UUID
    ) -> Optional[TeacherProfile]:
        stmt = (
            select(TeacherProfile)
            .options(
                selectinload(TeacherProfile.user),
                selectinload(TeacherProfile.department),
                selectinload(TeacherProfile.assignments).selectinload(TeacherAssignment.school_class),
                selectinload(TeacherProfile.assignments).selectinload(TeacherAssignment.section),
                selectinload(TeacherProfile.assignments).selectinload(TeacherAssignment.department),
                selectinload(TeacherProfile.assignments).selectinload(TeacherAssignment.course),
                selectinload(TeacherProfile.assignments).selectinload(TeacherAssignment.subject),
                selectinload(TeacherProfile.timetable_entries).selectinload(TimetableEntry.subject),
                selectinload(TeacherProfile.timetable_entries).selectinload(TimetableEntry.school_class),
                selectinload(TeacherProfile.timetable_entries).selectinload(TimetableEntry.section),
            )
            .where(
                TeacherProfile.tenant_id == tenant_id,
                TeacherProfile.user_id == user_id,
                TeacherProfile.is_deleted == False,
            )
        )
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def get_teacher_by_employee_id(
        self, tenant_id: uuid.UUID, employee_id: str
    ) -> Optional[TeacherProfile]:
        stmt = select(TeacherProfile).where(
            TeacherProfile.tenant_id == tenant_id,
            TeacherProfile.employee_id == employee_id.strip(),
            TeacherProfile.is_deleted == False,
        )
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def list_teachers(
        self,
        tenant_id: uuid.UUID,
        search: Optional[str] = None,
        department_id: Optional[uuid.UUID] = None,
        status: Optional[str] = None,
        employment_type: Optional[str] = None,
        page: int = 1,
        size: int = 20,
        allowed_departments: tuple[uuid.UUID, ...] | None = None,
    ) -> Tuple[List[TeacherProfile], int]:
        base_query = (
            select(TeacherProfile)
            .join(TeacherProfile.user)
            .options(
                selectinload(TeacherProfile.user),
                selectinload(TeacherProfile.department),
                selectinload(TeacherProfile.assignments).selectinload(TeacherAssignment.school_class),
                selectinload(TeacherProfile.assignments).selectinload(TeacherAssignment.section),
                selectinload(TeacherProfile.assignments).selectinload(TeacherAssignment.subject),
                selectinload(TeacherProfile.timetable_entries),
            )
            .where(
                TeacherProfile.tenant_id == tenant_id,
                TeacherProfile.is_deleted == False,
            )
        )
        count_query = (
            select(func.count(TeacherProfile.id))
            .join(TeacherProfile.user)
            .where(
                TeacherProfile.tenant_id == tenant_id,
                TeacherProfile.is_deleted == False,
            )
        )

        if search:
            s = f"%{search.strip()}%"
            filter_cond = or_(
                User.full_name.ilike(s),
                User.email.ilike(s),
                User.phone.ilike(s),
                TeacherProfile.employee_id.ilike(s),
                TeacherProfile.designation.ilike(s),
                TeacherProfile.specialization.ilike(s),
            )
            base_query = base_query.where(filter_cond)
            count_query = count_query.where(filter_cond)

        if department_id:
            base_query = base_query.where(TeacherProfile.department_id == department_id)
            count_query = count_query.where(TeacherProfile.department_id == department_id)

        if allowed_departments is not None:
            scope = TeacherProfile.department_id.in_(allowed_departments)
            base_query = base_query.where(scope)
            count_query = count_query.where(scope)

        if status:
            base_query = base_query.where(TeacherProfile.status == status)
            count_query = count_query.where(TeacherProfile.status == status)

        if employment_type:
            base_query = base_query.where(TeacherProfile.employment_type == employment_type)
            count_query = count_query.where(TeacherProfile.employment_type == employment_type)

        total = (await self.session.execute(count_query)).scalar() or 0
        paginated_query = (
            base_query.order_by(TeacherProfile.employee_id.asc())
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
        role_code: str = "TEACHER",
        initial_password: Optional[str] = None,
    ) -> Tuple[User, Membership]:
        user = (await self.session.execute(select(User).where(User.email == email.strip().lower()))).scalar_one_or_none()
        if not user:
            from app.core.security import hash_password
            user = User(
                email=email.strip().lower(),
                password_hash=hash_password(initial_password or f"Teacher@{uuid.uuid4().hex[:8]}!"),
                full_name=full_name.strip(),
                phone=phone,
                is_active=True,
                is_superadmin=False,
            )
            self.session.add(user)
            await self.session.flush()

        role = (await self.session.execute(select(Role).where(
            Role.code == role_code, Role.tenant_id.is_(None), Role.is_system_role.is_(True),
        ))).scalars().first()
        if not role:
            role = Role(name="Teacher", code=role_code, scope=RoleScope.TENANT, is_system_role=True)
            self.session.add(role)
            await self.session.flush()

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

    async def log_audit(
        self,
        tenant_id: uuid.UUID,
        user_id: Optional[uuid.UUID],
        action: str,
        entity_id: str,
        changes: Dict[str, Any],
    ) -> None:
        log = AuditLog(
            tenant_id=tenant_id,
            user_id=user_id,
            action=action,
            entity_type="TEACHER",
            entity_id=entity_id,
            changes=changes,
        )
        self.session.add(log)
