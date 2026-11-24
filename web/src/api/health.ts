import { apiClient } from './client'

export interface HealthData {
  status: 'healthy' | 'degraded'
  timestamp: string
  version: string
  environment: string
  dependencies?: {
    database: 'ok' | 'error'
    redis: 'ok' | 'error'
  }
}

export interface ApiResponse<T> {
  success: boolean
  data: T
  message: string
}

export async function fetchHealth(): Promise<HealthData> {
  const res = await apiClient.get<ApiResponse<HealthData>>('/health')
  return res.data.data
}

export async function fetchDetailedHealth(): Promise<HealthData> {
  const res = await apiClient.get<ApiResponse<HealthData>>('/health/detailed')
  return res.data.data
}
