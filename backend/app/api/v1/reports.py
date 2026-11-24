from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import ForbiddenException, NotFoundException
from app.models.academic import StudentProfile, TeacherProfile
from app.models.tenant import Tenant
from app.models.user import User
from app.permissions.rbac import (
    get_active_tenant_id,
    get_current_user,
    get_current_user_claims,
    require_any_role,
)
from app.schemas.report import (
    InstitutionAdminAnalyticsResponse,
    ParentAnalyticsResponse,
    ScheduledReportCreate,
    ScheduledReportResponse,
    StudentAnalyticsResponse,
    SuperAdminAnalyticsResponse,
    TeacherAnalyticsResponse,
)
from app.services.report_service import ReportService

router = APIRouter(prefix="/reports", tags=["Analytics & Reporting"])


# ─────────────────────────────────────────────────────────────────────────────
# 1. Super Admin Dashboard
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/super-admin", response_model=SuperAdminAnalyticsResponse)
async def get_super_admin_analytics(
    current_user: User = Depends(require_any_role(["SUPER_ADMIN"])),
    session: AsyncSession = Depends(get_db),
):
    service = ReportService(session)
    return await service.get_super_admin_analytics()


# ─────────────────────────────────────────────────────────────────────────────
# 2. Institution Admin Dashboard
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/institution-admin", response_model=InstitutionAdminAnalyticsResponse)
async def get_institution_admin_analytics(
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    academic_session_id: Optional[uuid.UUID] = Query(None),
    class_id: Optional[uuid.UUID] = Query(None),
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    current_user: User = Depends(require_any_role(["INSTITUTION_ADMIN", "SUPER_ADMIN"])),
    session: AsyncSession = Depends(get_db),
):
    service = ReportService(session)
    filters = {
        "start_date": start_date,
        "end_date": end_date,
        "academic_session_id": academic_session_id,
        "class_id": class_id,
    }
    return await service.get_institution_admin_analytics(tenant_id, filters)


# ─────────────────────────────────────────────────────────────────────────────
# 3. Teacher Dashboard
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/teacher", response_model=TeacherAnalyticsResponse)
async def get_teacher_analytics(
    teacher_id: Optional[uuid.UUID] = Query(None),
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    current_user: User = Depends(
        require_any_role(["TEACHER", "INSTITUTION_ADMIN", "SUPER_ADMIN"])
    ),
    claims: dict = Depends(get_current_user_claims),
    session: AsyncSession = Depends(get_db),
):
    service = ReportService(session)
    target_teacher_id = teacher_id

    # If teacher role, automatically resolve teacher profile linked to user
    if claims.get("role") == "TEACHER" or not target_teacher_id:
        t_stmt = select(TeacherProfile).where(
            TeacherProfile.tenant_id == tenant_id,
            TeacherProfile.user_id == current_user.id,
            TeacherProfile.is_deleted == False,
        )
        t_prof = (await session.execute(t_stmt)).scalars().first()
        if not t_prof:
            raise NotFoundException(message="Teacher profile not found for the current user")
        target_teacher_id = t_prof.id

    return await service.get_teacher_analytics(tenant_id, target_teacher_id, filters={})


# ─────────────────────────────────────────────────────────────────────────────
# 4. Student Dashboard
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/student", response_model=StudentAnalyticsResponse)
async def get_student_analytics(
    student_id: Optional[uuid.UUID] = Query(None),
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    current_user: User = Depends(
        require_any_role(["STUDENT", "PARENT", "TEACHER", "INSTITUTION_ADMIN", "SUPER_ADMIN"])
    ),
    claims: dict = Depends(get_current_user_claims),
    session: AsyncSession = Depends(get_db),
):
    service = ReportService(session)
    target_student_id = student_id

    if claims.get("role") == "STUDENT" or not target_student_id:
        s_stmt = select(StudentProfile).where(
            StudentProfile.tenant_id == tenant_id,
            StudentProfile.user_id == current_user.id,
            StudentProfile.is_deleted == False,
        )
        s_prof = (await session.execute(s_stmt)).scalars().first()
        if not s_prof:
            raise NotFoundException(message="Student profile not found for the current user")
        target_student_id = s_prof.id

    return await service.get_student_analytics(tenant_id, target_student_id)


# ─────────────────────────────────────────────────────────────────────────────
# 5. Parent Dashboard
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/parent", response_model=ParentAnalyticsResponse)
async def get_parent_analytics(
    parent_user_id: Optional[uuid.UUID] = Query(None),
    current_user: User = Depends(
        require_any_role(["PARENT", "INSTITUTION_ADMIN", "SUPER_ADMIN"])
    ),
    claims: dict = Depends(get_current_user_claims),
    session: AsyncSession = Depends(get_db),
):
    service = ReportService(session)
    target_parent_id = current_user.id if claims.get("role") == "PARENT" else (parent_user_id or current_user.id)
    return await service.get_parent_analytics(target_parent_id)


