import apiClient from './client'
import { openRazorpayCheckout } from './razorpay'

export interface FeeCategory {
  id: string
  name: string
  code: string
  fee_type: 'ACADEMIC' | 'FACILITY' | 'ONE_TIME' | 'OPTIONAL' | 'CUSTOM'
  description?: string
  is_active: boolean
  is_system_default: boolean
  created_at: string
}

export interface FeeStructureComponent {
  id?: string
  category_id: string
  category_name?: string
  name: string
  amount: number
  description?: string
}

export interface FeeStructureInstallment {
  id?: string
  installment_number: number
  title: string
  percentage: number
  amount: number
  due_date: string
}

export interface FeeStructure {
  id: string
  name: string
  code: string
  academic_session_id: string
  applicable_to: 'SCHOOL' | 'COLLEGE'
  class_id?: string
  course_id?: string
  semester_id?: string
  currency: string
  total_amount: number
  due_day_of_month?: number
  late_fine_daily_amount: number
  grace_period_days: number
  is_active: boolean
  created_at: string
  components: FeeStructureComponent[]
  installments: FeeStructureInstallment[]
}

export interface FeeDiscountScholarship {
  id: string
  name: string
  discount_type: 'CONCESSION' | 'SCHOLARSHIP' | 'SIBLING' | 'STAFF_WARD' | 'SPORTS_QUOTA' | 'NEED_BASED' | 'CUSTOM'
  calculation_type: 'PERCENTAGE' | 'FIXED_AMOUNT'
  value: number
  academic_session_id: string
  applicable_category_id?: string
  description?: string
  is_active: boolean
  created_at: string
}

export interface StudentFeeAllocation {
  id: string
  student_id: string
  student_name?: string
  admission_number?: string
  fee_structure_id: string
  fee_structure_name?: string
  discount_scholarship_id?: string
  discount_name?: string
  custom_discount_amount: number
  academic_session_id: string
  is_active: boolean
  created_at: string
}

export interface InvoiceLineItem {
  category_name: string
  description?: string
  amount: number
}

export interface FeeInvoice {
  id: string
  invoice_number: string
  student_id: string
  student_name?: string
  admission_number?: string
  class_name?: string
  academic_session_id: string
  academic_session_name?: string
  fee_structure_id?: string
  title: string
  issue_date: string
  due_date: string
  subtotal: number
  discount_amount: number
  scholarship_amount: number
  late_fine_amount: number
  total_amount: number
  paid_amount: number
  balance_amount: number
  status: 'DRAFT' | 'ISSUED' | 'PARTIALLY_PAID' | 'PAID' | 'OVERDUE' | 'CANCELLED'
  line_items: InvoiceLineItem[]
  remarks?: string
  created_at: string
}

export interface FeePayment {
  id: string
  receipt_number: string
  invoice_id: string
  invoice_number?: string
  student_id: string
  student_name?: string
  admission_number?: string
  amount: number
  payment_date: string
  payment_mode: 'CASH' | 'CHEQUE' | 'BANK_TRANSFER' | 'UPI' | 'POS_CARD' | 'RAZORPAY' | 'ONLINE'
  status: 'SUCCESS' | 'PENDING' | 'FAILED' | 'REFUNDED'
  cheque_number?: string
  bank_name?: string
  cheque_date?: string
  clearance_date?: string
  transaction_reference?: string
  razorpay_order_id?: string
  razorpay_payment_id?: string
  received_by_name?: string
  reconciliation_status: 'RECONCILED' | 'UNRECONCILED' | 'DISCREPANCY'
  remarks?: string
  created_at: string
}

export interface FeeReceipt {
  payment_id: string
  receipt_number: string
  institution_name: string
  institution_logo?: string
  invoice_number: string
  invoice_title: string
  student_name: string
  admission_number: string
  class_name?: string
  payment_date: string
  payment_mode: string
  amount_paid: number
  amount_in_words: string
  total_invoice_amount: number
  remaining_balance: number
  transaction_reference?: string
  collected_by: string
  line_items: InvoiceLineItem[]
}

export interface FinanceDashboardStats {
  total_invoiced_amount: number
  total_collected_amount: number
  total_outstanding_amount: number
  today_collection_amount: number
  month_collection_amount: number
  invoices_count: number
  paid_invoices_count: number
  overdue_invoices_count: number
  collection_by_payment_mode: Record<string, number>
}

export interface DefaulterStudent {
  student_id: string
  student_name: string
  admission_number: string
  class_name?: string
  parent_phone?: string
  parent_email?: string
  invoices_count: number
  total_overdue_balance: number
  oldest_due_date: string
  days_overdue: number
}

export interface DefaultersReportResponse {
  total_defaulters: number
  total_overdue_amount: number
  items: DefaulterStudent[]
}

export interface CollectionLedgerItem {
  payment_id: string
  receipt_number: string
  payment_date: string
  student_name: string
  admission_number: string
  invoice_number: string
  amount: number
  payment_mode: string
  transaction_reference?: string
  collected_by: string
  reconciliation_status: string
}

export interface CollectionLedgerResponse {
  total_count: number
  total_amount_collected: number
  items: CollectionLedgerItem[]
}

export interface StudentPortalFeesResponse {
  student: {
    id: string
    name: string
    admission_number: string
    class_name?: string
  }
  total_invoiced: number
  total_paid: number
  total_due: number
  invoices: FeeInvoice[]
  payments: FeePayment[]
}

