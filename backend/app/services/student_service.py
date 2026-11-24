from __future__ import annotations

import csv
import io
import re
import uuid
from datetime import date, datetime, timezone
from html import escape
from typing import Any, Dict, List, Optional, Tuple

from fastapi.encoders import jsonable_encoder
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

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
)
from app.models.tenant import Tenant
from app.models.user import User
from app.repositories.student import StudentRepository
from app.schemas.student import (
    BulkImportSummaryResponse,
    StudentCreateRequest,
    StudentDocumentCreateRequest,
    StudentIDCardResponse,
    StudentPromotionRequest,
    StudentResponse,
    StudentUpdateRequest,
)
from app.services.entitlement_service import EntitlementService
from app.utils.storage import storage_service

logger = get_logger(__name__)


def student_photo_url(photo: Optional[str], tenant_id: uuid.UUID) -> Optional[str]:
    if photo and re.fullmatch(rf"tenants/{tenant_id}/student-photos/[0-9a-f]{{12}}_photo\.(jpg|png)", photo):
        return storage_service.generate_signed_url(photo, for_download=False)
    if photo and photo.startswith("tenants/"):
        return None
    return photo


class StudentService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = StudentRepository(session)
        self.entitlement_service = EntitlementService(session)

    # ── Create Student ────────────────────────────────────────────────────────
    async def create_student(
        self,
        tenant_id: uuid.UUID,
        payload: StudentCreateRequest,
        actor_user_id: Optional[uuid.UUID] = None,
    ) -> StudentResponse:
        # 1. Dynamic Entitlement Check: Verify tenant has student capacity
        await self.entitlement_service.check_quota(tenant_id, "students", increment=1)

        # 2. Admission Number Generation / Uniqueness
        admission_number = payload.admission_number
        if not admission_number or not admission_number.strip():
            admission_number = await self.repo.generate_admission_number(tenant_id)
        else:
            admission_number = admission_number.strip()
            existing = await self.repo.get_student_by_admission_number(tenant_id, admission_number)
            if existing:
                raise AppException(409, "DUPLICATE_ADMISSION_NUMBER", f"Admission number '{admission_number}' already exists in this institution.")

        # 3. Create or Link User
        if payload.email:
            student_email = payload.email
        else:
            tenant_obj = (await self.session.execute(select(Tenant).where(Tenant.id == tenant_id))).scalar_one_or_none()
            t_slug = tenant_obj.slug.replace("-", "_") if tenant_obj else str(tenant_id)[:8]
            student_email = f"{admission_number.lower().replace('-', '_')}_{t_slug}@campus.internal"
        user, _ = await self.repo.get_or_create_user_and_membership(
            tenant_id=tenant_id,
            email=str(student_email),
            full_name=payload.full_name,
            phone=payload.phone,
            role_code="STUDENT",
        )

        # 4. Resolve Default Academic Session if not supplied
        session_id = payload.academic_session_id
        if not session_id:
            curr_session = (await self.session.execute(
                select(AcademicSession).where(
                    AcademicSession.tenant_id == tenant_id,
                    AcademicSession.is_current == True,
                )
            )).scalar_one_or_none()
            if curr_session:
                session_id = curr_session.id

        # 5. Create StudentProfile
        profile = StudentProfile(
            tenant_id=tenant_id,
            user_id=user.id,
            admission_number=admission_number,
            roll_number=payload.roll_number,
            admission_date=payload.admission_date or date.today(),
            academic_session_id=session_id,
            class_id=payload.class_id,
            section_id=payload.section_id,
            department_id=payload.department_id,
            course_id=payload.course_id,
            semester=payload.semester,
            batch_year=payload.batch_year,
            gender=payload.gender,
            date_of_birth=payload.date_of_birth,
            blood_group=payload.blood_group,
            address_line1=payload.address_line1,
            address_line2=payload.address_line2,
            city=payload.city,
            state=payload.state,
            postal_code=payload.postal_code,
            country=payload.country or "India",
            parent_name=payload.parent_name or payload.father_name or payload.guardian_name,
            parent_phone=payload.parent_phone or payload.father_phone or payload.guardian_phone,
            parent_email=payload.parent_email,
            father_name=payload.father_name,
            father_phone=payload.father_phone,
            father_occupation=payload.father_occupation,
            mother_name=payload.mother_name,
            mother_phone=payload.mother_phone,
            mother_occupation=payload.mother_occupation,
            guardian_name=payload.guardian_name,
            guardian_phone=payload.guardian_phone,
            guardian_relation=payload.guardian_relation,
            emergency_contact_name=payload.emergency_contact_name,
            emergency_contact_phone=payload.emergency_contact_phone,
            previous_school_name=payload.previous_school_name,
            previous_grade=payload.previous_grade,
            transfer_certificate_number=payload.transfer_certificate_number,
            photo_url=payload.photo_url,
            custom_fields=payload.custom_fields or {},
            status="ACTIVE",
        )

        enrollment = None
        if session_id:
            enrollment = StudentEnrollmentHistory(
                tenant_id=tenant_id,
                student_id=uuid.uuid4(),  # Will be reassigned in repo
                academic_session_id=session_id,
                class_id=payload.class_id,
                section_id=payload.section_id,
                department_id=payload.department_id,
                course_id=payload.course_id,
                semester=payload.semester,
                roll_number=payload.roll_number,
                enrollment_status="ENROLLED",
                remarks="Initial admission enrollment",
            )

        created_profile = await self.repo.create_student(profile, enrollment)

        # 6. Optional Parent Account & Linking
        if payload.parent_email and payload.parent_name:
            parent_user, _ = await self.repo.get_or_create_user_and_membership(
                tenant_id=tenant_id,
                email=payload.parent_email,
                full_name=payload.parent_name,
                phone=payload.parent_phone,
                role_code="PARENT",
            )
            student_parent = StudentParent(
                tenant_id=tenant_id,
                student_id=created_profile.id,
                parent_user_id=parent_user.id,
                relation_type=payload.guardian_relation or "GUARDIAN",
                is_primary=True,
            )
            self.session.add(student_parent)

        await self.repo.log_audit(
            tenant_id=tenant_id,
            user_id=actor_user_id,
            action="STUDENT_CREATED",
            entity_id=str(created_profile.id),
            changes={"admission_number": admission_number, "full_name": payload.full_name},
        )
        await self.session.commit()

        return await self.get_student_detail(tenant_id, created_profile.id)

    # ── Update Student ────────────────────────────────────────────────────────
    async def update_student(
        self,
        tenant_id: uuid.UUID,
        student_id: uuid.UUID,
        payload: StudentUpdateRequest,
        actor_user_id: Optional[uuid.UUID] = None,
    ) -> StudentResponse:
        student = await self.repo.get_student_by_id(tenant_id, student_id)
        if not student:
            raise AppException(404, "STUDENT_NOT_FOUND", "Student not found")

        update_dict = payload.model_dump(exclude_unset=True)

        # Update User full name or phone if present
        if "full_name" in update_dict and student.user:
            student.user.full_name = update_dict.pop("full_name")
        if "phone" in update_dict and student.user:
            student.user.phone = update_dict.pop("phone")
        if "email" in update_dict:
            new_email = update_dict.pop("email")
            if new_email and student.user:
                student.user.email = str(new_email).strip().lower()

        for k, v in update_dict.items():
            if hasattr(student, k):
                setattr(student, k, v)

        await self.repo.log_audit(
            tenant_id=tenant_id,
            user_id=actor_user_id,
            action="STUDENT_UPDATED",
            entity_id=str(student.id),
            changes=jsonable_encoder(update_dict),
        )
        await self.session.commit()
        return await self.get_student_detail(tenant_id, student.id)

    # ── Get Student Detail ────────────────────────────────────────────────────
    async def get_student_detail(
        self, tenant_id: uuid.UUID, student_id: uuid.UUID
    ) -> StudentResponse:
        s = await self.repo.get_student_by_id(tenant_id, student_id)
        if not s:
            raise AppException(404, "STUDENT_NOT_FOUND", "Student not found")

        return StudentResponse(
            id=s.id,
            tenant_id=s.tenant_id,
            user_id=s.user_id,
            full_name=s.user.full_name if s.user else "Unknown",
            email=s.user.email if s.user else None,
            phone=s.user.phone if s.user else None,
            admission_number=s.admission_number,
            roll_number=s.roll_number,
            admission_date=s.admission_date,
            status=s.status,
            gender=s.gender,
            date_of_birth=s.date_of_birth,
            blood_group=s.blood_group,
            academic_session_id=s.academic_session_id,
            academic_session_name=s.academic_session.name if s.academic_session else None,
            class_id=s.class_id,
            class_name=s.school_class.name if s.school_class else None,
            section_id=s.section_id,
            section_name=s.section.name if s.section else None,
            department_id=s.department_id,
            department_name=s.department.name if s.department else None,
            course_id=s.course_id,
            course_name=s.course.name if s.course else None,
            semester=s.semester,
            batch_year=s.batch_year,
            address_line1=s.address_line1,
            address_line2=s.address_line2,
            city=s.city,
            state=s.state,
            postal_code=s.postal_code,
            country=s.country,
            parent_name=s.parent_name,
            parent_phone=s.parent_phone,
            parent_email=s.parent_email,
            father_name=s.father_name,
            father_phone=s.father_phone,
            father_occupation=s.father_occupation,
            mother_name=s.mother_name,
            mother_phone=s.mother_phone,
            mother_occupation=s.mother_occupation,
            guardian_name=s.guardian_name,
            guardian_phone=s.guardian_phone,
            guardian_relation=s.guardian_relation,
            emergency_contact_name=s.emergency_contact_name,
            emergency_contact_phone=s.emergency_contact_phone,
            previous_school_name=s.previous_school_name,
            previous_grade=s.previous_grade,
            transfer_certificate_number=s.transfer_certificate_number,
            photo_url=student_photo_url(s.photo_url, tenant_id),
            custom_fields=s.custom_fields,
            created_at=s.created_at,
            updated_at=s.updated_at,
        )

    # ── List Students ─────────────────────────────────────────────────────────
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
    ) -> Tuple[List[StudentResponse], int]:
        students, total = await self.repo.list_students(
            tenant_id=tenant_id,
            search=search,
            class_id=class_id,
            section_id=section_id,
            department_id=department_id,
            course_id=course_id,
            semester=semester,
            academic_session_id=academic_session_id,
            status=status,
            gender=gender,
            page=page,
            size=size,
            teacher_user_id=teacher_user_id,
        )

        items = [
            StudentResponse(
                id=s.id,
                tenant_id=s.tenant_id,
                user_id=s.user_id,
                full_name=s.user.full_name if s.user else "Unknown",
                email=s.user.email if s.user else None,
                phone=s.user.phone if s.user else None,
                admission_number=s.admission_number,
                roll_number=s.roll_number,
                admission_date=s.admission_date,
                status=s.status,
                gender=s.gender,
                date_of_birth=s.date_of_birth,
                blood_group=s.blood_group,
                academic_session_id=s.academic_session_id,
                academic_session_name=s.academic_session.name if s.academic_session else None,
                class_id=s.class_id,
                class_name=s.school_class.name if s.school_class else None,
                section_id=s.section_id,
                section_name=s.section.name if s.section else None,
                department_id=s.department_id,
                department_name=s.department.name if s.department else None,
                course_id=s.course_id,
                course_name=s.course.name if s.course else None,
                semester=s.semester,
                batch_year=s.batch_year,
                address_line1=s.address_line1,
                address_line2=s.address_line2,
                city=s.city,
                state=s.state,
                postal_code=s.postal_code,
                country=s.country,
                parent_name=s.parent_name,
                parent_phone=s.parent_phone,
                parent_email=s.parent_email,
                father_name=s.father_name,
                father_phone=s.father_phone,
                father_occupation=s.father_occupation,
                mother_name=s.mother_name,
                mother_phone=s.mother_phone,
                mother_occupation=s.mother_occupation,
                guardian_name=s.guardian_name,
                guardian_phone=s.guardian_phone,
                guardian_relation=s.guardian_relation,
                emergency_contact_name=s.emergency_contact_name,
                emergency_contact_phone=s.emergency_contact_phone,
                previous_school_name=s.previous_school_name,
                previous_grade=s.previous_grade,
                transfer_certificate_number=s.transfer_certificate_number,
                photo_url=student_photo_url(s.photo_url, tenant_id),
                custom_fields=s.custom_fields,
                created_at=s.created_at,
                updated_at=s.updated_at,
            )
            for s in students
        ]
        return items, total

    # ── Deactivate Student ────────────────────────────────────────────────────
    async def deactivate_student(
        self, tenant_id: uuid.UUID, student_id: uuid.UUID, actor_user_id: Optional[uuid.UUID] = None
    ) -> None:
        student = await self.repo.get_student_by_id(tenant_id, student_id)
        if not student:
            raise AppException(404, "STUDENT_NOT_FOUND", "Student not found")

        student.status = "INACTIVE"
        await self.repo.log_audit(
            tenant_id=tenant_id,
            user_id=actor_user_id,
            action="STUDENT_DEACTIVATED",
            entity_id=str(student.id),
        )
        await self.session.commit()

    # ── Student Promotion & Graduation Engine ─────────────────────────────────
    async def promote_students(
        self,
        tenant_id: uuid.UUID,
        payload: StudentPromotionRequest,
        actor_user_id: Optional[uuid.UUID] = None,
    ) -> Dict[str, Any]:
        """
        Promotes, graduates, or transfers a cohort of students to a new session/class/semester.
        """
        target_session = (await self.session.execute(
            select(AcademicSession).where(
                AcademicSession.tenant_id == tenant_id,
                AcademicSession.id == payload.target_academic_session_id,
            )
        )).scalar_one_or_none()
        if not target_session:
            raise AppException(404, "SESSION_NOT_FOUND", "Target academic session not found")

        promoted_count = 0
        now = datetime.now(timezone.utc)

        for sid in payload.student_ids:
            student = await self.repo.get_student_by_id(tenant_id, sid)
            if not student:
                continue

            # Update student record
            student.academic_session_id = payload.target_academic_session_id
            if payload.target_class_id is not None:
                student.class_id = payload.target_class_id
            if payload.target_section_id is not None:
                student.section_id = payload.target_section_id
            if payload.target_course_id is not None:
                student.course_id = payload.target_course_id
            if payload.target_semester is not None:
                student.semester = payload.target_semester

            if payload.action == "GRADUATE":
                student.status = "GRADUATED"
            elif payload.action == "TRANSFER":
                student.status = "TRANSFERRED"
            else:
                student.status = "ACTIVE"

            # Create history record
            history = StudentEnrollmentHistory(
                tenant_id=tenant_id,
                student_id=student.id,
                academic_session_id=payload.target_academic_session_id,
                class_id=student.class_id,
                section_id=student.section_id,
                department_id=student.department_id,
                course_id=student.course_id,
                semester=student.semester,
                roll_number=student.roll_number,
                enrollment_status=payload.action,
                remarks=payload.remarks or f"Batch {payload.action} operation on {now.strftime('%Y-%m-%d')}",
            )
            self.session.add(history)
            promoted_count += 1

        await self.repo.log_audit(
            tenant_id=tenant_id,
            user_id=actor_user_id,
            action=f"STUDENTS_{payload.action}",
            entity_id="BATCH",
            changes={
                "count": promoted_count,
                "target_session_id": str(payload.target_academic_session_id),
                "action": payload.action,
            },
        )
        await self.session.commit()

        return {
            "success": True,
            "action": payload.action,
            "processed_students": promoted_count,
            "message": f"Successfully processed {promoted_count} students for {payload.action.lower()}.",
        }

    # ── Document Management ───────────────────────────────────────────────────
    async def upload_document(
        self,
        tenant_id: uuid.UUID,
        student_id: uuid.UUID,
        payload: StudentDocumentCreateRequest,
        actor_user_id: Optional[uuid.UUID] = None,
    ) -> StudentDocument:
        student = await self.repo.get_student_by_id(tenant_id, student_id)
        if not student:
            raise AppException(404, "STUDENT_NOT_FOUND", "Student not found")

        doc = StudentDocument(
            tenant_id=tenant_id,
            student_id=student_id,
            document_type=payload.document_type,
            document_name=payload.document_name,
            file_url=payload.file_url,
            file_size_bytes=payload.file_size_bytes,
            mime_type=payload.mime_type,
        )
        self.session.add(doc)
        await self.session.commit()
        await self.session.refresh(doc)
        return doc

    # ── Student ID Card Generator ─────────────────────────────────────────────
    async def generate_id_card(
        self, tenant_id: uuid.UUID, student_id: uuid.UUID
    ) -> StudentIDCardResponse:
        student = await self.get_student_detail(tenant_id, student_id)
        tenant = (await self.session.execute(select(Tenant).where(Tenant.id == tenant_id))).scalar_one_or_none()
        institution_name = tenant.name if tenant else "Educational Institution"

        class_or_course = student.class_name or student.course_name or "Standard"
        section_or_semester = f"Sec {student.section_name}" if student.section_name else (f"Sem {student.semester}" if student.semester else "Batch")
        barcode_data = f"ID:{student.admission_number}|INST:{tenant.slug if tenant else 'CRM'}"
        session_end = await self.session.scalar(
            select(AcademicSession.end_date).where(
                AcademicSession.id == student.academic_session_id,
                AcademicSession.tenant_id == tenant_id,
            )
        ) if student.academic_session_id else None

        return StudentIDCardResponse(
            student_id=student.id,
            full_name=student.full_name,
            admission_number=student.admission_number,
            roll_number=student.roll_number,
            photo_url=student_photo_url(student.photo_url, tenant_id),
            institution_name=institution_name,
            institution_logo_url=tenant.logo_url if tenant else None,
            institution_address=", ".join(filter(None, (tenant.city, tenant.state))) if tenant else "",
            class_or_course=class_or_course,
            section_or_semester=section_or_semester,
            academic_session=student.academic_session_name,
            blood_group=student.blood_group,
            emergency_contact=student.emergency_contact_phone or student.parent_phone,
            barcode_data=barcode_data,
            valid_until=session_end.strftime("%d %b %Y") if session_end else "Not specified",
        )

    async def generate_id_card_html(self, tenant_id: uuid.UUID, student_id: uuid.UUID) -> str:
        card = await self.generate_id_card(tenant_id, student_id)
        admission_number = escape(card.admission_number)
        image = card.photo_url or ""
        photo = (
            f'<img class="photo" src="{escape(image, quote=True)}" alt="Student photo" referrerpolicy="no-referrer">'
            if image.startswith(("https://", "http://")) or (image.startswith("/") and not image.startswith("//"))
            else '<div class="photo" role="img" aria-label="No student photo"></div>'
        )

        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>Student ID Card - {admission_number}</title>
            <style>
                body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; display: flex; justify-content: center; align-items: center; min-height: 100vh; margin: 0; background: #f1f5f9; }}
                .id-card {{ width: 340px; height: 520px; background: white; border-radius: 16px; box-shadow: 0 10px 25px -5px rgba(0,0,0,0.1); overflow: hidden; position: relative; border: 1px solid #cbd5e1; }}
                .header {{ background: linear-gradient(135deg, #0284c7 0%, #0369a1 100%); color: white; padding: 20px 16px; text-align: center; }}
                .inst-name {{ font-size: 16px; font-weight: 800; text-transform: uppercase; letter-spacing: 0.5px; margin: 0; }}
                .inst-sub {{ font-size: 11px; opacity: 0.85; margin: 2px 0 0; }}
                .photo-wrapper {{ display: flex; justify-content: center; margin-top: -30px; }}
                .photo {{ width: 95px; height: 95px; border-radius: 50%; border: 4px solid white; object-fit: cover; background: #e2e8f0; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1); }}
                .details {{ padding: 12px 24px; text-align: center; }}
                .name {{ font-size: 18px; font-weight: 800; color: #0f172a; margin: 4px 0 2px; }}
                .adm-badge {{ display: inline-block; background: #e0f2fe; color: #0369a1; padding: 2px 10px; border-radius: 9999px; font-size: 12px; font-weight: 700; margin-bottom: 12px; }}
                .info-grid {{ width: 100%; font-size: 12px; text-align: left; margin: 8px 0; border-collapse: collapse; }}
                .info-grid td {{ padding: 4px 0; }}
                .info-label {{ color: #64748b; font-weight: 600; width: 45%; }}
                .info-val {{ color: #1e293b; font-weight: 700; }}
                .footer {{ position: absolute; bottom: 0; width: 100%; background: #f8fafc; border-top: 1px solid #e2e8f0; padding: 12px; text-align: center; box-sizing: border-box; }}
                .barcode {{ font-family: monospace; letter-spacing: 3px; font-size: 14px; font-weight: bold; color: #334155; }}
            </style>
        </head>
        <body>
            <div class="id-card">
                <div class="header">
                    <h2 class="inst-name">{escape(card.institution_name)}</h2>
                    <p class="inst-sub">Student Identification Card</p>
                </div>
                <div class="photo-wrapper">
                    {photo}
                </div>
                <div class="details">
                    <div class="name">{escape(card.full_name)}</div>
                    <div class="adm-badge">{admission_number}</div>
                    <table class="info-grid">
                        <tr><td class="info-label">Class / Course:</td><td class="info-val">{escape(card.class_or_course)}</td></tr>
                        <tr><td class="info-label">Section / Sem:</td><td class="info-val">{escape(card.section_or_semester)}</td></tr>
                        <tr><td class="info-label">Roll Number:</td><td class="info-val">{escape(card.roll_number or '—')}</td></tr>
                        <tr><td class="info-label">Blood Group:</td><td class="info-val">{escape(card.blood_group or '—')}</td></tr>
                        <tr><td class="info-label">Emergency Phone:</td><td class="info-val">{escape(card.emergency_contact or '—')}</td></tr>
                    </table>
                </div>
                <div class="footer">
                    <div class="barcode">{admission_number}</div>
                    <div style="font-size: 10px; color: #94a3b8; margin-top: 4px;">Valid Thru: {escape(str(card.valid_until))}</div>
                </div>
            </div>
        </body>
        </html>
        """

    # ── Export Students CSV ───────────────────────────────────────────────────
    async def export_students_csv(
        self,
        tenant_id: uuid.UUID,
        class_id: Optional[uuid.UUID] = None,
        section_id: Optional[uuid.UUID] = None,
        status: Optional[str] = None,
        teacher_user_id: Optional[uuid.UUID] = None,
        search: Optional[str] = None,
        department_id: Optional[uuid.UUID] = None,
        course_id: Optional[uuid.UUID] = None,
        semester: Optional[int] = None,
    ) -> str:
        students, _ = await self.repo.list_students(
            tenant_id=tenant_id,
            search=search,
            class_id=class_id,
            section_id=section_id,
            department_id=department_id,
            course_id=course_id,
            semester=semester,
            status=status,
            page=1,
            size=10000,
            teacher_user_id=teacher_user_id,
        )

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([
            "Admission Number",
            "Full Name",
            "Email",
            "Phone",
            "Gender",
            "Class / Course",
            "Section / Semester",
            "Roll Number",
            "Parent Name",
            "Parent Phone",
            "Status",
            "Admission Date",
        ])

        for s in students:
            writer.writerow([
                s.admission_number,
                s.user.full_name if s.user else "",
                s.user.email if s.user else "",
                s.user.phone if s.user else "",
                s.gender or "",
                s.school_class.name if s.school_class else (s.course.name if s.course else ""),
                s.section.name if s.section else (f"Sem {s.semester}" if s.semester else ""),
                s.roll_number or "",
                s.parent_name or "",
                s.parent_phone or "",
                s.status,
                s.admission_date.isoformat() if s.admission_date else "",
            ])

        return output.getvalue()

    # ── Bulk Import CSV ───────────────────────────────────────────────────────
    async def bulk_import_students(
        self,
        tenant_id: uuid.UUID,
        csv_content: str,
        actor_user_id: Optional[uuid.UUID] = None,
    ) -> BulkImportSummaryResponse:
        f = io.StringIO(csv_content)
        reader = csv.DictReader(f)

        rows = list(reader)
        total = len(rows)

        # Quota check
        await self.entitlement_service.check_quota(tenant_id, "students", increment=total)

        successful = 0
        failed = 0
        errors: List[Dict[str, Any]] = []

        # Cache classes and sections
        classes = (await self.session.execute(select(SchoolClass).where(SchoolClass.tenant_id == tenant_id))).scalars().all()
        class_map = {c.name.strip().lower(): c.id for c in classes}
        class_map.update({c.code.strip().lower(): c.id for c in classes})

        sections = (await self.session.execute(select(Section).where(Section.tenant_id == tenant_id))).scalars().all()
        section_map = {s.name.strip().lower(): s.id for s in sections}

        for idx, row in enumerate(rows, start=1):
            full_name = row.get("full_name") or row.get("name")
            if not full_name:
                failed += 1
                errors.append({"row": idx, "error": "Missing full_name"})
                continue

            adm_num = row.get("admission_number")
            email = row.get("email")

            try:
                class_id = None
                class_name = row.get("class") or row.get("class_name")
                if class_name and class_name.strip().lower() in class_map:
                    class_id = class_map[class_name.strip().lower()]

                section_id = None
                sec_name = row.get("section") or row.get("section_name")
                if sec_name and sec_name.strip().lower() in section_map:
                    section_id = section_map[sec_name.strip().lower()]

                create_req = StudentCreateRequest(
                    full_name=full_name.strip(),
                    email=email.strip().lower() if email else None,
                    phone=row.get("phone"),
                    admission_number=adm_num.strip() if adm_num else None,
                    roll_number=row.get("roll_number"),
                    gender=row.get("gender"),
                    class_id=class_id,
                    section_id=section_id,
                    parent_name=row.get("parent_name") or row.get("father_name"),
                    parent_phone=row.get("parent_phone") or row.get("father_phone"),
                    city=row.get("city"),
                    state=row.get("state"),
                )
                await self.create_student(tenant_id, create_req, actor_user_id)
                successful += 1
            except Exception as e:
                failed += 1
                errors.append({"row": idx, "name": full_name, "error": str(e)})

        return BulkImportSummaryResponse(
            total_processed=total,
            successful=successful,
            failed=failed,
            errors=errors,
        )
