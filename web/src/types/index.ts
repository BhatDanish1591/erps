// API Response types
export interface ApiSuccess<T> {
  success: true
  data: T
  message: string
}

export interface ApiError {
  success: false
  error: {
    code: string
    message: string
    details: { field?: string; message: string }[]
  }
}

export interface Pagination {
  total: number
  page: number
  size: number
  pages: number
}

export interface PaginatedApiSuccess<T> {
  success: true
  data: T[]
  pagination: Pagination
}

// Common entity types
export type UUID = string

export interface Timestamps {
  created_at: string
  updated_at: string
}

export interface TenantEntity extends Timestamps {
  id: UUID
  tenant_id: UUID
  is_deleted: boolean
}

// Role types
export type UserRole = 'SUPER_ADMIN' | 'INSTITUTION_ADMIN' | 'PRINCIPAL' | 'HOD' | 'TEACHER' | 'STUDENT' | 'PARENT'

export type InstitutionType = 'SCHOOL' | 'COLLEGE'
