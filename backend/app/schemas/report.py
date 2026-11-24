from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


# ─────────────────────────────────────────────────────────────────────────────
# 1. Super Admin Analytics Schemas
# ─────────────────────────────────────────────────────────────────────────────

class MonthlyInstitutionGrowth(BaseModel):
    month: str
    new_institutions: int
    total_institutions: int


class PlanDistributionItem(BaseModel):
    plan_id: Optional[uuid.UUID] = None
    plan_name: str
    plan_code: str
    count: int
    percentage: float


class PaymentFailuresMetric(BaseModel):
    failed_count: int
    failed_amount: Decimal


class UserStatisticsMetric(BaseModel):
    total_users: int
    roles: Dict[str, int]


class SuperAdminAnalyticsResponse(BaseModel):
    total_institutions: int
    active_subscriptions: int
    expired_subscriptions: int
    monthly_recurring_revenue: Decimal
    annual_recurring_revenue: Decimal
    institution_growth: List[MonthlyInstitutionGrowth]
    subscription_plan_distribution: List[PlanDistributionItem]
    payment_failures: PaymentFailuresMetric
    user_statistics: UserStatisticsMetric


# ─────────────────────────────────────────────────────────────────────────────
# 2. Institution Admin Analytics Schemas
# ─────────────────────────────────────────────────────────────────────────────

class ClassDistributionItem(BaseModel):
    class_id: uuid.UUID
    class_name: str
    student_count: int
    section_count: int


class DailyAttendanceMetric(BaseModel):
    date: date
    present: int
    absent: int
    late: int
    leave: int
    total_roster: int
    rate_percentage: float


class MonthlyAttendanceItem(BaseModel):
    month: str
    rate_percentage: float


class ExamPerformanceMetric(BaseModel):
    total_exams: int
    total_evaluations: int
    average_score_percentage: float
    highest_score_percentage: float


class FeeCollectionMetric(BaseModel):
    total_collected: Decimal
    total_invoiced: Decimal
    by_payment_mode: Dict[str, Decimal]


class PendingFeesMetric(BaseModel):
    total_pending: Decimal
    overdue_invoices_count: int


class MonthlyAdmissionItem(BaseModel):
    month: str
    admissions_count: int


class TeacherPerformanceMetric(BaseModel):
    total_teachers: int
    active_teachers: int
    pending_evaluations_count: int


class AcademicTrendItem(BaseModel):
    grade_label: str
    student_count: int
    percentage: float


class InstitutionAdminAnalyticsResponse(BaseModel):
    total_students: int
    total_teachers: int
    class_distribution: List[ClassDistributionItem]
    daily_attendance: DailyAttendanceMetric
    monthly_attendance: List[MonthlyAttendanceItem]
    examination_performance: ExamPerformanceMetric
    pass_percentage: float
    fee_collection: FeeCollectionMetric
    pending_fees: PendingFeesMetric
    admission_statistics: List[MonthlyAdmissionItem]
    teacher_performance: TeacherPerformanceMetric
    academic_trends: List[AcademicTrendItem]


# ─────────────────────────────────────────────────────────────────────────────
# 3. Teacher Analytics Schemas
# ─────────────────────────────────────────────────────────────────────────────

class SubjectPerformanceItem(BaseModel):
    subject_id: uuid.UUID
    subject_name: str
    class_name: str
    student_count: int
    average_score: float
    pass_percentage: float


class TeacherAnalyticsResponse(BaseModel):
    teacher_id: uuid.UUID
    teacher_name: str
    assigned_students: int
    class_attendance_percentage: float
    subject_performance: List[SubjectPerformanceItem]
    examination_statistics: Dict[str, Any]
    pending_assignment_evaluation: int


# ─────────────────────────────────────────────────────────────────────────────
# 4. Student Analytics Schemas
# ─────────────────────────────────────────────────────────────────────────────

class StudentSubjectMarkItem(BaseModel):
    subject_name: str
    marks_obtained: float
    max_marks: float
    percentage: float
    grade: Optional[str] = None


class StudentExamHistoryItem(BaseModel):
    exam_id: uuid.UUID
    exam_title: str
    exam_date: Optional[date] = None
    marks_obtained: float
    total_marks: float
    percentage: float
    status: str  # PASS / FAIL


class StudentAnalyticsResponse(BaseModel):
    student_id: uuid.UUID
    student_name: str
    admission_number: Optional[str] = None
    attendance_percentage: float
    attendance_breakdown: Dict[str, int]
    subject_marks: List[StudentSubjectMarkItem]
    examination_history: List[StudentExamHistoryItem]
    assignment_completion: Dict[str, Any]
    academic_progress_trend: List[Dict[str, Any]]


# ─────────────────────────────────────────────────────────────────────────────
# 5. Parent Analytics Schemas
# ─────────────────────────────────────────────────────────────────────────────

class ChildProgressSummary(BaseModel):
    student_id: uuid.UUID
    student_name: str
    admission_number: Optional[str] = None
    class_name: Optional[str] = None
    attendance_percentage: float
    latest_exam_score: Optional[float] = None
    overall_grade: Optional[str] = None
    pending_assignments: int
    total_fee_dues: Decimal
    fee_overdue: bool


class ParentAnalyticsResponse(BaseModel):
    parent_user_id: uuid.UUID
    parent_name: str
    children_count: int
    children: List[ChildProgressSummary]


# ─────────────────────────────────────────────────────────────────────────────
# 6. Scheduled Reports Schemas
# ─────────────────────────────────────────────────────────────────────────────

class ScheduledReportCreate(BaseModel):
    title: str = Field(..., max_length=150)
    report_type: str = Field(..., max_length=50)  # SUPER_ADMIN_GROWTH, INSTITUTION_OVERVIEW, ATTENDANCE_SUMMARY, FEE_COLLECTION, EXAM_PERFORMANCE
    frequency: str = "WEEKLY"  # DAILY, WEEKLY, MONTHLY
    format: str = "PDF"  # PDF, EXCEL
    recipients: List[str] = Field(default_factory=list)
    filters: Dict[str, Any] = Field(default_factory=dict)


class ScheduledReportResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: Optional[uuid.UUID] = None
    user_id: uuid.UUID
    title: str
    report_type: str
    frequency: str
    format: str
    recipients: List[str]
    filters: Dict[str, Any]
    last_run_at: Optional[datetime] = None
    next_run_at: Optional[datetime] = None
    is_active: bool
    created_at: datetime
