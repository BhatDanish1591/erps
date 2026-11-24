from __future__ import annotations

import hashlib
import secrets
import uuid
from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import and_, delete, desc, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import set_database_context, set_tenant_session_context
from app.core.security import generate_secure_token, hash_password, hash_token
from app.models.academic import (
    AcademicSession,
    Course,
    Department,
    SchoolClass,
    Section,
    StudentProfile,
    Subject,
    TeacherProfile,
)
from app.models.auth import Membership, Role
from app.models.enums import InstitutionType, MembershipStatus, RoleScope, SessionStatus, SubscriptionStatus, TenantStatus
from app.models.invitation import Invitation
from app.models.subscription import Subscription, SubscriptionPlan
from app.models.tenant import Tenant, TenantDomain, TenantSetting
from app.models.user import User


class InstitutionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def is_slug_available(self, slug: str) -> bool:
        stmt = select(Tenant.id).where(Tenant.slug == slug)
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none() is None

    async def register_institution(
        self, data: Dict[str, Any]
    ) -> Tuple[Tenant, Invitation, str]:
        # 1. Create Tenant with PENDING status
        tenant = Tenant(
            name=data["name"],
            slug=data["slug"],
            institution_type=InstitutionType(data["institution_type"]),
            status=TenantStatus.PENDING,
            email=data["email"],
            phone=data.get("phone"),
            address=data.get("address"),
            city=data.get("city"),
            state=data.get("state"),
            country=data.get("country", "India"),
            postal_code=data.get("postal_code"),
            logo_url=data.get("logo_url"),
        )
        self.session.add(tenant)
        await self.session.flush()
        await set_tenant_session_context(self.session, tenant.id)

        # 2. Create primary domain: {slug}.edusaas.com
        domain = TenantDomain(
            tenant_id=tenant.id,
            domain=f"{tenant.slug}.edusaas.com",
            is_primary=True,
            is_verified=True,
        )
        self.session.add(domain)

        # 3. Save Principal details in TenantSetting
        principal_setting = TenantSetting(
            tenant_id=tenant.id,
            key="principal_details",
            value={
                "name": data["principal_name"],
                "email": data["principal_email"],
                "phone": data.get("principal_phone"),
            },
            is_public=False,
        )
        self.session.add(principal_setting)

        # 4. Save Initial Onboarding Progress
        onboarding_setting = TenantSetting(
            tenant_id=tenant.id,
            key="onboarding_progress",
            value={
                "is_completed": False,
                "current_step": 1,
                "steps": {
                    "profile": True,
                    "academic_session": False,
                    "structure": False,
                    "subjects": False,
                    "teachers": False,
                    "students": False,
                    "notifications": False,
                },
            },
            is_public=False,
        )
        self.session.add(onboarding_setting)

        # 5. Attach trial/plan subscription if plan_id provided
        if data.get("plan_id"):
            plan = (await self.session.execute(
                select(SubscriptionPlan).where(SubscriptionPlan.id == data["plan_id"])
            )).scalar_one_or_none()
            if plan:
                now = datetime.now(timezone.utc)
                sub = Subscription(
                    tenant_id=tenant.id,
                    plan_id=plan.id,
                    status=SubscriptionStatus.TRIAL,
                    billing_cycle=plan.billing_cycle,
                    current_period_start=now,
                    current_period_end=now + timedelta(days=30),
                    trial_ends_at=now + timedelta(days=30),
                    is_auto_renew=False,
                )
                self.session.add(sub)

        # 6. Find or resolve INSTITUTION_ADMIN role
        role = (await self.session.execute(
            select(Role).where(Role.code == "INSTITUTION_ADMIN")
        )).scalars().first()
        if not role:
            role = Role(
                name="Institution Admin",
                code="INSTITUTION_ADMIN",
                scope=RoleScope.TENANT,
                is_system_role=True,
            )
            self.session.add(role)
            await self.session.flush()

        # 7. Generate secure token for the First Administrator
        plain_token = generate_secure_token(32)
        token_hashed = hash_token(plain_token)

        invitation = Invitation(
            tenant_id=tenant.id,
            email=data["principal_email"],
            role_id=role.id,
            token_hash=token_hashed,
            first_name=data["principal_name"],
            status="PENDING",
            expires_at=datetime.now(timezone.utc) + timedelta(days=7),
        )
        self.session.add(invitation)
        await self.session.flush()

        return tenant, invitation, plain_token

    async def get_invitation_by_token(self, plain_token: str) -> Optional[Invitation]:
        t_hash = hash_token(plain_token)
        await set_database_context(self.session, invitation_token_hash=t_hash)
        now = datetime.now(timezone.utc)
        stmt = (
            select(Invitation)
            .options(selectinload(Invitation.tenant), selectinload(Invitation.role))
            .where(
                Invitation.token_hash == t_hash,
                Invitation.status == "PENDING",
                Invitation.expires_at > now,
            )
        )
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def accept_invitation(
        self, invitation: Invitation, password: str, full_name: Optional[str] = None, phone: Optional[str] = None
    ) -> Tuple[User, Membership]:
        now = datetime.now(timezone.utc)
        await set_tenant_session_context(self.session, invitation.tenant_id)

        # Check if user already exists
        user = (await self.session.execute(
            select(User).where(User.email == invitation.email)
        )).scalar_one_or_none()

        if not user:
            name_to_use = full_name or invitation.first_name or invitation.email.split("@")[0]
            user = User(
                email=invitation.email,
                password_hash=hash_password(password),
                full_name=name_to_use,
                phone=phone or invitation.phone,
                is_active=True,
                email_verified_at=now,
            )
            self.session.add(user)
            await self.session.flush()

        # Check existing membership
        existing_mem = (await self.session.execute(
            select(Membership).where(
                Membership.tenant_id == invitation.tenant_id,
                Membership.user_id == user.id,
            )
        )).scalar_one_or_none()

        if existing_mem:
            existing_mem.status = MembershipStatus.ACTIVE
            membership = existing_mem
        else:
            membership = Membership(
                tenant_id=invitation.tenant_id,
                user_id=user.id,
                role_id=invitation.role_id,
                status=MembershipStatus.ACTIVE,
            )
            self.session.add(membership)

        # Mark invitation accepted
        invitation.status = "ACCEPTED"
        invitation.accepted_at = now
        await self.session.flush()

        return user, membership

    async def get_tenant_profile(self, tenant_id: uuid.UUID) -> Optional[Tenant]:
        stmt = (
            select(Tenant)
            .options(selectinload(Tenant.domains), selectinload(Tenant.settings))
            .where(Tenant.id == tenant_id, Tenant.is_deleted.is_(False))
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def update_tenant_profile(self, tenant_id: uuid.UUID, updates: Dict[str, Any]) -> Tenant:
        stmt = select(Tenant).where(Tenant.id == tenant_id, Tenant.is_deleted.is_(False))
        tenant = (await self.session.execute(stmt)).scalar_one()
        for k, v in updates.items():
            if v is not None:
                setattr(tenant, k, v)
        await self.session.flush()
        return tenant

    # ── Onboarding Wizard Steps ───────────────────────────────────────────────
    async def get_onboarding_progress(self, tenant_id: uuid.UUID) -> Dict[str, Any]:
        stmt = select(TenantSetting).where(
            TenantSetting.tenant_id == tenant_id, TenantSetting.key == "onboarding_progress"
        )
        setting = (await self.session.execute(stmt)).scalar_one_or_none()
        if not setting:
            return {
                "is_completed": False,
                "current_step": 1,
                "steps": {
                    "profile": False,
                    "academic_session": False,
                    "structure": False,
                    "subjects": False,
                    "teachers": False,
                    "students": False,
                    "notifications": False,
                },
            }
        return setting.value

    async def update_onboarding_progress(
        self, tenant_id: uuid.UUID, step_name: str, step_number: int, is_completed: bool = False
    ) -> None:
        setting = (await self.session.execute(
            select(TenantSetting).where(
                TenantSetting.tenant_id == tenant_id, TenantSetting.key == "onboarding_progress"
            )
        )).scalar_one_or_none()

        if setting:
            val = dict(setting.value)
            steps = val.get("steps", {})
            steps[step_name] = True
            val["steps"] = steps
            val["current_step"] = step_number
            if is_completed:
                val["is_completed"] = True
            setting.value = val
        else:
            setting = TenantSetting(
                tenant_id=tenant_id,
                key="onboarding_progress",
                value={
                    "is_completed": is_completed,
                    "current_step": step_number,
                    "steps": {step_name: True},
                },
            )
            self.session.add(setting)
        await self.session.flush()

    async def save_academic_session(
        self, tenant_id: uuid.UUID, name: str, code: str, start_date: date, end_date: date
    ) -> AcademicSession:
        # Mark previous sessions as not current
        await self.session.execute(
            update(AcademicSession)
            .where(AcademicSession.tenant_id == tenant_id)
            .values(is_current=False)
        )
        session = AcademicSession(
            tenant_id=tenant_id,
            name=name,
            code=code,
            start_date=start_date,
            end_date=end_date,
            is_current=True,
            status=SessionStatus.ACTIVE,
        )
        self.session.add(session)
        await self.session.flush()
        return session

    async def save_classes_and_sections(
        self, tenant_id: uuid.UUID, items: List[Dict[str, Any]]
    ) -> List[SchoolClass]:
        classes: List[SchoolClass] = []
        for idx, item in enumerate(items):
            cls_record = SchoolClass(
                tenant_id=tenant_id,
                name=item["name"],
                code=item["code"],
                order_index=idx + 1,
            )
            self.session.add(cls_record)
            await self.session.flush()

            for sec_name in item.get("sub_items", ["A"]):
                sec = Section(
                    tenant_id=tenant_id,
                    class_id=cls_record.id,
                    name=sec_name,
                    capacity=40,
                )
                self.session.add(sec)
            classes.append(cls_record)
        await self.session.flush()
        return classes

    async def save_departments_and_courses(
        self, tenant_id: uuid.UUID, items: List[Dict[str, Any]]
    ) -> List[Department]:
        depts: List[Department] = []
        for item in items:
            dept = Department(
                tenant_id=tenant_id,
                name=item["name"],
                code=item["code"],
            )
            self.session.add(dept)
            await self.session.flush()

            for course_name in item.get("sub_items", []):
                course_code = f"{dept.code}-{course_name[:4].upper()}"
                crs = Course(
                    tenant_id=tenant_id,
                    department_id=dept.id,
                    name=course_name,
                    code=course_code,
                    duration_semesters=8,
                )
                self.session.add(crs)
            depts.append(dept)
        await self.session.flush()
        return depts

    async def save_subjects(self, tenant_id: uuid.UUID, subjects: List[Dict[str, Any]]) -> List[Subject]:
        records = []
        for s in subjects:
            rec = Subject(
                tenant_id=tenant_id,
                name=s["name"],
                code=s["code"],
                subject_type=s.get("subject_type", "THEORY"),
                credits=s.get("credits", 3),
            )
            self.session.add(rec)
            records.append(rec)
        await self.session.flush()
        return records

    async def bulk_invite_teachers(
        self, tenant_id: uuid.UUID, teachers: List[Dict[str, Any]], invited_by: Optional[uuid.UUID]
    ) -> List[Invitation]:
        role = (await self.session.execute(
            select(Role).where(Role.code == "TEACHER")
        )).scalars().first()

        invites = []
        now = datetime.now(timezone.utc)
        for t in teachers:
            token = generate_secure_token(32)
            token_hashed = hash_token(token)
            inv = Invitation(
                tenant_id=tenant_id,
                email=t["email"],
                role_id=role.id,
                token_hash=token_hashed,
                first_name=t["full_name"],
                phone=t.get("phone"),
                invited_by_user_id=invited_by,
                status="PENDING",
                expires_at=now + timedelta(days=14),
            )
            self.session.add(inv)
            invites.append(inv)
        await self.session.flush()
        return invites

    async def bulk_import_students(
        self, tenant_id: uuid.UUID, rows: List[Dict[str, Any]]
    ) -> Tuple[int, int, List[str]]:
        role = (await self.session.execute(
            select(Role).where(Role.code == "STUDENT")
        )).scalars().first()

        imported = 0
        skipped = 0
        errors = []
        now = datetime.now(timezone.utc)

        for row in rows:
            try:
                email = row["email"].strip().lower()
                adm_no = str(row["admission_number"]).strip()

                # Check if student admission number exists in this tenant
                existing = (await self.session.execute(
                    select(StudentProfile.id).where(
                        StudentProfile.tenant_id == tenant_id,
                        StudentProfile.admission_number == adm_no,
                    )
                )).scalar_one_or_none()

                if existing:
                    skipped += 1
                    errors.append(f"Admission number {adm_no} already exists. Skipped.")
                    continue

                # Find or create User
                user = (await self.session.execute(
                    select(User).where(User.email == email)
                )).scalar_one_or_none()

                if not user:
                    user = User(
                        email=email,
                        password_hash=hash_password("Welcome123!"),  # Temporary initial password
                        full_name=row["full_name"],
                        is_active=True,
                    )
                    self.session.add(user)
                    await self.session.flush()

                # Create Membership
                mem = Membership(
                    tenant_id=tenant_id,
                    user_id=user.id,
                    role_id=role.id,
                    status=MembershipStatus.ACTIVE,
                )
                self.session.add(mem)

                # Create StudentProfile
                profile = StudentProfile(
                    tenant_id=tenant_id,
                    user_id=user.id,
                    admission_number=adm_no,
                    gender=row.get("gender"),
                    parent_name=row.get("parent_name"),
                    parent_phone=row.get("parent_phone"),
                    status="ACTIVE",
                )
                self.session.add(profile)
                imported += 1
            except Exception as e:
                skipped += 1
                errors.append(f"Row {row.get('admission_number')}: {str(e)}")

        await self.session.flush()
        return imported, skipped, errors

    async def list_custom_domains(self, tenant_id: uuid.UUID) -> List[TenantDomain]:
        stmt = select(TenantDomain).where(TenantDomain.tenant_id == tenant_id)
        return list((await self.session.execute(stmt)).scalars().all())

    async def add_custom_domain(self, tenant_id: uuid.UUID, domain_name: str) -> TenantDomain:
        td = TenantDomain(
            tenant_id=tenant_id,
            domain=domain_name.strip().lower(),
            is_primary=False,
            is_verified=False,
        )
        self.session.add(td)
        await self.session.flush()
        return td