# ─────────────────────────────────────────────────────────────────────────────
# 6. Report Export Endpoints (PDF & Excel)
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/export/pdf")
async def export_report_pdf(
    report_type: str = Query(..., description="INSTITUTION_OVERVIEW, ATTENDANCE_SUMMARY, FEE_COLLECTION, EXAM_PERFORMANCE, SUPER_ADMIN_GROWTH"),
    academic_session_id: Optional[uuid.UUID] = Query(None),
    class_id: Optional[uuid.UUID] = Query(None),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    current_user: User = Depends(
        require_any_role(["INSTITUTION_ADMIN", "SUPER_ADMIN", "TEACHER"])
    ),
    session: AsyncSession = Depends(get_db),
):
    service = ReportService(session)
    filters = {
        "start_date": start_date,
        "end_date": end_date,
        "academic_session_id": academic_session_id,
        "class_id": class_id,
    }

    # Fetch institution data
    tenant = await session.get(Tenant, tenant_id)
    tenant_name = tenant.name if tenant else "EduSaaS Institution"

    if report_type == "SUPER_ADMIN_GROWTH":
        data = await service.get_super_admin_analytics()
        kpis = [
            ("Total Institutions", str(data.total_institutions)),
            ("Active Subscriptions", str(data.active_subscriptions)),
            ("Monthly Recurring Revenue", f"₹{data.monthly_recurring_revenue:,.2f}"),
            ("Annual Recurring Revenue", f"₹{data.annual_recurring_revenue:,.2f}"),
            ("Total Users", str(data.user_statistics.total_users)),
            ("Failed Payments", str(data.payment_failures.failed_count)),
        ]
        headers = ["Month", "New Institutions", "Total Running Institutions"]
        rows = [[g.month, str(g.new_institutions), str(g.total_institutions)] for g in data.institution_growth]
        pdf_bytes = service.generate_pdf_report(
            title="Platform Executive Growth Report",
            subtitle=f"Antigravity EduSaaS Platform Analytics • {datetime.now(timezone.utc).strftime('%B %d, %Y')}",
            summary_kpis=kpis,
            table_headers=headers,
            table_rows=rows,
        )
    elif report_type == "FEE_COLLECTION":
        data = await service.get_institution_admin_analytics(tenant_id, filters)
        kpis = [
            ("Total Collected", f"₹{data.fee_collection.total_collected:,.2f}"),
            ("Total Invoiced", f"₹{data.fee_collection.total_invoiced:,.2f}"),
            ("Total Outstanding", f"₹{data.pending_fees.total_pending:,.2f}"),
            ("Overdue Invoices", str(data.pending_fees.overdue_invoices_count)),
        ]
        headers = ["Payment Mode", "Total Amount Collected (₹)"]
        rows = [[mode, f"₹{amt:,.2f}"] for mode, amt in data.fee_collection.by_payment_mode.items()]
        pdf_bytes = service.generate_pdf_report(
            title=f"{tenant_name} — Fee Collection Ledger",
            subtitle=f"Institution Finance Report • Generated on {datetime.now(timezone.utc).strftime('%B %d, %Y')}",
            summary_kpis=kpis,
            table_headers=headers,
            table_rows=rows,
        )
    else:  # INSTITUTION_OVERVIEW default
        data = await service.get_institution_admin_analytics(tenant_id, filters)
        kpis = [
            ("Total Students", str(data.total_students)),
            ("Total Teachers", str(data.total_teachers)),
            ("Attendance Rate", f"{data.daily_attendance.rate_percentage}%"),
            ("Pass Percentage", f"{data.pass_percentage}%"),
            ("Total Fees Collected", f"₹{data.fee_collection.total_collected:,.2f}"),
            ("Pending Fees", f"₹{data.pending_fees.total_pending:,.2f}"),
        ]
        headers = ["Class / Grade", "Enrolled Students", "Sections Count"]
        rows = [[c.class_name, str(c.student_count), str(c.section_count)] for c in data.class_distribution]
        pdf_bytes = service.generate_pdf_report(
            title=f"{tenant_name} — Institutional Overview Report",
            subtitle=f"Comprehensive Academic & Operations Summary • Generated on {datetime.now(timezone.utc).strftime('%B %d, %Y')}",
            summary_kpis=kpis,
            table_headers=headers,
            table_rows=rows,
        )

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="report_{report_type.lower()}_{datetime.now().strftime("%Y%m%d")}.pdf"'},
    )


