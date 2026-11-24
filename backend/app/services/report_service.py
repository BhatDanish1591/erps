from __future__ import annotations

import io
import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

import openpyxl
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundException, ValidationException
from app.models.report import ScheduledReport
from app.repositories.report import ReportRepository
from app.schemas.report import (
    InstitutionAdminAnalyticsResponse,
    ParentAnalyticsResponse,
    ScheduledReportCreate,
    StudentAnalyticsResponse,
    SuperAdminAnalyticsResponse,
    TeacherAnalyticsResponse,
)


class ReportService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = ReportRepository(session)

    # ── Role Analytics Queries ───────────────────────────────────────────────

    async def get_super_admin_analytics(self) -> SuperAdminAnalyticsResponse:
        data = await self.repo.get_super_admin_analytics()
        return SuperAdminAnalyticsResponse(**data)

    async def get_institution_admin_analytics(
        self, tenant_id: uuid.UUID, filters: Dict[str, Any]
    ) -> InstitutionAdminAnalyticsResponse:
        data = await self.repo.get_institution_admin_analytics(tenant_id, filters)
        return InstitutionAdminAnalyticsResponse(**data)

    async def get_teacher_analytics(
        self, tenant_id: uuid.UUID, teacher_id: uuid.UUID, filters: Dict[str, Any]
    ) -> TeacherAnalyticsResponse:
        data = await self.repo.get_teacher_analytics(tenant_id, teacher_id)
        return TeacherAnalyticsResponse(**data)

    async def get_student_analytics(
        self, tenant_id: uuid.UUID, student_id: uuid.UUID
    ) -> StudentAnalyticsResponse:
        data = await self.repo.get_student_analytics(tenant_id, student_id)
        return StudentAnalyticsResponse(**data)

    async def get_parent_analytics(
        self, parent_user_id: uuid.UUID, tenant_id: Optional[uuid.UUID] = None
    ) -> ParentAnalyticsResponse:
        data = await self.repo.get_parent_analytics(parent_user_id, tenant_id)
        return ParentAnalyticsResponse(**data)

    # ── Export Engines ───────────────────────────────────────────────────────

    def generate_pdf_report(
        self, title: str, subtitle: str, summary_kpis: List[Tuple[str, str]], table_headers: List[str], table_rows: List[List[Any]]
    ) -> bytes:
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            rightMargin=36,
            leftMargin=36,
            topMargin=36,
            bottomMargin=36,
        )

        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            "ReportTitle",
            parent=styles["Heading1"],
            fontSize=20,
            leading=24,
            textColor=colors.HexColor("#0F172A"),
            spaceAfter=4,
        )
        subtitle_style = ParagraphStyle(
            "ReportSubtitle",
            parent=styles["Normal"],
            fontSize=10,
            textColor=colors.HexColor("#64748B"),
            spaceAfter=14,
        )
        body_style = ParagraphStyle(
            "ReportBody",
            parent=styles["Normal"],
            fontSize=9,
            textColor=colors.HexColor("#334155"),
        )
        header_cell_style = ParagraphStyle(
            "HeaderCell",
            parent=styles["Normal"],
            fontSize=9,
            fontName="Helvetica-Bold",
            textColor=colors.white,
        )

        elements = []

        # Title & Subtitle
        elements.append(Paragraph(title, title_style))
        elements.append(Paragraph(subtitle, subtitle_style))
        elements.append(Spacer(1, 10))

        # KPI Summary Grid
        if summary_kpis:
            kpi_data = []
            for i in range(0, len(summary_kpis), 3):
                chunk = summary_kpis[i : i + 3]
                row_label = [Paragraph(f"<b>{k[0]}</b>", body_style) for k in chunk]
                row_val = [Paragraph(f"<font size=12 color='#2563EB'><b>{k[1]}</b></font>", body_style) for k in chunk]
                # Pad if needed
                while len(row_label) < 3:
                    row_label.append(Paragraph("", body_style))
                    row_val.append(Paragraph("", body_style))
                kpi_data.append(row_label)
                kpi_data.append(row_val)

            kpi_table = Table(kpi_data, colWidths=[2.3 * inch, 2.3 * inch, 2.3 * inch])
            kpi_table.setStyle(
                TableStyle([
                    ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F8FAFC")),
                    ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#E2E8F0")),
                    ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
                    ("TOPPADDING", (0, 0), (-1, -1), 6),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ])
            )
            elements.append(kpi_table)
            elements.append(Spacer(1, 16))

        # Detail Data Table
        if table_headers and table_rows:
            formatted_table_data = [
                [Paragraph(h, header_cell_style) for h in table_headers]
            ]
            for row in table_rows:
                formatted_table_data.append([Paragraph(str(val), body_style) for val in row])

            col_width = (7.0 * inch) / max(1, len(table_headers))
            detail_table = Table(formatted_table_data, colWidths=[col_width] * len(table_headers))
            detail_table.setStyle(
                TableStyle([
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1E293B")),
                    ("BOTTOMPADDING", (0, 0), (-1, 0), 6),
                    ("TOPPADDING", (0, 0), (-1, 0), 6),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F1F5F9")]),
                ])
            )
            elements.append(detail_table)

        doc.build(elements)
        return buffer.getvalue()

    def generate_excel_report(
        self, sheet_title: str, summary_kpis: List[Tuple[str, str]], table_headers: List[str], table_rows: List[List[Any]]
    ) -> bytes:
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = sheet_title[:30]

        # Brand header fill
        header_fill = PatternFill(start_color="1E293B", end_color="1E293B", fill_type="solid")
        header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
        title_font = Font(name="Calibri", size=14, bold=True, color="0F172A")
        sub_font = Font(name="Calibri", size=9, italic=True, color="64748B")
        kpi_label_font = Font(name="Calibri", size=10, bold=True, color="334155")
        kpi_val_font = Font(name="Calibri", size=12, bold=True, color="2563EB")
        thin_border = Border(
            left=Side(style="thin", color="E2E8F0"),
            right=Side(style="thin", color="E2E8F0"),
            top=Side(style="thin", color="E2E8F0"),
            bottom=Side(style="thin", color="E2E8F0"),
        )

        ws.cell(row=1, column=1, value=sheet_title).font = title_font
        ws.cell(row=2, column=1, value=f"Generated on {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}").font = sub_font

        current_row = 4

        # KPIs
        if summary_kpis:
            for label, val in summary_kpis:
                ws.cell(row=current_row, column=1, value=label).font = kpi_label_font
                ws.cell(row=current_row, column=2, value=str(val)).font = kpi_val_font
                current_row += 1
            current_row += 1

        # Data table
        if table_headers and table_rows:
            for col_idx, h in enumerate(table_headers, 1):
                cell = ws.cell(row=current_row, column=col_idx, value=h)
                cell.fill = header_fill
                cell.font = header_font
                cell.alignment = Alignment(horizontal="center", vertical="center")

            current_row += 1
            for row_data in table_rows:
                for col_idx, val in enumerate(row_data, 1):
                    c = ws.cell(row=current_row, column=col_idx, value=val)
                    c.border = thin_border
                current_row += 1

        # Auto fit column widths
        for col in ws.columns:
            max_len = max(len(str(cell.value or "")) for cell in col)
            col_letter = openpyxl.utils.get_column_letter(col[0].column)
            ws.column_dimensions[col_letter].width = max(max_len + 3, 14)

        buf = io.BytesIO()
        wb.save(buf)
        return buf.getvalue()

    # ── Scheduled Reports ────────────────────────────────────────────────────

    async def create_scheduled_report(
        self, tenant_id: Optional[uuid.UUID], user_id: uuid.UUID, data: ScheduledReportCreate
    ) -> ScheduledReport:
        schedule = await self.repo.create_scheduled_report(
            tenant_id=tenant_id,
            user_id=user_id,
            title=data.title,
            report_type=data.report_type,
            frequency=data.frequency,
            report_format=data.format,
            recipients=data.recipients,
            filters=data.filters,
        )
        await self.session.commit()
        return schedule

    async def list_scheduled_reports(
        self, tenant_id: Optional[uuid.UUID] = None, user_id: Optional[uuid.UUID] = None
    ) -> List[ScheduledReport]:
        return await self.repo.list_scheduled_reports(tenant_id=tenant_id, user_id=user_id)

    async def delete_scheduled_report(
        self, schedule_id: uuid.UUID, tenant_id: Optional[uuid.UUID] = None
    ) -> bool:
        res = await self.repo.delete_scheduled_report(schedule_id, tenant_id=tenant_id)
        if not res:
            raise NotFoundException(message=f"Scheduled report {schedule_id} not found")
        await self.session.commit()
        return True

    async def trigger_scheduled_report(
        self, schedule_id: uuid.UUID, tenant_id: Optional[uuid.UUID] = None
    ) -> Dict[str, Any]:
        schedule = await self.repo.get_scheduled_report_by_id(schedule_id, tenant_id=tenant_id)
        if not schedule:
            raise NotFoundException(message=f"Scheduled report {schedule_id} not found")

        schedule.last_run_at = datetime.now(timezone.utc)
        await self.session.commit()

        return {
            "schedule_id": schedule.id,
            "title": schedule.title,
            "report_type": schedule.report_type,
            "recipients": schedule.recipients,
            "format": schedule.format,
            "status": "DISPATCHED",
            "dispatched_at": schedule.last_run_at,
        }
