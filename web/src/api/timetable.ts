import apiClient from './client'

export interface TimetableSetting {
  id: string
  tenant_id: string
  academic_session_id: string
  working_days: string[]
  periods_per_day: number
  period_duration_minutes: number
  break_duration_minutes: number
  lunch_duration_minutes: number
  school_start_time: string
  created_at: string
  updated_at: string
}

export interface TimetablePeriod {
  id: string
  tenant_id: string
  academic_session_id: string
  period_number: number
  name: string
  period_type: string
  start_time: string
  end_time: string
  is_break: boolean
  created_at: string
  updated_at: string
}

export interface TimetableHoliday {
  id: string
  tenant_id: string
  academic_session_id: string
  title: string
  holiday_date: string
  holiday_type: string
  description?: string
  is_half_day: boolean
  created_at: string
  updated_at: string
}

export interface TimetableSchedule {
  id: string
  tenant_id: string
  academic_session_id: string
  academic_session_name?: string
  name: string
  institution_type: string
  effective_from: string
  effective_to: string
  status: 'DRAFT' | 'PUBLISHED' | 'ARCHIVED'
  published_at?: string
  published_by?: string
  publisher_name?: string
  entries_count: number
  description?: string
  created_at: string
  updated_at: string
}

export interface TimetableEntry {
  id: string
  tenant_id: string
  academic_session_id?: string
  schedule_id?: string
  period_id?: string
  teacher_id: string
  teacher_name?: string
  teacher_employee_id?: string
  subject_id?: string
  subject_name?: string
  subject_code?: string
  class_id?: string
  class_name?: string
  section_id?: string
  section_name?: string
  course_id?: string
  course_name?: string
  semester?: number
  semester_id?: string
  batch_id?: string
  department_id?: string
  day_of_week: string
  period_number: number
  start_time: string
  end_time: string
  room_number?: string
  entry_type: string
  is_practical: boolean
  capacity?: number
  notes?: string
  active_substitute_teacher_id?: string
  active_substitute_teacher_name?: string
  is_substituted?: boolean
  created_at: string
  updated_at: string
}

export interface ConflictItem {
  conflict_type: string
  severity: string
  message: string
  day_of_week?: string
  start_time?: string
  end_time?: string
  entity_id?: string
  entity_name?: string
  conflicting_entry_id?: string
}

export interface ConflictCheckResponse {
  has_conflicts: boolean
  conflicts_count: number
  conflicts: ConflictItem[]
}

export interface DayScheduleResponse {
  day_of_week: string
  date?: string
  is_working_day: boolean
  is_holiday: boolean
  holiday_title?: string
  entries: TimetableEntry[]
}

export interface WeeklyTimetableResponse {
  schedule_id?: string
  schedule_name?: string
  entity_type: string
  entity_name?: string
  days: DayScheduleResponse[]
}

export interface SubstituteAssignment {
  id: string
  tenant_id: string
  timetable_entry_id: string
  assignment_date: string
  original_teacher_id: string
  original_teacher_name?: string
  substitute_teacher_id: string
  substitute_teacher_name?: string
  assigned_by?: string
  assigned_by_name?: string
  reason?: string
  status: string
  created_at: string
  updated_at: string
}

