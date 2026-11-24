import apiClient from './client'

export interface MonthlyInstitutionGrowth {
  month: string
  new_institutions: number
  total_institutions: number
}

export interface PlanDistributionItem {
  plan_id?: string
  plan_name: string
  plan_code: string
  count: number
  percentage: number
}

export interface SuperAdminAnalyticsResponse {
  total_institutions: number
  active_subscriptions: number
  expired_subscriptions: number
  monthly_recurring_revenue: number
  annual_recurring_revenue: number
  institution_growth: MonthlyInstitutionGrowth[]
  subscription_plan_distribution: PlanDistributionItem[]
  payment_failures: {
    failed_count: number
    failed_amount: number
  }
  user_statistics: {
    total_users: number
    roles: Record<string, number>
  }
}

export interface ClassDistributionItem {
  class_id: string
  class_name: string
  student_count: number
  section_count: number
}

export interface DailyAttendanceMetric {
  date: string
  present: number
  absent: number
  late: number
  leave: number
  total_roster: number
  rate_percentage: number
}

export interface MonthlyAttendanceItem {
  month: string
  rate_percentage: number
}

export interface ExamPerformanceMetric {
  total_exams: number
  total_evaluations: number
  average_score_percentage: number
  highest_score_percentage: number
}

export interface FeeCollectionMetric {
  total_collected: number
  total_invoiced: number
  by_payment_mode: Record<string, number>
}

export interface PendingFeesMetric {
  total_pending: number
  overdue_invoices_count: number
}

export interface MonthlyAdmissionItem {
  month: string
  admissions_count: number
}

export interface AcademicTrendItem {
  grade_label: string
  student_count: number
  percentage: number
}

export interface InstitutionAdminAnalyticsResponse {
  total_students: number
  total_teachers: number
  class_distribution: ClassDistributionItem[]
  daily_attendance: DailyAttendanceMetric
  monthly_attendance: MonthlyAttendanceItem[]
  examination_performance: ExamPerformanceMetric
  pass_percentage: number
  fee_collection: FeeCollectionMetric
  pending_fees: PendingFeesMetric
  admission_statistics: MonthlyAdmissionItem[]
  teacher_performance: {
    total_teachers: number
    active_teachers: number
    pending_evaluations_count: number
  }
  academic_trends: AcademicTrendItem[]
}

export interface SubjectPerformanceItem {
  subject_id: string
  subject_name: string
  class_name: string
  student_count: number
  average_score: number
  pass_percentage: number
}

export interface TeacherAnalyticsResponse {
  teacher_id: string
  teacher_name: string
  assigned_students: number
  class_attendance_percentage: number
  subject_performance: SubjectPerformanceItem[]
  examination_statistics: Record<string, any>
  pending_assignment_evaluation: number
}

export interface StudentSubjectMarkItem {
  subject_name: string
  marks_obtained: number
  max_marks: number
  percentage: number
  grade?: string
}

export interface StudentExamHistoryItem {
  exam_id: string
  exam_title: string
  exam_date?: string
  marks_obtained: number
  total_marks: number
  percentage: number
  status: string
}

export interface StudentAnalyticsResponse {
  student_id: string
  student_name: string
  admission_number?: string
  attendance_percentage: number
  attendance_breakdown: {
    present: number
    absent: number
    late: number
    leave: number
    total_sessions: number
  }
  subject_marks: StudentSubjectMarkItem[]
  examination_history: StudentExamHistoryItem[]
  assignment_completion: {
    total_assigned: number
    total_submitted: number
    total_graded: number
    completion_rate: number
  }
  academic_progress_trend: Array<{ label: string; percentage: number }>
}

export interface ChildProgressSummary {
  student_id: string
  student_name: string
  admission_number?: string
  class_name?: string
  attendance_percentage: number
  latest_exam_score?: number
  overall_grade?: string
  pending_assignments: number
  total_fee_dues: number
  fee_overdue: boolean
}

export interface ParentAnalyticsResponse {
  parent_user_id: string
  parent_name: string
  children_count: number
  children: ChildProgressSummary[]
}

export interface ScheduledReport {
  id: string
  tenant_id?: string
  user_id: string
  title: string
  report_type: string
  frequency: string
  format: string
  recipients: string[]
  filters: Record<string, any>
  last_run_at?: string
  next_run_at?: string
  is_active: boolean
  created_at: string
}

export interface ScheduledReportCreate {
  title: string
  report_type: string
  frequency?: string
  format?: string
  recipients?: string[]
  filters?: Record<string, any>
}

export interface AnalyticsFilterParams {
  start_date?: string
  end_date?: string
  academic_session_id?: string
  class_id?: string
  subject_id?: string
}

export const reportsApi = {
  // Super Admin
  getSuperAdminAnalytics: async (): Promise<SuperAdminAnalyticsResponse> => {
    const res = await apiClient.get<SuperAdminAnalyticsResponse>('/reports/super-admin')
    return res.data
  },

  // Institution Admin
  getInstitutionAdminAnalytics: async (
    params?: AnalyticsFilterParams
  ): Promise<InstitutionAdminAnalyticsResponse> => {
    const res = await apiClient.get<InstitutionAdminAnalyticsResponse>('/reports/institution-admin', {
      params,
    })
    return res.data
  },

  // Teacher
  getTeacherAnalytics: async (teacherId?: string): Promise<TeacherAnalyticsResponse> => {
    const res = await apiClient.get<TeacherAnalyticsResponse>('/reports/teacher', {
      params: teacherId ? { teacher_id: teacherId } : undefined,
    })
    return res.data
  },

  // Student
  getStudentAnalytics: async (studentId?: string): Promise<StudentAnalyticsResponse> => {
    const res = await apiClient.get<StudentAnalyticsResponse>('/reports/student', {
      params: studentId ? { student_id: studentId } : undefined,
    })
    return res.data
  },

  // Parent
  getParentAnalytics: async (parentUserId?: string): Promise<ParentAnalyticsResponse> => {
    const res = await apiClient.get<ParentAnalyticsResponse>('/reports/parent', {
      params: parentUserId ? { parent_user_id: parentUserId } : undefined,
    })
    return res.data
  },

  // Binary Exports
  exportPdf: async (reportType: string, params?: AnalyticsFilterParams): Promise<Blob> => {
    const res = await apiClient.get('/reports/export/pdf', {
      params: { report_type: reportType, ...params },
      responseType: 'blob',
    })
    return res.data
  },

  exportExcel: async (reportType: string, params?: AnalyticsFilterParams): Promise<Blob> => {
    const res = await apiClient.get('/reports/export/excel', {
      params: { report_type: reportType, ...params },
      responseType: 'blob',
    })
    return res.data
  },

  // Scheduled Reports CRUD
  listScheduledReports: async (): Promise<ScheduledReport[]> => {
    const res = await apiClient.get<ScheduledReport[]>('/reports/scheduled')
    return res.data
  },

  createScheduledReport: async (data: ScheduledReportCreate): Promise<ScheduledReport> => {
    const res = await apiClient.post<ScheduledReport>('/reports/scheduled', data)
    return res.data
  },

  triggerScheduledReport: async (scheduleId: string): Promise<{ success: boolean; status: string }> => {
    const res = await apiClient.post(`/reports/scheduled/${scheduleId}/trigger`)
    return res.data
  },

  deleteScheduledReport: async (scheduleId: string): Promise<{ success: boolean }> => {
    const res = await apiClient.delete(`/reports/scheduled/${scheduleId}`)
    return res.data
  },
}
