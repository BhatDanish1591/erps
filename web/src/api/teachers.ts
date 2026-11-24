import client from './client'

export type StaffRole = 'PRINCIPAL' | 'HOD' | 'TEACHER'

export const staffRoleLabels: Record<StaffRole, string> = {
  PRINCIPAL: 'Principal',
  HOD: 'Head of Department',
  TEACHER: 'Teacher',
}

export interface StaffDepartment {
  id: string
  name: string
}

export interface TeacherAssignment {
  id: string
  teacher_id: string
  academic_session_id?: string | null
  class_id?: string | null
  class_name?: string | null
  section_id?: string | null
  section_name?: string | null
  department_id?: string | null
  department_name?: string | null
  course_id?: string | null
  course_name?: string | null
  semester?: number | null
  subject_id?: string | null
  subject_name?: string | null
  subject_code?: string | null
  is_class_teacher: boolean
}

export interface TimetableEntry {
  id: string
  academic_session_id?: string | null
  teacher_id: string
  teacher_name?: string | null
  subject_id?: string | null
  subject_name?: string | null
  class_id?: string | null
  class_name?: string | null
  section_id?: string | null
  section_name?: string | null
  course_id?: string | null
  course_name?: string | null
  semester?: number | null
  day_of_week: string
  period_number: number
  start_time: string
  end_time: string
  room_number?: string | null
}

export interface TeacherWorkload {
  total_classes_assigned: number
  total_subjects_assigned: number
  weekly_periods_count: number
  is_class_teacher_of?: string | null
  approved_leave_days?: number | null
  attendance_rate_percentage?: number | null
}

export interface TeacherItem {
  id: string
  tenant_id: string
  user_id: string
  staff_role?: StaffRole | null
  full_name: string
  email?: string | null
  phone?: string | null
  employee_id: string
  designation?: string | null
  qualification?: string | null
  specialization?: string | null
  experience_years: number
  department_id?: string | null
  department_name?: string | null
  joining_date?: string | null
  employment_type: string
  status: 'ACTIVE' | 'INACTIVE'

  address_line1?: string | null
  address_line2?: string | null
  city?: string | null
  state?: string | null
  postal_code?: string | null
  country?: string

  emergency_contact_name?: string | null
  emergency_contact_phone?: string | null
  pan_number?: string | null
  aadhar_number?: string | null
  bank_name?: string | null
  bank_account_number?: string | null
  bank_ifsc?: string | null

  photo_url?: string | null
  custom_fields?: Record<string, any>
  assignments: TeacherAssignment[]
  workload?: TeacherWorkload
  leave_history?: TeacherLeaveItem[]
  attendance_history?: TeacherAttendanceItem[]
  created_at: string
  updated_at: string
}

export interface TeacherListParams {
  search?: string
  department_id?: string
  status?: string
  employment_type?: string
  page?: number
  size?: number
}

export interface TeacherListResponse {
  items: TeacherItem[]
  total: number
  page: number
  size: number
  pages: number
}

export interface TeacherCreatePayload {
  full_name: string
  email?: string
  initial_password?: string
  phone?: string
  employee_id?: string
  designation?: string
  qualification?: string
  specialization?: string
  experience_years?: number
  department_id?: string
  joining_date?: string
  employment_type?: string

  address_line1?: string
  address_line2?: string
  city?: string
  state?: string
  postal_code?: string
  country?: string

  emergency_contact_name?: string
  emergency_contact_phone?: string
  pan_number?: string
  aadhar_number?: string
  bank_name?: string
  bank_account_number?: string
  bank_ifsc?: string
  photo_url?: string
}

export interface TeacherLeaveItem {
  id: string
  teacher_id: string
  teacher_name: string
  leave_type: string
  start_date: string
  end_date: string
  days_count: number
  reason: string
  status: 'PENDING' | 'APPROVED' | 'REJECTED' | 'CANCELLED'
  rejection_reason?: string | null
  applied_at: string
  reviewed_at?: string | null
}

export interface TeacherAttendanceItem {
  id: string
  attendance_date: string
  status: string
  check_in_time?: string | null
  check_out_time?: string | null
}

