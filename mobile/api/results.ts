import { apiClient } from './client'

export interface MobileStudentSubjectResult {
  id: string
  subject_name?: string
  subject_code?: string
  theory_marks: number
  practical_marks: number
  internal_marks: number
  assignment_marks: number
  total_marks: number
  max_marks: number
  percentage?: number
  grade?: string
  credits: number
  is_passed: boolean
}

export interface MobileStudentTermResult {
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
  total_obtained: number
  total_max: number
  overall_percentage: number
  overall_grade: string
  cgpa?: number
  sgpa?: number
  rank?: number
  is_passed: boolean
  attendance_percentage?: number
  approval_status: string
  subject_results?: MobileStudentSubjectResult[]
}

export interface MobileReEvaluationCreate {
  subject_result_id: string
  reason: string
}

export const mobileResultsApi = {
  getStudentReportCard: async (examId: string, studentId: string): Promise<MobileStudentTermResult> => {
    const res = await apiClient.get(`/results/exams/${examId}/students/${studentId}`)
    return res.data.data
  },

  submitReEvaluation: async (data: MobileReEvaluationCreate): Promise<any> => {
    const res = await apiClient.post('/results/re-evaluations', data)
    return res.data.data
  },
}
