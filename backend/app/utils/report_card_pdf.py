from __future__ import annotations

import io
from typing import Any, Dict, List, Optional
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import HRFlowable, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


def generate_report_card_pdf(
    institution_data: Dict[str, Any],
    student_data: Dict[str, Any],
    exam_data: Dict[str, Any],
    subject_results: List[Dict[str, Any]],
    term_summary: Dict[str, Any],
    template_config: Optional[Dict[str, Any]] = None,
) -> bytes:
    """
    Generates a professional academic report card in vector PDF format using ReportLab.
    Includes institution branding, student academic credentials, subject-wise assessment breakdown,
    attendance summary, and signature blocks.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36,
    )

    styles = getSampleStyleSheet()

    # Custom typography styles
    title_style = ParagraphStyle(
        "InstTitle",
        parent=styles["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=18,
        leading=22,
        alignment=1,
        textColor=colors.HexColor("#1e3a8a"),
    )
    subtitle_style = ParagraphStyle(
        "InstSubtitle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9,
        leading=12,
        alignment=1,
        textColor=colors.HexColor("#64748b"),
    )
    report_header_style = ParagraphStyle(
        "ReportHeader",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=13,
        leading=16,
        alignment=1,
        textColor=colors.HexColor("#0f172a"),
        spaceAfter=10,
    )
    meta_label = ParagraphStyle(
        "MetaLabel",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=9,
        leading=12,
        textColor=colors.HexColor("#334155"),
    )
    meta_val = ParagraphStyle(
        "MetaVal",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9,
        leading=12,
        textColor=colors.HexColor("#0f172a"),
    )
    table_header_style = ParagraphStyle(
        "TableHeader",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=8,
        leading=10,
        alignment=1,
        textColor=colors.white,
    )
    table_body_style = ParagraphStyle(
        "TableBody",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8,
        leading=10,
        alignment=0,
    )
    table_body_center = ParagraphStyle(
        "TableBodyCenter",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8,
        leading=10,
        alignment=1,
    )

    def _safe_str(val: Any, fallback: str = "N/A") -> str:
        if val is None:
            return fallback
        s = str(val).strip()
        return s if s else fallback

    story = []

    # ── 1. Institution Header ─────────────────────────────────────────────────
    inst_name = _safe_str(institution_data.get("name"), "EduSaaS Academic Institution")
    inst_addr = _safe_str(institution_data.get("address"), "Official Campus • Affiliated & Accredited")
    story.append(Paragraph(inst_name.upper(), title_style))
    story.append(Spacer(1, 2))
    story.append(Paragraph(inst_addr, subtitle_style))
    story.append(Spacer(1, 6))

    header_title = _safe_str((template_config or {}).get("header_title"), "OFFICIAL ACADEMIC REPORT CARD")
    story.append(Paragraph(f"<b>{header_title}</b>", report_header_style))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#1e3a8a"), spaceAfter=10))

    # ── 2. Student & Examination Information Table ────────────────────────────
    student_meta = [
        [
            Paragraph("Student Name:", meta_label),
            Paragraph(_safe_str(student_data.get("name")), meta_val),
            Paragraph("Examination:", meta_label),
            Paragraph(_safe_str(exam_data.get("title")), meta_val),
        ],
        [
            Paragraph("Admission No:", meta_label),
            Paragraph(_safe_str(student_data.get("admission_number")), meta_val),
            Paragraph("Academic Session:", meta_label),
            Paragraph(_safe_str(exam_data.get("academic_session"), "2026-2027"), meta_val),
        ],
        [
            Paragraph("Roll Number:", meta_label),
            Paragraph(_safe_str(student_data.get("roll_number")), meta_val),
            Paragraph("Class / Semester:", meta_label),
            Paragraph(_safe_str(f"{student_data.get('class_name') or ''} {student_data.get('section_name') or ''}".strip()), meta_val),
        ],
    ]

    meta_table = Table(student_meta, colWidths=[1.3 * inch, 2.3 * inch, 1.4 * inch, 2.3 * inch])
    meta_table.setStyle(
        TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("TOPPADDING", (0, 0), (-1, -1), 2),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
        ])
    )
    story.append(meta_table)
    story.append(Spacer(1, 10))

    # ── 3. Subject-wise Assessment Marks Table ────────────────────────────────
    headers = [
        Paragraph("Subject", table_header_style),
        Paragraph("Theory", table_header_style),
        Paragraph("Practical", table_header_style),
        Paragraph("Internal", table_header_style),
        Paragraph("Total", table_header_style),
        Paragraph("Max", table_header_style),
        Paragraph("%", table_header_style),
        Paragraph("Grade", table_header_style),
        Paragraph("Credits", table_header_style),
    ]

    table_data = [headers]
    for sub in subject_results:
        s_name = _safe_str(sub.get("subject_name"), "Subject")
        s_code = _safe_str(sub.get("subject_code"), "")
        row = [
            Paragraph(f"<b>{s_name}</b><br/><font color='#64748b' size=7>{s_code}</font>", table_body_style),
            Paragraph(f"{sub.get('theory_marks', 0)}/{sub.get('theory_max', 70)}", table_body_center),
            Paragraph(f"{sub.get('practical_marks', 0)}/{sub.get('practical_max', 20)}", table_body_center),
            Paragraph(f"{sub.get('internal_marks', 0)}/{sub.get('internal_max', 10)}", table_body_center),
            Paragraph(f"<b>{sub.get('total_marks', 0)}</b>", table_body_center),
            Paragraph(str(sub.get("max_marks", 100)), table_body_center),
            Paragraph(f"{sub.get('percentage', 0)}%", table_body_center),
            Paragraph(f"<b>{_safe_str(sub.get('grade'), '-')}</b>", table_body_center),
            Paragraph(str(sub.get("credits", 3.0)), table_body_center),
        ]
        table_data.append(row)

    marks_table = Table(
        table_data,
        colWidths=[2.2 * inch, 0.7 * inch, 0.7 * inch, 0.7 * inch, 0.65 * inch, 0.55 * inch, 0.55 * inch, 0.6 * inch, 0.65 * inch],
    )
    marks_table.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e3a8a")),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ])
    )
    story.append(marks_table)
    story.append(Spacer(1, 12))

    # ── 4. Cumulative Performance & Attendance Summary ────────────────────────
    summary_data = [
        [
            Paragraph("Total Marks Obtained:", meta_label),
            Paragraph(f"<b>{term_summary.get('total_obtained', 0)} / {term_summary.get('total_max', 0)}</b>", meta_val),
            Paragraph("Overall Percentage:", meta_label),
            Paragraph(f"<b>{term_summary.get('overall_percentage', 0)}%</b>", meta_val),
        ],
        [
            Paragraph("Final Grade:", meta_label),
            Paragraph(f"<b>{_safe_str(term_summary.get('overall_grade'), 'N/A')}</b>", meta_val),
            Paragraph("Result Status:", meta_label),
            Paragraph(
                f"<font color='{'green' if term_summary.get('is_passed') else 'red'}'><b>{'PASSED' if term_summary.get('is_passed') else 'FAILED'}</b></font>",
                meta_val,
            ),
        ],
    ]

    if term_summary.get("cgpa") is not None:
        summary_data.append([
            Paragraph("Cumulative GPA (CGPA):", meta_label),
            Paragraph(f"<b>{_safe_str(term_summary.get('cgpa'))}</b>", meta_val),
            Paragraph("Semester GPA (SGPA):", meta_label),
            Paragraph(f"<b>{_safe_str(term_summary.get('sgpa'), 'N/A')}</b>", meta_val),
        ])

    if term_summary.get("rank") is not None:
        summary_data.append([
            Paragraph("Class Rank:", meta_label),
            Paragraph(f"Rank #{term_summary.get('rank')}", meta_val),
            Paragraph("", meta_label),
            Paragraph("", meta_val),
        ])

    # Attendance summary
    att_pct = term_summary.get("attendance_percentage")
    att_text = f"{att_pct}%" if att_pct is not None else "N/A"
    if term_summary.get("present_days") is not None and term_summary.get("total_attendance_days") is not None:
        att_text += f" ({term_summary.get('present_days')}/{term_summary.get('total_attendance_days')} Days)"

    summary_data.append([
        Paragraph("Attendance Summary:", meta_label),
        Paragraph(_safe_str(att_text, "N/A"), meta_val),
        Paragraph("Result Publication Date:", meta_label),
        Paragraph(_safe_str(term_summary.get("published_at"), "N/A"), meta_val),
    ])

    summary_table = Table(summary_data, colWidths=[1.8 * inch, 1.8 * inch, 1.8 * inch, 1.9 * inch])
    summary_table.setStyle(
        TableStyle([
            ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#1e3a8a")),
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ])
    )
    story.append(summary_table)
    story.append(Spacer(1, 24))

    # ── 5. Authorized Signatures ──────────────────────────────────────────────
    sig_data = [
        [
            Paragraph("____________________________<br/><b>Class Teacher</b>", table_body_center),
            Paragraph("____________________________<br/><b>Exam Controller</b>", table_body_center),
            Paragraph("____________________________<br/><b>Principal / Director</b>", table_body_center),
        ]
    ]
    sig_table = Table(sig_data, colWidths=[2.4 * inch, 2.4 * inch, 2.5 * inch])
    sig_table.setStyle(
        TableStyle([
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "BOTTOM"),
        ])
    )
    story.append(sig_table)
    story.append(Spacer(1, 10))

    # Footer note
    footer_text = (template_config or {}).get("custom_footer", "This report card is generated electronically by the EduSaaS Education CRM System. No alteration or erasure is permitted.")
    story.append(Paragraph(f"<font size=7 color='#64748b'><i>{footer_text}</i></font>", subtitle_style))

    doc.build(story)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes
