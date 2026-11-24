from __future__ import annotations

import io
import uuid
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, Response, UploadFile, status
from fastapi.responses import HTMLResponse, PlainTextResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import AppException, AuthorizationException, BadRequestException
from app.models.academic import StudentProfile
from app.models.enums import InstitutionType
from app.dependencies.tenant import get_registered_institution_type
from app.models.user import User
from app.permissions.rbac import get_active_tenant_id, get_current_user, get_current_user_claims, get_teacher_scope_user, require_any_role
from app.services.staff_access_service import load_staff_access
from app.repositories.student import teacher_student_scope
from app.schemas.student import (
    BulkImportSummaryResponse,
    StudentCreateRequest,
    StudentDocumentCreateRequest,
    StudentDocumentResponse,
    StudentIDCardResponse,
    StudentPromotionRequest,
    StudentResponse,
    StudentUpdateRequest,
)
from app.services.student_service import StudentService
from app.utils.storage import storage_service

router = APIRouter(prefix="/students", tags=["Students"])


@router.post("/photo", status_code=status.HTTP_201_CREATED)
async def upload_student_photo(
    file: UploadFile = File(...),
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    current_user: User = Depends(require_any_role(["INSTITUTION_ADMIN", "SUPER_ADMIN", "PRINCIPAL", "HOD"])),
) -> Dict[str, Any]:
    content = await file.read(5 * 1024 * 1024 + 1)
    if len(content) > 5 * 1024 * 1024:
        raise BadRequestException("The photo must be 5 MB or smaller.")
    if content.startswith(b"\xff\xd8\xff"):
        extension, mime = ".jpg", "image/jpeg"
    elif content.startswith(b"\x89PNG\r\n\x1a\n"):
        extension, mime = ".png", "image/png"
    else:
        raise BadRequestException("Select a JPEG or PNG image.")
    key = storage_service.build_storage_key(tenant_id, "student-photos", "photo" + extension)
    storage_service.upload_file_bytes(content, key, mime)
    return {"success": True, "data": {"photo_key": key}}


async def require_assigned_student(
    student_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    teacher_user_id: Optional[uuid.UUID] = Depends(get_teacher_scope_user),
    session: AsyncSession = Depends(get_db),
) -> None:
    if teacher_user_id is None:
        return
    assigned = await session.scalar(
        select(StudentProfile.id).where(
            StudentProfile.id == student_id,
            StudentProfile.tenant_id == tenant_id,
            StudentProfile.is_deleted.is_(False),
            teacher_student_scope(tenant_id, teacher_user_id),
        )
    )
    if assigned is None:
        raise AuthorizationException("This student is outside your assigned classes or courses.")


# ── List Students ─────────────────────────────────────────────────────────────
@router.get("", response_model=Dict[str, Any])
async def list_students(
    search: Optional[str] = Query(None, description="Search by name, email, admission or roll number"),
    class_id: Optional[uuid.UUID] = Query(None, description="Filter by class"),
    section_id: Optional[uuid.UUID] = Query(None, description="Filter by section"),
    department_id: Optional[uuid.UUID] = Query(None, description="Filter by college department"),
    course_id: Optional[uuid.UUID] = Query(None, description="Filter by college course"),
    semester: Optional[int] = Query(None, ge=1, le=16, description="Filter by semester"),
    status: Optional[str] = Query(None, description="Filter by status (ACTIVE, INACTIVE, etc.)"),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=200),
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    current_user: User = Depends(require_any_role(["INSTITUTION_ADMIN", "SUPER_ADMIN", "PRINCIPAL", "HOD", "TEACHER"])),
    teacher_user_id: Optional[uuid.UUID] = Depends(get_teacher_scope_user),
    session: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    service = StudentService(session)
    students, total = await service.list_students(
        tenant_id=tenant_id,
        search=search,
        class_id=class_id,
        section_id=section_id,
        department_id=department_id,
        course_id=course_id,
        semester=semester,
        status=status,
        page=page,
        size=size,
        teacher_user_id=teacher_user_id,
    )

    return {
        "success": True,
        "data": {
            "items": [s.model_dump() for s in students],
            "total": total,
            "page": page,
            "size": size,
            "pages": (total + size - 1) // size if size > 0 else 1,
        },
    }


