from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import AppException, AuthorizationException, BadRequestException, NotFoundException
from app.models.academic import StudentParent, StudentProfile
from app.models.examination import StudentExamAttempt
from app.models.user import User
from app.permissions.rbac import get_active_tenant_id, get_current_user, get_current_user_claims, require_any_role
from app.schemas.examination import (
    AttemptEvaluationDetailResponse,
    AutosaveRequest,
    AutosaveResponse,
    EvaluateAttemptRequest,
    ExaminationCreate,
    ExaminationDetailResponse,
    ExaminationQuestionAdd,
    ExaminationQuestionResponse,
    ExaminationReportAnalytics,
    ExaminationUpdate,
    QuestionBankCreate,
    QuestionBankResponse,
    QuestionBankUpdate,
    StudentActiveAttemptResponse,
    StudentExamResultResponse,
    SubmitAttemptRequest,
    SubmitAttemptResponse,
)
from app.services.examination_service import ExaminationService

router = APIRouter(prefix="/examinations", tags=["Examination Management Engine"])


# ─────────────────────────────────────────────────────────────────────────────
# 1. Question Bank Endpoints
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/questions", response_model=Dict[str, Any], status_code=status.HTTP_201_CREATED)
async def create_question_bank_item(
    data: QuestionBankCreate,
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    current_user: User = Depends(require_any_role(["INSTITUTION_ADMIN", "SUPER_ADMIN", "TEACHER"])),
    session: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    service = ExaminationService(session)
    res = await service.create_question(tenant_id, data, current_user)
    return {"success": True, "data": res.model_dump()}


@router.get("/questions", response_model=Dict[str, Any])
async def list_question_bank_items(
    subject_id: Optional[uuid.UUID] = Query(None),
    category: Optional[str] = Query(None),
    difficulty: Optional[str] = Query(None),
    question_type: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    current_user: User = Depends(require_any_role(["INSTITUTION_ADMIN", "SUPER_ADMIN", "TEACHER"])),
    session: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    service = ExaminationService(session)
    items, total = await service.list_questions(
        tenant_id=tenant_id,
        subject_id=subject_id,
        category=category,
        difficulty=difficulty,
        question_type=question_type,
        search=search,
        skip=skip,
        limit=limit,
    )
    return {
        "success": True,
        "data": [i.model_dump() for i in items],
        "total": total,
        "skip": skip,
        "limit": limit,
    }


@router.get("/questions/{question_id}", response_model=Dict[str, Any])
async def get_question_bank_item(
    question_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    current_user: User = Depends(require_any_role(["INSTITUTION_ADMIN", "SUPER_ADMIN", "TEACHER"])),
    session: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    service = ExaminationService(session)
    item = await service.get_question(tenant_id, question_id)
    return {"success": True, "data": item.model_dump()}


@router.put("/questions/{question_id}", response_model=Dict[str, Any])
async def update_question_bank_item(
    question_id: uuid.UUID,
    data: QuestionBankUpdate,
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    current_user: User = Depends(require_any_role(["INSTITUTION_ADMIN", "SUPER_ADMIN", "TEACHER"])),
    session: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    service = ExaminationService(session)
    updated = await service.update_question(tenant_id, question_id, data)
    return {"success": True, "data": updated.model_dump()}


@router.delete("/questions/{question_id}", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
async def delete_question_bank_item(
    question_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    current_user: User = Depends(require_any_role(["INSTITUTION_ADMIN", "SUPER_ADMIN", "TEACHER"])),
    session: AsyncSession = Depends(get_db),
) -> Response:
    service = ExaminationService(session)
    await service.delete_question(tenant_id, question_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ─────────────────────────────────────────────────────────────────────────────
# 2. Examination CRUD & Scheduling
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/", response_model=Dict[str, Any], status_code=status.HTTP_201_CREATED)
async def create_examination(
    data: ExaminationCreate,
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    current_user: User = Depends(require_any_role(["INSTITUTION_ADMIN", "SUPER_ADMIN", "TEACHER"])),
    session: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    service = ExaminationService(session)
    exam = await service.create_examination(tenant_id, data, current_user)
    return {"success": True, "data": exam.model_dump()}


@router.get("/", response_model=Dict[str, Any])
async def list_examinations(
    academic_session_id: Optional[uuid.UUID] = Query(None),
    subject_id: Optional[uuid.UUID] = Query(None),
    class_id: Optional[uuid.UUID] = Query(None),
    section_id: Optional[uuid.UUID] = Query(None),
    course_id: Optional[uuid.UUID] = Query(None),
    semester_id: Optional[uuid.UUID] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    exam_type: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    current_user: User = Depends(require_any_role(["INSTITUTION_ADMIN", "SUPER_ADMIN", "TEACHER", "STUDENT", "PARENT"])),
    session: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    service = ExaminationService(session)
    exams, total = await service.list_examinations(
        tenant_id=tenant_id,
        academic_session_id=academic_session_id,
        subject_id=subject_id,
        class_id=class_id,
        section_id=section_id,
        course_id=course_id,
        semester_id=semester_id,
        status=status_filter,
        exam_type=exam_type,
        search=search,
        skip=skip,
        limit=limit,
    )
    return {
        "success": True,
        "data": [e.model_dump() for e in exams],
        "total": total,
        "skip": skip,
        "limit": limit,
    }


@router.get("/{exam_id}", response_model=Dict[str, Any])
async def get_examination(
    exam_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    current_user: User = Depends(require_any_role(["INSTITUTION_ADMIN", "SUPER_ADMIN", "TEACHER"])),
    session: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    service = ExaminationService(session)
    exam = await service.get_examination(tenant_id, exam_id)
    return {"success": True, "data": exam.model_dump()}


@router.put("/{exam_id}", response_model=Dict[str, Any])
async def update_examination(
    exam_id: uuid.UUID,
    data: ExaminationUpdate,
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    current_user: User = Depends(require_any_role(["INSTITUTION_ADMIN", "SUPER_ADMIN", "TEACHER"])),
    session: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    service = ExaminationService(session)
    updated = await service.update_examination(tenant_id, exam_id, data)
    return {"success": True, "data": updated.model_dump()}


@router.delete("/{exam_id}", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
async def delete_examination(
    exam_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    current_user: User = Depends(require_any_role(["INSTITUTION_ADMIN", "SUPER_ADMIN", "TEACHER"])),
    session: AsyncSession = Depends(get_db),
) -> Response:
    service = ExaminationService(session)
    await service.delete_examination(tenant_id, exam_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{exam_id}/questions", response_model=Dict[str, Any], status_code=status.HTTP_201_CREATED)
async def add_question_to_examination(
    exam_id: uuid.UUID,
    data: ExaminationQuestionAdd,
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    current_user: User = Depends(require_any_role(["INSTITUTION_ADMIN", "SUPER_ADMIN", "TEACHER"])),
    session: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    service = ExaminationService(session)
    q = await service.add_question(tenant_id, exam_id, data)
    return {"success": True, "data": q.model_dump()}


@router.delete("/{exam_id}/questions/{question_id}", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
async def remove_question_from_examination(
    exam_id: uuid.UUID,
    question_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    current_user: User = Depends(require_any_role(["INSTITUTION_ADMIN", "SUPER_ADMIN", "TEACHER"])),
    session: AsyncSession = Depends(get_db),
) -> Response:
    service = ExaminationService(session)
    await service.remove_question(tenant_id, exam_id, question_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ─────────────────────────────────────────────────────────────────────────────
# 3. Student Online Exam Room (Timer, Autosave, Submit)
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/{exam_id}/start", response_model=Dict[str, Any])
async def start_or_resume_exam(
    exam_id: uuid.UUID,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    current_user: User = Depends(require_any_role(["STUDENT"])),
    session: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    # Find student profile for the current user
    stmt = select(StudentProfile).where(
        StudentProfile.tenant_id == tenant_id, StudentProfile.user_id == current_user.id,
        StudentProfile.status == "ACTIVE", StudentProfile.is_deleted.is_(False),
    )
    result = await session.execute(stmt)
    student = result.scalars().first()
    if not student:
        raise AuthorizationException("An active student profile is required to take this examination.")

    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")

    service = ExaminationService(session)
    attempt_data = await service.start_or_resume_exam(
        tenant_id=tenant_id,
        exam_id=exam_id,
        student_profile_id=student.id,
        client_ip=client_ip,
        user_agent=user_agent,
    )
    return {"success": True, "data": attempt_data.model_dump()}


async def require_attempt_owner(
    session: AsyncSession, tenant_id: uuid.UUID, attempt_id: uuid.UUID, user_id: uuid.UUID,
) -> None:
    attempt = await session.scalar(select(StudentExamAttempt.id).join(
        StudentProfile, StudentProfile.id == StudentExamAttempt.student_id,
    ).where(
        StudentExamAttempt.id == attempt_id, StudentExamAttempt.tenant_id == tenant_id,
        StudentExamAttempt.is_deleted.is_(False), StudentProfile.tenant_id == tenant_id,
        StudentProfile.user_id == user_id, StudentProfile.is_deleted.is_(False),
    ).with_for_update(of=StudentExamAttempt))
    if not attempt:
        raise AuthorizationException("You cannot change another student's examination attempt.")


@router.post("/attempts/{attempt_id}/autosave", response_model=Dict[str, Any])
async def autosave_exam_answers(
    attempt_id: uuid.UUID,
    data: AutosaveRequest,
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    current_user: User = Depends(require_any_role(["STUDENT"])),
    session: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    await require_attempt_owner(session, tenant_id, attempt_id, current_user.id)
    service = ExaminationService(session)
    res = await service.autosave_draft(tenant_id, attempt_id, data.answers)
    return {"success": True, "data": res.model_dump()}


@router.post("/attempts/{attempt_id}/submit", response_model=Dict[str, Any])
async def submit_exam_attempt(
    attempt_id: uuid.UUID,
    data: SubmitAttemptRequest,
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    current_user: User = Depends(require_any_role(["STUDENT"])),
    session: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    await require_attempt_owner(session, tenant_id, attempt_id, current_user.id)
    service = ExaminationService(session)
    res = await service.submit_exam(
        tenant_id=tenant_id,
        attempt_id=attempt_id,
        final_answers=data.final_answers,
        submission_hash=data.submission_hash,
    )
    return {"success": True, "data": res.model_dump()}


@router.get("/attempts/{attempt_id}/result", response_model=Dict[str, Any])
async def get_student_exam_result(
    attempt_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    current_user: User = Depends(require_any_role(["STUDENT", "INSTITUTION_ADMIN", "SUPER_ADMIN", "TEACHER", "PARENT"])),
    session: AsyncSession = Depends(get_db),
    claims: dict = Depends(get_current_user_claims),
) -> Dict[str, Any]:
    service = ExaminationService(session)
    student_profile_id = None
    role = claims.get("role")
    if not current_user.is_superadmin and role == "STUDENT":
        student_profile_id = await session.scalar(select(StudentProfile.id).where(
            StudentProfile.tenant_id == tenant_id, StudentProfile.user_id == current_user.id,
            StudentProfile.is_deleted.is_(False),
        ))
        if student_profile_id is None:
            raise AuthorizationException("An active student profile is required.")
    elif not current_user.is_superadmin and role == "PARENT":
        student_profile_id = await session.scalar(
            select(StudentExamAttempt.student_id)
            .join(StudentParent, StudentParent.student_id == StudentExamAttempt.student_id)
            .where(
                StudentExamAttempt.id == attempt_id, StudentExamAttempt.tenant_id == tenant_id,
                StudentParent.tenant_id == tenant_id, StudentParent.parent_user_id == current_user.id,
                StudentParent.status == "VERIFIED", StudentParent.can_view_grades.is_(True),
                StudentParent.is_deleted.is_(False),
            )
        )
        if student_profile_id is None:
            raise AuthorizationException("You cannot view this examination attempt.")

    res = await service.get_student_exam_result(tenant_id, attempt_id, student_profile_id)
    return {"success": True, "data": res.model_dump()}


# ─────────────────────────────────────────────────────────────────────────────
# 4. Teacher Evaluation & Scoring
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/{exam_id}/attempts", response_model=Dict[str, Any])
async def list_exam_attempts(
    exam_id: uuid.UUID,
    status_filter: Optional[str] = Query(None, alias="status"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    current_user: User = Depends(require_any_role(["INSTITUTION_ADMIN", "SUPER_ADMIN", "TEACHER"])),
    session: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    service = ExaminationService(session)
    attempts, total = await service.list_exam_attempts(
        tenant_id=tenant_id,
        exam_id=exam_id,
        status=status_filter,
        skip=skip,
        limit=limit,
    )
    return {
        "success": True,
        "data": attempts,
        "total": total,
        "skip": skip,
        "limit": limit,
    }


@router.get("/attempts/{attempt_id}/evaluation", response_model=Dict[str, Any])
async def get_attempt_for_evaluation(
    attempt_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    current_user: User = Depends(require_any_role(["INSTITUTION_ADMIN", "SUPER_ADMIN", "TEACHER"])),
    session: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    service = ExaminationService(session)
    detail = await service.get_attempt_for_evaluation(tenant_id, attempt_id)
    return {"success": True, "data": detail.model_dump()}


@router.post("/attempts/{attempt_id}/evaluate", response_model=Dict[str, Any])
async def evaluate_student_attempt(
    attempt_id: uuid.UUID,
    data: EvaluateAttemptRequest,
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    current_user: User = Depends(require_any_role(["INSTITUTION_ADMIN", "SUPER_ADMIN", "TEACHER"])),
    session: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    service = ExaminationService(session)
    evaluated = await service.evaluate_attempt(tenant_id, attempt_id, data, current_user)
    return {"success": True, "data": evaluated.model_dump()}


# ─────────────────────────────────────────────────────────────────────────────
# 5. Examination Analytics & Performance Reports
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/{exam_id}/analytics", response_model=Dict[str, Any])
async def get_exam_analytics(
    exam_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    current_user: User = Depends(require_any_role(["INSTITUTION_ADMIN", "SUPER_ADMIN", "TEACHER"])),
    session: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    service = ExaminationService(session)
    analytics = await service.get_exam_analytics(tenant_id, exam_id)
    return {"success": True, "data": analytics.model_dump()}
