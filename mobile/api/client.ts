import axios from 'axios'
import * as SecureStore from 'expo-secure-store'
import Constants from 'expo-constants'
import { Platform } from 'react-native'

declare const process: { env?: Record<string, string | undefined> }

function resolveApiBaseUrl(): string {
  const envUrl = process.env?.EXPO_PUBLIC_API_URL
  if (envUrl && !envUrl.includes('localhost') && !envUrl.includes('127.0.0.1')) {
    return envUrl
  }

  // Derive host IP from Expo bundler connection (for physical devices running Expo Go)
  const hostUri =
    Constants.expoConfig?.hostUri ||
    (Constants as any).manifest?.debuggerHost ||
    (Constants as any).manifest2?.extra?.expoGo?.debuggerHost
  if (hostUri) {
    const hostIp = hostUri.split(':')[0]
    if (hostIp && hostIp !== 'localhost' && hostIp !== '127.0.0.1') {
      return `http://${hostIp}:8000`
    }
  }

  // Android emulator loopback alias
  if (Platform.OS === 'android') {
    return 'http://10.0.2.2:8000'
  }

  return envUrl || 'http://localhost:8000'
}

const API_BASE_URL = resolveApiBaseUrl()

export const apiClient = axios.create({
  baseURL: `${API_BASE_URL}/api/v1`,
  timeout: 30_000,
  headers: { 'Content-Type': 'application/json' },
})

apiClient.interceptors.request.use(async (config) => {
  try {
    const token = await SecureStore.getItemAsync('edusaas_access_token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    const tenantId = await SecureStore.getItemAsync('edusaas_tenant_id')
    if (tenantId) {
      config.headers['X-Tenant-ID'] = tenantId
    }
  } catch {
    // SecureStore access error
  }
  return config
})

apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    const apiError = {
      status: error.response?.status ?? 0,
      code: error.response?.data?.error?.code ?? 'NETWORK_ERROR',
      message: error.response?.data?.error?.message ?? error.message ?? 'Network error',
    }
    return Promise.reject(apiError)
  },
)
