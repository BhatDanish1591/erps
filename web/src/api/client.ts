import axios, { AxiosInstance, AxiosResponse, InternalAxiosRequestConfig } from 'axios'
import type { TokenResponseData } from './auth'

const API_BASE_URL = (import.meta.env.VITE_API_URL?.trim() || 'http://localhost:8000').replace(/\/+$/, '')
const API_V1_URL = API_BASE_URL.endsWith('/api/v1') ? API_BASE_URL : `${API_BASE_URL}/api/v1`

export const apiClient: AxiosInstance = axios.create({
  baseURL: API_V1_URL,
  timeout: 30_000,
  headers: {
    'Content-Type': 'application/json',
  },
  withCredentials: true,
})

let refreshInFlight: Promise<void> | null = null

async function refreshSession() {
  const oldRefreshToken = localStorage.getItem('refresh_token')
  const tenantId = localStorage.getItem('tenant_id')
  if (!oldRefreshToken) throw new Error('Your session has expired. Please sign in again.')

  const refreshed = await axios.post<{ data: TokenResponseData }>(
    `${API_V1_URL}/auth/refresh`, { refresh_token: oldRefreshToken }, { withCredentials: true },
  )
  let tokens = refreshed.data.data
  if (localStorage.getItem('refresh_token') !== oldRefreshToken) {
    throw new Error('Your session changed. Please try again.')
  }
  // Save the rotated token before restoring the tenant so a failed network request
  // does not leave the session holding a revoked refresh token.
  localStorage.setItem('refresh_token', tokens.refresh_token)
  const { useAuthStore } = await import('@/store/authStore')
  useAuthStore.setState({ refresh_token: tokens.refresh_token })
  const rotatedRefreshToken = tokens.refresh_token
  if (tenantId) {
    // Refresh returns an unscoped token, so restore the selected institution.
    const scoped = await axios.post<{ data: TokenResponseData }>(
      `${API_V1_URL}/auth/select-institution`, { tenant_id: tenantId },
      { headers: { Authorization: `Bearer ${tokens.access_token}` }, withCredentials: true },
    )
    tokens = scoped.data.data
  }
  if (localStorage.getItem('refresh_token') !== rotatedRefreshToken || localStorage.getItem('tenant_id') !== tenantId) {
    throw new Error('Your session changed. Please try again.')
  }
  useAuthStore.getState().setAuth(tokens)
}

// Attach access token and tenant ID on every request
apiClient.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    const token = localStorage.getItem('access_token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    const tenantId = localStorage.getItem('tenant_id')
    if (tenantId) {
      config.headers['X-Tenant-ID'] = tenantId
    }
    return config
  },
  (error) => Promise.reject(error),
)

// Normalise error shape
apiClient.interceptors.response.use(
  (response: AxiosResponse) => response,
  async (error) => {
    const config = error.config as (InternalAxiosRequestConfig & { _authRetried?: boolean }) | undefined
    const authEndpoint = config?.url?.startsWith('/auth/')
    if (error.response?.status === 401 && config && !config._authRetried && !authEndpoint &&
        localStorage.getItem('access_token')) {
      config._authRetried = true
      if (config.headers.Authorization !== `Bearer ${localStorage.getItem('access_token')}`) {
        return apiClient(config)
      }
      try {
        if (!refreshInFlight) {
          refreshInFlight = refreshSession().finally(() => { refreshInFlight = null })
        }
        await refreshInFlight
        return apiClient(config)
      } catch (refreshError) {
        if (!localStorage.getItem('refresh_token') ||
            (axios.isAxiosError(refreshError) && [401, 403].includes(refreshError.response?.status ?? 0))) {
          const { useAuthStore } = await import('@/store/authStore')
          useAuthStore.getState().clearAuth()
          return Promise.reject({ status: 401, code: 'SESSION_EXPIRED', message: 'Your session has expired. Please sign in again.', details: [] })
        }
        return Promise.reject({ status: 0, code: 'SESSION_REFRESH_FAILED', message: 'Unable to refresh your session. Please try again.', details: [] })
      }
    }
    const apiError = {
      status: error.response?.status ?? 0,
      code: error.response?.data?.error?.code ?? 'NETWORK_ERROR',
      message:
        error.response?.data?.error?.message ??
        error.message ??
        'Network error. Please check your connection.',
      details: error.response?.data?.error?.details ?? [],
    }
    return Promise.reject(apiError)
  },
)

export default apiClient
