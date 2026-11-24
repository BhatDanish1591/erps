import apiClient from './client'

export interface AttendanceRosterStudent {
  student_id: string
  full_name: string
  admission_number: string
  roll_number?: string
  current_status?: string
  remarks?: string
  parent_phone?: string
  parent_email?: string
}

export interface AttendanceRosterResponse {
  academic_session_id: string
  session_date: string
  session_type: string
  class_id?: string
  section_id?: string
  subject_id?: string
  period_number?: number
  existing_session_id?: string
  is_submitted: boolean
  students: AttendanceRosterStudent[]
}

export interface StudentAttendanceEntryItem {
  student_id: string
  status: 'PRESENT' | 'ABSENT' | 'LATE' | 'LEAVE' | 'HALF_DAY' | 'EXCUSED'
  remarks?: string
  marked_via?: string
}

export interface SubmitAttendanceSessionPayload {
  academic_session_id: string
  session_date: string
  session_type: string
  class_id?: string
  section_id?: string
  course_id?: string
  semester_id?: string
  subject_id?: string
  period_number?: number
  remarks?: string
  entries: StudentAttendanceEntryItem[]
  notify_absent_parents?: boolean
}

export interface StudentAttendanceEntryResponse {
  id: string
  session_id: string
  student_id: string
  student_name?: string
  admission_number?: string
  roll_number?: string
  status: string
  remarks?: string
  marked_via: string
  marked_at: string
  is_corrected: boolean
  corrected_at?: string
  correction_reason?: string
}

export interface StudentAttendanceSessionResponse {
  id: string
  tenant_id: string
  academic_session_id: string
  session_date: string
  session_type: string
  class_id?: string
  section_id?: string
  course_id?: string
  semester_id?: string
  subject_id?: string
  period_number?: number
  conducted_by_teacher_id?: string
  teacher_name?: string
  class_name?: string
  section_name?: string
  subject_name?: string
  status: string
  total_students: number
  present_count: number
  absent_count: number
  late_count: number
  leave_count: number
  attendance_rate: number
  remarks?: string
  submitted_at?: string
  entries?: StudentAttendanceEntryResponse[]
}

export interface AdminAttendanceOverview {
  today: string
  total_students_enrolled: number
  total_marked_today: number
  overall_attendance_rate_today: number
  total_present_today: number
  total_absent_today: number
  total_late_today: number
  total_leave_today: number
  low_attendance_students_count: number
  sessions_conducted_today: number
}

export interface LowAttendanceAlertItem {
  student_id: string
  full_name: string
  admission_number: string
  class_name?: string
  section_name?: string
  total_sessions: number
  attended_sessions: number
  attendance_percentage: number
  parent_name?: string
  parent_phone?: string
}

export interface AttendanceCorrectionLog {
  id: string
  tenant_id: string
  entry_id: string
  previous_status: string
  new_status: string
  reason: string
  corrected_by_user_id: string
  corrected_at: string
}

export interface MonthlyAttendanceDayRecord {
  date: string
  status: string
  period_number?: number
  subject_name?: string
}

export interface StudentMonthlyAttendanceReport {
  student_id: string
  full_name: string
  admission_number: string
  year: number
  month: number
  total_days: number
  conducted_days: number
  present_days: number
  absent_days: number
  late_days: number
  leave_days: number
  percentage: number
  records: MonthlyAttendanceDayRecord[]
}

export interface StudentAttendanceSummary {
  student_id: string
  full_name: string
  admission_number: string
  total_conducted: number
  total_attended: number
  present_count: number
  absent_count: number
  late_count: number
  leave_count: number
  attendance_percentage: number
  is_low_attendance: boolean
}

export interface CollegeStudentAttendanceItem {
  student_id: string
  admission_number: string
  roll_number?: string
  full_name: string
  department_id?: string
  department_name?: string
  course_id: string
  course_name: string
  course_code: string
  semester_id?: string
  semester_name: string
  semester_number: number
  total_classes: number
  attended_classes: number
  present_count: number
  late_count: number
  absent_count: number
  leave_count: number
  attendance_percentage: number
  status: 'EXCELLENT' | 'AVERAGE' | 'CRITICAL'
}

export interface CollegeCohortAttendanceResponse {
  department_id?: string
  course_id?: string
  semester_id?: string
  total_students: number
  average_attendance: number
  critical_attendance_count: number
  excellent_attendance_count: number
  students: CollegeStudentAttendanceItem[]
}

export interface CohortAttendanceCounts {
  total: number
  attended: number
  percentage: number | null
}

export interface CohortAttendanceStudent extends CohortAttendanceCounts {
  id: string
  name: string
  admission_number: string
}

export interface CohortAttendanceSubject extends CohortAttendanceCounts {
  id: string | null
  name: string
  classes: number
  students: CohortAttendanceStudent[]
}

