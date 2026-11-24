import { apiClient } from './client'

export interface UserInstitutionMembership {
  tenant_id: string
  institution_name: string
  institution_slug: string
  institution_type: string
  role_code: string
  role_name: string
  status: string
  permissions: string[]
}

export interface AuthUser {
  id: string
  email: string
  full_name: string
  phone?: string
  is_superadmin: boolean
  is_active: boolean
  current_tenant_id?: string
  current_role?: string
  permissions: string[]
  institutions: UserInstitutionMembership[]
}

export interface TokenResponse {
  access_token: string
  refresh_token: string
  token_type: string
  expires_in: number
  user: AuthUser
}

export const mobileAuthApi = {
  login: async (credentials: {
    identifier: string
    password: string
    tenant_id?: string
  }): Promise<TokenResponse> => {
    const res = await apiClient.post<any>('/auth/login', credentials)
    return res.data?.data ?? res.data
  },

  selectInstitution: async (tenantId: string): Promise<TokenResponse> => {
    const res = await apiClient.post<any>('/auth/select-institution', {
      tenant_id: tenantId,
    })
    return res.data?.data ?? res.data
  },

  forgotPassword: async (email: string): Promise<{ success: boolean; message: string }> => {
    const res = await apiClient.post('/auth/forgot-password', { email })
    return res.data?.data ?? res.data
  },

  verifyOTP: async (phone: string, otp: string): Promise<{ success: boolean; message: string }> => {
    const res = await apiClient.post('/auth/verify-otp', { phone, otp })
    return res.data?.data ?? res.data
  },

  logout: async (refreshToken: string): Promise<void> => {
    await apiClient.post('/auth/logout', { refresh_token: refreshToken })
  },

  getMe: async (): Promise<AuthUser> => {
    const res = await apiClient.get<any>('/auth/me')
    return res.data?.data ?? res.data
  },
}
