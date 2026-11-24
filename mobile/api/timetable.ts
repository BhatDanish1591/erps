import { apiClient } from './client'

export interface MobileTimetableEntry {
  id: string
  period_number: number
  start_time: string
  end_time: string
  subject_name?: string
  subject_code?: string
  teacher_name?: string
  room_number?: string
  entry_type: string
  is_practical: boolean
  is_substituted?: boolean
  active_substitute_teacher_name?: string
  notes?: string
}

export interface MobileDaySchedule {
  day_of_week: string
  date?: string
  is_working_day: boolean
  is_holiday: boolean
  holiday_title?: string
  entries: MobileTimetableEntry[]
}

export interface MobileWeeklyTimetable {
  schedule_name?: string
  entity_type: string
  entity_name?: string
  days: MobileDaySchedule[]
}

export const timetableMobileApi = {
  getMyTimetable: async (targetDate?: string): Promise<MobileWeeklyTimetable> => {
    const res = await apiClient.get<any>('/timetable/my-timetable', {
      params: { target_date: targetDate },
    })
    return res.data?.data ?? res.data
  },

  getClassTimetable: async (classId: string, sectionId?: string, targetDate?: string): Promise<MobileWeeklyTimetable> => {
    const res = await apiClient.get<any>('/timetable/weekly-matrix', {
      params: { class_id: classId, section_id: sectionId, target_date: targetDate },
    })
    return res.data?.data ?? res.data
  },

  getTeacherTimetable: async (teacherId: string, targetDate?: string): Promise<MobileWeeklyTimetable> => {
    const res = await apiClient.get<any>('/timetable/weekly-matrix', {
      params: { teacher_id: teacherId, target_date: targetDate },
    })
    return res.data?.data ?? res.data
  },
}
