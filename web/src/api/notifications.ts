import apiClient from './client'

export interface UserNotification {
  id: string
  tenant_id: string
  user_id: string
  event_type: string
  title: string
  message: string
  action_url?: string | null
  is_read: boolean
  read_at?: string | null
  created_at: string
}

export interface UserNotificationPreference {
  id: string
  tenant_id: string
  user_id: string
  channel_email: boolean
  channel_whatsapp: boolean
  channel_sms: boolean
  channel_push: boolean
  channel_in_app: boolean
  category_attendance: boolean
  category_academic: boolean
  category_examinations: boolean
  category_finance: boolean
  category_announcements: boolean
  quiet_hours_enabled: boolean
  quiet_hours_start?: string | null
  quiet_hours_end?: string | null
}

export interface NotificationTemplate {
  id: string
  tenant_id?: string | null
  event_type: string
  channel: string
  name: string
  subject_template?: string | null
  body_template: string
  whatsapp_template_name?: string | null
  whatsapp_template_namespace?: string | null
  whatsapp_language: string
  msg91_template_id?: string | null
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface NotificationOutboxEntry {
  id: string
  tenant_id: string
  event_type: string
  event_payload: Record<string, any>
  idempotency_key: string
  status: 'PENDING' | 'PROCESSING' | 'PROCESSED' | 'FAILED' | 'CANCELLED'
  retry_count: number
  max_retries: number
  scheduled_for: string
  processed_at?: string | null
  error_message?: string | null
  created_at: string
}

export interface NotificationLogEntry {
  id: string
  tenant_id: string
  outbox_id?: string | null
  user_id?: string | null
  recipient: string
  channel: string
  provider: string
  event_type: string
  subject?: string | null
  content?: string | null
  provider_message_id?: string | null
  status: 'QUEUED' | 'DISPATCHED' | 'DELIVERED' | 'FAILED' | 'BOUNCED' | 'READ'
  attempt_count: number
  error_details?: string | null
  delivered_at?: string | null
  read_at?: string | null
  created_at: string
}

export const notificationsApi = {
  // In-App Notifications
  listInApp: async (unreadOnly: boolean = false): Promise<UserNotification[]> => {
    const res = await apiClient.get<UserNotification[]>('/notifications/in-app', {
      params: { unread_only: unreadOnly },
    })
    return res.data
  },

  markAsRead: async (notificationId: string): Promise<UserNotification> => {
    const res = await apiClient.post<UserNotification>(`/notifications/in-app/${notificationId}/read`)
    return res.data
  },

  markAllAsRead: async (): Promise<{ message: string; count: number }> => {
    const res = await apiClient.post<{ message: string; count: number }>('/notifications/in-app/mark-all-read')
    return res.data
  },

  // Preferences
  getPreferences: async (): Promise<UserNotificationPreference> => {
    const res = await apiClient.get<UserNotificationPreference>('/notifications/preferences')
    return res.data
  },

  updatePreferences: async (
    updates: Partial<UserNotificationPreference>
  ): Promise<UserNotificationPreference> => {
    const res = await apiClient.put<UserNotificationPreference>('/notifications/preferences', updates)
    return res.data
  },

  // Outbox & Non-blocking Emission
  emitEvent: async (data: {
    event_type: string
    event_payload: Record<string, any>
    idempotency_key?: string
  }): Promise<NotificationOutboxEntry> => {
    const res = await apiClient.post<NotificationOutboxEntry>('/notifications/emit', data)
    return res.data
  },

  listOutbox: async (limit: number = 50): Promise<NotificationOutboxEntry[]> => {
    const res = await apiClient.get<NotificationOutboxEntry[]>('/notifications/outbox', {
      params: { limit },
    })
    return res.data
  },

  processOutboxBatch: async (limit: number = 50): Promise<{ message: string; processed_count: number }> => {
    const res = await apiClient.post<{ message: string; processed_count: number }>('/notifications/outbox/process-batch', null, {
      params: { limit },
    })
    return res.data
  },

  // Delivery Logs
  listLogs: async (params?: {
    channel?: string
    status?: string
    event_type?: string
    limit?: number
  }): Promise<NotificationLogEntry[]> => {
    const res = await apiClient.get<NotificationLogEntry[]>('/notifications/logs', { params })
    return res.data
  },

  // Templates
  listTemplates: async (): Promise<NotificationTemplate[]> => {
    const res = await apiClient.get<NotificationTemplate[]>('/notifications/templates')
    return res.data
  },

  createTemplate: async (data: {
    event_type: string
    channel: string
    name: string
    body_template: string
    subject_template?: string
    whatsapp_template_name?: string
    whatsapp_language?: string
    msg91_template_id?: string
  }): Promise<NotificationTemplate> => {
    const res = await apiClient.post<NotificationTemplate>('/notifications/templates', data)
    return res.data
  },
}

export default notificationsApi
