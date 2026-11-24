import client from './client'

export interface SuperAdminStats {
  total_institutions: number
  active_institutions: number
  pending_institutions: number
  suspended_institutions: number
  total_students: number
  total_teachers: number
  total_subscriptions: number
  mrr: number
  arr: number
  subscription_renewals: number
  expired_subscriptions: number
  payment_failures: number
  recent_institutions: Array<{
    id: string
    name: string
    slug: string
    institution_type: string
    status: string
    email?: string
    created_at: string
  }>
  recent_users: Array<{
    id: string
    email: string
    full_name: string
    is_superadmin: boolean
    created_at: string
  }>
  revenue_trend: Array<{ month: string; revenue: number }>
  institution_growth: Array<{ month: string; count: number }>
}

export interface InstitutionItem {
  id: string
  name: string
  slug: string
  institution_type: string
  status: string
  email?: string
  phone?: string
  city?: string
  state?: string
  country: string
  created_at: string
}

export interface InstitutionDetail extends InstitutionItem {
  address?: string
  postal_code?: string
  logo_url?: string
  currency: string
  timezone: string
  domains: string[]
  total_users: number
  current_plan?: string
  subscription_status?: string
}

export interface SubscriptionPlanItem {
  id: string
  name: string
  code: string
  description?: string
  institution_type?: string
  billing_cycle: string
  price: number
  monthly_price: number
  annual_price: number
  currency: string
  max_students: number
  max_teachers: number
  storage_limit_gb: number
  notification_quota: number
  trial_days: number
  is_active: boolean
  features: Array<{ feature_key: string; feature_value: Record<string, unknown>; is_enabled: boolean }>
  created_at: string
}

export interface CouponItem {
  id: string
  code: string
  description?: string
  discount_type: 'PERCENTAGE' | 'FIXED_AMOUNT'
  discount_value: number
  max_redemptions?: number
  times_redeemed: number
  valid_from: string
  valid_until?: string
  is_active: boolean
  applicable_institution_type?: string
  created_at: string
}

export interface PlatformSubscriptionItem {
  id: string
  tenant_id: string
  tenant_name: string
  institution_type: string
  plan_name: string
  plan_code: string
  status: string
  billing_cycle: string
  current_period_start: string
  current_period_end: string
  trial_ends_at?: string
  is_auto_renew: boolean
  created_at: string
}

export interface GlobalAnnouncementItem {
  id: string
  title: string
  content: string
  target_role?: string
  priority: string
  is_active: boolean
  expires_at?: string
  created_at: string
}

export interface SupportTicketItem {
  id: string
  ticket_number: string
  tenant_id?: string
  tenant_name?: string
  user_id: string
  user_name: string
  user_email: string
  subject: string
  description: string
  category: string
  priority: string
  status: string
  assigned_to_user_id?: string
  created_at: string
  replies: Array<{
    id: string
    ticket_id: string
    user_id: string
    user_name: string
    message: string
    is_internal: boolean
    created_at: string
  }>
}

export interface PlatformSettingItem {
  id: string
  category: string
  key: string
  value: Record<string, unknown>
  description?: string
  is_secret: boolean
  updated_at: string
}

export interface PlatformIntegrationItem {
  id: string
  provider: string
  name: string
  is_enabled: boolean
  config: Record<string, unknown>
  status: string
  last_tested_at?: string
  updated_at: string
}

export interface AuditLogItem {
  id: string
  tenant_id?: string
  user_id?: string
  actor_email: string
  action: string
  entity_type: string
  entity_id?: string
  ip_address?: string
  changes: Record<string, unknown>
  created_at: string
}