export interface TeacherDashboardSummary {
  teacher: TeacherItem
  assigned_classes: Array<{ id: string; title: string; is_class_teacher?: boolean }>
  assigned_subjects: Array<{ id: string; title: string; code?: string }>
  today_timetable: TimetableEntry[]
  attendance_tasks: Array<{ class_name: string; status: string; due_time: string }>
  upcoming_examinations: Array<{ title: string; subject: string; date: string }>
  assignments_to_evaluate: Array<{ title: string; class_name: string; submissions_count: number; evaluated_count: number }>
  notifications: Array<{ title: string; message: string; created_at: string }>
}

export const teachersApi = {
  deleteTeacher: async (teacherId: string): Promise<void> => {
    await client.delete(`/teachers/${teacherId}`)
  },
  listDepartments: async (): Promise<StaffDepartment[]> => {
    const res = await client.get('/teachers/departments')
    return res.data.data
  },

  listPendingLeaves: async (): Promise<TeacherLeaveItem[]> => {
    const res = await client.get('/teachers/leaves')
    return res.data.data
  },

  updateStaffAccess: async (id: string, payload: { role: StaffRole; department_id?: string }): Promise<void> => {
    await client.put(`/teachers/${id}/access`, payload)
  },

  listTeachers: async (params?: TeacherListParams): Promise<TeacherListResponse> => {
    const res = await client.get('/teachers', { params })
    return res.data.data
  },

  getTeacher: async (id: string): Promise<TeacherItem> => {
    const res = await client.get(`/teachers/${id}`)
    return res.data.data
  },

  createTeacher: async (payload: TeacherCreatePayload): Promise<TeacherItem> => {
    const res = await client.post('/teachers', payload)
    return res.data.data
  },

  updateTeacher: async (id: string, payload: Partial<TeacherCreatePayload>): Promise<TeacherItem> => {
    const res = await client.put(`/teachers/${id}`, payload)
    return res.data.data
  },

  assignResource: async (
    teacherId: string,
    payload: {
      class_id?: string
      section_id?: string
      subject_id?: string
      department_id?: string
      course_id?: string
      semester?: number
      is_class_teacher?: boolean
    }
  ): Promise<{ id: string }> => {
    const res = await client.post(`/teachers/${teacherId}/assignments`, payload)
    return res.data.data
  },

  removeAssignment: async (teacherId: string, assignmentId: string): Promise<void> => {
    await client.delete(`/teachers/${teacherId}/assignments/${assignmentId}`)
  },

  getTimetable: async (teacherId: string, day_of_week?: string): Promise<TimetableEntry[]> => {
    const res = await client.get(`/teachers/${teacherId}/timetable`, { params: { day_of_week } })
    return res.data.data
  },

  createTimetableEntry: async (
    teacherId: string,
    payload: {
      day_of_week: string
      period_number: number
      start_time: string
      end_time: string
      room_number?: string
      subject_id?: string
      class_id?: string
      section_id?: string
    }
  ): Promise<{ id: string }> => {
    const res = await client.post(`/teachers/${teacherId}/timetable`, payload)
    return res.data.data
  },

  recordAttendance: async (
    teacherId: string,
    payload: {
      attendance_date: string
      status: string
      check_in_time?: string
      check_out_time?: string
      remarks?: string
    }
  ): Promise<any> => {
    const res = await client.post(`/teachers/${teacherId}/attendance`, payload)
    return res.data.data
  },

  applyLeave: async (
    teacherId: string,
    payload: {
      leave_type: string
      start_date: string
      end_date: string
      days_count: number
      reason: string
    }
  ): Promise<TeacherLeaveItem> => {
    const res = await client.post(`/teachers/${teacherId}/leaves`, payload)
    return res.data.data
  },

  reviewLeave: async (
    leaveId: string,
    payload: { status: 'APPROVED' | 'REJECTED'; rejection_reason?: string }
  ): Promise<TeacherLeaveItem> => {
    const res = await client.put(`/teachers/leaves/${leaveId}/review`, payload)
    return res.data.data
  },

  setTeacherStatus: async (teacherId: string, status: 'ACTIVE' | 'INACTIVE'): Promise<any> => {
    const res = await client.post(`/teachers/${teacherId}/status`, null, { params: { status } })
    return res.data.data
  },

  getTeacherDashboard: async (): Promise<TeacherDashboardSummary> => {
    const res = await client.get('/teachers/dashboard')
    return res.data.data
  },
}
