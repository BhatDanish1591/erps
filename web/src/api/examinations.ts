import apiClient from './client'

export interface QuestionBankItem {
  id: string
  subject_id?: string
  category: string
  difficulty: 'EASY' | 'MEDIUM' | 'HARD'
  question_type: 'MCQ' | 'MULTIPLE_SELECT' | 'TRUE_FALSE' | 'SHORT_ANSWER' | 'LONG_ANSWER' | 'FILL_IN_THE_BLANKS' | 'MATCHING' | 'NUMERICAL' | 'FILE_UPLOAD'
  question_text: string
  options?: any
  correct_answer?: any
  explanation?: string
  rubric?: any
  default_marks: number
  default_negative_marks: number
  is_active: boolean
  created_at: string
}

export interface ExaminationQuestion {
  id: string
  exam_id: string
  question_id?: string
  question_type: string
  question_text: string
  options?: any
  correct_answer?: any
  explanation?: string
  order_index: number
  marks: number
  negative_marks: number
  is_mandatory: boolean
}

export interface ExaminationItem {
  id: string
  academic_session_id: string
  title: string
  code?: string
  exam_type: string
  mode: 'ONLINE' | 'OFFLINE' | 'HYBRID'
  subject_id?: string
  class_id?: string
  section_id?: string
  course_id?: string
  semester_id?: string
  batch_id?: string
  total_marks: number
  passing_marks: number
  duration_minutes: number
  start_datetime?: string
  end_datetime?: string
  shuffle_questions: boolean
  shuffle_options: boolean
  allow_late_submission: boolean
  late_submission_grace_minutes: number
  max_attempts: number
  instructions?: string
  status: 'DRAFT' | 'SCHEDULED' | 'ONGOING' | 'COMPLETED' | 'ARCHIVED'
  is_published: boolean
  is_results_published: boolean
  results_published_at?: string
  created_at: string
  subject_name?: string
  class_name?: string
  section_name?: string
  course_name?: string
  semester_name?: string
  questions_count: number
  attempts_count: number
  questions?: ExaminationQuestion[]
}

export interface StudentExamQuestionTaking {
  id: string
  order_index: number
  question_type: string
  question_text: string
  options?: any
  marks: number
  negative_marks: number
  is_mandatory: boolean
}

export interface StudentActiveAttemptResponse {
  attempt_id: string
  exam_id: string
  exam_title: string
  duration_minutes: number
  started_at: string
  expires_at: string
  remaining_seconds: number
  status: string
  questions: StudentExamQuestionTaking[]
  saved_answers: Record<string, any>
}

export interface SubmitAttemptResponse {
  attempt_id: string
  status: string
  submitted_at: string
  instant_score?: number
  is_evaluated: boolean
  message: string
}

export interface StudentResultQuestionReview {
  question_id: string
  order_index: number
  question_text: string
  question_type: string
  options?: any
  student_answer?: any
  correct_answer?: any
  explanation?: string
  marks_awarded?: number
  max_marks: number
  is_correct?: boolean
  teacher_feedback?: string
}

export interface StudentExamResultResponse {
  attempt_id: string
  exam_id: string
  exam_title: string
  total_marks: number
  passing_marks: number
  total_score?: number
  percentage?: number
  is_passed?: boolean
  rank?: number
  status: string
  is_results_published: boolean
  submitted_at?: string
  review_questions?: StudentResultQuestionReview[]
}

export interface AttemptEvaluationAnswer {
  id: string
  exam_question_id: string
  question_text: string
  question_type: string
  options?: any
  correct_answer?: any
  explanation?: string
  student_answer?: any
  max_marks: number
  negative_marks: number
  is_correct?: boolean
  marks_awarded?: number
  teacher_feedback?: string
  is_evaluated: boolean
}

export interface AttemptEvaluationDetailResponse {
  attempt_id: string
  exam_id: string
  exam_title: string
  student_id: string
  student_name: string
  admission_number: string
  roll_number?: string
  attempt_number: number
  status: string
  started_at: string
  submitted_at?: string
  total_score?: number
  percentage?: number
  is_passed?: boolean
  answers: AttemptEvaluationAnswer[]
}