export interface RazorpayOrderResponse {
  payment_id: string
  invoice_id: string
  invoice_number: string
  amount: number
  currency: string
  gateway: string
  razorpay_order_id: string
  key_id: string
  student_name: string
  student_email?: string
  student_phone?: string
}

export const feesApi = {
  // 1. Categories
  listCategories: (activeOnly = true) =>
    apiClient.get<FeeCategory[]>('/fees/categories', { params: { active_only: activeOnly } }).then(r => r.data),
  createCategory: (data: Partial<FeeCategory>) =>
    apiClient.post<FeeCategory>('/fees/categories', data).then(r => r.data),
  updateCategory: (id: string, data: Partial<FeeCategory>) =>
    apiClient.put<FeeCategory>(`/fees/categories/${id}`, data).then(r => r.data),
  deleteCategory: (id: string) =>
    apiClient.delete(`/fees/categories/${id}`).then(r => r.data),

  // 2. Structures
  listStructures: (params?: { academic_session_id?: string; applicable_to?: string }) =>
    apiClient.get<FeeStructure[]>('/fees/structures', { params }).then(r => r.data),
  getStructure: (id: string) =>
    apiClient.get<FeeStructure>(`/fees/structures/${id}`).then(r => r.data),
  createStructure: (data: any) =>
    apiClient.post<FeeStructure>('/fees/structures', data).then(r => r.data),
  deleteStructure: (id: string) =>
    apiClient.delete(`/fees/structures/${id}`).then(r => r.data),

  // 3. Discounts
  listDiscounts: (academicSessionId?: string) =>
    apiClient.get<FeeDiscountScholarship[]>('/fees/discounts', { params: { academic_session_id: academicSessionId } }).then(r => r.data),
  createDiscount: (data: any) =>
    apiClient.post<FeeDiscountScholarship>('/fees/discounts', data).then(r => r.data),

  // 4. Allocations
  allocateFee: (data: any) =>
    apiClient.post<StudentFeeAllocation>('/fees/allocations', data).then(r => r.data),
  bulkAllocateFee: (data: any) =>
    apiClient.post('/fees/allocations/bulk', data).then(r => r.data),

  // 5. Invoices
  listInvoices: (params?: { academic_session_id?: string; student_id?: string; status?: string; class_id?: string }) =>
    apiClient.get<FeeInvoice[]>('/fees/invoices', { params }).then(r => r.data),
  getInvoice: (id: string) =>
    apiClient.get<FeeInvoice>(`/fees/invoices/${id}`).then(r => r.data),
  createInvoice: (data: any) =>
    apiClient.post<FeeInvoice>('/fees/invoices', data).then(r => r.data),
  generateCohortInvoices: (data: any) =>
    apiClient.post('/fees/invoices/generate-cohort', data).then(r => r.data),
  cancelInvoice: (id: string, reason?: string) =>
    apiClient.post<FeeInvoice>(`/fees/invoices/${id}/cancel`, null, { params: { reason } }).then(r => r.data),

  // 6. Payments
  recordOfflinePayment: (data: any) =>
    apiClient.post<FeePayment>('/fees/payments/offline', data).then(r => r.data),
  initiateOnlinePayment: (invoiceId: string, amount?: number) =>
    apiClient.post<RazorpayOrderResponse>('/fees/payments/razorpay/order', { invoice_id: invoiceId, amount }).then(r => r.data),
  verifyOnlinePayment: (data: { payment_id: string; razorpay_order_id: string; razorpay_payment_id: string; razorpay_signature: string }) =>
    apiClient.post<FeePayment>('/fees/payments/razorpay/verify', data).then(r => r.data),

  // 7. Receipts
  getReceipt: (paymentId: string) =>
    apiClient.get<FeeReceipt>(`/fees/receipts/${paymentId}`).then(r => r.data),
  getReceiptHtml: (paymentId: string) =>
    apiClient.get<string>(`/fees/receipts/${paymentId}/html`).then(r => r.data),

  // 8. Portal & Reports
  getMyFees: () =>
    apiClient.get<StudentPortalFeesResponse>('/fees/my-fees').then(r => r.data),
  getDashboardStats: (academicSessionId?: string) =>
    apiClient.get<FinanceDashboardStats>('/fees/dashboard', { params: { academic_session_id: academicSessionId } }).then(r => r.data),
  getDefaultersReport: (params?: { academic_session_id?: string; class_id?: string; min_days_overdue?: number }) =>
    apiClient.get<DefaultersReportResponse>('/fees/reports/defaulters', { params }).then(r => r.data),
  getCollectionLedger: (params?: { start_date?: string; end_date?: string; payment_mode?: string; reconciliation_status?: string }) =>
    apiClient.get<CollectionLedgerResponse>('/fees/reports/collection-ledger', { params }).then(r => r.data),
}

export default feesApi

export async function payFeeInvoice(invoiceId: string, balance: number) {
  const order = await feesApi.initiateOnlinePayment(invoiceId, balance)
  const confirmation = await openRazorpayCheckout({
    key: order.key_id,
    order_id: order.razorpay_order_id,
    amount: Math.round(order.amount * 100),
    currency: order.currency,
    name: 'Institutional Fee Payment',
    description: order.invoice_number,
    prefill: {
      name: order.student_name,
      email: order.student_email,
      contact: order.student_phone,
    },
  })
  if (!confirmation) return null
  return feesApi.verifyOnlinePayment({ payment_id: order.payment_id, ...confirmation })
}
