from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppException, AuthorizationException
from app.models.academic import AcademicSession, CollegeSemester, Department, Section, Subject, TeacherAssignment, TeacherProfile
from app.models.auth import Membership, Role
from app.models.enums import MembershipStatus
from app.permissions.rbac import ACADEMIC_STAFF_ROLES
from app.repositories.teacher import TeacherRepository
from app.schemas.teacher import StaffAccessUpdate, TeacherResponse


@dataclass(frozen=True)
class StaffAccess:
    user_id: UUID
    role: str
    department_ids: tuple[UUID, ...] | None = None

    @property
    def is_admin(self) -> bool:
        return self.role in ("SUPER_ADMIN", "INSTITUTION_ADMIN")

    def can_view(self, teacher: TeacherResponse | TeacherProfile) -> bool:
        if self.is_admin or self.user_id == teacher.user_id or self.role == "PRINCIPAL":
            return True
        return self.role == "HOD" and teacher.department_id in (self.department_ids or ())


async def require_teaching_assignment(
    session: AsyncSession, tenant_id: UUID, teacher_user_id: UUID | None, academic_session_id: UUID,
    *, class_id: UUID | None = None, section_id: UUID | None = None, course_id: UUID | None = None,
    semester_id: UUID | None = None, subject_id: UUID | None = None,
) -> None:
    if teacher_user_id is None:
        return
    if class_id and course_id:
        raise AuthorizationException("Select either a school class or a college course.")
    for model, resource_id in ((AcademicSession, academic_session_id), (Subject, subject_id)):
        if resource_id is not None and not await session.scalar(
            select(model.id).where(model.id == resource_id, model.tenant_id == tenant_id, model.is_deleted.is_(False))
        ):
            raise AuthorizationException("Select academic resources in this institution.")
    if section_id:
        section = await session.scalar(select(Section).where(
            Section.id == section_id, Section.tenant_id == tenant_id, Section.is_deleted.is_(False),
        ))
        if section is None or (class_id and section.class_id != class_id) or (course_id and section.course_id != course_id):
            raise AuthorizationException("This section is outside the selected class or course.")
    semester = None
    if semester_id:
        semester = await session.scalar(select(CollegeSemester.semester_number).where(
            CollegeSemester.id == semester_id, CollegeSemester.tenant_id == tenant_id,
            CollegeSemester.course_id == course_id, CollegeSemester.is_deleted.is_(False),
        ))
        if semester is None:
            raise AuthorizationException("This semester is outside your assigned courses.")

    cohorts = [
        and_(TeacherAssignment.class_id.is_not(None), TeacherAssignment.class_id == class_id),
        and_(TeacherAssignment.course_id.is_not(None), TeacherAssignment.course_id == course_id),
        and_(TeacherAssignment.section_id.is_not(None), TeacherAssignment.section_id == section_id),
    ]
    query = (
        select(TeacherAssignment.id)
        .join(TeacherProfile, TeacherProfile.id == TeacherAssignment.teacher_id)
        .where(
            TeacherAssignment.tenant_id == tenant_id, TeacherAssignment.is_deleted.is_(False),
            TeacherProfile.tenant_id == tenant_id, TeacherProfile.user_id == teacher_user_id,
            TeacherProfile.status == "ACTIVE", TeacherProfile.is_deleted.is_(False),
            or_(*cohorts),
            or_(TeacherAssignment.class_id.is_(None), TeacherAssignment.class_id == class_id),
            or_(TeacherAssignment.course_id.is_(None), TeacherAssignment.course_id == course_id),
            or_(TeacherAssignment.section_id.is_(None), TeacherAssignment.section_id == section_id),
            or_(TeacherAssignment.semester.is_(None), TeacherAssignment.semester == semester),
            or_(TeacherAssignment.academic_session_id.is_(None), TeacherAssignment.academic_session_id == academic_session_id),
        )
    )
    if subject_id:
        query = query.where(or_(TeacherAssignment.subject_id.is_(None), TeacherAssignment.subject_id == subject_id))
    if not await session.scalar(query.limit(1)):
        raise AuthorizationException("This class, section, course, or subject is outside your teaching assignments.")