export interface ExaminationAnalytics {
  exam_id: string
  title: string
  total_enrolled: number
  total_attempts: number
  submitted_count: number
  evaluated_count: number
  average_score: number
  highest_score: number
  lowest_score: number
  pass_percentage: number
  grade_distribution: Record<string, number>
  question_analytics: Array<{
    question_id: string
    order_index: number
    question_text: string
    question_type: string
    max_marks: number
    total_attempts: number
    correct_count: number
    success_rate: number
  }>
}

export const examinationsApi = {
  // Question Bank
  listQuestions: async (params?: {
    subject_id?: string
    category?: string
    difficulty?: string
    question_type?: string
    search?: string
    skip?: number
    limit?: number
  }) => {
    const res = await apiClient.get('/examinations/questions', { params })
    return res.data
  },

  createQuestion: async (payload: Partial<QuestionBankItem>) => {
    const res = await apiClient.post('/examinations/questions', payload)
    return res.data.data
  },

  updateQuestion: async (id: string, payload: Partial<QuestionBankItem>) => {
    const res = await apiClient.put(`/examinations/questions/${id}`, payload)
    return res.data.data
  },

  deleteQuestion: async (id: string) => {
    await apiClient.delete(`/examinations/questions/${id}`)
  },

  // Examinations
  listExaminations: async (params?: {
    academic_session_id?: string
    subject_id?: string
    class_id?: string
    section_id?: string
    course_id?: string
    semester_id?: string
    status?: string
    exam_type?: string
    search?: string
    skip?: number
    limit?: number
  }) => {
    const res = await apiClient.get('/examinations/', { params })
    return res.data
  },

  getExamination: async (id: string) => {
    const res = await apiClient.get(`/examinations/${id}`)
    return res.data.data as ExaminationItem
  },

  createExamination: async (payload: any) => {
    const res = await apiClient.post('/examinations/', payload)
    return res.data.data as ExaminationItem
  },

  updateExamination: async (id: string, payload: any) => {
    const res = await apiClient.put(`/examinations/${id}`, payload)
    return res.data.data as ExaminationItem
  },

  deleteExamination: async (id: string) => {
    await apiClient.delete(`/examinations/${id}`)
  },

  addQuestionToExam: async (examId: string, payload: any) => {
    const res = await apiClient.post(`/examinations/${examId}/questions`, payload)
    return res.data.data
  },

  removeQuestionFromExam: async (examId: string, questionId: string) => {
    await apiClient.delete(`/examinations/${examId}/questions/${questionId}`)
  },

  // Student Online Room & Taking
  startOrResumeExam: async (examId: string) => {
    const res = await apiClient.post(`/examinations/${examId}/start`)
    return res.data.data as StudentActiveAttemptResponse
  },

  autosaveExamAnswers: async (attemptId: string, answers: Array<{ question_id: string; student_answer: any }>) => {
    const res = await apiClient.post(`/examinations/attempts/${attemptId}/autosave`, { answers })
    return res.data.data
  },

  submitExamAttempt: async (attemptId: string, payload: { submission_hash?: string; final_answers?: any[] }) => {
    const res = await apiClient.post(`/examinations/attempts/${attemptId}/submit`, payload)
    return res.data.data as SubmitAttemptResponse
  },

  getExamResult: async (attemptId: string) => {
    const res = await apiClient.get(`/examinations/attempts/${attemptId}/result`)
    return res.data.data as StudentExamResultResponse
  },

  // Teacher / Admin Grading & Monitoring
  listExamAttempts: async (examId: string, params?: { status?: string; skip?: number; limit?: number }) => {
    const res = await apiClient.get(`/examinations/${examId}/attempts`, { params })
    return res.data
  },

  getAttemptForEvaluation: async (attemptId: string) => {
    const res = await apiClient.get(`/examinations/attempts/${attemptId}/evaluation`)
    return res.data.data as AttemptEvaluationDetailResponse
  },

  evaluateAttempt: async (attemptId: string, payload: { evaluations: Array<{ answer_id: string; marks_awarded: number; teacher_feedback?: string }> }) => {
    const res = await apiClient.post(`/examinations/attempts/${attemptId}/evaluate`, payload)
    return res.data.data as AttemptEvaluationDetailResponse
  },

  getExamAnalytics: async (examId: string) => {
    const res = await apiClient.get(`/examinations/${examId}/analytics`)
    return res.data.data as ExaminationAnalytics
  },
}
