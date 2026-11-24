import { apiClient } from './client'

export interface MobileUserNotification {
  id: string
  event_type: string
  title: string
  message: string
  action_url?: string | null
  is_read: boolean
  read_at?: string | null
  created_at: string
}

export interface MobileNotificationPreference {
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
}

export const notificationsApi = {
  listInApp: async (unreadOnly: boolean = false): Promise<MobileUserNotification[]> => {
    const res = await apiClient.get<any>('/notifications/in-app', {
      params: { unread_only: unreadOnly },
    })
    return res.data?.data ?? res.data
  },

  markAsRead: async (notificationId: string): Promise<any> => {
    const res = await apiClient.post<any>(`/notifications/in-app/${notificationId}/read`)
    return res.data?.data ?? res.data
  },

  markAllAsRead: async (): Promise<any> => {
    const res = await apiClient.post<any>('/notifications/in-app/mark-all-read')
    return res.data?.data ?? res.data
  },

  getPreferences: async (): Promise<MobileNotificationPreference> => {
    const res = await apiClient.get<any>('/notifications/preferences')
    return res.data?.data ?? res.data
  },

  updatePreferences: async (updates: Partial<MobileNotificationPreference>): Promise<any> => {
    const res = await apiClient.put<any>('/notifications/preferences', updates)
    return res.data?.data ?? res.data
  },
}

export default notificationsApi
