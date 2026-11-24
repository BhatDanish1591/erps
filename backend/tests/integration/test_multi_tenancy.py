from __future__ import annotations

import datetime
import uuid
import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import set_tenant_session_context
from app.core.tenant_context import reset_current_tenant_id, set_current_tenant_id
from app.models.academic import AcademicSession
from app.models.enums import InstitutionType, SessionStatus, TenantStatus
from app.models.tenant import Tenant, TenantSetting
from app.repositories.academic import AcademicSessionRepository
from app.repositories.tenant import TenantRepository, TenantSettingRepository


@pytest.mark.asyncio
async def test_multi_tenant_isolation_and_cross_tenant_prevention(db_session: AsyncSession):
    """
    Test Multi-Tenancy Architecture:
    1. Create two separate tenants (School A and College B).
    2. Create records (Academic Sessions, Tenant Settings) in each tenant.
    3. Verify that queries scoped to Tenant A can NEVER read, update, or delete Tenant B's data.
    4. Verify that Tenant B can NEVER read, update, or delete Tenant A's data.
    5. Verify PostgreSQL session transaction-local configuration 'app.current_tenant_id'.
    """
    tenant_repo = TenantRepository(db_session)

    # ── 1. Create Institution 1 (School) ──────────────────────────────────────
    school = await tenant_repo.create(
        name="Oakridge International School",
        slug=f"oakridge-{uuid.uuid4().hex[:6]}",
        institution_type=InstitutionType.SCHOOL,
        status=TenantStatus.ACTIVE,
        email="admin@oakridge.edu",
    )
    school_id = school.id

    # ── 2. Create Institution 2 (College) ─────────────────────────────────────
    college = await tenant_repo.create(
        name="Apex Institute of Technology",
        slug=f"apex-tech-{uuid.uuid4().hex[:6]}",
        institution_type=InstitutionType.COLLEGE,
        status=TenantStatus.ACTIVE,
        email="contact@apextech.ac.in",
    )
    college_id = college.id

    assert school_id != college_id

    # ── 3. Create Tenant-Specific Data for School A ───────────────────────────
    school_academic_repo = AcademicSessionRepository(db_session, tenant_id=school_id)
    school_session = await school_academic_repo.create(
        name="Academic Year 2026-2027",
        code="AY-2026-27",
        start_date=datetime.date(2026, 4, 1),
        end_date=datetime.date(2027, 3, 31),
        is_current=True,
        status=SessionStatus.ACTIVE,
    )
    school_session_id = school_session.id

    school_settings_repo = TenantSettingRepository(db_session, tenant_id=school_id)
    school_setting = await school_settings_repo.create(
        key="branding_theme",
        value={"primary_color": "#2563eb", "school_code": "OAK-01"},
        is_public=True,
    )

    # ── 4. Create Tenant-Specific Data for College B ──────────────────────────
    college_academic_repo = AcademicSessionRepository(db_session, tenant_id=college_id)
    college_session = await college_academic_repo.create(
        name="Fall Semester 2026",
        code="SEM-FALL-26",
        start_date=datetime.date(2026, 8, 1),
        end_date=datetime.date(2026, 12, 31),
        is_current=True,
        status=SessionStatus.ACTIVE,
    )
    college_session_id = college_session.id

    college_settings_repo = TenantSettingRepository(db_session, tenant_id=college_id)
    college_setting = await college_settings_repo.create(
        key="branding_theme",
        value={"primary_color": "#dc2626", "college_code": "APX-99"},
        is_public=True,
    )

    # ── 5. Verify School A cannot access College B's Academic Session ─────────
    # Query by ID
    cross_access_session = await school_academic_repo.get_by_id(college_session_id)
    assert cross_access_session is None, "CRITICAL: School A accessed College B academic session by ID!"

    # Query list
    school_sessions_list = await school_academic_repo.list()
    assert len(school_sessions_list) == 1
    assert school_sessions_list[0].id == school_session_id
    assert all(s.tenant_id == school_id for s in school_sessions_list)

    # ── 6. Verify College B cannot access School A's Academic Session ─────────
    cross_access_session_b = await college_academic_repo.get_by_id(school_session_id)
    assert cross_access_session_b is None, "CRITICAL: College B accessed School A academic session by ID!"

    college_sessions_list = await college_academic_repo.list()
    assert len(college_sessions_list) == 1
    assert college_sessions_list[0].id == college_session_id
    assert all(s.tenant_id == college_id for s in college_sessions_list)

    # ── 7. Verify Cross-Tenant Mutation Prevention ────────────────────────────
    # School attempts to update College's session
    update_result = await school_academic_repo.update(
        college_session_id, name="Tampered Name"
    )
    assert update_result is None, "CRITICAL: School A updated College B record across tenants!"

    # Verify College session was NOT modified
    unmodified_college_session = await college_academic_repo.get_by_id(college_session_id)
    assert unmodified_college_session is not None
    assert unmodified_college_session.name == "Fall Semester 2026"

    # School attempts to delete College's session
    delete_result = await school_academic_repo.soft_delete(college_session_id)
    assert delete_result is False, "CRITICAL: School A deleted College B record across tenants!"

    # ── 8. Verify Tenant Settings Isolation (Same Key in Both Tenants) ───────
    # Both tenants have a setting with key 'branding_theme'
    fetched_school_setting = await school_settings_repo.get_by_key("branding_theme")
    assert fetched_school_setting is not None
    assert fetched_school_setting.value["primary_color"] == "#2563eb"
    assert fetched_school_setting.tenant_id == school_id

    fetched_college_setting = await college_settings_repo.get_by_key("branding_theme")
    assert fetched_college_setting is not None
    assert fetched_college_setting.value["primary_color"] == "#dc2626"
    assert fetched_college_setting.tenant_id == college_id

    # ── 9. Verify PostgreSQL Session Context Parameter (app.current_tenant_id)
    await set_tenant_session_context(db_session, school_id)
    result = await db_session.execute(
        text("SELECT current_setting('app.current_tenant_id', true)")
    )
    current_val = result.scalar()
    assert current_val == str(school_id), "PostgreSQL app.current_tenant_id was not set properly!"
