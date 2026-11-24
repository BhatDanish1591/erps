import { apiClient } from './client'

export interface AttendanceRosterStudent {
  student_id: string
  full_name: string
  admission_number: string
  roll_number?: string
  current_status?: string
}

export interface AttendanceRosterResponse {
  academic_session_id: string
  session_date: string
  session_type: string
  class_id?: string
  section_id?: string
  is_submitted: boolean
  students: AttendanceRosterStudent[]
}

export interface StudentAttendanceEntryItem {
  student_id: string
  status: 'PRESENT' | 'ABSENT' | 'LATE' | 'LEAVE'
  remarks?: string
}

export interface SubmitAttendanceSessionPayload {
  academic_session_id: string
  session_date: string
  session_type: string
  class_id?: string
  section_id?: string
  entries: StudentAttendanceEntryItem[]
  notify_absent_parents?: boolean
}

export interface StudentAttendanceSummary {
  student_id: string
  attendance_percentage: number
  total_sessions: number
  present: number
  absent: number
  late: number
  leave: number
}

export const mobileAttendanceApi = {
  getRoster: async (params: {
    class_id?: string
    section_id?: string
    session_date: string
    session_type?: string
  }): Promise<AttendanceRosterResponse> => {
    const res = await apiClient.get<any>('/attendance/roster', { params })
    return res.data?.data ?? res.data
  },

  submitAttendance: async (payload: SubmitAttendanceSessionPayload): Promise<any> => {
    const res = await apiClient.post<any>('/attendance/sessions', payload)
    return res.data?.data ?? res.data
  },

  getMyAttendanceSummary: async (studentId?: string): Promise<StudentAttendanceSummary> => {
    const res = await apiClient.get<any>('/attendance/summary', {
      params: studentId ? { student_id: studentId } : undefined,
    })
    return res.data?.data ?? res.data
  },
}
