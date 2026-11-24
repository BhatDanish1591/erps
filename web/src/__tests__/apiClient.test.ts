import { afterEach, expect, it, vi } from 'vitest'

afterEach(() => { vi.unstubAllEnvs() })

it.each([
  ['/api/v1', '/api/v1'],
  ['https://erp.example.com/api/v1/', 'https://erp.example.com/api/v1'],
  ['http://localhost:8000', 'http://localhost:8000/api/v1'],
])('normalizes the configured API URL %s', async (configured, expected) => {
  vi.resetModules()
  vi.stubEnv('VITE_API_URL', configured)
  const { apiClient } = await import('@/api/client')
  expect(apiClient.defaults.baseURL).toBe(expected)
})

it('refreshes concurrent expired requests and restores the selected institution', async () => {
  vi.resetModules()
  localStorage.clear()
  const axios = (await import('axios')).default
  const { apiClient } = await import('@/api/client')
  const { useAuthStore } = await import('@/store/authStore')
  const user = { id: 'user', email: 'admin@example.com', full_name: 'Admin', is_superadmin: false, is_active: true, current_tenant_id: 'tenant', current_role: 'INSTITUTION_ADMIN', permissions: [], institutions: [] }
  useAuthStore.getState().setAuth({ access_token: 'expired', refresh_token: 'old', token_type: 'bearer', expires_in: 60, user })
  const post = vi.spyOn(axios, 'post').mockImplementation(async (url) => ({
    data: { data: { access_token: url.endsWith('/refresh') ? 'unscoped' : 'scoped', refresh_token: url.endsWith('/refresh') ? 'rotated' : 'final', token_type: 'bearer', expires_in: 60, user } },
  }))
  apiClient.defaults.adapter = async (config) => {
    if (config.headers.Authorization === 'Bearer expired') {
      throw new axios.AxiosError('Expired', 'ERR_BAD_REQUEST', config, undefined, { status: 401, statusText: 'Unauthorized', headers: {}, config, data: {} })
    }
    return { status: 200, statusText: 'OK', headers: {}, config, data: { saved: true } }
  }
  const responses = await Promise.all([apiClient.post('/academics/departments', { name: 'Science' }), apiClient.get('/academics/courses')])
  expect(responses.every((response) => response.data.saved)).toBe(true)
  expect(post).toHaveBeenCalledTimes(2)
  expect(post).toHaveBeenLastCalledWith(expect.stringContaining('/auth/select-institution'), { tenant_id: 'tenant' }, expect.objectContaining({ headers: { Authorization: 'Bearer unscoped' } }))
  expect(localStorage.getItem('access_token')).toBe('scoped')
  expect(localStorage.getItem('refresh_token')).toBe('final')
  post.mockRestore()
  localStorage.clear()
})