async def load_staff_access(
    session: AsyncSession, tenant_id: UUID, user_id: UUID, role: str
) -> StaffAccess:
    if role != "HOD":
        return StaffAccess(user_id, role)
    department_ids = await session.scalars(
        select(Department.id)
        .join(TeacherProfile, TeacherProfile.id == Department.hod_teacher_id)
        .where(
            Department.tenant_id == tenant_id,
            Department.is_deleted.is_(False),
            TeacherProfile.tenant_id == tenant_id,
            TeacherProfile.user_id == user_id,
            TeacherProfile.status == "ACTIVE",
            TeacherProfile.is_deleted.is_(False),
        )
    )
    return StaffAccess(user_id, role, tuple(department_ids))


def staff_role_query(tenant_id: UUID):
    return (
        select(Membership.user_id, Role.code)
        .join(Role, Role.id == Membership.role_id)
        .where(
            Membership.tenant_id == tenant_id,
            Membership.is_deleted.is_(False),
            Membership.status == MembershipStatus.ACTIVE,
        )
    )


async def assign_staff_access(
    session: AsyncSession, tenant_id: UUID, teacher_id: UUID, payload: StaffAccessUpdate, actor_id: UUID
) -> None:
    teacher = await session.scalar(
        select(TeacherProfile)
        .where(
            TeacherProfile.tenant_id == tenant_id,
            TeacherProfile.id == teacher_id,
            TeacherProfile.is_deleted.is_(False),
        )
        .with_for_update()
    )
    if not teacher:
        raise AppException(404, "TEACHER_NOT_FOUND", "Faculty member not found")
    result = await session.execute(
        select(Membership, Role.code)
        .join(Role, Role.id == Membership.role_id)
        .where(
            Membership.tenant_id == tenant_id,
            Membership.user_id == teacher.user_id,
            Membership.status == MembershipStatus.ACTIVE,
            Membership.is_deleted.is_(False),
        )
        .with_for_update(of=Membership)
    )
    membership = result.one_or_none()
    if not membership or membership[1] not in ACADEMIC_STAFF_ROLES:
        raise AuthorizationException("Only active academic staff memberships can be changed here.")
    current_membership, current_role = membership
    role_id = await session.scalar(
        select(Role.id).where(
            Role.code == payload.role,
            Role.tenant_id.is_(None),
            Role.is_system_role.is_(True),
        ).order_by(Role.id).limit(1)
    )
    if role_id is None:
        raise AppException(409, "ROLE_UNAVAILABLE", "This staff role is unavailable.")

    if payload.role == "HOD" and payload.department_id is None:
        raise AppException(422, "DEPARTMENT_REQUIRED", "Select a department for the HOD.")
    departments = list(await session.scalars(
        select(Department)
        .where(
            Department.tenant_id == tenant_id,
            Department.is_deleted.is_(False),
            or_(Department.hod_teacher_id == teacher.id, Department.id == payload.department_id),
        )
        .order_by(Department.id)
        .with_for_update()
    ))
    selected = next((department for department in departments if department.id == payload.department_id), None)
    if payload.department_id is not None and selected is None:
        raise AppException(422, "INVALID_DEPARTMENT", "Select a department in this institution.")
    if payload.role == "HOD" and selected is not None and selected.hod_teacher_id not in (None, teacher.id):
        raise AppException(409, "DEPARTMENT_HAS_HOD", "Transfer the current HOD before assigning a new one.")
    for department in departments:
        if department.hod_teacher_id == teacher.id:
            department.hod_teacher_id = None
    if selected is not None:
        teacher.department_id = selected.id
        if payload.role == "HOD":
            selected.hod_teacher_id = teacher.id
    current_membership.role_id = role_id

    await TeacherRepository(session).log_audit(
        tenant_id, actor_id, "STAFF_ACCESS_UPDATED", str(teacher.id),
        {"previous_role": current_role, "role": payload.role, "department_id": str(teacher.department_id) if teacher.department_id else None},
    )
