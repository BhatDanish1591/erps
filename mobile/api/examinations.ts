import { apiClient } from './client'

export interface MobileExaminationItem {
  id: string
  title: string
  code?: string
  exam_type: string
  mode: string
  total_marks: number
  passing_marks: number
  duration_minutes: number
  start_datetime?: string
  end_datetime?: string
  status: string
  is_published: boolean
  is_results_published: boolean
  subject_name?: string
  class_name?: string
  questions_count: number
}

export interface MobileQuestionTaking {
  id: string
  order_index: number
  question_type: string
  question_text: string
  options?: Array<{ id: string; text: string }>
  marks: number
  negative_marks: number
  is_mandatory: boolean
}

export interface MobileActiveAttempt {
  attempt_id: string
  exam_id: string
  exam_title: string
  duration_minutes: number
  started_at: string
  expires_at: string
  remaining_seconds: number
  status: string
  questions: MobileQuestionTaking[]
  saved_answers: Record<string, any>
}

export interface MobileSubmitResult {
  attempt_id: string
  status: string
  submitted_at: string
  instant_score?: number
  is_evaluated: boolean
  message: string
}

export interface MobileExamResultDetail {
  attempt_id: string
  exam_id: string
  exam_title: string
  total_marks: number
  passing_marks: number
  total_score?: number
  percentage?: number
  is_passed?: boolean
  status: string
  is_results_published: boolean
}

export const mobileExaminationsApi = {
  listExaminations: async (params?: { status?: string }) => {
    const res = await apiClient.get('/examinations/', { params })
    return res.data.data as MobileExaminationItem[]
  },

  startOrResumeExam: async (examId: string) => {
    const res = await apiClient.post(`/examinations/${examId}/start`)
    return res.data.data as MobileActiveAttempt
  },

  autosaveAnswers: async (attemptId: string, answers: Array<{ question_id: string; student_answer: any }>) => {
    const res = await apiClient.post(`/examinations/attempts/${attemptId}/autosave`, { answers })
    return res.data.data
  },

  submitExam: async (attemptId: string, payload: { submission_hash?: string; final_answers?: any[] }) => {
    const res = await apiClient.post(`/examinations/attempts/${attemptId}/submit`, payload)
    return res.data.data as MobileSubmitResult
  },

  getExamResult: async (attemptId: string) => {
    const res = await apiClient.get(`/examinations/attempts/${attemptId}/result`)
    return res.data.data as MobileExamResultDetail
  },
}
