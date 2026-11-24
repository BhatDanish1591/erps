from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional

from sqlalchemy import and_, case, desc, distinct, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.academic import (
    AcademicSession,
    SchoolClass,
    Section,
    StudentParent,
    StudentProfile,
    Subject,
    TeacherProfile,
    TeacherSubjectMapping,
)
from app.models.attendance import (
    StudentAttendanceEntry,
    StudentAttendanceSession,
)
from app.models.auth import Membership, Role
from app.models.enums import BillingCycle, SubscriptionStatus
from app.models.examination import (
    Examination,
    StudentExamAttempt,
)
from app.models.fee import (
    FeeInvoice,
    FeePayment,
)
from app.models.lms import (
    Assignment,
    AssignmentSubmission,
)
from app.models.report import ScheduledReport
from app.models.result import StudentSubjectResult
from app.models.subscription import (
    Subscription,
    SubscriptionPayment,
    SubscriptionPlan,
)
from app.models.tenant import Tenant
from app.models.user import User


class ReportRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    # ═════════════════════════════════════════════════════════════════════════
    # 1. Super Admin Analytics
    # ═════════════════════════════════════════════════════════════════════════
    async def get_super_admin_analytics(self) -> Dict[str, Any]:
        # A. Institution Counts
        tot_inst = (await self.session.execute(
            select(func.count(Tenant.id)).where(Tenant.is_deleted == False)
        )).scalar() or 0

        # B. Subscription States
        active_subs = (await self.session.execute(
            select(func.count(Subscription.id)).where(
                Subscription.status.in_([SubscriptionStatus.ACTIVE, SubscriptionStatus.TRIAL]),
            )
        )).scalar() or 0

        expired_subs = (await self.session.execute(
            select(func.count(Subscription.id)).where(
                Subscription.status.in_([
                    SubscriptionStatus.EXPIRED,
                    SubscriptionStatus.CANCELED,
                    SubscriptionStatus.SUSPENDED,
                    SubscriptionStatus.PAST_DUE,
                ]),
            )
        )).scalar() or 0

        # C. Monthly & Annual Recurring Revenue (MRR / ARR)
        mrr_stmt = (
            select(
                func.coalesce(
                    func.sum(
                        case(
                            (Subscription.billing_cycle == BillingCycle.YEARLY, SubscriptionPlan.price / 12),
                            else_=SubscriptionPlan.price,
                        )
                    ),
                    Decimal("0.00"),
                )
            )
            .select_from(Subscription)
            .join(SubscriptionPlan, Subscription.plan_id == SubscriptionPlan.id)
            .where(
                Subscription.status == SubscriptionStatus.ACTIVE,
            )
        )
        mrr = (await self.session.execute(mrr_stmt)).scalar() or Decimal("0.00")
        mrr = Decimal(str(round(mrr, 2)))
        arr = Decimal(str(round(mrr * 12, 2)))

        # D. Institution Growth (Last 6 Months)
        growth_stmt = (
            select(
                func.to_char(Tenant.created_at, "YYYY-MM").label("month"),
                func.count(Tenant.id).label("new_institutions"),
            )
            .where(Tenant.is_deleted == False)
            .group_by("month")
            .order_by("month")
        )
        growth_rows = (await self.session.execute(growth_stmt)).all()
        growth_list = []
        running_total = 0
        for r in growth_rows:
            running_total += r.new_institutions
            growth_list.append({
                "month": r.month,
                "new_institutions": r.new_institutions,
                "total_institutions": running_total,
            })
        if not growth_list:
            growth_list.append({
                "month": datetime.now(timezone.utc).strftime("%Y-%m"),
                "new_institutions": tot_inst,
                "total_institutions": tot_inst,
            })

        # E. Subscription Plan Distribution
        plan_stmt = (
            select(
                SubscriptionPlan.id,
                SubscriptionPlan.name,
                SubscriptionPlan.code,
                func.count(Subscription.id).label("sub_count"),
            )
            .join(Subscription, Subscription.plan_id == SubscriptionPlan.id)
            .where(
                Subscription.status.in_([SubscriptionStatus.ACTIVE, SubscriptionStatus.TRIAL]),
            )
            .group_by(SubscriptionPlan.id, SubscriptionPlan.name, SubscriptionPlan.code)
        )
        plan_rows = (await self.session.execute(plan_stmt)).all()
        plan_dist = []
        for p in plan_rows:
            pct = round((p.sub_count / max(1, active_subs)) * 100, 1)
            plan_dist.append({
                "plan_id": p.id,
                "plan_name": p.name,
                "plan_code": p.code,
                "count": p.sub_count,
                "percentage": pct,
            })

        # F. Payment Failures
        fail_stmt = (
            select(
                func.count(SubscriptionPayment.id).label("fail_count"),
                func.coalesce(func.sum(SubscriptionPayment.amount), Decimal("0.00")).label("fail_amount"),
            )
            .where(SubscriptionPayment.status == "FAILED")
        )
        fail_res = (await self.session.execute(fail_stmt)).first()
        payment_failures = {
            "failed_count": fail_res.fail_count if fail_res else 0,
            "failed_amount": fail_res.fail_amount if fail_res else Decimal("0.00"),
        }

        # G. User Statistics
        tot_users = (await self.session.execute(
            select(func.count(User.id)).where(User.is_deleted == False)
        )).scalar() or 0

        roles_stmt = (
            select(Role.code, func.count(distinct(Membership.user_id)))
            .join(Membership, Membership.role_id == Role.id)
            .where(Membership.is_deleted == False)
            .group_by(Role.code)
        )
        role_rows = (await self.session.execute(roles_stmt)).all()
        roles_dict = {r[0]: r[1] for r in role_rows}

        return {
            "total_institutions": tot_inst,
            "active_subscriptions": active_subs,
            "expired_subscriptions": expired_subs,
            "monthly_recurring_revenue": mrr,
            "annual_recurring_revenue": arr,
            "institution_growth": growth_list,
            "subscription_plan_distribution": plan_dist,
            "payment_failures": payment_failures,
            "user_statistics": {
                "total_users": tot_users,
                "roles": roles_dict,
            },
        }

    # ═════════════════════════════════════════════════════════════════════════
    # 2. Institution Admin Analytics
    # ═════════════════════════════════════════════════════════════════════════
    async def get_institution_admin_analytics(
        self, tenant_id: uuid.UUID, filters: Dict[str, Any]
    ) -> Dict[str, Any]:
        class_id = filters.get("class_id")
        academic_session_id = filters.get("academic_session_id")
        start_date = filters.get("start_date")
        end_date = filters.get("end_date")

        # A. Total Students
        student_stmt = select(func.count(StudentProfile.id)).where(
            StudentProfile.tenant_id == tenant_id,
            StudentProfile.is_deleted == False,
            StudentProfile.status == "ACTIVE",
        )
        if class_id:
            student_stmt = student_stmt.where(StudentProfile.class_id == class_id)
        if academic_session_id:
            student_stmt = student_stmt.where(StudentProfile.academic_session_id == academic_session_id)
        total_students = (await self.session.execute(student_stmt)).scalar() or 0

        # B. Total Teachers
        teacher_stmt = select(func.count(TeacherProfile.id)).where(
            TeacherProfile.tenant_id == tenant_id,
            TeacherProfile.is_deleted == False,
            TeacherProfile.status == "ACTIVE",
        )
        total_teachers = (await self.session.execute(teacher_stmt)).scalar() or 0

        # C. Class Distribution
        class_stmt = (
            select(
                SchoolClass.id,
                SchoolClass.name,
                func.count(distinct(StudentProfile.id)).label("stu_count"),
                func.count(distinct(Section.id)).label("sec_count"),
            )
            .outerjoin(StudentProfile, and_(StudentProfile.class_id == SchoolClass.id, StudentProfile.status == "ACTIVE", StudentProfile.is_deleted == False))
            .outerjoin(Section, and_(Section.class_id == SchoolClass.id, Section.is_deleted == False))
            .where(
                SchoolClass.tenant_id == tenant_id,
                SchoolClass.is_deleted == False,
            )
            .group_by(SchoolClass.id, SchoolClass.name, SchoolClass.order_index)
            .order_by(SchoolClass.order_index.asc())
        )
        class_rows = (await self.session.execute(class_stmt)).all()
        class_distribution = [
            {
                "class_id": r.id,
                "class_name": r.name,
                "student_count": r.stu_count,
                "section_count": r.sec_count,
            }
            for r in class_rows
        ]

        # D. Daily Attendance (Latest Session or Filter Date)
        att_session_stmt = (
            select(StudentAttendanceSession)
            .where(
                StudentAttendanceSession.tenant_id == tenant_id,
                StudentAttendanceSession.is_deleted == False,
            )
            .order_by(StudentAttendanceSession.session_date.desc())
        )
        if start_date:
            att_session_stmt = att_session_stmt.where(StudentAttendanceSession.session_date >= start_date)
        if class_id:
            att_session_stmt = att_session_stmt.where(StudentAttendanceSession.class_id == class_id)
        latest_session = (await self.session.execute(att_session_stmt)).scalars().first()

        daily_date = latest_session.session_date if latest_session else date.today()
        daily_entries_stmt = (
            select(
                StudentAttendanceEntry.status,
                func.count(StudentAttendanceEntry.id),
            )
            .join(StudentAttendanceSession, StudentAttendanceEntry.session_id == StudentAttendanceSession.id)
            .where(
                StudentAttendanceSession.tenant_id == tenant_id,
                StudentAttendanceSession.session_date == daily_date,
            )
            .group_by(StudentAttendanceEntry.status)
        )
        daily_rows = dict((await self.session.execute(daily_entries_stmt)).all())
        p_cnt = daily_rows.get("PRESENT", 0)
        a_cnt = daily_rows.get("ABSENT", 0)
        l_cnt = daily_rows.get("LATE", 0)
        lv_cnt = daily_rows.get("LEAVE", 0)
        tot_roster = p_cnt + a_cnt + l_cnt + lv_cnt
        rate_pct = round(((p_cnt + l_cnt) / max(1, tot_roster)) * 100, 1)

        daily_attendance = {
            "date": daily_date,
            "present": p_cnt,
            "absent": a_cnt,
            "late": l_cnt,
            "leave": lv_cnt,
            "total_roster": tot_roster,
            "rate_percentage": rate_pct,
        }

        # E. Monthly Attendance Trend
        monthly_att_stmt = (
            select(
                func.to_char(StudentAttendanceSession.session_date, "YYYY-MM").label("month"),
                func.count(case((StudentAttendanceEntry.status.in_(["PRESENT", "LATE"]), 1))).label("present_count"),
                func.count(StudentAttendanceEntry.id).label("total_entries"),
            )
            .join(StudentAttendanceEntry, StudentAttendanceEntry.session_id == StudentAttendanceSession.id)
            .where(
                StudentAttendanceSession.tenant_id == tenant_id,
                StudentAttendanceSession.is_deleted == False,
            )
            .group_by("month")
            .order_by("month")
        )
        monthly_att_rows = (await self.session.execute(monthly_att_stmt)).all()
        monthly_attendance = [
            {
                "month": r.month,
                "rate_percentage": round((r.present_count / max(1, r.total_entries)) * 100, 1),
            }
            for r in monthly_att_rows
        ]

        # F. Examination Performance & Pass Percentage
        exam_stmt = (
            select(
                func.count(distinct(StudentSubjectResult.exam_id)).label("tot_exams"),
                func.count(StudentSubjectResult.id).label("tot_evals"),
                func.coalesce(func.avg(StudentSubjectResult.percentage), 0.0).label("avg_pct"),
                func.coalesce(func.max(StudentSubjectResult.percentage), 0.0).label("max_pct"),
                func.count(case((StudentSubjectResult.is_passed == True, 1))).label("pass_cnt"),
            )
            .where(
                StudentSubjectResult.tenant_id == tenant_id,
                StudentSubjectResult.is_deleted == False,
            )
        )
        exam_res = (await self.session.execute(exam_stmt)).first()
        tot_evals = exam_res.tot_evals if exam_res else 0
        pass_cnt = exam_res.pass_cnt if exam_res else 0
        overall_pass_pct = round((pass_cnt / max(1, tot_evals)) * 100, 1)

        examination_performance = {
            "total_exams": exam_res.tot_exams if exam_res else 0,
            "total_evaluations": tot_evals,
            "average_score_percentage": round(float(exam_res.avg_pct), 1) if exam_res else 0.0,
            "highest_score_percentage": round(float(exam_res.max_pct), 1) if exam_res else 0.0,
        }

        # G. Fee Collection
        fee_pay_stmt = (
            select(
                FeePayment.payment_mode,
                func.coalesce(func.sum(FeePayment.amount), Decimal("0.00")),
            )
            .where(
                FeePayment.tenant_id == tenant_id,
                FeePayment.status.in_(["SUCCESS", "SUCCESSFUL"]),
            )
            .group_by(FeePayment.payment_mode)
        )
        pay_rows = (await self.session.execute(fee_pay_stmt)).all()
        by_mode: Dict[str, Decimal] = {}
        tot_collected = Decimal("0.00")
        for mode, amt in pay_rows:
            by_mode[str(mode)] = amt
            tot_collected += amt

        # Invoiced total
        tot_inv_stmt = select(func.coalesce(func.sum(FeeInvoice.total_amount), Decimal("0.00"))).where(
            FeeInvoice.tenant_id == tenant_id,
            FeeInvoice.is_deleted == False,
        )
        tot_invoiced = (await self.session.execute(tot_inv_stmt)).scalar() or Decimal("0.00")

        fee_collection = {
            "total_collected": tot_collected,
            "total_invoiced": tot_invoiced,
            "by_payment_mode": by_mode,
        }

        # H. Pending Fees
        pending_stmt = (
            select(
                func.coalesce(func.sum(FeeInvoice.balance_amount), Decimal("0.00")),
                func.count(case((and_(FeeInvoice.due_date < date.today(), FeeInvoice.balance_amount > 0), 1))),
            )
            .where(
                FeeInvoice.tenant_id == tenant_id,
                FeeInvoice.status.in_(["ISSUED", "PARTIALLY_PAID", "OVERDUE"]),
                FeeInvoice.is_deleted == False,
            )
        )
        pend_res = (await self.session.execute(pending_stmt)).first()
        pending_fees = {
            "total_pending": pend_res[0] if pend_res else Decimal("0.00"),
            "overdue_invoices_count": pend_res[1] if pend_res else 0,
        }

        # I. Admission Statistics (Monthly)
        adm_stmt = (
            select(
                func.to_char(func.coalesce(StudentProfile.admission_date, StudentProfile.created_at), "YYYY-MM").label("month"),
                func.count(StudentProfile.id).label("admissions"),
            )
            .where(
                StudentProfile.tenant_id == tenant_id,
                StudentProfile.is_deleted == False,
            )
            .group_by("month")
            .order_by("month")
        )
        adm_rows = (await self.session.execute(adm_stmt)).all()
        admission_statistics = [{"month": r.month, "admissions_count": r.admissions} for r in adm_rows]

        # J. Teacher Performance & Workload
        pending_eval_stmt = (
            select(func.count(AssignmentSubmission.id))
            .where(
                AssignmentSubmission.tenant_id == tenant_id,
                AssignmentSubmission.status == "SUBMITTED",
            )
        )
        pending_evals = (await self.session.execute(pending_eval_stmt)).scalar() or 0
        teacher_performance = {
            "total_teachers": total_teachers,
            "active_teachers": total_teachers,
            "pending_evaluations_count": pending_evals,
        }

        # K. Academic Trends (Grade distribution)
        grades_stmt = (
            select(
                case(
                    (StudentSubjectResult.percentage >= 90, "A+ (90-100%)"),
                    (StudentSubjectResult.percentage >= 80, "A (80-89%)"),
                    (StudentSubjectResult.percentage >= 70, "B (70-79%)"),
                    (StudentSubjectResult.percentage >= 60, "C (60-69%)"),
                    (StudentSubjectResult.percentage >= 50, "D (50-59%)"),
                    else_="F (<50%)",
                ).label("grade_label"),
                func.count(StudentSubjectResult.id).label("count"),
            )
            .where(
                StudentSubjectResult.tenant_id == tenant_id,
                StudentSubjectResult.is_deleted == False,
            )
            .group_by("grade_label")
        )
        grade_rows = (await self.session.execute(grades_stmt)).all()
        academic_trends = [
            {
                "grade_label": r.grade_label,
                "student_count": r.count,
                "percentage": round((r.count / max(1, tot_evals)) * 100, 1),
            }
            for r in grade_rows
        ]

        return {
            "total_students": total_students,
            "total_teachers": total_teachers,
            "class_distribution": class_distribution,
            "daily_attendance": daily_attendance,
            "monthly_attendance": monthly_attendance,
            "examination_performance": examination_performance,
            "pass_percentage": overall_pass_pct,
            "fee_collection": fee_collection,
            "pending_fees": pending_fees,
            "admission_statistics": admission_statistics,
            "teacher_performance": teacher_performance,
            "academic_trends": academic_trends,
        }

    # ═════════════════════════════════════════════════════════════════════════
    # 3. Teacher Analytics
    # ═════════════════════════════════════════════════════════════════════════
    async def get_teacher_analytics(
        self, tenant_id: uuid.UUID, teacher_id: uuid.UUID
    ) -> Dict[str, Any]:
        teacher = await self.session.get(TeacherProfile, teacher_id)
        teacher_user = await self.session.get(User, teacher.user_id) if teacher else None
        teacher_name = teacher_user.full_name if teacher_user else "Teacher"

        # Assigned subjects & classes
        mappings_stmt = (
            select(TeacherSubjectMapping)
            .where(
                TeacherSubjectMapping.tenant_id == tenant_id,
                TeacherSubjectMapping.teacher_id == teacher_id,
                TeacherSubjectMapping.is_deleted == False,
            )
            .options(
                selectinload(TeacherSubjectMapping.subject),
                selectinload(TeacherSubjectMapping.school_class),
            )
        )
        mappings = (await self.session.execute(mappings_stmt)).scalars().all()
        assigned_subject_ids = [m.subject_id for m in mappings if m.subject_id]
        assigned_class_ids = [m.class_id for m in mappings if m.class_id]

        # Assigned students count
        stu_stmt = select(func.count(distinct(StudentProfile.id))).where(
            StudentProfile.tenant_id == tenant_id,
            StudentProfile.class_id.in_(assigned_class_ids) if assigned_class_ids else False,
            StudentProfile.status == "ACTIVE",
            StudentProfile.is_deleted == False,
        )
        assigned_students = (await self.session.execute(stu_stmt)).scalar() or 0

        # Attendance percentage for teacher's classes
        att_stmt = (
            select(
                func.count(case((StudentAttendanceEntry.status.in_(["PRESENT", "LATE"]), 1))),
                func.count(StudentAttendanceEntry.id),
            )
            .join(StudentAttendanceSession, StudentAttendanceEntry.session_id == StudentAttendanceSession.id)
            .where(
                StudentAttendanceSession.tenant_id == tenant_id,
                StudentAttendanceSession.class_id.in_(assigned_class_ids) if assigned_class_ids else False,
            )
        )
        att_res = (await self.session.execute(att_stmt)).first()
        pres = att_res[0] if att_res else 0
        tot_att = att_res[1] if att_res else 0
        class_att_pct = round((pres / max(1, tot_att)) * 100, 1)

        # Subject performance list
        subject_performance = []
        for m in mappings:
            if not m.subject:
                continue
            res_stmt = (
                select(
                    func.count(StudentSubjectResult.id).label("tot"),
                    func.coalesce(func.avg(StudentSubjectResult.percentage), 0.0).label("avg_score"),
                    func.count(case((StudentSubjectResult.is_passed == True, 1))).label("pass_cnt"),
                )
                .where(
                    StudentSubjectResult.tenant_id == tenant_id,
                    StudentSubjectResult.subject_id == m.subject_id,
                    StudentSubjectResult.class_id == m.class_id,
                )
            )
            res_row = (await self.session.execute(res_stmt)).first()
            tot_s = res_row.tot if res_row else 0
            pass_s = res_row.pass_cnt if res_row else 0
            subject_performance.append({
                "subject_id": m.subject.id,
                "subject_name": m.subject.name,
                "class_name": m.school_class.name if m.school_class else "General",
                "student_count": tot_s,
                "average_score": round(float(res_row.avg_score), 1) if res_row else 0.0,
                "pass_percentage": round((pass_s / max(1, tot_s)) * 100, 1),
            })

        # Examination Statistics
        exam_stmt = (
            select(
                func.count(distinct(StudentSubjectResult.exam_id)),
                func.coalesce(func.avg(StudentSubjectResult.percentage), 0.0),
                func.coalesce(func.max(StudentSubjectResult.percentage), 0.0),
                func.coalesce(func.min(StudentSubjectResult.percentage), 0.0),
            )
            .where(
                StudentSubjectResult.tenant_id == tenant_id,
                StudentSubjectResult.subject_id.in_(assigned_subject_ids) if assigned_subject_ids else False,
            )
        )
        ex_res = (await self.session.execute(exam_stmt)).first()
        exam_stats = {
            "total_exams": ex_res[0] if ex_res else 0,
            "average_score": round(float(ex_res[1]), 1) if ex_res else 0.0,
            "highest_score": round(float(ex_res[2]), 1) if ex_res else 0.0,
            "lowest_score": round(float(ex_res[3]), 1) if ex_res else 0.0,
        }

        # Pending assignment evaluations
        teacher_user_id = teacher.user_id if teacher else None
        pending_stmt = (
            select(func.count(AssignmentSubmission.id))
            .join(Assignment, AssignmentSubmission.assignment_id == Assignment.id)
            .where(
                Assignment.tenant_id == tenant_id,
                Assignment.created_by == teacher_user_id if teacher_user_id else False,
                AssignmentSubmission.status == "SUBMITTED",
            )
        )
        pending_evals = (await self.session.execute(pending_stmt)).scalar() or 0

        return {
            "teacher_id": teacher_id,
            "teacher_name": teacher_name,
            "assigned_students": assigned_students,
            "class_attendance_percentage": class_att_pct,
            "subject_performance": subject_performance,
            "examination_statistics": exam_stats,
            "pending_assignment_evaluation": pending_evals,
        }

    # ═════════════════════════════════════════════════════════════════════════
    # 4. Student Analytics
    # ═════════════════════════════════════════════════════════════════════════
    async def get_student_analytics(
        self, tenant_id: uuid.UUID, student_id: uuid.UUID
    ) -> Dict[str, Any]:
        student = await self.session.get(StudentProfile, student_id)
        user = await self.session.get(User, student.user_id) if student else None
        student_name = user.full_name if user else "Student"

        # Attendance calculation
        att_stmt = (
            select(
                StudentAttendanceEntry.status,
                func.count(StudentAttendanceEntry.id),
            )
            .where(
                StudentAttendanceEntry.tenant_id == tenant_id,
                StudentAttendanceEntry.student_id == student_id,
            )
            .group_by(StudentAttendanceEntry.status)
        )
        att_rows = dict((await self.session.execute(att_stmt)).all())
        p_cnt = att_rows.get("PRESENT", 0)
        a_cnt = att_rows.get("ABSENT", 0)
        l_cnt = att_rows.get("LATE", 0)
        lv_cnt = att_rows.get("LEAVE", 0)
        tot_sessions = p_cnt + a_cnt + l_cnt + lv_cnt
        att_pct = round(((p_cnt + l_cnt) / max(1, tot_sessions)) * 100, 1)

        # Subject marks
        sub_stmt = (
            select(StudentSubjectResult)
            .where(
                StudentSubjectResult.tenant_id == tenant_id,
                StudentSubjectResult.student_id == student_id,
                StudentSubjectResult.is_deleted == False,
            )
            .options(selectinload(StudentSubjectResult.subject))
        )
        sub_rows = (await self.session.execute(sub_stmt)).scalars().all()
        subject_marks = [
            {
                "subject_name": r.subject.name if r.subject else "Subject",
                "marks_obtained": float(r.total_marks or 0.0),
                "max_marks": float(r.max_marks or 100.0),
                "percentage": float(r.percentage or 0.0),
                "grade": r.grade,
            }
            for r in sub_rows
        ]

        # Examination history
        attempt_stmt = (
            select(StudentExamAttempt)
            .where(
                StudentExamAttempt.tenant_id == tenant_id,
                StudentExamAttempt.student_id == student_id,
                StudentExamAttempt.status.in_(["SUBMITTED", "EVALUATED"]),
            )
            .options(selectinload(StudentExamAttempt.exam))
            .order_by(StudentExamAttempt.submitted_at.desc())
        )
        attempts = (await self.session.execute(attempt_stmt)).scalars().all()
        exam_history = []
        for a in attempts:
            tot = float(a.exam.total_marks) if a.exam else 100.0
            obt = float(a.total_score or 0.0)
            pct = round((obt / max(1.0, tot)) * 100, 1)
            is_pass = pct >= (float(a.exam.passing_marks) if a.exam and a.exam.passing_marks else 35.0)
            exam_history.append({
                "exam_id": a.exam_id,
                "exam_title": a.exam.title if a.exam else "Exam",
                "exam_date": a.submitted_at.date() if a.submitted_at else None,
                "marks_obtained": obt,
                "total_marks": tot,
                "percentage": pct,
                "status": "PASS" if is_pass else "FAIL",
            })

        # Assignment completion
        assigned_stmt = select(func.count(Assignment.id)).where(
            Assignment.tenant_id == tenant_id,
            Assignment.class_id == student.class_id if student else False,
        )
        total_assigned = (await self.session.execute(assigned_stmt)).scalar() or 0

        sub_stmt2 = select(func.count(AssignmentSubmission.id)).where(
            AssignmentSubmission.tenant_id == tenant_id,
            AssignmentSubmission.student_id == student_id,
        )
        total_submitted = (await self.session.execute(sub_stmt2)).scalar() or 0

        graded_stmt = select(func.count(AssignmentSubmission.id)).where(
            AssignmentSubmission.tenant_id == tenant_id,
            AssignmentSubmission.student_id == student_id,
            AssignmentSubmission.status == "GRADED",
        )
        total_graded = (await self.session.execute(graded_stmt)).scalar() or 0

        # Academic progress trend (ordered exam scores)
        progress_trend = [
            {"label": e["exam_title"], "percentage": e["percentage"]}
            for e in reversed(exam_history[-5:])
        ]

        return {
            "student_id": student_id,
            "student_name": student_name,
            "admission_number": student.admission_number if student else None,
            "attendance_percentage": att_pct,
            "attendance_breakdown": {
                "present": p_cnt,
                "absent": a_cnt,
                "late": l_cnt,
                "leave": lv_cnt,
                "total_sessions": tot_sessions,
            },
            "subject_marks": subject_marks,
            "examination_history": exam_history,
            "assignment_completion": {
                "total_assigned": total_assigned,
                "total_submitted": total_submitted,
                "total_graded": total_graded,
                "completion_rate": round((total_submitted / max(1, total_assigned)) * 100, 1),
            },
            "academic_progress_trend": progress_trend,
        }

    # ═════════════════════════════════════════════════════════════════════════
    # 5. Parent Analytics
    # ═════════════════════════════════════════════════════════════════════════
    async def get_parent_analytics(
        self, parent_user_id: uuid.UUID, tenant_id: Optional[uuid.UUID] = None
    ) -> Dict[str, Any]:
        parent_user = await self.session.get(User, parent_user_id)
        parent_name = parent_user.full_name if parent_user else "Parent"

        # Verified children query
        links_stmt = (
            select(StudentParent)
            .where(
                StudentParent.parent_user_id == parent_user_id,
                StudentParent.status == "VERIFIED",
                StudentParent.is_deleted == False,
            )
            .options(
                selectinload(StudentParent.student).selectinload(StudentProfile.user),
                selectinload(StudentParent.student).selectinload(StudentProfile.school_class),
            )
        )
        if tenant_id:
            links_stmt = links_stmt.where(StudentParent.tenant_id == tenant_id)

        links = (await self.session.execute(links_stmt)).scalars().all()
        children_summaries = []

        for link in links:
            sp = link.student
            if not sp:
                continue

            child_id = sp.id
            child_name = sp.user.full_name if "user" in sp.__dict__ and sp.user else "Child"
            adm_no = sp.admission_number
            cls_name = sp.school_class.name if "school_class" in sp.__dict__ and sp.school_class else None

            # Attendance
            att_stmt = (
                select(
                    func.count(case((StudentAttendanceEntry.status.in_(["PRESENT", "LATE"]), 1))),
                    func.count(StudentAttendanceEntry.id),
                )
                .where(
                    StudentAttendanceEntry.tenant_id == link.tenant_id,
                    StudentAttendanceEntry.student_id == child_id,
                )
            )
            att_res = (await self.session.execute(att_stmt)).first()
            p_cnt = att_res[0] if att_res else 0
            tot_cnt = att_res[1] if att_res else 0
            child_att_pct = round((p_cnt / max(1, tot_cnt)) * 100, 1)

            # Latest Exam Result
            ex_stmt = (
                select(StudentSubjectResult.percentage, StudentSubjectResult.grade)
                .where(
                    StudentSubjectResult.tenant_id == link.tenant_id,
                    StudentSubjectResult.student_id == child_id,
                )
                .order_by(StudentSubjectResult.created_at.desc())
            )
            latest_res = (await self.session.execute(ex_stmt)).first()
            latest_score = float(latest_res[0]) if latest_res else None
            latest_grade = latest_res[1] if latest_res else None

            # Pending assignments
            assigned_stmt = select(func.count(Assignment.id)).where(
                Assignment.tenant_id == link.tenant_id,
                Assignment.class_id == sp.class_id,
            )
            tot_ass = (await self.session.execute(assigned_stmt)).scalar() or 0

            sub_stmt = select(func.count(AssignmentSubmission.id)).where(
                AssignmentSubmission.tenant_id == link.tenant_id,
                AssignmentSubmission.student_id == child_id,
            )
            tot_sub = (await self.session.execute(sub_stmt)).scalar() or 0
            pending_ass = max(0, tot_ass - tot_sub)

            # Fee Dues
            due_stmt = (
                select(
                    func.coalesce(func.sum(FeeInvoice.balance_amount), Decimal("0.00")),
                    func.count(case((and_(FeeInvoice.due_date < date.today(), FeeInvoice.balance_amount > 0), 1))),
                )
                .where(
                    FeeInvoice.tenant_id == link.tenant_id,
                    FeeInvoice.student_id == child_id,
                    FeeInvoice.status.in_(["ISSUED", "PARTIALLY_PAID", "OVERDUE"]),
                )
            )
            fee_res = (await self.session.execute(due_stmt)).first()
            dues = fee_res[0] if fee_res else Decimal("0.00")
            overdue = (fee_res[1] > 0) if fee_res else False

            children_summaries.append({
                "student_id": child_id,
                "student_name": child_name,
                "admission_number": adm_no,
                "class_name": cls_name,
                "attendance_percentage": child_att_pct,
                "latest_exam_score": latest_score,
                "overall_grade": latest_grade,
                "pending_assignments": pending_ass,
                "total_fee_dues": dues,
                "fee_overdue": overdue,
            })

        return {
            "parent_user_id": parent_user_id,
            "parent_name": parent_name,
            "children_count": len(children_summaries),
            "children": children_summaries,
        }

    # ═════════════════════════════════════════════════════════════════════════
    # 6. Scheduled Reports CRUD
    # ═════════════════════════════════════════════════════════════════════════
    async def create_scheduled_report(
        self,
        tenant_id: Optional[uuid.UUID],
        user_id: uuid.UUID,
        title: str,
        report_type: str,
        frequency: str = "WEEKLY",
        report_format: str = "PDF",
        recipients: Optional[List[str]] = None,
        filters: Optional[Dict[str, Any]] = None,
    ) -> ScheduledReport:
        now = datetime.now(timezone.utc)
        delta_days = 1 if frequency == "DAILY" else 7 if frequency == "WEEKLY" else 30
        schedule = ScheduledReport(
            tenant_id=tenant_id,
            user_id=user_id,
            title=title,
            report_type=report_type,
            frequency=frequency,
            format=report_format,
            recipients=recipients or [],
            filters=filters or {},
            next_run_at=now + timedelta(days=delta_days),
            is_active=True,
        )
        self.session.add(schedule)
        await self.session.flush()
        return schedule

    async def list_scheduled_reports(
        self, tenant_id: Optional[uuid.UUID] = None, user_id: Optional[uuid.UUID] = None
    ) -> List[ScheduledReport]:
        stmt = select(ScheduledReport).where(ScheduledReport.is_deleted == False)
        if tenant_id is not None:
            stmt = stmt.where(ScheduledReport.tenant_id == tenant_id)
        if user_id is not None:
            stmt = stmt.where(ScheduledReport.user_id == user_id)
        stmt = stmt.order_by(ScheduledReport.created_at.desc())
        return list((await self.session.execute(stmt)).scalars().all())

    async def get_scheduled_report_by_id(
        self, schedule_id: uuid.UUID, tenant_id: Optional[uuid.UUID] = None
    ) -> Optional[ScheduledReport]:
        stmt = select(ScheduledReport).where(
            ScheduledReport.id == schedule_id,
            ScheduledReport.is_deleted == False,
        )
        if tenant_id is not None:
            stmt = stmt.where(ScheduledReport.tenant_id == tenant_id)
        return (await self.session.execute(stmt)).scalars().first()

    async def delete_scheduled_report(
        self, schedule_id: uuid.UUID, tenant_id: Optional[uuid.UUID] = None
    ) -> bool:
        schedule = await self.get_scheduled_report_by_id(schedule_id, tenant_id)
        if not schedule:
            return False
        schedule.is_deleted = True
        schedule.is_active = False
        await self.session.flush()
        return True
