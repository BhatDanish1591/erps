import { create } from 'zustand'
import { persist, createJSONStorage } from 'zustand/middleware'
import { AuthUser, TokenResponseData, selectInstitution, logoutUser } from '@/api/auth'

interface AuthState {
  user: AuthUser | null
  access_token: string | null
  refresh_token: string | null
  is_authenticated: boolean

  // Actions
  setAuth: (data: TokenResponseData) => void
  clearAuth: () => void
  switchInstitution: (tenant_id: string) => Promise<void>
  hasPermission: (permission: string) => boolean
  hasRole: (roles: string | string[]) => boolean
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      user: null,
      access_token: null,
      refresh_token: null,
      is_authenticated: false,

      setAuth: (data) => {
        localStorage.setItem('access_token', data.access_token)
        localStorage.setItem('refresh_token', data.refresh_token)
        if (data.user.current_tenant_id) {
          localStorage.setItem('tenant_id', data.user.current_tenant_id)
        } else {
          localStorage.removeItem('tenant_id')
        }

        set({
          user: data.user,
          access_token: data.access_token,
          refresh_token: data.refresh_token,
          is_authenticated: true,
        })
      },

      clearAuth: () => {
        const refreshToken = get().refresh_token
        if (refreshToken) {
          logoutUser(refreshToken).catch(() => {})
        }
        localStorage.removeItem('access_token')
        localStorage.removeItem('refresh_token')
        localStorage.removeItem('tenant_id')
        set({
          user: null,
          access_token: null,
          refresh_token: null,
          is_authenticated: false,
        })
      },

      switchInstitution: async (tenant_id: string) => {
        const data = await selectInstitution(tenant_id)
        get().setAuth(data)
      },

      hasPermission: (permission: string) => {
        const user = get().user
        if (!user) return false
        if (user.is_superadmin) return true
        return user.permissions.includes(permission) || user.permissions.includes('*:*')
      },

      hasRole: (roles: string | string[]) => {
        const user = get().user
        if (!user) return false
        if (user.is_superadmin) return true
        const allowed = Array.isArray(roles) ? roles : [roles]
        return Boolean(user.current_role && allowed.includes(user.current_role))
      },
    }),
    {
      name: 'edusaas-auth',
      storage: createJSONStorage(() => localStorage),
      partialize: (state) => ({
        user: state.user,
        access_token: state.access_token,
        refresh_token: state.refresh_token,
        is_authenticated: state.is_authenticated,
      }),
    },
  ),
)
