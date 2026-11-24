import apiClient from './client'

export interface TransportVehicle {
  id: string
  tenant_id: string
  registration_number: string
  vehicle_model: string
  seating_capacity: number
  fuel_type: string
  insurance_number?: string
  insurance_expiry?: string
  fitness_certificate_expiry?: string
  gps_device_id?: string
  status: string
  created_at: string
}

export interface TransportDriver {
  id: string
  tenant_id: string
  full_name: string
  phone: string
  license_number: string
  license_expiry?: string
  emergency_contact?: string
  experience_years: number
  is_active: boolean
  created_at: string
}

export interface TransportStop {
  id: string
  tenant_id: string
  route_id: string
  name: string
  stop_order: number
  pickup_time: string
  drop_time: string
  stop_fee: number
  latitude?: number
  longitude?: number
}

export interface TransportRoute {
  id: string
  tenant_id: string
  name: string
  code: string
  start_location: string
  end_location: string
  vehicle_id?: string
  vehicle_registration?: string
  driver_id?: string
  driver_name?: string
  total_distance_km?: number
  monthly_fare: number
  status: string
  stops: TransportStop[]
  created_at: string
}

export interface StudentTransportAllocation {
  id: string
  tenant_id: string
  student_id: string
  student_name?: string
  admission_number?: string
  route_id: string
  route_name?: string
  stop_id: string
  stop_name?: string
  pickup_time?: string
  drop_time?: string
  pickup_drop_type: 'PICKUP_ONLY' | 'DROP_ONLY' | 'BOTH'
  monthly_fee: number
  start_date: string
  end_date?: string
  status: string
  created_at: string
}

export interface TransportMaintenanceLog {
  id: string
  tenant_id: string
  vehicle_id: string
  maintenance_date: string
  maintenance_type: string
  cost: number
  odometer_reading?: number
  description: string
  service_center?: string
  next_service_due?: string
  created_at: string
}

export interface TransportGpsLog {
  id: string
  tenant_id: string
  vehicle_id: string
  latitude: number
  longitude: number
  speed_kmh: number
  recorded_at: string
}

export const transportApi = {
  // Vehicles
  listVehicles: async (): Promise<TransportVehicle[]> => {
    const res = await apiClient.get<TransportVehicle[]>('/transport/vehicles')
    return res.data
  },
  createVehicle: async (data: {
    registration_number: string
    vehicle_model: string
    seating_capacity: number
    fuel_type?: string
    insurance_number?: string
    insurance_expiry?: string
    fitness_certificate_expiry?: string
    gps_device_id?: string
    status?: string
  }): Promise<TransportVehicle> => {
    const res = await apiClient.post<TransportVehicle>('/transport/vehicles', data)
    return res.data
  },

  // Drivers
  listDrivers: async (): Promise<TransportDriver[]> => {
    const res = await apiClient.get<TransportDriver[]>('/transport/drivers')
    return res.data
  },
  createDriver: async (data: {
    full_name: string
    phone: string
    license_number: string
    license_expiry?: string
    emergency_contact?: string
    experience_years?: number
  }): Promise<TransportDriver> => {
    const res = await apiClient.post<TransportDriver>('/transport/drivers', data)
    return res.data
  },

  // Routes
  listRoutes: async (): Promise<TransportRoute[]> => {
    const res = await apiClient.get<TransportRoute[]>('/transport/routes')
    return res.data
  },
  getRoute: async (routeId: string): Promise<TransportRoute> => {
    const res = await apiClient.get<TransportRoute>(`/transport/routes/${routeId}`)
    return res.data
  },
  createRoute: async (data: {
    name: string
    code: string
    start_location: string
    end_location: string
    vehicle_id?: string
    driver_id?: string
    total_distance_km?: number
    monthly_fare?: number
    stops?: Array<{
      name: string
      stop_order: number
      pickup_time: string
      drop_time: string
      stop_fee?: number
      latitude?: number
      longitude?: number
    }>
  }): Promise<TransportRoute> => {
    const res = await apiClient.post<TransportRoute>('/transport/routes', data)
    return res.data
  },

  // Student Allocations
  listAllocations: async (params?: {
    student_id?: string
    route_id?: string
  }): Promise<StudentTransportAllocation[]> => {
    const res = await apiClient.get<StudentTransportAllocation[]>('/transport/allocations', { params })
    return res.data
  },
  allocateStudent: async (data: {
    student_id: string
    route_id: string
    stop_id: string
    pickup_drop_type?: 'PICKUP_ONLY' | 'DROP_ONLY' | 'BOTH'
    monthly_fee?: number
    start_date: string
    end_date?: string
  }): Promise<StudentTransportAllocation> => {
    const res = await apiClient.post<StudentTransportAllocation>('/transport/allocations', data)
    return res.data
  },

  // Maintenance & GPS
  addMaintenance: async (data: {
    vehicle_id: string
    maintenance_date: string
    maintenance_type: string
    cost: number
    odometer_reading?: number
    description: string
    service_center?: string
    next_service_due?: string
  }): Promise<TransportMaintenanceLog> => {
    const res = await apiClient.post<TransportMaintenanceLog>('/transport/maintenance', data)
    return res.data
  },
  recordGps: async (data: {
    vehicle_id: string
    latitude: number
    longitude: number
    speed_kmh?: number
  }): Promise<TransportGpsLog> => {
    const res = await apiClient.post<TransportGpsLog>('/transport/gps/ping', data)
    return res.data
  },
  getLiveLocation: async (vehicleId: string): Promise<TransportGpsLog | null> => {
    const res = await apiClient.get<TransportGpsLog | null>(`/transport/vehicles/${vehicleId}/live-location`)
    return res.data
  },
}
