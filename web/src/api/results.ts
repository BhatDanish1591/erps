import apiClient from './client'

export interface GradeRule {
  grade: string
  min_percentage: number
  max_percentage: number
  grade_point: number
  description?: string
}

export interface GradingScale {
  id: string
  name: string
  scale_type: string
  grades: GradeRule[]
  is_default: boolean
  created_at: string
}

export interface SubjectMarksEntryItem {
  student_id: string
  student_name?: string
  admission_number?: string
  roll_number?: string
  theory_marks: number
  theory_max_marks: number
  practical_marks: number
  practical_max_marks: number
  internal_marks: number
  internal_max_marks: number
  assignment_marks: number
  assignment_max_marks: number
  credits: number
  remarks?: string
}

export interface BulkSubjectMarksEntryRequest {
  exam_id: string
  academic_session_id: string
  subject_id: string
  class_id?: string
  section_id?: string
  course_id?: string
  semester_id?: string
  entries: SubjectMarksEntryItem[]
}

export interface StudentSubjectResult {
  id: string
  student_id: string
  student_name?: string
  admission_number?: string
  roll_number?: string
  exam_id: string
  subject_id: string
  subject_name?: string
  subject_code?: string
  theory_marks: number
  theory_max_marks: number
  practical_marks: number
  practical_max_marks: number
  internal_marks: number
  internal_max_marks: number
  assignment_marks: number
  assignment_max_marks: number
  total_marks: number
  max_marks: number
  percentage?: number
  grade?: string
  grade_point: number
  credits: number
  credit_points: number
  is_passed: boolean
  status: string
  remarks?: string
}

export interface StudentTermResult {
  id: string
  student_id: string
  student_name: string
  admission_number: string
  roll_number?: string
  exam_id: string
  exam_title: string
  academic_session_name?: string
  class_name?: string
  section_name?: string
  course_name?: string
  semester_name?: string
  total_obtained: number
  total_max: number
  overall_percentage: number
  overall_grade: string
  cgpa?: number
  sgpa?: number
  total_credits: number
  earned_credits: number
  rank?: number
  is_passed: boolean
  attendance_percentage?: number
  total_attendance_days?: number
  present_days?: number
  approval_status: 'DRAFT' | 'SUBMITTED' | 'IN_REVIEW' | 'APPROVED' | 'PUBLISHED'
  approved_at?: string
  published_at?: string
  subject_results?: StudentSubjectResult[]
}

export interface ResultApprovalWorkflowRequest {
  exam_id: string
  action: 'SUBMIT_FOR_REVIEW' | 'START_REVIEW' | 'APPROVE' | 'PUBLISH' | 'REJECT_TO_DRAFT'
  comments?: string
}

export interface ResultRevisionHistory {
  id: string
  subject_result_id: string
  previous_marks: Record<string, any>
  new_marks: Record<string, any>
  revision_reason: string
  modified_by: string
  modified_by_name?: string
  approved_by?: string
  approved_by_name?: string
  modified_at: string
}

export interface ResultRevisionRequest {
  subject_result_id: string
  theory_marks?: number
  practical_marks?: number
  internal_marks?: number
  assignment_marks?: number
  revision_reason: string
}

export interface ReEvaluationRequestItem {
  id: string
  subject_result_id: string
  student_id: string
  student_name: string
  subject_name: string
  reason: string
  status: 'PENDING' | 'UNDER_REVIEW' | 'APPROVED_UPDATED' | 'REJECTED'
  reviewer_name?: string
  reviewer_remarks?: string
  reviewed_at?: string
  created_at: string
}

export interface ReEvaluationActionRequest {
  status: 'UNDER_REVIEW' | 'APPROVED_UPDATED' | 'REJECTED'
  reviewer_remarks: string
  updated_theory_marks?: number
  updated_practical_marks?: number
  updated_internal_marks?: number
}

export interface SubjectPerformanceStats {
  subject_id: string
  subject_name: string
  subject_code: string
  average_marks: number
  highest_marks: number
  lowest_marks: number
  pass_percentage: number
  total_appeared: number
}

export interface ClassPerformanceAnalytics {
  exam_id: string
  exam_title: string
  total_students: number
  passed_students: number
  failed_students: number
  pass_percentage: number
  class_average_percentage: number
  highest_percentage: number
  lowest_percentage: number
  subject_analytics: SubjectPerformanceStats[]
  grade_distribution: Record<string, number>
}

export const resultsApi = {
  getMarksRoster: async (examId: string, subjectId: string) => {
    const response = await apiClient.get<{ data: (Partial<SubjectMarksEntryItem> & { student_id: string })[] }>(
      `/results/exams/${examId}/marks-roster`, { params: { subject_id: subjectId } },
    )
    return response.data.data
  },
  getGradingScale: async (): Promise<GradingScale> => {
    const res = await apiClient.get('/results/grading-scales')
    return res.data.data
  },

  createGradingScale: async (data: Partial<GradingScale>): Promise<GradingScale> => {
    const res = await apiClient.post('/results/grading-scales', data)
    return res.data.data
  },

  bulkEnterMarks: async (data: BulkSubjectMarksEntryRequest): Promise<StudentSubjectResult[]> => {
    const res = await apiClient.post('/results/marks/bulk', data)
    return res.data.data
  },

  listExamResults: async (
    examId: string,
    params?: { class_id?: string; section_id?: string; approval_status?: string }
  ): Promise<StudentTermResult[]> => {
    const res = await apiClient.get(`/results/exams/${examId}`, { params })
    return res.data.data
  },

  getStudentReportCard: async (examId: string, studentId: string): Promise<StudentTermResult> => {
    const res = await apiClient.get(`/results/exams/${examId}/students/${studentId}`)
    return res.data.data
  },

  processApprovalWorkflow: async (data: ResultApprovalWorkflowRequest): Promise<any> => {
    const res = await apiClient.post('/results/approval-workflow', data)
    return res.data.data
  },

  reviseMarks: async (data: ResultRevisionRequest): Promise<StudentSubjectResult> => {
    const res = await apiClient.post('/results/revisions', data)
    return res.data.data
  },

  getRevisionHistory: async (subjectResultId: string): Promise<ResultRevisionHistory[]> => {
    const res = await apiClient.get(`/results/revisions/${subjectResultId}`)
    return res.data.data
  },

  submitReevaluation: async (data: { subject_result_id: string; reason: string }): Promise<ReEvaluationRequestItem> => {
    const res = await apiClient.post('/results/re-evaluations', data)
    return res.data.data
  },

  listReevaluations: async (status?: string): Promise<ReEvaluationRequestItem[]> => {
    const res = await apiClient.get('/results/re-evaluations', { params: { status } })
    return res.data.data
  },

  resolveReevaluation: async (requestId: string, data: ReEvaluationActionRequest): Promise<ReEvaluationRequestItem> => {
    const res = await apiClient.post(`/results/re-evaluations/${requestId}/resolve`, data)
    return res.data.data
  },

  getClassAnalytics: async (examId: string): Promise<ClassPerformanceAnalytics> => {
    const res = await apiClient.get(`/results/exams/${examId}/analytics`)
    return res.data.data
  },

  downloadReportCardPdf: async (examId: string, studentId: string): Promise<Blob> => {
    const res = await apiClient.get(`/results/exams/${examId}/students/${studentId}/pdf`, {
      responseType: 'blob',
    })
    return res.data
  },
}
