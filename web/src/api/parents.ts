import apiClient from './client'

export interface LinkedChildSummary {
  student_id: string
  student_name: string
  admission_number: string
  institution_id: string
  institution_name: string
  relation_type: string
  verification_status: 'PENDING_APPROVAL' | 'VERIFIED' | 'REJECTED' | 'REVOKED'
  class_name?: string | null
  section_name?: string | null
  course_name?: string | null
  total_due_fees: number
  can_view_grades: boolean
  can_pay_fees: boolean
}

export interface LinkChildRequest {
  admission_number: string
  relation_type: string
  verification_code?: string
  notes?: string
}

export interface ChildDetailedProfileResponse {
  student_id: string
  admission_number: string
  full_name: string
  date_of_birth?: string | null
  gender?: string | null
  blood_group?: string | null
  emergency_contact: boolean
  institution_name: string
  academic_session_name?: string | null
  class_name?: string | null
  section_name?: string | null
  course_name?: string | null
}

export interface ChildAttendanceResponse {
  overall_percentage: number
  total_days: number
  present_days: number
  absent_days: number
  late_days: number
  low_attendance_alert: boolean
  recent_entries: {
    date: string
    status: string
    period_number?: number | null
    subject_name?: string | null
    remarks?: string | null
  }[]
}

export interface ChildTimetableResponse {
  schedule: {
    day_of_week: string
    entries: {
      period_number: number
      start_time: string
      end_time: string
      subject_name: string
      teacher_name?: string | null
      room_number?: string | null
    }[]
  }[]
}

interface ChildExamScheduleItem {
  exam_id: string
  title: string
  exam_type: string
  is_online: boolean
  exam_date: string
  start_time: string
  duration_minutes: number
  total_marks: number
  passing_marks: number
  subject_name: string
}

export interface ChildExaminationsResponse {
  upcoming_exams: ChildExamScheduleItem[]
  past_exams: ChildExamScheduleItem[]
}

export interface ChildTermResultResponse {
  result_id: string
  examination_title: string
  academic_session_name: string
  total_marks_obtained: number
  max_marks_possible: number
  percentage: number
  final_grade?: string | null
  cgpa?: number | null
  result_status: 'PASS' | 'FAIL'
  subjects: {
    subject_name: string
    subject_code: string
    theory_marks?: number | null
    practical_marks?: number | null
    assignment_marks?: number | null
    total_marks: number
    max_marks: number
    grade?: string | null
    is_pass: boolean
  }[]
}

export interface ChildAssignmentItem {
  id: string
  title: string
  subject_name: string
  teacher_name: string
  due_date: string
  max_score: number
  is_submitted: boolean
  is_late: boolean
  score?: number | null
  teacher_feedback?: string | null
}

export interface ChildStudyMaterialItem {
  id: string
  title: string
  subject_name: string
  material_type: string
  download_url?: string | null
  external_url?: string | null
  created_at: string
}

export interface ChildFeesResponse {
  total_due: number
  invoices: {
    id: string
    invoice_number: string
    title: string
    due_date: string
    total_amount: number
    paid_amount: number
    balance_amount: number
    status: string
  }[]
  payments: {
    id: string
    receipt_number: string
    amount: number
    payment_mode: string
    payment_date: string
    status: string
    transaction_reference?: string | null
  }[]
}

export interface ChildTeacherItem {
  teacher_user_id: string
  teacher_name: string
  subject_name: string
}

export interface ParentTeacherMessageResponse {
  id: string
  sender_role: string
  parent_name: string
  teacher_name: string
  subject: string
  message: string
  created_at: string
  replies: ParentTeacherMessageResponse[]
}

export interface SendMessageRequest {
  teacher_user_id: string
  student_id: string
  subject: string
  message: string
}

export const parentsApi = {
  // Parent Operations
  listChildren: async (): Promise<LinkedChildSummary[]> => {
    const res = await apiClient.get<LinkedChildSummary[]>('/parents/children')
    return res.data
  },

  requestLinkChild: async (data: LinkChildRequest): Promise<{ status: string; message: string }> => {
    const res = await apiClient.post<{ status: string; message: string }>('/parents/link-requests', data)
    return res.data
  },

  getChildProfile: async (studentId: string): Promise<ChildDetailedProfileResponse> => {
    const res = await apiClient.get<ChildDetailedProfileResponse>(`/parents/children/${studentId}/profile`)
    return res.data
  },

  getChildAttendance: async (studentId: string): Promise<ChildAttendanceResponse> => {
    const res = await apiClient.get<ChildAttendanceResponse>(`/parents/children/${studentId}/attendance`)
    return res.data
  },

  getChildTimetable: async (studentId: string): Promise<ChildTimetableResponse> => {
    const res = await apiClient.get<ChildTimetableResponse>(`/parents/children/${studentId}/timetable`)
    return res.data
  },

  getChildExaminations: async (studentId: string): Promise<ChildExaminationsResponse> => {
    const res = await apiClient.get<ChildExaminationsResponse>(`/parents/children/${studentId}/examinations`)
    return res.data
  },

  getChildResults: async (studentId: string): Promise<ChildTermResultResponse[]> => {
    const res = await apiClient.get<ChildTermResultResponse[]>(`/parents/children/${studentId}/results`)
    return res.data
  },

  getChildAssignments: async (studentId: string): Promise<ChildAssignmentItem[]> => {
    const res = await apiClient.get<ChildAssignmentItem[]>(`/parents/children/${studentId}/assignments`)
    return res.data
  },

  getChildMaterials: async (studentId: string): Promise<ChildStudyMaterialItem[]> => {
    const res = await apiClient.get<ChildStudyMaterialItem[]>(`/parents/children/${studentId}/materials`)
    return res.data
  },

  getChildFees: async (studentId: string): Promise<ChildFeesResponse> => {
    const res = await apiClient.get<ChildFeesResponse>(`/parents/children/${studentId}/fees`)
    return res.data
  },

  getChildTeachers: async (studentId: string): Promise<ChildTeacherItem[]> => {
    const res = await apiClient.get<ChildTeacherItem[]>(`/parents/children/${studentId}/teachers`)
    return res.data
  },

  listMessages: async (studentId?: string): Promise<ParentTeacherMessageResponse[]> => {
    const params = studentId ? { student_id: studentId } : undefined
    const res = await apiClient.get<ParentTeacherMessageResponse[]>('/parents/communications', { params })
    return res.data
  },

  sendMessage: async (data: SendMessageRequest): Promise<{ id: string; status: string; message: string }> => {
    const res = await apiClient.post<{ id: string; status: string; message: string }>('/parents/communications', data)
    return res.data
  },

  // Admin Operations
  listPendingLinkRequests: async (): Promise<any[]> => {
    const res = await apiClient.get<any[]>('/parents/admin/linking-requests')
    return res.data
  },

  processLinkRequest: async (linkId: string, action: 'APPROVE' | 'REJECT', notes?: string): Promise<any> => {
    const res = await apiClient.post(`/parents/admin/linking-requests/${linkId}/process`, { action, approval_notes: notes })
    return res.data
  },

  generateVerificationCode: async (studentId: string, expiresDays: number = 7): Promise<any> => {
    const res = await apiClient.post('/parents/admin/verification-codes', {
      student_id: studentId,
      valid_days: expiresDays,
    })
    return res.data
  },

  adminInviteParent: async (data: {
    parent_email: string
    parent_phone?: string
    parent_name: string
    student_id: string
    relation_type: string
  }): Promise<any> => {
    const res = await apiClient.post('/parents/admin/invite', data)
    return res.data
  },
}

export default parentsApi
