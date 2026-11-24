import { apiClient } from './client'

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
  subject_marks: Array<{
    subject_name: string
    marks_obtained: number
    max_marks: number
    percentage: number
    grade?: string
  }>
  examination_history: Array<{
    exam_id: string
    exam_title: string
    exam_date?: string
    marks_obtained: number
    total_marks: number
    percentage: number
    status: string
  }>
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

export interface TeacherAnalyticsResponse {
  teacher_id: string
  teacher_name: string
  assigned_students: number
  class_attendance_percentage: number
  subject_performance: Array<{
    subject_id: string
    subject_name: string
    class_name: string
    student_count: number
    average_score: number
    pass_percentage: number
  }>
  examination_statistics: Record<string, any>
  pending_assignment_evaluation: number
}

export const mobileReportsApi = {
  getStudentAnalytics: async (studentId?: string): Promise<StudentAnalyticsResponse> => {
    const res = await apiClient.get<StudentAnalyticsResponse>('/reports/student', {
      params: studentId ? { student_id: studentId } : undefined,
    })
    return res.data
  },

  getParentAnalytics: async (parentUserId?: string): Promise<ParentAnalyticsResponse> => {
    const res = await apiClient.get<ParentAnalyticsResponse>('/reports/parent', {
      params: parentUserId ? { parent_user_id: parentUserId } : undefined,
    })
    return res.data
  },

  getTeacherAnalytics: async (teacherId?: string): Promise<TeacherAnalyticsResponse> => {
    const res = await apiClient.get<TeacherAnalyticsResponse>('/reports/teacher', {
      params: teacherId ? { teacher_id: teacherId } : undefined,
    })
    return res.data
  },
}
