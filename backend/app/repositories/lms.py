from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.academic import (
    AcademicSession,
    CollegeSemester,
    Course,
    SchoolClass,
    SchoolEnrollmentDetail,
    Section,
    StudentAcademicEnrollment,
    StudentProfile,
    Subject,
)
from app.models.lms import (
    Assignment,
    AssignmentSubmission,
    StudyMaterial,
    StudyMaterialVersion,
)
from app.models.user import User


class LMSRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    # ─────────────────────────────────────────────────────────────────────────
    # 1. Study Materials
    # ─────────────────────────────────────────────────────────────────────────

    async def create_study_material(
        self,
        tenant_id: uuid.UUID,
        data: Dict[str, Any],
        uploaded_by: uuid.UUID,
        file_meta: Optional[Dict[str, Any]] = None,
    ) -> StudyMaterial:
        material = StudyMaterial(
            tenant_id=tenant_id,
            academic_session_id=data["academic_session_id"],
            subject_id=data.get("subject_id"),
            class_id=data.get("class_id"),
            section_id=data.get("section_id"),
            department_id=data.get("department_id"),
            course_id=data.get("course_id"),
            semester_id=data.get("semester_id"),
            batch_id=data.get("batch_id"),
            title=data["title"],
            description=data.get("description"),
            chapter=data.get("chapter"),
            material_type=data.get("material_type", "PDF"),
            category=data.get("category", "GENERAL"),
            external_url=data.get("external_url"),
            tags=data.get("tags", []),
            is_published=data.get("is_published", True),
            uploaded_by=uploaded_by,
        )

        if file_meta:
            material.file_key = file_meta.get("file_key")
            material.file_name = file_meta.get("file_name")
            material.file_size_bytes = file_meta.get("file_size_bytes")
            material.mime_type = file_meta.get("mime_type")

        self.session.add(material)
        await self.session.flush()

        # Add initial version 1 if file was uploaded
        if file_meta:
            initial_version = StudyMaterialVersion(
                tenant_id=tenant_id,
                material_id=material.id,
                version_number=1,
                file_key=file_meta.get("file_key"),
                file_name=file_meta.get("file_name"),
                file_size_bytes=file_meta.get("file_size_bytes"),
                mime_type=file_meta.get("mime_type"),
                change_summary="Initial upload",
                uploaded_by=uploaded_by,
            )
            self.session.add(initial_version)
            await self.session.flush()

        return material

    async def update_study_material(
        self,
        tenant_id: uuid.UUID,
        material_id: uuid.UUID,
        data: Dict[str, Any],
    ) -> StudyMaterial:
        stmt = select(StudyMaterial).where(
            StudyMaterial.tenant_id == tenant_id,
            StudyMaterial.id == material_id,
            StudyMaterial.is_deleted == False,
        )
        material = (await self.session.execute(stmt)).scalars().first()
        if not material:
            raise ValueError("Study material not found.")

        for key, value in data.items():
            if value is not None and hasattr(material, key):
                setattr(material, key, value)

        await self.session.flush()
        return material

    async def upload_new_material_version(
        self,
        tenant_id: uuid.UUID,
        material_id: uuid.UUID,
        file_meta: Dict[str, Any],
        change_summary: str,
        uploaded_by: uuid.UUID,
    ) -> StudyMaterial:
        stmt = select(StudyMaterial).where(
            StudyMaterial.tenant_id == tenant_id,
            StudyMaterial.id == material_id,
            StudyMaterial.is_deleted == False,
        )
        material = (await self.session.execute(stmt)).scalars().first()
        if not material:
            raise ValueError("Study material not found.")

        material.version += 1
        material.file_key = file_meta.get("file_key")
        material.file_name = file_meta.get("file_name")
        material.file_size_bytes = file_meta.get("file_size_bytes")
        material.mime_type = file_meta.get("mime_type")

        version_log = StudyMaterialVersion(
            tenant_id=tenant_id,
            material_id=material.id,
            version_number=material.version,
            file_key=file_meta.get("file_key"),
            file_name=file_meta.get("file_name"),
            file_size_bytes=file_meta.get("file_size_bytes"),
            mime_type=file_meta.get("mime_type"),
            change_summary=change_summary,
            uploaded_by=uploaded_by,
        )
        self.session.add(version_log)
        await self.session.flush()
        return material

    async def get_study_material(
        self, tenant_id: uuid.UUID, material_id: uuid.UUID
    ) -> Optional[StudyMaterial]:
        stmt = (
            select(StudyMaterial)
            .where(
                StudyMaterial.tenant_id == tenant_id,
                StudyMaterial.id == material_id,
                StudyMaterial.is_deleted == False,
            )
            .options(
                selectinload(StudyMaterial.uploader),
                selectinload(StudyMaterial.subject),
                selectinload(StudyMaterial.academic_session),
                selectinload(StudyMaterial.versions).selectinload(StudyMaterialVersion.uploader),
            )
        )
        return (await self.session.execute(stmt)).scalars().first()

    async def delete_study_material(self, tenant_id: uuid.UUID, material_id: uuid.UUID) -> bool:
        stmt = select(StudyMaterial).where(
            StudyMaterial.tenant_id == tenant_id,
            StudyMaterial.id == material_id,
            StudyMaterial.is_deleted == False,
        )
        material = (await self.session.execute(stmt)).scalars().first()
        if not material:
            return False
        material.is_deleted = True
        await self.session.flush()
        return True

    async def list_study_materials(
        self,
        tenant_id: uuid.UUID,
        academic_session_id: Optional[uuid.UUID] = None,
        subject_id: Optional[uuid.UUID] = None,
        class_id: Optional[uuid.UUID] = None,
        section_id: Optional[uuid.UUID] = None,
        category: Optional[str] = None,
        material_type: Optional[str] = None,
        search: Optional[str] = None,
        is_published: Optional[bool] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[List[StudyMaterial], int]:
        stmt = (
            select(StudyMaterial)
            .where(
                StudyMaterial.tenant_id == tenant_id,
                StudyMaterial.is_deleted == False,
            )
            .options(
                selectinload(StudyMaterial.uploader),
                selectinload(StudyMaterial.subject),
                selectinload(StudyMaterial.academic_session),
                selectinload(StudyMaterial.versions).selectinload(StudyMaterialVersion.uploader),
            )
        )

        if academic_session_id:
            stmt = stmt.where(StudyMaterial.academic_session_id == academic_session_id)
        if subject_id:
            stmt = stmt.where(StudyMaterial.subject_id == subject_id)
        if class_id:
            stmt = stmt.where(StudyMaterial.class_id == class_id)
        if section_id:
            stmt = stmt.where(or_(StudyMaterial.section_id == section_id, StudyMaterial.section_id.is_(None)))
        if category:
            stmt = stmt.where(StudyMaterial.category == category)
        if material_type:
            stmt = stmt.where(StudyMaterial.material_type == material_type)
        if is_published is not None:
            stmt = stmt.where(StudyMaterial.is_published == is_published)
        if search:
            q = f"%{search.strip()}%"
            stmt = stmt.where(
                or_(
                    StudyMaterial.title.ilike(q),
                    StudyMaterial.description.ilike(q),
                    StudyMaterial.chapter.ilike(q),
                )
            )

        # Count
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = (await self.session.execute(count_stmt)).scalar() or 0

        stmt = stmt.order_by(StudyMaterial.created_at.desc()).limit(limit).offset(offset)
        items = list((await self.session.execute(stmt)).scalars().all())
        return items, total

    async def increment_stats(
        self, tenant_id: uuid.UUID, material_id: uuid.UUID, is_download: bool = True
    ) -> None:
        stmt = select(StudyMaterial).where(
            StudyMaterial.tenant_id == tenant_id,
            StudyMaterial.id == material_id,
        )
        material = (await self.session.execute(stmt)).scalars().first()
        if material:
            if is_download:
                material.download_count += 1
            else:
                material.view_count += 1
            await self.session.flush()

    # ─────────────────────────────────────────────────────────────────────────
    # 2. Assignments
    # ─────────────────────────────────────────────────────────────────────────

    async def create_assignment(
        self,
        tenant_id: uuid.UUID,
        data: Dict[str, Any],
        created_by: uuid.UUID,
        instructions_file_meta: Optional[Dict[str, Any]] = None,
    ) -> Assignment:
        assignment = Assignment(
            tenant_id=tenant_id,
            academic_session_id=data["academic_session_id"],
            subject_id=data.get("subject_id"),
            class_id=data.get("class_id"),
            section_id=data.get("section_id"),
            course_id=data.get("course_id"),
            semester_id=data.get("semester_id"),
            title=data["title"],
            description=data["description"],
            due_datetime=data["due_datetime"],
            allow_late_submission=data.get("allow_late_submission", True),
            late_penalty_percent=data.get("late_penalty_percent", Decimal("0.00")),
            total_marks=data.get("total_marks", Decimal("100.00")),
            passing_marks=data.get("passing_marks", Decimal("40.00")),
            status=data.get("status", "PUBLISHED"),
            created_by=created_by,
        )

        if instructions_file_meta:
            assignment.instructions_file_key = instructions_file_meta.get("file_key")
            assignment.instructions_file_name = instructions_file_meta.get("file_name")
            assignment.instructions_file_size = instructions_file_meta.get("file_size_bytes")

        self.session.add(assignment)
        await self.session.flush()
        return assignment

    async def update_assignment(
        self,
        tenant_id: uuid.UUID,
        assignment_id: uuid.UUID,
        data: Dict[str, Any],
    ) -> Assignment:
        stmt = select(Assignment).where(
            Assignment.tenant_id == tenant_id,
            Assignment.id == assignment_id,
            Assignment.is_deleted == False,
        )
        assignment = (await self.session.execute(stmt)).scalars().first()
        if not assignment:
            raise ValueError("Assignment not found.")

        for key, value in data.items():
            if value is not None and hasattr(assignment, key):
                setattr(assignment, key, value)

        await self.session.flush()
        return assignment

    async def get_assignment(
        self, tenant_id: uuid.UUID, assignment_id: uuid.UUID
    ) -> Optional[Assignment]:
        stmt = (
            select(Assignment)
            .where(
                Assignment.tenant_id == tenant_id,
                Assignment.id == assignment_id,
                Assignment.is_deleted == False,
            )
            .options(
                selectinload(Assignment.creator),
                selectinload(Assignment.subject),
                selectinload(Assignment.academic_session),
                selectinload(Assignment.submissions),
            )
        )
        return (await self.session.execute(stmt)).scalars().first()

    async def list_assignments(
        self,
        tenant_id: uuid.UUID,
        academic_session_id: Optional[uuid.UUID] = None,
        subject_id: Optional[uuid.UUID] = None,
        class_id: Optional[uuid.UUID] = None,
        section_id: Optional[uuid.UUID] = None,
        status: Optional[str] = None,
        search: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[List[Assignment], int]:
        stmt = (
            select(Assignment)
            .where(
                Assignment.tenant_id == tenant_id,
                Assignment.is_deleted == False,
            )
            .options(
                selectinload(Assignment.creator),
                selectinload(Assignment.subject),
                selectinload(Assignment.academic_session),
                selectinload(Assignment.submissions),
            )
        )

        if academic_session_id:
            stmt = stmt.where(Assignment.academic_session_id == academic_session_id)
        if subject_id:
            stmt = stmt.where(Assignment.subject_id == subject_id)
        if class_id:
            stmt = stmt.where(Assignment.class_id == class_id)
        if section_id:
            stmt = stmt.where(or_(Assignment.section_id == section_id, Assignment.section_id.is_(None)))
        if status:
            stmt = stmt.where(Assignment.status == status)
        if search:
            q = f"%{search.strip()}%"
            stmt = stmt.where(
                or_(
                    Assignment.title.ilike(q),
                    Assignment.description.ilike(q),
                )
            )

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = (await self.session.execute(count_stmt)).scalar() or 0

        stmt = stmt.order_by(Assignment.due_datetime.desc()).limit(limit).offset(offset)
        items = list((await self.session.execute(stmt)).scalars().all())
        return items, total

    # ─────────────────────────────────────────────────────────────────────────
    # 3. Assignment Submissions & Evaluations
    # ─────────────────────────────────────────────────────────────────────────

    async def submit_assignment(
        self,
        tenant_id: uuid.UUID,
        assignment_id: uuid.UUID,
        student_id: uuid.UUID,
        submission_text: Optional[str] = None,
        attachment_file_meta: Optional[Dict[str, Any]] = None,
    ) -> AssignmentSubmission:
        # Check assignment exists and is open
        stmt = select(Assignment).where(
            Assignment.tenant_id == tenant_id,
            Assignment.id == assignment_id,
            Assignment.is_deleted == False,
        )
        assignment = (await self.session.execute(stmt)).scalars().first()
        if not assignment:
            raise ValueError("Assignment not found.")

        now = datetime.now(timezone.utc)
        is_late = now > assignment.due_datetime
        if is_late and not assignment.allow_late_submission:
            raise ValueError("Deadline has passed and late submissions are not allowed for this assignment.")

        # Check existing submission
        sub_stmt = select(AssignmentSubmission).where(
            AssignmentSubmission.tenant_id == tenant_id,
            AssignmentSubmission.assignment_id == assignment_id,
            AssignmentSubmission.student_id == student_id,
        )
        existing = (await self.session.execute(sub_stmt)).scalars().first()

        if existing:
            existing.submission_text = submission_text
            existing.submitted_at = now
            existing.is_late = is_late
            existing.status = "SUBMITTED"
            if attachment_file_meta:
                existing.attachment_file_key = attachment_file_meta.get("file_key")
                existing.attachment_file_name = attachment_file_meta.get("file_name")
                existing.attachment_file_size = attachment_file_meta.get("file_size_bytes")
            await self.session.flush()
            return existing

        submission = AssignmentSubmission(
            tenant_id=tenant_id,
            assignment_id=assignment_id,
            student_id=student_id,
            submission_text=submission_text,
            submitted_at=now,
            is_late=is_late,
            status="SUBMITTED",
        )
        if attachment_file_meta:
            submission.attachment_file_key = attachment_file_meta.get("file_key")
            submission.attachment_file_name = attachment_file_meta.get("file_name")
            submission.attachment_file_size = attachment_file_meta.get("file_size_bytes")

        self.session.add(submission)
        await self.session.flush()
        return submission

    async def get_submission(
        self, tenant_id: uuid.UUID, submission_id: uuid.UUID
    ) -> Optional[AssignmentSubmission]:
        stmt = (
            select(AssignmentSubmission)
            .where(
                AssignmentSubmission.tenant_id == tenant_id,
                AssignmentSubmission.id == submission_id,
            )
            .options(
                selectinload(AssignmentSubmission.assignment),
                selectinload(AssignmentSubmission.student).selectinload(StudentProfile.user),
                selectinload(AssignmentSubmission.evaluator),
            )
        )
        return (await self.session.execute(stmt)).scalars().first()

    async def get_student_submission(
        self, tenant_id: uuid.UUID, assignment_id: uuid.UUID, student_id: uuid.UUID
    ) -> Optional[AssignmentSubmission]:
        stmt = (
            select(AssignmentSubmission)
            .where(
                AssignmentSubmission.tenant_id == tenant_id,
                AssignmentSubmission.assignment_id == assignment_id,
                AssignmentSubmission.student_id == student_id,
            )
            .options(
                selectinload(AssignmentSubmission.assignment),
                selectinload(AssignmentSubmission.student).selectinload(StudentProfile.user),
                selectinload(AssignmentSubmission.evaluator),
            )
        )
        return (await self.session.execute(stmt)).scalars().first()

    async def list_submissions(
        self,
        tenant_id: uuid.UUID,
        assignment_id: uuid.UUID,
        status: Optional[str] = None,
    ) -> List[AssignmentSubmission]:
        stmt = (
            select(AssignmentSubmission)
            .where(
                AssignmentSubmission.tenant_id == tenant_id,
                AssignmentSubmission.assignment_id == assignment_id,
            )
            .options(
                selectinload(AssignmentSubmission.student).selectinload(StudentProfile.user),
                selectinload(AssignmentSubmission.evaluator),
            )
            .order_by(AssignmentSubmission.submitted_at.desc())
        )
        if status:
            stmt = stmt.where(AssignmentSubmission.status == status)

        return list((await self.session.execute(stmt)).scalars().all())

    async def evaluate_submission(
        self,
        tenant_id: uuid.UUID,
        submission_id: uuid.UUID,
        marks_obtained: Decimal,
        grade: Optional[str],
        teacher_feedback: Optional[str],
        evaluated_by: uuid.UUID,
        status: str = "EVALUATED",
    ) -> AssignmentSubmission:
        stmt = (
            select(AssignmentSubmission)
            .where(
                AssignmentSubmission.tenant_id == tenant_id,
                AssignmentSubmission.id == submission_id,
            )
            .options(
                selectinload(AssignmentSubmission.assignment),
                selectinload(AssignmentSubmission.student).selectinload(StudentProfile.user),
            )
        )
        sub = (await self.session.execute(stmt)).scalars().first()
        if not sub:
            raise ValueError("Assignment submission record not found.")

        # Apply late penalty if configured on assignment and submission was late
        final_marks = marks_obtained
        if sub.is_late and sub.assignment and sub.assignment.late_penalty_percent > Decimal("0.00"):
            penalty = (final_marks * sub.assignment.late_penalty_percent) / Decimal("100.00")
            final_marks = max(Decimal("0.00"), final_marks - penalty)

        sub.marks_obtained = final_marks
        sub.grade = grade
        sub.teacher_feedback = teacher_feedback
        sub.evaluated_by = evaluated_by
        sub.evaluated_at = datetime.now(timezone.utc)
        sub.status = status

        await self.session.flush()
        return sub

    async def get_assignment_report(
        self, tenant_id: uuid.UUID, assignment_id: uuid.UUID
    ) -> Dict[str, Any]:
        stmt = select(Assignment).where(Assignment.tenant_id == tenant_id, Assignment.id == assignment_id)
        assignment = (await self.session.execute(stmt)).scalars().first()
        if not assignment:
            raise ValueError("Assignment not found.")

        # Total assigned students (based on class enrollment)
        assigned_count = 0
        if assignment.class_id:
            enroll_stmt = select(func.count(SchoolEnrollmentDetail.id)).where(
                SchoolEnrollmentDetail.tenant_id == tenant_id,
                SchoolEnrollmentDetail.class_id == assignment.class_id,
            )
            assigned_count = (await self.session.execute(enroll_stmt)).scalar() or 0

        # Submissions aggregate
        sub_stmt = select(AssignmentSubmission).where(
            AssignmentSubmission.tenant_id == tenant_id,
            AssignmentSubmission.assignment_id == assignment_id,
        )
        submissions = list((await self.session.execute(sub_stmt)).scalars().all())

        total_submitted = len(submissions)
        total_evaluated = sum(1 for s in submissions if s.status == "EVALUATED" and s.marks_obtained is not None)
        total_pending = total_submitted - total_evaluated

        scores = [float(s.marks_obtained) for s in submissions if s.marks_obtained is not None]
        avg_score = round(sum(scores) / len(scores), 2) if scores else 0.0
        max_score = max(scores) if scores else 0.0
        min_score = min(scores) if scores else 0.0
        passed = sum(1 for s in submissions if s.marks_obtained is not None and s.marks_obtained >= assignment.passing_marks)
        pass_pct = round((passed / len(scores)) * 100, 2) if scores else 0.0

        if assigned_count < total_submitted:
            assigned_count = total_submitted

        sub_rate = round((total_submitted / assigned_count) * 100, 2) if assigned_count > 0 else 0.0

        return {
            "assignment_id": assignment_id,
            "assignment_title": assignment.title,
            "total_assigned": assigned_count,
            "total_submitted": total_submitted,
            "total_evaluated": total_evaluated,
            "total_pending": total_pending,
            "submission_rate_percent": sub_rate,
            "average_score": avg_score,
            "highest_score": max_score,
            "lowest_score": min_score,
            "pass_percentage": pass_pct,
        }