export const superAdminApi = {
  getStats: async (): Promise<SuperAdminStats> => {
    const res = await client.get<{ success: boolean; data: SuperAdminStats }>('/super-admin/stats')
    return res.data.data
  },

  listInstitutions: async (params?: {
    search?: string
    status?: string
    institution_type?: string
    page?: number
    size?: number
  }) => {
    const res = await client.get<{
      success: boolean
      data: { items: InstitutionItem[]; total: number; page: number; size: number; pages: number }
    }>('/super-admin/institutions', { params })
    return res.data.data
  },

  getInstitutionDetail: async (id: string): Promise<InstitutionDetail> => {
    const res = await client.get<{ success: boolean; data: InstitutionDetail }>(`/super-admin/institutions/${id}`)
    return res.data.data
  },

  updateInstitutionStatus: async (id: string, status: string, reason?: string) => {
    const res = await client.post<{ success: boolean; message: string }>(
      `/super-admin/institutions/${id}/status`,
      { status, reason }
    )
    return res.data
  },

  listInstitutionUsers: async (id: string, page = 1, size = 20) => {
    const res = await client.get<{
      success: boolean
      data: {
        items: Array<{
          membership_id: string
          user_id: string
          full_name: string
          email: string
          role_name: string
          status: string
          created_at: string
        }>
        total: number
      }
    }>(`/super-admin/institutions/${id}/users`, { params: { page, size } })
    return res.data.data
  },

  listPlans: async (): Promise<SubscriptionPlanItem[]> => {
    const res = await client.get<{ success: boolean; data: SubscriptionPlanItem[] }>('/super-admin/plans')
    return res.data.data
  },

  createPlan: async (payload: {
    name: string
    code: string
    description?: string
    institution_type?: string
    billing_cycle?: string
    price: number
    monthly_price?: number
    annual_price?: number
    currency?: string
    max_students?: number
    max_teachers?: number
    storage_limit_gb?: number
    notification_quota?: number
    trial_days?: number
    features?: Array<{ feature_key: string; feature_value: Record<string, unknown>; is_enabled: boolean }>
  }) => {
    const res = await client.post<{ success: boolean; message: string }>('/super-admin/plans', payload)
    return res.data
  },

  updatePlan: async (
    id: string,
    payload: {
      name?: string
      description?: string
      price?: number
      monthly_price?: number
      annual_price?: number
      max_students?: number
      max_teachers?: number
      storage_limit_gb?: number
      notification_quota?: number
      trial_days?: number
      is_active?: boolean
    }
  ) => {
    const res = await client.put<{ success: boolean; message: string }>(`/super-admin/plans/${id}`, payload)
    return res.data
  },

  listAnnouncements: async (): Promise<GlobalAnnouncementItem[]> => {
    const res = await client.get<{ success: boolean; data: GlobalAnnouncementItem[] }>('/super-admin/announcements')
    return res.data.data
  },

  createAnnouncement: async (payload: {
    title: string
    content: string
    priority: string
    target_role?: string
  }) => {
    const res = await client.post<{ success: boolean; message: string }>('/super-admin/announcements', payload)
    return res.data
  },

  deleteAnnouncement: async (id: string) => {
    const res = await client.delete<{ success: boolean; message: string }>(`/super-admin/announcements/${id}`)
    return res.data
  },

  listTickets: async (status?: string): Promise<SupportTicketItem[]> => {
    const res = await client.get<{ success: boolean; data: SupportTicketItem[] }>('/super-admin/tickets', {
      params: { status },
    })
    return res.data.data
  },

  updateTicketStatus: async (id: string, status: string, assigned_to_user_id?: string) => {
    const res = await client.put<{ success: boolean; message: string }>(`/super-admin/tickets/${id}/status`, {
      status,
      assigned_to_user_id,
    })
    return res.data
  },

  replyTicket: async (id: string, message: string, is_internal = false) => {
    const res = await client.post<{ success: boolean; message: string }>(`/super-admin/tickets/${id}/replies`, {
      message,
      is_internal,
    })
    return res.data
  },

  getSettings: async (): Promise<PlatformSettingItem[]> => {
    const res = await client.get<{ success: boolean; data: PlatformSettingItem[] }>('/super-admin/settings')
    return res.data.data
  },

  updateSetting: async (payload: { category: string; key: string; value: Record<string, unknown>; description?: string }) => {
    const res = await client.post<{ success: boolean; message: string }>('/super-admin/settings', payload)
    return res.data
  },

  listIntegrations: async (): Promise<PlatformIntegrationItem[]> => {
    const res = await client.get<{ success: boolean; data: PlatformIntegrationItem[] }>('/super-admin/integrations')
    return res.data.data
  },

  updateIntegration: async (
    provider: string,
    payload: { is_enabled: boolean; config: Record<string, unknown>; status?: string }
  ) => {
    const res = await client.put<{ success: boolean; message: string }>(`/super-admin/integrations/${provider}`, payload)
    return res.data
  },

  listAuditLogs: async (params?: { action?: string; entity_type?: string; page?: number; size?: number }) => {
    const res = await client.get<{
      success: boolean
      data: { items: AuditLogItem[]; total: number; page: number; size: number; pages: number }
    }>('/super-admin/audit-logs', { params })
    return res.data.data
  },

  // ── Coupons ────────────────────────────────────────────────────────────────
  listCoupons: async (): Promise<CouponItem[]> => {
    const res = await client.get<{ success: boolean; data: CouponItem[] }>('/super-admin/coupons')
    return res.data.data
  },

  createCoupon: async (payload: {
    code: string
    description?: string
    discount_type: 'PERCENTAGE' | 'FIXED_AMOUNT'
    discount_value: number
    max_redemptions?: number
    valid_from?: string
    valid_until?: string
    is_active?: boolean
    applicable_institution_type?: string
  }) => {
    const res = await client.post<{ success: boolean; data: { id: string; code: string }; message: string }>(
      '/super-admin/coupons',
      payload
    )
    return res.data
  },

  deactivateCoupon: async (couponId: string) => {
    const res = await client.delete<{ success: boolean; message: string }>(`/super-admin/coupons/${couponId}`)
    return res.data
  },

  // ── Platform Subscriptions ────────────────────────────────────────────────
  listAllSubscriptions: async (params?: { status?: string; page?: number; size?: number }) => {
    const res = await client.get<{
      success: boolean
      data: { items: PlatformSubscriptionItem[]; total: number; page: number; size: number; pages: number }
    }>('/super-admin/subscriptions', { params })
    return res.data.data
  },

  suspendSubscription: async (subscriptionId: string, reason?: string) => {
    const res = await client.post<{ success: boolean; message: string }>(
      `/super-admin/subscriptions/${subscriptionId}/suspend`,
      {},
      { params: { reason } }
    )
    return res.data
  },

  reactivateSubscription: async (subscriptionId: string) => {
    const res = await client.post<{ success: boolean; message: string }>(
      `/super-admin/subscriptions/${subscriptionId}/reactivate`
    )
    return res.data
  },

  extendTrial: async (subscriptionId: string, days = 14) => {
    const res = await client.post<{ success: boolean; message: string }>(
      `/super-admin/subscriptions/${subscriptionId}/extend-trial`,
      {},
      { params: { days } }
    )
    return res.data
  },

  seedPlans: async () => {
    const res = await client.post<{ success: boolean; message: string }>('/super-admin/plans/seed')
    return res.data
  },
}
