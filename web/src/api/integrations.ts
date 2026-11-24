import apiClient from './client'

export interface TenantIntegrationItem {
  id: string
  tenant_id: string
  provider_type:
    | 'EMAIL_SES'
    | 'EMAIL_RESEND'
    | 'WHATSAPP_META'
    | 'SMS_MSG91'
    | 'PUSH_FIREBASE'
    | 'PUSH_APNS'
    | 'PAYMENT_RAZORPAY'
    | 'STORAGE_S3'
    | 'STORAGE_R2'
  is_enabled: boolean
  masked_credentials?: Record<string, string> | null
  settings?: Record<string, any> | null
  status: 'ACTIVE' | 'INACTIVE' | 'ERROR' | 'UNTESTED'
  last_tested_at?: string | null
  last_error?: string | null
  created_at: string
  updated_at: string
}

export interface ConfigureIntegrationRequest {
  provider_type: string
  is_enabled?: boolean
  credentials?: Record<string, any>
  settings?: Record<string, any>
  webhook_secret?: string
}

export interface TestIntegrationResponse {
  success: boolean
  provider_type: string
  message: string
  details?: Record<string, any> | null
}

export const integrationsApi = {
  list: async (): Promise<TenantIntegrationItem[]> => {
    const res = await apiClient.get<TenantIntegrationItem[]>('/integrations')
    return res.data
  },

  configure: async (data: ConfigureIntegrationRequest): Promise<TenantIntegrationItem> => {
    const res = await apiClient.post<TenantIntegrationItem>('/integrations', data)
    return res.data
  },

  get: async (providerType: string): Promise<TenantIntegrationItem> => {
    const res = await apiClient.get<TenantIntegrationItem>(`/integrations/${providerType}`)
    return res.data
  },

  testConnection: async (providerType: string, recipient?: string): Promise<TestIntegrationResponse> => {
    const res = await apiClient.post<TestIntegrationResponse>(`/integrations/${providerType}/test`, {
      provider_type: providerType,
      recipient,
    })
    return res.data
  },
}

export default integrationsApi
