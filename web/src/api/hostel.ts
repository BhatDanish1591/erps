import apiClient from './client'

export interface HostelBuilding {
  id: string
  tenant_id: string
  name: string
  code: string
  hostel_type: 'BOYS' | 'GIRLS' | 'CO_ED'
  total_floors: number
  warden_name: string
  warden_phone: string
  warden_email?: string
  address?: string
  total_rooms?: number
  total_capacity?: number
  occupied_beds?: number
  created_at: string
}

export interface HostelRoom {
  id: string
  tenant_id: string
  building_id: string
  building_name?: string
  room_number: string
  floor: number
  room_type: 'SINGLE' | 'DOUBLE' | 'TRIPLE' | 'FOUR_SHARING' | 'DORMITORY'
  is_ac: boolean
  capacity: number
  occupied_beds: number
  available_beds?: number
  rent_per_term: number
  status: string
  created_at: string
}

export interface HostelRoomAllocation {
  id: string
  tenant_id: string
  building_id: string
  building_name?: string
  room_id: string
  room_number?: string
  student_id: string
  student_name?: string
  admission_number?: string
  bed_number: string
  check_in_date: string
  check_out_date?: string
  rent_amount: number
  status: 'ACTIVE' | 'VACATED'
  notes?: string
  created_at: string
}

export interface HostelAttendance {
  id: string
  tenant_id: string
  building_id: string
  student_id: string
  student_name?: string
  attendance_date: string
  status: 'PRESENT' | 'ABSENT' | 'NIGHT_OUT' | 'LEAVE'
  in_time?: string
  out_time?: string
  remarks?: string
  created_at: string
}

export interface HostelVisitor {
  id: string
  tenant_id: string
  building_id: string
  student_id: string
  student_name?: string
  visitor_name: string
  relation: string
  phone: string
  visit_date: string
  in_time: string
  out_time?: string
  purpose: string
  created_at: string
}

export interface HostelMaintenanceRequest {
  id: string
  tenant_id: string
  building_id: string
  room_id: string
  room_number?: string
  reported_by_student_id?: string
  issue_type: 'ELECTRICAL' | 'PLUMBING' | 'CARPENTRY' | 'CLEANING' | 'OTHER'
  description: string
  status: 'PENDING' | 'IN_PROGRESS' | 'RESOLVED' | 'REJECTED'
  priority: 'LOW' | 'MEDIUM' | 'HIGH' | 'EMERGENCY'
  resolved_at?: string
  resolution_notes?: string
  created_at: string
}

export const hostelApi = {
  // Buildings
  listBuildings: async (): Promise<HostelBuilding[]> => {
    const res = await apiClient.get<HostelBuilding[]>('/hostel/buildings')
    return res.data
  },
  getBuilding: async (buildingId: string): Promise<HostelBuilding> => {
    const res = await apiClient.get<HostelBuilding>(`/hostel/buildings/${buildingId}`)
    return res.data
  },
  createBuilding: async (data: {
    name: string
    code: string
    hostel_type: 'BOYS' | 'GIRLS' | 'CO_ED'
    total_floors?: number
    warden_name: string
    warden_phone: string
    warden_email?: string
    address?: string
  }): Promise<HostelBuilding> => {
    const res = await apiClient.post<HostelBuilding>('/hostel/buildings', data)
    return res.data
  },

  // Rooms
  listRooms: async (params?: { building_id?: string; status?: string }): Promise<HostelRoom[]> => {
    const res = await apiClient.get<HostelRoom[]>('/hostel/rooms', { params })
    return res.data
  },
  createRoom: async (data: {
    building_id: string
    room_number: string
    floor?: number
    room_type?: string
    is_ac?: boolean
    capacity?: number
    rent_per_term?: number
  }): Promise<HostelRoom> => {
    const res = await apiClient.post<HostelRoom>('/hostel/rooms', data)
    return res.data
  },

  // Allocations
  listAllocations: async (params?: {
    building_id?: string
    student_id?: string
    status?: string
  }): Promise<HostelRoomAllocation[]> => {
    const res = await apiClient.get<HostelRoomAllocation[]>('/hostel/allocations', { params })
    return res.data
  },
  allocateRoom: async (data: {
    building_id: string
    room_id: string
    student_id: string
    bed_number?: string
    check_in_date: string
    rent_amount?: number
    notes?: string
  }): Promise<HostelRoomAllocation> => {
    const res = await apiClient.post<HostelRoomAllocation>('/hostel/allocations', data)
    return res.data
  },

  // Attendance
  listAttendance: async (params?: {
    building_id?: string
    student_id?: string
    attendance_date?: string
  }): Promise<HostelAttendance[]> => {
    const res = await apiClient.get<HostelAttendance[]>('/hostel/attendance', { params })
    return res.data
  },
  recordAttendance: async (data: {
    building_id: string
    student_id: string
    attendance_date: string
    status: string
    in_time?: string
    out_time?: string
    remarks?: string
  }): Promise<HostelAttendance> => {
    const res = await apiClient.post<HostelAttendance>('/hostel/attendance', data)
    return res.data
  },

  // Visitors
  listVisitors: async (params?: {
    building_id?: string
    student_id?: string
  }): Promise<HostelVisitor[]> => {
    const res = await apiClient.get<HostelVisitor[]>('/hostel/visitors', { params })
    return res.data
  },
  logVisitor: async (data: {
    building_id: string
    student_id: string
    visitor_name: string
    relation: string
    phone: string
    visit_date: string
    in_time: string
    purpose: string
  }): Promise<HostelVisitor> => {
    const res = await apiClient.post<HostelVisitor>('/hostel/visitors', data)
    return res.data
  },

  // Maintenance
  listMaintenance: async (params?: {
    building_id?: string
    status?: string
  }): Promise<HostelMaintenanceRequest[]> => {
    const res = await apiClient.get<HostelMaintenanceRequest[]>('/hostel/maintenance', { params })
    return res.data
  },
  requestMaintenance: async (data: {
    building_id: string
    room_id: string
    reported_by_student_id?: string
    issue_type: string
    description: string
    priority?: string
  }): Promise<HostelMaintenanceRequest> => {
    const res = await apiClient.post<HostelMaintenanceRequest>('/hostel/maintenance', data)
    return res.data
  },
}