@router.get("/export/excel")
async def export_report_excel(
    report_type: str = Query(..., description="INSTITUTION_OVERVIEW, ATTENDANCE_SUMMARY, FEE_COLLECTION, EXAM_PERFORMANCE, SUPER_ADMIN_GROWTH"),
    academic_session_id: Optional[uuid.UUID] = Query(None),
    class_id: Optional[uuid.UUID] = Query(None),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    tenant_id: uuid.UUID = Depends(get_active_tenant_id),
    current_user: User = Depends(
        require_any_role(["INSTITUTION_ADMIN", "SUPER_ADMIN", "TEACHER"])
    ),
    session: AsyncSession = Depends(get_db),
):
    service = ReportService(session)
    filters = {
        "start_date": start_date,
        "end_date": end_date,
        "academic_session_id": academic_session_id,
        "class_id": class_id,
    }

    tenant = await session.get(Tenant, tenant_id)
    tenant_name = tenant.name if tenant else "Institution"

    if report_type == "SUPER_ADMIN_GROWTH":
        data = await service.get_super_admin_analytics()
        kpis = [
            ("Total Institutions", str(data.total_institutions)),
            ("Active Subscriptions", str(data.active_subscriptions)),
            ("Monthly Recurring Revenue", f"₹{data.monthly_recurring_revenue:,.2f}"),
            ("Annual Recurring Revenue", f"₹{data.annual_recurring_revenue:,.2f}"),
        ]
        headers = ["Month", "New Registrations", "Total Running Count"]
        rows = [[g.month, g.new_institutions, g.total_institutions] for g in data.institution_growth]
        xlsx_bytes = service.generate_excel_report("Platform Growth", kpis, headers, rows)
    elif report_type == "FEE_COLLECTION":
        data = await service.get_institution_admin_analytics(tenant_id, filters)
        kpis = [
            ("Total Collected", f"₹{data.fee_collection.total_collected:,.2f}"),
            ("Total Invoiced", f"₹{data.fee_collection.total_invoiced:,.2f}"),
            ("Total Outstanding", f"₹{data.pending_fees.total_pending:,.2f}"),
        ]
        headers = ["Payment Mode", "Collected Amount (₹)"]
        rows = [[mode, float(amt)] for mode, amt in data.fee_collection.by_payment_mode.items()]
        xlsx_bytes = service.generate_excel_report("Fee Collection", kpis, headers, rows)
    else:  # INSTITUTION_OVERVIEW default
        data = await service.get_institution_admin_analytics(tenant_id, filters)
        kpis = [
            ("Total Students", str(data.total_students)),
            ("Total Teachers", str(data.total_teachers)),
            ("Attendance Rate", f"{data.daily_attendance.rate_percentage}%"),
            ("Pass Rate", f"{data.pass_percentage}%"),
        ]
        headers = ["Class Name", "Student Count", "Section Count"]
        rows = [[c.class_name, c.student_count, c.section_count] for c in data.class_distribution]
        xlsx_bytes = service.generate_excel_report(f"{tenant_name} Overview", kpis, headers, rows)

    return Response(
        content=xlsx_bytes,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="report_{report_type.lower()}_{datetime.now().strftime("%Y%m%d")}.xlsx"'},
    )


# ─────────────────────────────────────────────────────────────────────────────
# 7. Scheduled Reports Management
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/scheduled", response_model=List[ScheduledReportResponse])
async def list_scheduled_reports(
    tenant_id: Optional[uuid.UUID] = Depends(get_active_tenant_id),
    current_user: User = Depends(require_any_role(["INSTITUTION_ADMIN", "SUPER_ADMIN", "TEACHER"])),
    session: AsyncSession = Depends(get_db),
):
    service = ReportService(session)
    return await service.list_scheduled_reports(tenant_id=tenant_id)


@router.post(
    "/scheduled",
    response_model=ScheduledReportResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_scheduled_report(
    payload: ScheduledReportCreate,
    tenant_id: Optional[uuid.UUID] = Depends(get_active_tenant_id),
    current_user: User = Depends(require_any_role(["INSTITUTION_ADMIN", "SUPER_ADMIN"])),
    session: AsyncSession = Depends(get_db),
):
    service = ReportService(session)
    return await service.create_scheduled_report(
        tenant_id=tenant_id,
        user_id=current_user.id,
        data=payload,
    )


@router.delete("/scheduled/{schedule_id}", status_code=status.HTTP_200_OK)
async def delete_scheduled_report(
    schedule_id: uuid.UUID,
    tenant_id: Optional[uuid.UUID] = Depends(get_active_tenant_id),
    current_user: User = Depends(require_any_role(["INSTITUTION_ADMIN", "SUPER_ADMIN"])),
    session: AsyncSession = Depends(get_db),
):
    service = ReportService(session)
    await service.delete_scheduled_report(schedule_id, tenant_id=tenant_id)
    return {"success": True, "message": "Scheduled report cancelled"}


@router.post("/scheduled/{schedule_id}/trigger", status_code=status.HTTP_200_OK)
async def trigger_scheduled_report(
    schedule_id: uuid.UUID,
    tenant_id: Optional[uuid.UUID] = Depends(get_active_tenant_id),
    current_user: User = Depends(require_any_role(["INSTITUTION_ADMIN", "SUPER_ADMIN"])),
    session: AsyncSession = Depends(get_db),
):
    service = ReportService(session)
    return await service.trigger_scheduled_report(schedule_id, tenant_id=tenant_id)
