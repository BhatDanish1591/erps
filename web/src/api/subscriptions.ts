import client from './client'

export interface UsageQuotaItem {
  current?: number
  used?: number
  limit?: number
  quota?: number
  remaining?: number
  percentage: number
  used_mb?: number
  limit_gb?: number
}

export interface TenantSubscriptionUsage {
  has_subscription: boolean
  subscription_id?: string
  status: 'TRIAL' | 'ACTIVE' | 'PAST_DUE' | 'CANCELED' | 'EXPIRED' | 'SUSPENDED' | 'NO_SUBSCRIPTION'
  billing_cycle?: 'MONTHLY' | 'YEARLY'
  current_period_start?: string
  current_period_end?: string
  trial_ends_at?: string
  is_auto_renew: boolean
  plan?: {
    id: string
    name: string
    code: string
    price: number
    currency: string
  }
  usage: {
    students: UsageQuotaItem
    teachers: UsageQuotaItem
    storage: UsageQuotaItem
    notifications: UsageQuotaItem
  }
  features: Record<string, boolean>
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
  features: Array<{
    feature_key: string
    feature_value: Record<string, unknown>
    is_enabled: boolean
  }>
}

export interface OrderPricingBreakdown {
  plan_id: string
  plan_name: string
  plan_code: string
  billing_cycle: string
  base_price: number
  discount_amount: number
  subtotal: number
  tax_rate_percent: number
  tax_amount: number
  total_amount: number
  currency: string
  coupon_applied?: string
}

export interface CreateOrderResponse {
  order_id: string
  amount: number
  amount_paise: number
  currency: string
  key_id: string
  invoice_id: string
  plan_id: string
  plan_name: string
  billing_cycle: string
}

export interface SubscriptionInvoiceSummary {
  id: string
  invoice_number: string
  billing_cycle: string
  subtotal: number
  discount_amount: number
  tax_amount: number
  total_amount: number
  currency: string
  status: 'DRAFT' | 'ISSUED' | 'PAID' | 'VOID' | 'UNCOLLECTIBLE'
  due_date: string
  paid_at?: string
  created_at: string
}

export const subscriptionsApi = {
  getCurrentUsage: async (): Promise<TenantSubscriptionUsage> => {
    const res = await client.get<{ success: boolean; data: TenantSubscriptionUsage }>('/subscriptions/current')
    return res.data.data
  },

  getAvailablePlans: async (institutionType?: string): Promise<SubscriptionPlanItem[]> => {
    const res = await client.get<{ success: boolean; data: SubscriptionPlanItem[] }>('/subscriptions/plans', {
      params: { institution_type: institutionType },
    })
    return res.data.data
  },

  previewOrder: async (payload: {
    plan_id: string
    billing_cycle: 'MONTHLY' | 'YEARLY'
    coupon_code?: string
  }): Promise<OrderPricingBreakdown> => {
    const res = await client.post<{ success: boolean; data: OrderPricingBreakdown }>(
      '/subscriptions/preview-order',
      payload
    )
    return res.data.data
  },

  createOrder: async (payload: {
    plan_id: string
    billing_cycle: 'MONTHLY' | 'YEARLY'
    coupon_code?: string
    billing_name?: string
    billing_address?: string
  }): Promise<CreateOrderResponse> => {
    const res = await client.post<{ success: boolean; data: CreateOrderResponse }>(
      '/subscriptions/create-order',
      payload
    )
    return res.data.data
  },

  verifyPayment: async (payload: {
    razorpay_order_id: string
    razorpay_payment_id: string
    razorpay_signature: string
    invoice_id: string
  }) => {
    const res = await client.post<{ success: boolean; data: unknown; message: string }>(
      '/subscriptions/verify-payment',
      payload
    )
    return res.data
  },

  cancelSubscription: async (payload: { immediate?: boolean; reason?: string }) => {
    const res = await client.post<{ success: boolean; data: unknown; message: string }>(
      '/subscriptions/cancel',
      payload
    )
    return res.data
  },

  listInvoices: async (params?: { page?: number; size?: number }) => {
    const res = await client.get<{
      success: boolean
      data: { items: SubscriptionInvoiceSummary[]; total: number; page: number; size: number; pages: number }
    }>('/subscriptions/invoices', { params })
    return res.data.data
  },

  getInvoiceHtml: async (invoiceId: string) => {
    const response = await client.get<string>(`/subscriptions/invoices/${invoiceId}/html`, { responseType: 'text' })
    return response.data
  },
}