export const timetableApi = {
  // Settings
  getSettings: async (academicSessionId: string): Promise<TimetableSetting> => {
    const res = await apiClient.get<TimetableSetting>('/timetable/settings', {
      params: { academic_session_id: academicSessionId },
    })
    return res.data
  },

  updateSettings: async (data: {
    academic_session_id: string
    working_days?: string[]
    periods_per_day?: number
    period_duration_minutes?: number
    break_duration_minutes?: number
    lunch_duration_minutes?: number
    school_start_time?: string
  }): Promise<TimetableSetting> => {
    const res = await apiClient.put<TimetableSetting>('/timetable/settings', data)
    return res.data
  },

  // Periods
  listPeriods: async (academicSessionId: string): Promise<TimetablePeriod[]> => {
    const res = await apiClient.get<TimetablePeriod[]>('/timetable/periods', {
      params: { academic_session_id: academicSessionId },
    })
    return res.data
  },

  createPeriod: async (data: {
    academic_session_id: string
    period_number: number
    name: string
    period_type?: string
    start_time: string
    end_time: string
    is_break?: boolean
  }): Promise<TimetablePeriod> => {
    const res = await apiClient.post<TimetablePeriod>('/timetable/periods', data)
    return res.data
  },

  deletePeriod: async (periodId: string): Promise<void> => {
    await apiClient.delete(`/timetable/periods/${periodId}`)
  },

  // Holidays
  listHolidays: async (params?: {
    academic_session_id?: string
    from_date?: string
    to_date?: string
  }): Promise<TimetableHoliday[]> => {
    const res = await apiClient.get<TimetableHoliday[]>('/timetable/holidays', { params })
    return res.data
  },

  createHoliday: async (data: {
    academic_session_id: string
    title: string
    holiday_date: string
    holiday_type?: string
    description?: string
    is_half_day?: boolean
  }): Promise<TimetableHoliday> => {
    const res = await apiClient.post<TimetableHoliday>('/timetable/holidays', data)
    return res.data
  },

  deleteHoliday: async (holidayId: string): Promise<void> => {
    await apiClient.delete(`/timetable/holidays/${holidayId}`)
  },

  // Schedules
  listSchedules: async (params?: {
    academic_session_id?: string
    status?: string
  }): Promise<TimetableSchedule[]> => {
    const res = await apiClient.get<TimetableSchedule[]>('/timetable/schedules', { params })
    return res.data
  },

  getSchedule: async (scheduleId: string): Promise<TimetableSchedule> => {
    const res = await apiClient.get<TimetableSchedule>(`/timetable/schedules/${scheduleId}`)
    return res.data
  },

  createSchedule: async (data: {
    academic_session_id: string
    name: string
    institution_type?: string
    effective_from: string
    effective_to: string
    description?: string
  }): Promise<TimetableSchedule> => {
    const res = await apiClient.post<TimetableSchedule>('/timetable/schedules', data)
    return res.data
  },

  updateSchedule: async (
    scheduleId: string,
    data: {
      name?: string
      effective_from?: string
      effective_to?: string
      description?: string
      status?: string
    }
  ): Promise<TimetableSchedule> => {
    const res = await apiClient.put<TimetableSchedule>(`/timetable/schedules/${scheduleId}`, data)
    return res.data
  },

  publishSchedule: async (
    scheduleId: string,
    ignoreConflicts: boolean = false
  ): Promise<TimetableSchedule> => {
    const res = await apiClient.post<TimetableSchedule>(
      `/timetable/schedules/${scheduleId}/publish`,
      null,
      { params: { ignore_conflicts: ignoreConflicts } }
    )
    return res.data
  },

  getScheduleConflicts: async (scheduleId: string): Promise<ConflictCheckResponse> => {
    const res = await apiClient.get<ConflictCheckResponse>(
      `/timetable/schedules/${scheduleId}/conflicts`
    )
    return res.data
  },

  // Entries
  listEntries: async (params: {
    schedule_id?: string
    academic_session_id?: string
    class_id?: string
    section_id?: string
    teacher_id?: string
    course_id?: string
    room_number?: string
    day_of_week?: string
  }): Promise<TimetableEntry[]> => {
    const res = await apiClient.get<TimetableEntry[]>('/timetable/entries', { params })
    return res.data
  },

  createEntry: async (
    data: {
      academic_session_id?: string
      schedule_id?: string
      period_id?: string
      teacher_id: string
      subject_id?: string
      class_id?: string
      section_id?: string
      course_id?: string
      semester?: number
      semester_id?: string
      batch_id?: string
      department_id?: string
      day_of_week: string
      period_number?: number
      start_time: string
      end_time: string
      room_number?: string
      entry_type?: string
      is_practical?: boolean
      capacity?: number
      notes?: string
    },
    ignoreConflicts: boolean = false
  ): Promise<TimetableEntry> => {
    const res = await apiClient.post<TimetableEntry>('/timetable/entries', data, {
      params: { ignore_conflicts: ignoreConflicts },
    })
    return res.data
  },

  updateEntry: async (
    entryId: string,
    data: Partial<TimetableEntry>
  ): Promise<TimetableEntry> => {
    const res = await apiClient.put<TimetableEntry>(`/timetable/entries/${entryId}`, data)
    return res.data
  },

  deleteEntry: async (entryId: string): Promise<void> => {
    await apiClient.delete(`/timetable/entries/${entryId}`)
  },

  checkConflicts: async (data: {
    day_of_week: string
    start_time: string
    end_time: string
    teacher_id?: string
    room_number?: string
    class_id?: string
    section_id?: string
    course_id?: string
    semester?: number
    batch_id?: string
    schedule_id?: string
    exclude_entry_id?: string
  }): Promise<ConflictCheckResponse> => {
    const res = await apiClient.get<{ data: { has_conflicts: boolean; total_conflicts: number; conflicts: ConflictItem[] } }>(
      '/timetable/check-conflicts', { params: data },
    )
    const { has_conflicts, total_conflicts, conflicts } = res.data.data
    return { has_conflicts, conflicts_count: total_conflicts, conflicts }
  },

  // Weekly Matrix View
  getWeeklyMatrix: async (params: {
    schedule_id?: string
    class_id?: string
    section_id?: string
    teacher_id?: string
    course_id?: string
    room_number?: string
    target_date?: string
  }): Promise<WeeklyTimetableResponse> => {
    const res = await apiClient.get<WeeklyTimetableResponse>('/timetable/weekly-matrix', { params })
    return res.data
  },

  // Personalized "My Timetable"
  getMyTimetable: async (targetDate?: string): Promise<WeeklyTimetableResponse> => {
    const res = await apiClient.get<WeeklyTimetableResponse>('/timetable/my-timetable', {
      params: { target_date: targetDate },
    })
    return res.data
  },

  // Substitutes
  assignSubstitute: async (data: {
    timetable_entry_id: string
    assignment_date: string
    substitute_teacher_id: string
    reason?: string
  }): Promise<SubstituteAssignment> => {
    const res = await apiClient.post<SubstituteAssignment>('/timetable/substitutes', data)
    return res.data
  },

  listSubstitutes: async (params?: {
    from_date?: string
    to_date?: string
    teacher_id?: string
  }): Promise<SubstituteAssignment[]> => {
    const res = await apiClient.get<SubstituteAssignment[]>('/timetable/substitutes', { params })
    return res.data
  },
}