# ── Create Student ────────────────────────────────────────────────────────────
@router.post("", response_model=Dict[str, Any], status_code=status.HTTP_201_CREATED)
async def create_student(
    payload: StudentCreateRequest,
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    current_user: User = Depends(require_any_role(["INSTITUTION_ADMIN", "SUPER_ADMIN", "PRINCIPAL", "HOD"])),
    claims: dict = Depends(get_current_user_claims),
    institution_type: InstitutionType = Depends(get_registered_institution_type),
    session: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    if claims.get("role") == "HOD" and not current_user.is_superadmin:
        access = await load_staff_access(session, tenant_id, current_user.id, "HOD")
        if institution_type != InstitutionType.COLLEGE or payload.department_id not in (access.department_ids or ()):
            raise AuthorizationException("Admissions are limited to your assigned college department.")
    service = StudentService(session)
    student = await service.create_student(
        tenant_id=tenant_id,
        payload=payload,
        actor_user_id=current_user.id,
    )
    return {
        "success": True,
        "data": student.model_dump(),
        "message": f"Student '{student.full_name}' admitted successfully with admission number '{student.admission_number}'.",
    }


# ── Bulk Student Promotion & Cohort Transition ────────────────────────────────
@router.post("/promote", response_model=Dict[str, Any])
async def promote_students(
    payload: StudentPromotionRequest,
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    current_user: User = Depends(require_any_role(["INSTITUTION_ADMIN", "SUPER_ADMIN"])),
    session: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    service = StudentService(session)
    res = await service.promote_students(
        tenant_id=tenant_id,
        payload=payload,
        actor_user_id=current_user.id,
    )
    return {"success": True, "data": res}


# ── Export Students as CSV ────────────────────────────────────────────────────
@router.get("/export")
async def export_students_csv(
    search: Optional[str] = Query(None),
    class_id: Optional[uuid.UUID] = Query(None),
    section_id: Optional[uuid.UUID] = Query(None),
    department_id: Optional[uuid.UUID] = Query(None),
    course_id: Optional[uuid.UUID] = Query(None),
    semester: Optional[int] = Query(None, ge=1, le=16),
    status: Optional[str] = Query(None),
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    current_user: User = Depends(require_any_role(["INSTITUTION_ADMIN", "SUPER_ADMIN", "TEACHER"])),
    teacher_user_id: Optional[uuid.UUID] = Depends(get_teacher_scope_user),
    session: AsyncSession = Depends(get_db),
) -> Response:
    service = StudentService(session)
    csv_data = await service.export_students_csv(
        tenant_id=tenant_id,
        search=search,
        class_id=class_id,
        section_id=section_id,
        department_id=department_id,
        course_id=course_id,
        semester=semester,
        status=status,
        teacher_user_id=teacher_user_id,
    )
    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=students_export.csv"},
    )


# ── Bulk Import Students CSV ──────────────────────────────────────────────────
@router.post("/import", response_model=Dict[str, Any])
async def bulk_import_students(
    file: UploadFile = File(...),
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    current_user: User = Depends(require_any_role(["INSTITUTION_ADMIN", "SUPER_ADMIN"])),
    session: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    if not file.filename.lower().endswith((".csv", ".txt")):
        raise AppException(400, "INVALID_FILE_TYPE", "Only CSV files are supported for student bulk import.")

    content_bytes = await file.read()
    csv_text = content_bytes.decode("utf-8-sig", errors="replace")

    service = StudentService(session)
    result = await service.bulk_import_students(
        tenant_id=tenant_id,
        csv_content=csv_text,
        actor_user_id=current_user.id,
    )
    return {"success": True, "data": result.model_dump()}


# ── Get Student Profile ───────────────────────────────────────────────────────
@router.get("/{student_id}", response_model=Dict[str, Any], dependencies=[Depends(require_assigned_student)])
async def get_student_detail(
    student_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    current_user: User = Depends(require_any_role(["INSTITUTION_ADMIN", "SUPER_ADMIN", "TEACHER", "STUDENT", "PARENT"])),
    session: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    service = StudentService(session)
    student = await service.get_student_detail(tenant_id=tenant_id, student_id=student_id)
    return {"success": True, "data": student.model_dump()}


# ── Update Student Profile ────────────────────────────────────────────────────
@router.put("/{student_id}", response_model=Dict[str, Any])
async def update_student(
    student_id: uuid.UUID,
    payload: StudentUpdateRequest,
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    current_user: User = Depends(require_any_role(["INSTITUTION_ADMIN", "SUPER_ADMIN"])),
    session: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    service = StudentService(session)
    student = await service.update_student(
        tenant_id=tenant_id,
        student_id=student_id,
        payload=payload,
        actor_user_id=current_user.id,
    )
    return {"success": True, "data": student.model_dump(), "message": "Student profile updated successfully."}


# ── Deactivate Student ────────────────────────────────────────────────────────
@router.delete("/{student_id}", response_model=Dict[str, Any])
async def deactivate_student(
    student_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    current_user: User = Depends(require_any_role(["INSTITUTION_ADMIN", "SUPER_ADMIN"])),
    session: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    service = StudentService(session)
    res = await service.deactivate_student(
        tenant_id=tenant_id,
        student_id=student_id,
        actor_user_id=current_user.id,
    )
    return {"success": True, "data": res, "message": "Student record deactivated successfully."}


# ── Student ID Card JSON ──────────────────────────────────────────────────────
@router.get("/{student_id}/id-card", response_model=Dict[str, Any], dependencies=[Depends(require_assigned_student)])
async def get_student_id_card(
    student_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    current_user: User = Depends(require_any_role(["INSTITUTION_ADMIN", "SUPER_ADMIN", "TEACHER", "STUDENT", "PARENT"])),
    session: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    service = StudentService(session)
    card = await service.generate_id_card(tenant_id=tenant_id, student_id=student_id)
    return {"success": True, "data": card.model_dump()}


# ── Student ID Card Printable HTML ────────────────────────────────────────────
@router.get("/{student_id}/id-card/html", response_class=HTMLResponse, dependencies=[Depends(require_assigned_student)])
async def get_student_id_card_html(
    student_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    current_user: User = Depends(require_any_role(["INSTITUTION_ADMIN", "SUPER_ADMIN", "TEACHER", "STUDENT", "PARENT"])),
    session: AsyncSession = Depends(get_db),
) -> HTMLResponse:
    service = StudentService(session)
    html_content = await service.generate_id_card_html(tenant_id=tenant_id, student_id=student_id)
    return HTMLResponse(content=html_content, status_code=status.HTTP_200_OK)


# ── Upload Student Document ───────────────────────────────────────────────────
@router.post("/{student_id}/documents", response_model=Dict[str, Any], status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_assigned_student)])
async def upload_student_document(
    student_id: uuid.UUID,
    payload: StudentDocumentCreateRequest,
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    current_user: User = Depends(require_any_role(["INSTITUTION_ADMIN", "SUPER_ADMIN", "TEACHER"])),
    session: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    service = StudentService(session)
    doc = await service.upload_document(
        tenant_id=tenant_id,
        student_id=student_id,
        payload=payload,
        actor_user_id=current_user.id,
    )
    return {
        "success": True,
        "data": {
            "id": str(doc.id),
            "student_id": str(doc.student_id),
            "document_type": doc.document_type,
            "document_name": doc.document_name,
            "file_url": doc.file_url,
            "file_size_bytes": doc.file_size_bytes,
            "mime_type": doc.mime_type,
            "created_at": doc.created_at.isoformat() if doc.created_at else None,
        },
        "message": "Student document registered successfully.",
    }
