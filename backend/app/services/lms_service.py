from __future__ import annotations

import uuid
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BadRequestException, NotFoundException, AuthorizationException
from app.core.logging import get_logger
from app.models.academic import StudentProfile
from app.models.lms import Assignment, AssignmentSubmission, StudyMaterial
from app.repositories.lms import LMSRepository
from app.schemas.lms import (
    AssignmentReportResponse,
    AssignmentResponse,
    AssignmentSubmissionResponse,
    StudyMaterialResponse,
    StudyMaterialVersionResponse,
)
from app.utils.storage import storage_service

logger = get_logger(__name__)


class LMSService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = LMSRepository(session)

    # ─────────────────────────────────────────────────────────────────────────
    # 1. Study Materials
    # ─────────────────────────────────────────────────────────────────────────

    async def create_study_material(
        self,
        tenant_id: uuid.UUID,
        data: Dict[str, Any],
        uploaded_by: uuid.UUID,
        file_bytes: Optional[bytes] = None,
        file_name: Optional[str] = None,
        content_type: Optional[str] = None,
    ) -> StudyMaterialResponse:
        file_meta = None
        if file_bytes and file_name:
            storage_service.validate_file(
                file_name=file_name,
                content_type=content_type,
                file_size_bytes=len(file_bytes),
            )
            storage_key = storage_service.build_storage_key(tenant_id, "materials", file_name)
            storage_service.upload_file_bytes(file_bytes, storage_key, content_type or "application/octet-stream")
            file_meta = {
                "file_key": storage_key,
                "file_name": file_name,
                "file_size_bytes": len(file_bytes),
                "mime_type": content_type or "application/octet-stream",
            }

        material = await self.repo.create_study_material(
            tenant_id=tenant_id,
            data=data,
            uploaded_by=uploaded_by,
            file_meta=file_meta,
        )
        detailed = await self.repo.get_study_material(tenant_id, material.id)
        if not detailed:
            raise NotFoundException("Study material not found.")
        return self._format_material_response(detailed)

    async def update_study_material(
        self,
        tenant_id: uuid.UUID,
        material_id: uuid.UUID,
        data: Dict[str, Any],
    ) -> StudyMaterialResponse:
        material = await self.repo.update_study_material(tenant_id, material_id, data)
        # Fetch fresh with relations
        detailed = await self.repo.get_study_material(tenant_id, material.id)
        if not detailed:
            raise NotFoundException("Study material not found.")
        return self._format_material_response(detailed)

    async def upload_material_version(
        self,
        tenant_id: uuid.UUID,
        material_id: uuid.UUID,
        change_summary: str,
        uploaded_by: uuid.UUID,
        file_bytes: bytes,
        file_name: str,
        content_type: Optional[str] = None,
    ) -> StudyMaterialResponse:
        storage_service.validate_file(
            file_name=file_name,
            content_type=content_type,
            file_size_bytes=len(file_bytes),
        )
        storage_key = storage_service.build_storage_key(tenant_id, "materials", file_name)
        storage_service.upload_file_bytes(file_bytes, storage_key, content_type or "application/octet-stream")
        file_meta = {
            "file_key": storage_key,
            "file_name": file_name,
            "file_size_bytes": len(file_bytes),
            "mime_type": content_type or "application/octet-stream",
        }

        await self.repo.upload_new_material_version(
            tenant_id=tenant_id,
            material_id=material_id,
            file_meta=file_meta,
            change_summary=change_summary,
            uploaded_by=uploaded_by,
        )
        detailed = await self.repo.get_study_material(tenant_id, material_id)
        if not detailed:
            raise NotFoundException("Study material not found.")
        return self._format_material_response(detailed)

    async def get_study_material(
        self, tenant_id: uuid.UUID, material_id: uuid.UUID, track_view: bool = True
    ) -> StudyMaterialResponse:
        material = await self.repo.get_study_material(tenant_id, material_id)
        if not material:
            raise NotFoundException("Study material not found.")
        response = self._format_material_response(material)
        if track_view:
            response.view_count += 1
            material.view_count += 1
            await self.session.flush()
        return response

    async def get_download_url(
        self, tenant_id: uuid.UUID, material_id: uuid.UUID
    ) -> Dict[str, str]:
        material = await self.repo.get_study_material(tenant_id, material_id)
        if not material:
            raise NotFoundException("Study material not found.")
        if not material.file_key:
            if material.external_url:
                return {"url": material.external_url, "type": "external"}
            raise BadRequestException("This study material does not have an attached file.")

        material.download_count += 1
        await self.session.flush()
        url = storage_service.generate_signed_url(
            storage_key=material.file_key,
            original_filename=material.file_name,
            expires_in=3600,
            for_download=True,
        )
        return {"url": url, "type": "signed_url", "filename": material.file_name or "download"}

    async def delete_study_material(self, tenant_id: uuid.UUID, material_id: uuid.UUID) -> bool:
        material = await self.repo.get_study_material(tenant_id, material_id)
        if not material:
            raise NotFoundException("Study material not found.")
        if material.file_key:
            storage_service.delete_file(material.file_key)
        return await self.repo.delete_study_material(tenant_id, material_id)

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
    ) -> Tuple[List[StudyMaterialResponse], int]:
        items, total = await self.repo.list_study_materials(
            tenant_id=tenant_id,
            academic_session_id=academic_session_id,
            subject_id=subject_id,
            class_id=class_id,
            section_id=section_id,
            category=category,
            material_type=material_type,
            search=search,
            is_published=is_published,
            limit=limit,
            offset=offset,
        )
        responses = [self._format_material_response(m) for m in items]
        return responses, total

    def _format_material_response(self, material: StudyMaterial) -> StudyMaterialResponse:
        download_url = None
        preview_url = None
        if material.file_key:
            download_url = storage_service.generate_signed_url(
                material.file_key, original_filename=material.file_name, expires_in=7200, for_download=True
            )
            preview_url = storage_service.generate_signed_url(
                material.file_key, original_filename=material.file_name, expires_in=7200, for_download=False
            )
        elif material.external_url:
            download_url = material.external_url
            preview_url = material.external_url

        uploader_name = material.uploader.full_name if material.uploader else None

        subject_name = material.subject.name if material.subject else None
        subject_code = material.subject.code if material.subject else None
        session_name = material.academic_session.name if material.academic_session else None

        versions_resp = []
        if material.versions:
            for v in material.versions:
                v_up_name = v.uploader.full_name if v.uploader else None
                versions_resp.append(
                    StudyMaterialVersionResponse(
                        id=v.id,
                        material_id=v.material_id,
                        version_number=v.version_number,
                        file_name=v.file_name,
                        file_size_bytes=v.file_size_bytes,
                        mime_type=v.mime_type,
                        change_summary=v.change_summary,
                        uploader_name=v_up_name,
                        created_at=v.created_at,
                    )
                )

        return StudyMaterialResponse(
            id=material.id,
            tenant_id=material.tenant_id,
            academic_session_id=material.academic_session_id,
            academic_session_name=session_name,
            subject_id=material.subject_id,
            subject_name=subject_name,
            subject_code=subject_code,
            class_id=material.class_id,
            class_name=None,
            section_id=material.section_id,
            section_name=None,
            department_id=material.department_id,
            course_id=material.course_id,
            semester_id=material.semester_id,
            batch_id=material.batch_id,
            title=material.title,
            description=material.description,
            chapter=material.chapter,
            material_type=material.material_type,
            category=material.category,
            external_url=material.external_url,
            tags=material.tags or [],
            is_published=material.is_published,
            file_key=material.file_key,
            file_name=material.file_name,
            file_size_bytes=material.file_size_bytes,
            mime_type=material.mime_type,
            download_url=download_url,
            preview_url=preview_url,
            version=material.version,
            download_count=material.download_count,
            view_count=material.view_count,
            uploaded_by=material.uploaded_by,
            uploader_name=uploader_name,
            created_at=material.created_at,
            updated_at=material.updated_at,
            versions=versions_resp,
        )

    # ─────────────────────────────────────────────────────────────────────────
    # 2. Assignments
    # ─────────────────────────────────────────────────────────────────────────

    async def create_assignment(
        self,
        tenant_id: uuid.UUID,
        data: Dict[str, Any],
        created_by: uuid.UUID,
        instructions_bytes: Optional[bytes] = None,
        instructions_filename: Optional[str] = None,
        content_type: Optional[str] = None,
    ) -> AssignmentResponse:
        instructions_meta = None
        if instructions_bytes and instructions_filename:
            storage_service.validate_file(
                file_name=instructions_filename,
                content_type=content_type,
                file_size_bytes=len(instructions_bytes),
            )
            storage_key = storage_service.build_storage_key(tenant_id, "assignments", instructions_filename)
            storage_service.upload_file_bytes(instructions_bytes, storage_key, content_type or "application/octet-stream")
            instructions_meta = {
                "file_key": storage_key,
                "file_name": instructions_filename,
                "file_size_bytes": len(instructions_bytes),
            }

        assignment = await self.repo.create_assignment(
            tenant_id=tenant_id,
            data=data,
            created_by=created_by,
            instructions_file_meta=instructions_meta,
        )
        detailed = await self.repo.get_assignment(tenant_id, assignment.id)
        if not detailed:
            raise NotFoundException("Assignment not found.")
        return self._format_assignment_response(detailed)

    async def update_assignment(
        self,
        tenant_id: uuid.UUID,
        assignment_id: uuid.UUID,
        data: Dict[str, Any],
    ) -> AssignmentResponse:
        await self.repo.update_assignment(tenant_id, assignment_id, data)
        detailed = await self.repo.get_assignment(tenant_id, assignment_id)
        if not detailed:
            raise NotFoundException("Assignment not found.")
        return self._format_assignment_response(detailed)

    async def get_assignment(self, tenant_id: uuid.UUID, assignment_id: uuid.UUID) -> AssignmentResponse:
        assignment = await self.repo.get_assignment(tenant_id, assignment_id)
        if not assignment:
            raise NotFoundException("Assignment not found.")
        return self._format_assignment_response(assignment)

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
    ) -> Tuple[List[AssignmentResponse], int]:
        items, total = await self.repo.list_assignments(
            tenant_id=tenant_id,
            academic_session_id=academic_session_id,
            subject_id=subject_id,
            class_id=class_id,
            section_id=section_id,
            status=status,
            search=search,
            limit=limit,
            offset=offset,
        )
        responses = [self._format_assignment_response(a) for a in items]
        return responses, total

    def _format_assignment_response(self, assignment: Assignment) -> AssignmentResponse:
        download_url = None
        if assignment.instructions_file_key:
            download_url = storage_service.generate_signed_url(
                assignment.instructions_file_key,
                original_filename=assignment.instructions_file_name,
                expires_in=7200,
                for_download=True,
            )

        creator_name = assignment.creator.full_name if assignment.creator else None

        subject_name = assignment.subject.name if assignment.subject else None
        subject_code = assignment.subject.code if assignment.subject else None
        session_name = assignment.academic_session.name if assignment.academic_session else None

        submissions = assignment.submissions or []
        sub_count = len(submissions)
        eval_count = sum(1 for s in submissions if s.status == "EVALUATED")
        pending_count = sub_count - eval_count

        return AssignmentResponse(
            id=assignment.id,
            tenant_id=assignment.tenant_id,
            academic_session_id=assignment.academic_session_id,
            academic_session_name=session_name,
            subject_id=assignment.subject_id,
            subject_name=subject_name,
            subject_code=subject_code,
            class_id=assignment.class_id,
            class_name=None,
            section_id=assignment.section_id,
            section_name=None,
            course_id=assignment.course_id,
            semester_id=assignment.semester_id,
            title=assignment.title,
            description=assignment.description,
            due_datetime=assignment.due_datetime,
            allow_late_submission=assignment.allow_late_submission,
            late_penalty_percent=assignment.late_penalty_percent,
            total_marks=assignment.total_marks,
            passing_marks=assignment.passing_marks,
            status=assignment.status,
            instructions_file_key=assignment.instructions_file_key,
            instructions_file_name=assignment.instructions_file_name,
            instructions_file_size=assignment.instructions_file_size,
            instructions_download_url=download_url,
            created_by=assignment.created_by,
            creator_name=creator_name,
            submissions_count=sub_count,
            evaluated_count=eval_count,
            pending_count=pending_count,
            created_at=assignment.created_at,
            updated_at=assignment.updated_at,
        )

    # ─────────────────────────────────────────────────────────────────────────
    # 3. Submissions & Evaluations
    # ─────────────────────────────────────────────────────────────────────────

    async def get_student_profile_by_user(
        self, tenant_id: uuid.UUID, user_id: uuid.UUID
    ) -> Optional[StudentProfile]:
        stmt = select(StudentProfile).where(
            StudentProfile.tenant_id == tenant_id,
            StudentProfile.user_id == user_id,
            StudentProfile.is_deleted == False,
        )
        return (await self.session.execute(stmt)).scalars().first()

    async def submit_assignment(
        self,
        tenant_id: uuid.UUID,
        assignment_id: uuid.UUID,
        student_id: uuid.UUID,
        submission_text: Optional[str] = None,
        file_bytes: Optional[bytes] = None,
        file_name: Optional[str] = None,
        content_type: Optional[str] = None,
    ) -> AssignmentSubmissionResponse:
        file_meta = None
        if file_bytes and file_name:
            storage_service.validate_file(
                file_name=file_name,
                content_type=content_type,
                file_size_bytes=len(file_bytes),
            )
            storage_key = storage_service.build_storage_key(tenant_id, "submissions", file_name)
            storage_service.upload_file_bytes(file_bytes, storage_key, content_type or "application/octet-stream")
            file_meta = {
                "file_key": storage_key,
                "file_name": file_name,
                "file_size_bytes": len(file_bytes),
            }

        submission = await self.repo.submit_assignment(
            tenant_id=tenant_id,
            assignment_id=assignment_id,
            student_id=student_id,
            submission_text=submission_text,
            attachment_file_meta=file_meta,
        )
        detailed = await self.repo.get_submission(tenant_id, submission.id)
        if not detailed:
            raise NotFoundException("Submission not found.")
        return self._format_submission_response(detailed)

    async def evaluate_submission(
        self,
        tenant_id: uuid.UUID,
        submission_id: uuid.UUID,
        marks_obtained: Decimal,
        grade: Optional[str],
        teacher_feedback: Optional[str],
        evaluated_by: uuid.UUID,
        status: str = "EVALUATED",
    ) -> AssignmentSubmissionResponse:
        submission = await self.repo.evaluate_submission(
            tenant_id=tenant_id,
            submission_id=submission_id,
            marks_obtained=marks_obtained,
            grade=grade,
            teacher_feedback=teacher_feedback,
            evaluated_by=evaluated_by,
            status=status,
        )
        detailed = await self.repo.get_submission(tenant_id, submission.id)
        if not detailed:
            raise NotFoundException("Submission not found.")
        return self._format_submission_response(detailed)

    async def list_submissions(
        self,
        tenant_id: uuid.UUID,
        assignment_id: uuid.UUID,
        status: Optional[str] = None,
    ) -> List[AssignmentSubmissionResponse]:
        subs = await self.repo.list_submissions(tenant_id, assignment_id, status)
        return [self._format_submission_response(s) for s in subs]

    async def get_student_submission(
        self,
        tenant_id: uuid.UUID,
        assignment_id: uuid.UUID,
        student_id: uuid.UUID,
    ) -> Optional[AssignmentSubmissionResponse]:
        sub = await self.repo.get_student_submission(tenant_id, assignment_id, student_id)
        if not sub:
            return None
        return self._format_submission_response(sub)

    async def get_assignment_report(
        self, tenant_id: uuid.UUID, assignment_id: uuid.UUID
    ) -> AssignmentReportResponse:
        data = await self.repo.get_assignment_report(tenant_id, assignment_id)
        return AssignmentReportResponse(**data)

    def _format_submission_response(self, sub: AssignmentSubmission) -> AssignmentSubmissionResponse:
        attachment_url = None
        if sub.attachment_file_key:
            attachment_url = storage_service.generate_signed_url(
                sub.attachment_file_key,
                original_filename=sub.attachment_file_name,
                expires_in=7200,
                for_download=True,
            )

        student_name = "Unknown Student"
        admission_num = "N/A"
        roll_num = None
        if sub.student:
            admission_num = sub.student.admission_number
            roll_num = sub.student.roll_number
            if sub.student.user:
                student_name = sub.student.user.full_name

        evaluator_name = sub.evaluator.full_name if sub.evaluator else None

        return AssignmentSubmissionResponse(
            id=sub.id,
            tenant_id=sub.tenant_id,
            assignment_id=sub.assignment_id,
            student_id=sub.student_id,
            student_name=student_name,
            admission_number=admission_num,
            roll_number=roll_num,
            submission_text=sub.submission_text,
            attachment_file_key=sub.attachment_file_key,
            attachment_file_name=sub.attachment_file_name,
            attachment_file_size=sub.attachment_file_size,
            attachment_download_url=attachment_url,
            submitted_at=sub.submitted_at,
            is_late=sub.is_late,
            marks_obtained=sub.marks_obtained,
            grade=sub.grade,
            teacher_feedback=sub.teacher_feedback,
            evaluated_by=sub.evaluated_by,
            evaluator_name=evaluator_name,
            evaluated_at=sub.evaluated_at,
            status=sub.status,
        )
