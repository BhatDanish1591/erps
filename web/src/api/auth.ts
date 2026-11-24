import { apiClient } from './client'
import { ApiResponse } from './health'

export interface UserInstitutionMembership {
  tenant_id: string
  institution_name: string
  institution_slug: string
  institution_type: 'SCHOOL' | 'COLLEGE'
  role_code: string
  role_name: string
  status: string
  permissions: string[]
}

export interface AuthUser {
  id: string
  email: string
  full_name: string
  phone?: string | null
  is_superadmin: boolean
  is_active: boolean
  current_tenant_id?: string | null
  current_role?: string | null
  permissions: string[]
  institutions: UserInstitutionMembership[]
}

export interface TokenResponseData {
  access_token: string
  refresh_token: string
  token_type: string
  expires_in: number
  user: AuthUser
}

export interface LoginPayload {
  identifier: string
  password: string
  tenant_id?: string | null
}

export interface RegisterPayload {
  email: string
  password: string
  full_name: string
  phone?: string
  institution_name?: string
  institution_type?: 'SCHOOL' | 'COLLEGE'
}

export async function loginUser(payload: LoginPayload): Promise<TokenResponseData> {
  const res = await apiClient.post<ApiResponse<TokenResponseData>>('/auth/login', payload)
  return res.data.data
}

export async function registerUser(payload: RegisterPayload): Promise<TokenResponseData> {
  const res = await apiClient.post<ApiResponse<TokenResponseData>>('/auth/register', payload)
  return res.data.data
}

export async function selectInstitution(tenant_id: string): Promise<TokenResponseData> {
  const res = await apiClient.post<ApiResponse<TokenResponseData>>('/auth/select-institution', { tenant_id })
  return res.data.data
}

export async function refreshAccessToken(refresh_token: string): Promise<TokenResponseData> {
  const res = await apiClient.post<ApiResponse<TokenResponseData>>('/auth/refresh', { refresh_token })
  return res.data.data
}

export async function logoutUser(refresh_token: string): Promise<void> {
  await apiClient.post('/auth/logout', { refresh_token })
}

export async function fetchMyProfile(): Promise<AuthUser> {
  const res = await apiClient.get<ApiResponse<AuthUser>>('/auth/me')
  return res.data.data
}

export async function forgotPassword(email: string): Promise<void> {
  await apiClient.post('/auth/forgot-password', { email })
}

export async function resetPassword(token: string, new_password: string): Promise<void> {
  await apiClient.post('/auth/reset-password', { token, new_password })
}
