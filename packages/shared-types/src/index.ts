// Shared types used by both web and mobile

export type UUID = string

export type UserRole =
  | 'SUPER_ADMIN'
  | 'INSTITUTION_ADMIN'
  | 'TEACHER'
  | 'STUDENT'
  | 'PARENT'

export type InstitutionType = 'SCHOOL' | 'COLLEGE'

export type SubscriptionStatus = 'trial' | 'active' | 'past_due' | 'canceled' | 'suspended'

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
