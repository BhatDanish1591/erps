from __future__ import annotations

import csv
import io
import uuid
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppException
from app.models.academic import AcademicSession
from app.models.enums import InstitutionType
from app.models.invitation import Invitation
from app.models.tenant import Tenant, TenantDomain, TenantSetting
from app.models.user import User
from app.repositories.institution import InstitutionRepository
from app.repositories.super_admin import SuperAdminRepository
from app.schemas.institution import (
    AcademicSessionSetupRequest,
    BulkImportResponse,
    BulkTeacherInviteRequest,
    CheckSubdomainResponse,
    InstitutionProfileUpdate,
    InstitutionRegistrationRequest,
    OnboardingNotificationSetupRequest,
    OnboardingStructureSetupRequest,
    OnboardingSubjectsSetupRequest,
)


class InstitutionService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = InstitutionRepository(session)
        self.audit_repo = SuperAdminRepository(session)

    async def check_subdomain(self, slug: str) -> CheckSubdomainResponse:
        clean_slug = slug.strip().lower()
        is_avail = await self.repo.is_slug_available(clean_slug)
        suggestion = None if is_avail else f"{clean_slug}-{uuid.uuid4().hex[:4]}"
        return CheckSubdomainResponse(slug=clean_slug, available=is_avail, suggestion=suggestion)

    async def register_institution(
        self, payload: InstitutionRegistrationRequest, ip_address: Optional[str] = None
    ) -> Dict[str, Any]:
        # Validate slug availability
        clean_slug = payload.slug.strip().lower()
        if not await self.repo.is_slug_available(clean_slug):
            raise AppException(409, "SLUG_TAKEN", f"Subdomain slug '{clean_slug}' is already registered.")

        data = payload.model_dump()
        data["slug"] = clean_slug
        tenant, invitation, plain_token = await self.repo.register_institution(data)

        # Record audit log
        await self.audit_repo.record_audit_log(
            action="INSTITUTION_REGISTERED",
            entity_type="TENANT",
            entity_id=str(tenant.id),
            user_id=None,
            tenant_id=tenant.id,
            changes={
                "name": tenant.name,
                "slug": tenant.slug,
                "type": tenant.institution_type.value,
                "principal_email": payload.principal_email,
            },
            ip_address=ip_address,
        )

        return {
            "tenant_id": str(tenant.id),
            "name": tenant.name,
            "slug": tenant.slug,
            "status": tenant.status.value,
            "invitation_token": plain_token,  # Provided for immediate verification or email dispatch
            "message": "Institution registered successfully. Status is PENDING platform approval.",
        }

    async def verify_invitation(self, token: str) -> Dict[str, Any]:
        invitation = await self.repo.get_invitation_by_token(token)
        if not invitation:
            return {"valid": False, "message": "Invalid or expired invitation token."}

        return {
            "valid": True,
            "email": invitation.email,
            "institution_name": invitation.tenant.name,
            "institution_slug": invitation.tenant.slug,
            "role_name": invitation.role.name,
            "first_name": invitation.first_name,
            "last_name": invitation.last_name,
        }

    async def accept_invitation(
        self, token: str, password: str, full_name: Optional[str] = None, phone: Optional[str] = None
    ) -> Dict[str, Any]:
        invitation = await self.repo.get_invitation_by_token(token)
        if not invitation:
            raise AppException(message="Invalid or expired invitation token.", code="INVALID_INVITATION")

        user, membership = await self.repo.accept_invitation(invitation, password, full_name, phone)

        # Record audit log
        await self.audit_repo.record_audit_log(
            action="INVITATION_ACCEPTED",
            entity_type="MEMBERSHIP",
            entity_id=str(membership.id),
            user_id=user.id,
            tenant_id=invitation.tenant_id,
            changes={"email": user.email, "role": invitation.role.name},
        )

        return {
            "user_id": str(user.id),
            "email": user.email,
            "tenant_id": str(invitation.tenant_id),
            "membership_id": str(membership.id),
            "message": "Account successfully activated.",
        }

    async def get_profile(self, tenant_id: uuid.UUID) -> Dict[str, Any]:
        tenant = await self.repo.get_tenant_profile(tenant_id)
        if not tenant:
            raise AppException(message="Institution not found.", code="NOT_FOUND")

        return {
            "id": str(tenant.id),
            "name": tenant.name,
            "slug": tenant.slug,
            "institution_type": tenant.institution_type.value,
            "status": tenant.status.value,
            "email": tenant.email,
            "phone": tenant.phone,
            "address": tenant.address,
            "city": tenant.city,
            "state": tenant.state,
            "country": tenant.country,
            "postal_code": tenant.postal_code,
            "logo_url": tenant.logo_url,
            "timezone": tenant.timezone,
            "currency": tenant.currency,
            "domains": [d.domain for d in tenant.domains],
        }

    async def update_profile(self, tenant_id: uuid.UUID, payload: InstitutionProfileUpdate) -> Dict[str, Any]:
        updates = payload.model_dump(exclude_unset=True)
        tenant = await self.repo.update_tenant_profile(tenant_id, updates)
        return {"id": str(tenant.id), "name": tenant.name, "message": "Profile updated successfully."}

    # ── Onboarding Wizard Steps ───────────────────────────────────────────────
    async def get_onboarding_status(self, tenant_id: uuid.UUID) -> Dict[str, Any]:
        tenant = await self.repo.get_tenant_profile(tenant_id)
        if not tenant:
            raise AppException(message="Institution not found.", code="NOT_FOUND")

        progress = await self.repo.get_onboarding_progress(tenant_id)
        return {
            "tenant_id": str(tenant.id),
            "institution_name": tenant.name,
            "institution_type": tenant.institution_type.value,
            "is_completed": progress.get("is_completed", False),
            "current_step": progress.get("current_step", 1),
            "steps_status": progress.get("steps", {}),
        }

    async def setup_academic_session(
        self, tenant_id: uuid.UUID, payload: AcademicSessionSetupRequest
    ) -> AcademicSession:
        session = await self.repo.save_academic_session(
            tenant_id=tenant_id,
            name=payload.name,
            code=payload.code,
            start_date=payload.start_date,
            end_date=payload.end_date,
        )
        await self.repo.update_onboarding_progress(tenant_id, "academic_session", 3)
        return session

    async def setup_structure(
        self, tenant_id: uuid.UUID, payload: OnboardingStructureSetupRequest
    ) -> Dict[str, Any]:
        tenant = await self.repo.get_tenant_profile(tenant_id)
        is_school = tenant.institution_type == InstitutionType.SCHOOL if tenant else True

        items_data = [item.model_dump() for item in payload.items]
        if is_school:
            res = await self.repo.save_classes_and_sections(tenant_id, items_data)
        else:
            res = await self.repo.save_departments_and_courses(tenant_id, items_data)

        await self.repo.update_onboarding_progress(tenant_id, "structure", 4)
        return {"count": len(res), "message": "Academic hierarchy saved successfully."}

    async def setup_subjects(
        self, tenant_id: uuid.UUID, payload: OnboardingSubjectsSetupRequest
    ) -> Dict[str, Any]:
        subjects_data = [s.model_dump() for s in payload.subjects]
        records = await self.repo.save_subjects(tenant_id, subjects_data)
        await self.repo.update_onboarding_progress(tenant_id, "subjects", 5)
        return {"count": len(records), "message": "Subjects configured successfully."}

    async def invite_teachers(
        self, tenant_id: uuid.UUID, payload: BulkTeacherInviteRequest, user_id: Optional[uuid.UUID]
    ) -> Dict[str, Any]:
        teachers_data = [t.model_dump() for t in payload.teachers]
        invites = await self.repo.bulk_invite_teachers(tenant_id, teachers_data, user_id)
        await self.repo.update_onboarding_progress(tenant_id, "teachers", 6)
        return {"invited_count": len(invites), "message": f"{len(invites)} teacher invitations issued."}

    async def setup_notifications(
        self, tenant_id: uuid.UUID, payload: OnboardingNotificationSetupRequest
    ) -> Dict[str, Any]:
        from app.models.tenant import TenantSetting
        setting = (await self.session.execute(
            TenantSetting.__table__.select().where(
                TenantSetting.tenant_id == tenant_id, TenantSetting.key == "notification_preferences"
            )
        )).first()

        data = payload.model_dump()
        if setting:
            await self.session.execute(
                TenantSetting.__table__.update()
                .where(TenantSetting.tenant_id == tenant_id, TenantSetting.key == "notification_preferences")
                .values(value=data)
            )
        else:
            ns = TenantSetting(
                tenant_id=tenant_id,
                key="notification_preferences",
                value=data,
                is_public=False,
            )
            self.session.add(ns)

        await self.repo.update_onboarding_progress(tenant_id, "notifications", 7)
        return {"success": True, "message": "Notification preferences saved."}

    async def complete_onboarding(self, tenant_id: uuid.UUID) -> Dict[str, Any]:
        await self.repo.update_onboarding_progress(tenant_id, "completed", 8, is_completed=True)
        return {"success": True, "message": "Institution onboarding completed successfully!"}

    # ── Bulk Import Templates & CSV Parsing ───────────────────────────────────
    def get_template_csv(self, import_type: str) -> str:
        output = io.StringIO()
        writer = csv.writer(output)
        if import_type.lower() == "students":
            writer.writerow([
                "admission_number",
                "full_name",
                "email",
                "gender",
                "class_or_department",
                "section_or_course",
                "parent_name",
                "parent_phone",
            ])
            writer.writerow([
                "ADM-2026-001",
                "Aarav Sharma",
                "aarav.sharma@example.com",
                "Male",
                "Class 10",
                "A",
                "Rajesh Sharma",
                "+919876543210",
            ])
            writer.writerow([
                "ADM-2026-002",
                "Diya Patel",
                "diya.patel@example.com",
                "Female",
                "Class 10",
                "B",
                "Suresh Patel",
                "+919876543211",
            ])
        else:  # Teachers
            writer.writerow(["email", "full_name", "phone", "designation", "department_name"])
            writer.writerow(["rahul.verma@example.com", "Dr. Rahul Verma", "+919876500001", "Senior Lecturer", "Mathematics"])
            writer.writerow(["priya.nair@example.com", "Priya Nair", "+919876500002", "Assistant Professor", "Physics"])

        return output.getvalue()

    async def parse_and_import_students(
        self, tenant_id: uuid.UUID, csv_content: str
    ) -> BulkImportResponse:
        f = io.StringIO(csv_content)
        reader = csv.DictReader(f)
        rows: List[Dict[str, Any]] = []

        for row in reader:
            if not row.get("admission_number") or not row.get("full_name") or not row.get("email"):
                continue
            rows.append({
                "admission_number": row["admission_number"],
                "full_name": row["full_name"],
                "email": row["email"],
                "gender": row.get("gender"),
                "class_or_department": row.get("class_or_department", "Default"),
                "section_or_course": row.get("section_or_course", "A"),
                "parent_name": row.get("parent_name"),
                "parent_phone": row.get("parent_phone"),
            })

        imported, skipped, errors = await self.repo.bulk_import_students(tenant_id, rows)
        await self.repo.update_onboarding_progress(tenant_id, "students", 7)

        return BulkImportResponse(
            total_rows=len(rows),
            imported_count=imported,
            skipped_count=skipped,
            errors=errors,
        )