export interface CohortAttendanceFilters {
  academic_session_id: string
  department_id?: string
  course_id?: string
  semester_id?: string
  class_id?: string
  section_id?: string
}

interface CohortAttendanceReport {
  students: CohortAttendanceStudent[]
  subjects: CohortAttendanceSubject[]
  overview: CohortAttendanceCounts
}

export interface QRCodeAttendanceResponse {
  qr_token: string
  session_id: string
  expires_at: string
  geo_fence_enabled: boolean
  allowed_radius_meters?: number
}

export interface TeacherAttendanceRecord {
  id: string
  teacher_id: string
  teacher_name?: string
  employee_id?: string
  attendance_date: string
  status: string
  check_in_time?: string
  check_out_time?: string
  working_hours?: number
  check_in_method?: string
  notes?: string
}

export const attendanceApi = {
  getCohortReport: async (params: CohortAttendanceFilters) => {
    const response = await apiClient.get<{ data: CohortAttendanceReport }>('/attendance/cohort-report', { params })
    return response.data.data
  },
  getOverview: async (targetDate?: string) => {
    const params = targetDate ? { target_date: targetDate } : {}
    const res = await apiClient.get<{ success: boolean; data: AdminAttendanceOverview }>('/attendance/overview', { params })
    return res.data.data
  },

  getCollegeCohortAttendance: async (params?: {
    department_id?: string
    course_id?: string
    semester_id?: string
    academic_session_id?: string
    search?: string
  }) => {
    const res = await apiClient.get<{ success: boolean; data: CollegeCohortAttendanceResponse }>(
      '/attendance/college/cohort-attendance',
      { params }
    )
    return res.data.data
  },

  getRoster: async (params: {
    academic_session_id: string
    session_date: string
    session_type?: string
    class_id?: string
    section_id?: string
    course_id?: string
    semester_id?: string
    subject_id?: string
    period_number?: number
  }) => {
    const res = await apiClient.get<{ success: boolean; data: AttendanceRosterResponse }>('/attendance/roster', { params })
    return res.data.data
  },

  submitSession: async (payload: SubmitAttendanceSessionPayload) => {
    const res = await apiClient.post<{ success: boolean; data: StudentAttendanceSessionResponse }>('/attendance/sessions', payload)
    return res.data.data
  },

  correctEntry: async (payload: { entry_id: string; new_status: string; reason: string }) => {
    const res = await apiClient.post<{ success: boolean; data: StudentAttendanceEntryResponse }>('/attendance/entries/correct', payload)
    return res.data.data
  },

  getCorrectionLogs: async (entryId?: string) => {
    const params = entryId ? { entry_id: entryId } : {}
    const res = await apiClient.get<{ success: boolean; data: AttendanceCorrectionLog[] }>('/attendance/corrections', { params })
    return res.data.data
  },

  getLowAttendanceAlerts: async (threshold: number = 75.0) => {
    const res = await apiClient.get<{ success: boolean; data: LowAttendanceAlertItem[] }>('/attendance/low-attendance', {
      params: { threshold },
    })
    return res.data.data
  },

  getStudentSummary: async (studentId: string, academicSessionId?: string) => {
    const params = academicSessionId ? { academic_session_id: academicSessionId } : {}
    const res = await apiClient.get<{ success: boolean; data: StudentAttendanceSummary }>(
      `/attendance/students/${studentId}/summary`,
      { params }
    )
    return res.data.data
  },

  getStudentMonthlyReport: async (studentId: string, year: number, month: number) => {
    const res = await apiClient.get<{ success: boolean; data: StudentMonthlyAttendanceReport }>(
      `/attendance/students/${studentId}/monthly`,
      { params: { year, month } }
    )
    return res.data.data
  },

  generateQR: async (academicSessionId: string, payload: {
    class_id?: string
    section_id?: string
    course_id?: string
    semester_id?: string
    subject_id?: string
    period_number?: number
    validity_minutes?: number
  }) => {
    const res = await apiClient.post<{ success: boolean; data: QRCodeAttendanceResponse }>(
      `/attendance/qr/generate?academic_session_id=${academicSessionId}`,
      payload
    )
    return res.data.data
  },

  scanQR: async (payload: { qr_token: string; latitude?: number; longitude?: number }) => {
    const res = await apiClient.post<{ success: boolean; data: StudentAttendanceEntryResponse }>(
      '/attendance/qr/scan',
      payload
    )
    return res.data.data
  },

  teacherCheckIn: async (payload: { check_in_method?: string; latitude?: number; longitude?: number; notes?: string }) => {
    const res = await apiClient.post<{ success: boolean; data: TeacherAttendanceRecord }>(
      '/attendance/teacher/check-in',
      payload
    )
    return res.data.data
  },

  teacherCheckOut: async (payload: { notes?: string }) => {
    const res = await apiClient.post<{ success: boolean; data: TeacherAttendanceRecord }>(
      '/attendance/teacher/check-out',
      payload
    )
    return res.data.data
  },
}
