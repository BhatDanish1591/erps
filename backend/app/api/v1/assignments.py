from __future__ import annotations

import uuid
from decimal import Decimal
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Request, Response, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import BadRequestException, NotFoundException, AuthorizationException
from app.models.user import User
from app.permissions.rbac import get_active_tenant_id, get_current_user, get_current_user_claims, require_any_role
from app.schemas.lms import (
    AssignmentCreate,
    AssignmentEvaluationRequest,
    AssignmentReportResponse,
    AssignmentResponse,
    AssignmentSubmissionResponse,
    AssignmentUpdate,
)
from app.services.lms_service import LMSService

router = APIRouter(prefix="/assignments", tags=["Assignments & LMS Module"])


# ─────────────────────────────────────────────────────────────────────────────
# 1. Assignment Management
# ─────────────────────────────────────────────────────────────────────────────

@router.post("", response_model=Dict[str, Any], status_code=status.HTTP_201_CREATED)
async def create_assignment_json(
    data: AssignmentCreate,
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    current_user: User = Depends(require_any_role(["INSTITUTION_ADMIN", "SUPER_ADMIN", "TEACHER"])),
    session: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """
    Create assignment with JSON metadata.
    """
    service = LMSService(session)
    result = await service.create_assignment(
        tenant_id=tenant_id,
        data=data.model_dump(),
        created_by=current_user.id,
    )
    return {"success": True, "data": result.model_dump()}


@router.post("/with-file", response_model=Dict[str, Any], status_code=status.HTTP_201_CREATED)
async def create_assignment_with_instructions(
    title: str = Form(...),
    description: str = Form(...),
    academic_session_id: uuid.UUID = Form(...),
    due_datetime: str = Form(...),
    subject_id: Optional[uuid.UUID] = Form(None),
    class_id: Optional[uuid.UUID] = Form(None),
    section_id: Optional[uuid.UUID] = Form(None),
    course_id: Optional[uuid.UUID] = Form(None),
    semester_id: Optional[uuid.UUID] = Form(None),
    allow_late_submission: bool = Form(True),
    late_penalty_percent: Decimal = Form(Decimal("0.00")),
    total_marks: Decimal = Form(Decimal("100.00")),
    passing_marks: Decimal = Form(Decimal("40.00")),
    status_val: str = Form("PUBLISHED"),
    instructions_file: Optional[UploadFile] = File(None),
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    current_user: User = Depends(require_any_role(["INSTITUTION_ADMIN", "SUPER_ADMIN", "TEACHER"])),
    session: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """
    Create assignment with optional instructions attachment file.
    """
    from datetime import datetime
    try:
        parsed_due = datetime.fromisoformat(due_datetime)
    except Exception:
        raise BadRequestException("Invalid due_datetime format. Use ISO format (YYYY-MM-DDTHH:MM:SS).")

    file_bytes = None
    file_name = None
    content_type = None
    if instructions_file:
        file_bytes = await instructions_file.read()
        file_name = instructions_file.filename
        content_type = instructions_file.content_type

    data = {
        "title": title,
        "description": description,
        "academic_session_id": academic_session_id,
        "due_datetime": parsed_due,
        "subject_id": subject_id,
        "class_id": class_id,
        "section_id": section_id,
        "course_id": course_id,
        "semester_id": semester_id,
        "allow_late_submission": allow_late_submission,
        "late_penalty_percent": late_penalty_percent,
        "total_marks": total_marks,
        "passing_marks": passing_marks,
        "status": status_val,
    }

    service = LMSService(session)
    result = await service.create_assignment(
        tenant_id=tenant_id,
        data=data,
        created_by=current_user.id,
        instructions_bytes=file_bytes,
        instructions_filename=file_name,
        content_type=content_type,
    )
    return {"success": True, "data": result.model_dump()}


@router.get("", response_model=Dict[str, Any])
async def list_assignments(
    academic_session_id: Optional[uuid.UUID] = Query(None),
    subject_id: Optional[uuid.UUID] = Query(None),
    class_id: Optional[uuid.UUID] = Query(None),
    section_id: Optional[uuid.UUID] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    search: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=100),
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    current_user: User = Depends(require_any_role(["INSTITUTION_ADMIN", "SUPER_ADMIN", "TEACHER", "STUDENT", "PARENT"])),
    session: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """
    List assignments with filters, search, and pagination.
    """
    service = LMSService(session)
    offset = (page - 1) * size
    items, total = await service.list_assignments(
        tenant_id=tenant_id,
        academic_session_id=academic_session_id,
        subject_id=subject_id,
        class_id=class_id,
        section_id=section_id,
        status=status_filter,
        search=search,
        limit=size,
        offset=offset,
    )
    return {
        "success": True,
        "data": [item.model_dump() for item in items],
        "pagination": {
            "page": page,
            "size": size,
            "total": total,
            "total_pages": (total + size - 1) // size if total > 0 else 1,
        },
    }


@router.get("/{assignment_id}", response_model=Dict[str, Any])
async def get_assignment(
    assignment_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    current_user: User = Depends(require_any_role(["INSTITUTION_ADMIN", "SUPER_ADMIN", "TEACHER", "STUDENT", "PARENT"])),
    session: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    service = LMSService(session)
    result = await service.get_assignment(tenant_id, assignment_id)
    return {"success": True, "data": result.model_dump()}


@router.put("/{assignment_id}", response_model=Dict[str, Any])
async def update_assignment(
    assignment_id: uuid.UUID,
    data: AssignmentUpdate,
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    current_user: User = Depends(require_any_role(["INSTITUTION_ADMIN", "SUPER_ADMIN", "TEACHER"])),
    session: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    service = LMSService(session)
    updated = await service.update_assignment(tenant_id, assignment_id, data.model_dump(exclude_unset=True))
    return {"success": True, "data": updated.model_dump()}


# ─────────────────────────────────────────────────────────────────────────────
# 2. Student Submissions
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/{assignment_id}/submit", response_model=Dict[str, Any], status_code=status.HTTP_201_CREATED)
async def submit_assignment(
    assignment_id: uuid.UUID,
    submission_text: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None),
    student_id: Optional[uuid.UUID] = Form(None),
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    claims: dict = Depends(get_current_user_claims),
    current_user: User = Depends(require_any_role(["STUDENT", "INSTITUTION_ADMIN", "TEACHER"])),
    session: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """
    Submit an assignment response with optional text content and attachment.
    If the caller is a STUDENT, student profile is resolved automatically from their session.
    """
    service = LMSService(session)
    user_role = claims.get("role")

    # Determine student ID
    target_student_id = student_id
    if user_role == "STUDENT" or not target_student_id:
        profile = await service.get_student_profile_by_user(tenant_id, current_user.id)
        if not profile:
            raise BadRequestException("Student profile not found for current user account.")
        target_student_id = profile.id

    file_bytes = None
    file_name = None
    content_type = None
    if file:
        file_bytes = await file.read()
        file_name = file.filename
        content_type = file.content_type

    submission = await service.submit_assignment(
        tenant_id=tenant_id,
        assignment_id=assignment_id,
        student_id=target_student_id,
        submission_text=submission_text,
        file_bytes=file_bytes,
        file_name=file_name,
        content_type=content_type,
    )
    return {"success": True, "data": submission.model_dump()}


@router.get("/{assignment_id}/my-submission", response_model=Dict[str, Any])
async def get_my_submission(
    assignment_id: uuid.UUID,
    student_id: Optional[uuid.UUID] = Query(None),
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    claims: dict = Depends(get_current_user_claims),
    current_user: User = Depends(require_any_role(["STUDENT", "INSTITUTION_ADMIN", "TEACHER", "PARENT"])),
    session: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """
    Get current student's submission status and evaluation for an assignment.
    """
    service = LMSService(session)
    user_role = claims.get("role")
    target_student_id = student_id
    if user_role == "STUDENT" or not target_student_id:
        profile = await service.get_student_profile_by_user(tenant_id, current_user.id)
        if not profile:
            return {"success": True, "data": None}
        target_student_id = profile.id

    submission = await service.get_student_submission(tenant_id, assignment_id, target_student_id)
    return {"success": True, "data": submission.model_dump() if submission else None}


@router.get("/{assignment_id}/submissions", response_model=Dict[str, Any])
async def list_assignment_submissions(
    assignment_id: uuid.UUID,
    status_filter: Optional[str] = Query(None, alias="status"),
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    current_user: User = Depends(require_any_role(["INSTITUTION_ADMIN", "SUPER_ADMIN", "TEACHER"])),
    session: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """
    Teacher/Admin view of all submissions for an assignment.
    """
    service = LMSService(session)
    subs = await service.list_submissions(tenant_id, assignment_id, status_filter)
    return {"success": True, "data": [s.model_dump() for s in subs]}


# ─────────────────────────────────────────────────────────────────────────────
# 3. Teacher Evaluation & Feedback
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/submissions/{submission_id}/evaluate", response_model=Dict[str, Any])
async def evaluate_submission(
    submission_id: uuid.UUID,
    data: AssignmentEvaluationRequest,
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    current_user: User = Depends(require_any_role(["INSTITUTION_ADMIN", "SUPER_ADMIN", "TEACHER"])),
    session: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """
    Teacher evaluates a student submission: marks, grade, feedback, and handles late penalty automatically.
    """
    service = LMSService(session)
    evaluated = await service.evaluate_submission(
        tenant_id=tenant_id,
        submission_id=submission_id,
        marks_obtained=data.marks_obtained,
        grade=data.grade,
        teacher_feedback=data.teacher_feedback,
        evaluated_by=current_user.id,
        status=data.status,
    )
    return {"success": True, "data": evaluated.model_dump()}


# ─────────────────────────────────────────────────────────────────────────────
# 4. Reports & Completion Statistics
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/{assignment_id}/report", response_model=Dict[str, Any])
async def get_assignment_report(
    assignment_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    current_user: User = Depends(require_any_role(["INSTITUTION_ADMIN", "SUPER_ADMIN", "TEACHER"])),
    session: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """
    Get detailed assignment analytics: completion rate %, average score, pass %, evaluated vs pending.
    """
    service = LMSService(session)
    report = await service.get_assignment_report(tenant_id, assignment_id)
    return {"success": True, "data": report.model_dump()}
