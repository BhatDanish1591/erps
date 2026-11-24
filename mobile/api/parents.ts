import { apiClient } from './client'

export interface MobileLinkedChildSummary {
  id: string
  student_id: string
  admission_number: string
  student_name: string
  gender?: string | null
  tenant_id: string
  institution_name: string
  institution_type: string
  relationship_type: string
  status: 'PENDING_APPROVAL' | 'VERIFIED' | 'REJECTED' | 'REVOKED'
  class_name?: string | null
  section_name?: string | null
  course_name?: string | null
  total_due_amount: number
  overall_attendance_pct?: number | null
}

export interface MobileLinkChildRequest {
  admission_number: string
  relationship_type: string
  verification_code?: string
  tenant_id?: string
  notes?: string
}

export type LinkedChildSummary = MobileLinkedChildSummary

export const parentsApi = {
  listChildren: async (): Promise<MobileLinkedChildSummary[]> => {
    const res = await apiClient.get<MobileLinkedChildSummary[]>('/parents/children')
    return res.data
  },
  getLinkedChildren: async (): Promise<MobileLinkedChildSummary[]> => {
    const res = await apiClient.get<MobileLinkedChildSummary[]>('/parents/children')
    return res.data
  },

  requestLinkChild: async (data: MobileLinkChildRequest): Promise<MobileLinkedChildSummary> => {
    const res = await apiClient.post<MobileLinkedChildSummary>('/parents/link-child', data)
    return res.data
  },

  getChildProfile: async (studentId: string): Promise<any> => {
    const res = await apiClient.get(`/parents/children/${studentId}/profile`)
    return res.data
  },

  getChildAttendance: async (studentId: string): Promise<any> => {
    const res = await apiClient.get(`/parents/children/${studentId}/attendance`)
    return res.data
  },

  getChildTimetable: async (studentId: string): Promise<any> => {
    const res = await apiClient.get(`/parents/children/${studentId}/timetable`)
    return res.data
  },

  getChildExaminations: async (studentId: string): Promise<any> => {
    const res = await apiClient.get(`/parents/children/${studentId}/examinations`)
    return res.data
  },

  getChildResults: async (studentId: string): Promise<any[]> => {
    const res = await apiClient.get(`/parents/children/${studentId}/results`)
    return res.data
  },

  getChildAssignments: async (studentId: string): Promise<any[]> => {
    const res = await apiClient.get(`/parents/children/${studentId}/assignments`)
    return res.data
  },

  getChildMaterials: async (studentId: string): Promise<any[]> => {
    const res = await apiClient.get(`/parents/children/${studentId}/study-materials`)
    return res.data
  },

  getChildFees: async (studentId: string): Promise<any> => {
    const res = await apiClient.get(`/parents/children/${studentId}/fees`)
    return res.data
  },

  createFeeOrder: async (studentId: string, invoiceId: string): Promise<any> => {
    const res = await apiClient.post(`/parents/children/${studentId}/fees/${invoiceId}/create-order`)
    return res.data
  },

  verifyFeePayment: async (
    studentId: string,
    data: {
      invoice_id: string
      razorpay_order_id: string
      razorpay_payment_id: string
      razorpay_signature: string
    }
  ): Promise<any> => {
    const res = await apiClient.post(`/parents/children/${studentId}/fees/verify-payment`, data)
    return res.data
  },

  getChildTeachers: async (studentId: string): Promise<any[]> => {
    const res = await apiClient.get(`/parents/children/${studentId}/teachers`)
    return res.data
  },

  listMessages: async (studentId?: string): Promise<any[]> => {
    const params = studentId ? { student_id: studentId } : undefined
    const res = await apiClient.get('/parents/messages', { params })
    return res.data
  },

  sendMessage: async (data: {
    recipient_user_id: string
    student_id: string
    subject: string
    message: string
    parent_message_id?: string
  }): Promise<any> => {
    const res = await apiClient.post('/parents/messages', data)
    return res.data
  },
}

export const mobileParentsApi = parentsApi
export default parentsApi
