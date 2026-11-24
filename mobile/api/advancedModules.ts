import { apiClient } from './client'

// ─────────────────────────────────────────────────────────────────────────────
// Library Module Mobile Types & Endpoints
// ─────────────────────────────────────────────────────────────────────────────

export interface MobileLibraryBook {
  id: string
  title: string
  author: string
  isbn?: string
  total_copies: number
  available_copies: number
  shelf_location?: string
  category_name?: string
}

export interface MobileBorrowRecord {
  id: string
  book_title?: string
  accession_number?: string
  issue_date: string
  due_date: string
  return_date?: string
  status: 'ISSUED' | 'RETURNED' | 'OVERDUE'
  fine_amount: number
  fine_paid: boolean
}

export const mobileLibraryApi = {
  getBooks: async (search?: string): Promise<MobileLibraryBook[]> => {
    const res = await apiClient.get<MobileLibraryBook[]>('/library/books', {
      params: { search },
    })
    return res.data
  },
  getMyBorrows: async (): Promise<MobileBorrowRecord[]> => {
    const res = await apiClient.get<MobileBorrowRecord[]>('/library/borrows')
    return res.data
  },
}

// ─────────────────────────────────────────────────────────────────────────────
// Transport Module Mobile Types & Endpoints
// ─────────────────────────────────────────────────────────────────────────────

export interface MobileStudentTransportAllocation {
  id: string
  student_id: string
  student_name?: string
  route_id: string
  route_name?: string
  stop_id: string
  stop_name?: string
  pickup_time?: string
  drop_time?: string
  pickup_drop_type: string
  monthly_fee: number
  status: string
}

export interface MobileVehicleLocation {
  vehicle_id: string
  latitude: number
  longitude: number
  speed_kmh: number
  recorded_at: string
}

export const mobileTransportApi = {
  getMyAllocation: async (studentId?: string): Promise<MobileStudentTransportAllocation[]> => {
    const res = await apiClient.get<MobileStudentTransportAllocation[]>('/transport/allocations', {
      params: { student_id: studentId },
    })
    return res.data
  },
  getVehicleLiveLocation: async (vehicleId: string): Promise<MobileVehicleLocation | null> => {
    const res = await apiClient.get<MobileVehicleLocation | null>(
      `/transport/vehicles/${vehicleId}/live-location`
    )
    return res.data
  },
}

// ─────────────────────────────────────────────────────────────────────────────
// Hostel Module Mobile Types & Endpoints
// ─────────────────────────────────────────────────────────────────────────────

export interface MobileHostelAllocation {
  id: string
  building_name?: string
  room_number?: string
  bed_number: string
  check_in_date: string
  rent_amount: number
  status: string
}

export interface MobileHostelAttendance {
  id: string
  attendance_date: string
  status: 'PRESENT' | 'ABSENT' | 'NIGHT_OUT' | 'LEAVE'
  in_time?: string
  remarks?: string
}

export interface MobileMaintenanceTicketCreate {
  building_id: string
  room_id: string
  reported_by_student_id?: string
  issue_type: string
  description: string
  priority?: string
}

export const mobileHostelApi = {
  getMyAllocations: async (studentId?: string): Promise<MobileHostelAllocation[]> => {
    const res = await apiClient.get<MobileHostelAllocation[]>('/hostel/allocations', {
      params: { student_id: studentId },
    })
    return res.data
  },
  getMyAttendance: async (studentId?: string): Promise<MobileHostelAttendance[]> => {
    const res = await apiClient.get<MobileHostelAttendance[]>('/hostel/attendance', {
      params: { student_id: studentId },
    })
    return res.data
  },
  submitMaintenanceTicket: async (data: MobileMaintenanceTicketCreate) => {
    const res = await apiClient.post('/hostel/maintenance', data)
    return res.data
  },
}
