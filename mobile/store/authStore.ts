import { create } from 'zustand'
import * as SecureStore from 'expo-secure-store'
import { UserInstitutionMembership, mobileAuthApi } from '../api/auth'

export type UserRole = 'SUPER_ADMIN' | 'INSTITUTION_ADMIN' | 'TEACHER' | 'STUDENT' | 'PARENT'

export interface AuthUser {
  id: string
  email: string
  full_name: string
  phone?: string
  avatar_url?: string
  role: UserRole
  current_role?: string
  is_superadmin: boolean
  tenant_id: string | null
  current_tenant_id?: string
  permissions?: string[]
  institutions?: UserInstitutionMembership[]
}

interface AuthState {
  user: AuthUser | null
  access_token: string | null
  refresh_token: string | null
  is_authenticated: boolean
  setAuth: (user: AuthUser, accessToken: string, refreshToken?: string, tenantId?: string) => Promise<void>
  switchInstitution: (tenantId: string) => Promise<void>
  clearAuth: () => Promise<void>
  loadFromStorage: () => Promise<void>
}

const TOKEN_KEY = 'edusaas_access_token'
const REFRESH_KEY = 'edusaas_refresh_token'
const TENANT_KEY = 'edusaas_tenant_id'
const USER_KEY = 'edusaas_user'

export const useAuthStore = create<AuthState>((set, get) => ({
  user: null,
  access_token: null,
  refresh_token: null,
  is_authenticated: false,

  setAuth: async (user, accessToken, refreshToken, tenantId) => {
    await SecureStore.setItemAsync(TOKEN_KEY, accessToken)
    if (refreshToken) {
      await SecureStore.setItemAsync(REFRESH_KEY, refreshToken)
    }
    const resolvedTenant = tenantId || user.current_tenant_id || user.tenant_id
    if (resolvedTenant) {
      await SecureStore.setItemAsync(TENANT_KEY, resolvedTenant)
    } else {
      await SecureStore.deleteItemAsync(TENANT_KEY)
    }
    await SecureStore.setItemAsync(USER_KEY, JSON.stringify(user))

    set({
      user,
      access_token: accessToken,
      refresh_token: refreshToken || null,
      is_authenticated: true,
    })
  },

  switchInstitution: async (tenantId: string) => {
    const res = await mobileAuthApi.selectInstitution(tenantId)
    const tokenData = (res as any)?.data ?? res
    const user = tokenData?.user
    const normalizedUser: AuthUser = {
      ...user,
      role: (user?.current_role || 'STUDENT') as UserRole,
      tenant_id: user?.current_tenant_id || null,
    }
    await get().setAuth(normalizedUser, tokenData.access_token, tokenData.refresh_token, tenantId)
  },

  clearAuth: async () => {
    const refresh = get().refresh_token
    if (refresh) {
      mobileAuthApi.logout(refresh).catch(() => {})
    }
    await SecureStore.deleteItemAsync(TOKEN_KEY)
    await SecureStore.deleteItemAsync(REFRESH_KEY)
    await SecureStore.deleteItemAsync(TENANT_KEY)
    await SecureStore.deleteItemAsync(USER_KEY)
    set({ user: null, access_token: null, refresh_token: null, is_authenticated: false })
  },

  loadFromStorage: async () => {
    try {
      const token = await SecureStore.getItemAsync(TOKEN_KEY)
      const refresh = await SecureStore.getItemAsync(REFRESH_KEY)
      const userStr = await SecureStore.getItemAsync(USER_KEY)
      if (token && userStr) {
        set({
          user: JSON.parse(userStr),
          access_token: token,
          refresh_token: refresh || null,
          is_authenticated: true,
        })
      }
    } catch {
      // SecureStore read failed - treat as unauthenticated
    }
  },
}))
