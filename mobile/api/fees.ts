import { apiClient } from './client'

export interface MobileInvoiceLineItem {
  category_name: string
  description?: string
  amount: number
}

export interface MobileFeeInvoice {
  id: string
  invoice_number: string
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
  line_items: MobileInvoiceLineItem[]
}

export interface MobileFeePayment {
  id: string
  receipt_number: string
  invoice_id: string
  amount: number
  payment_date: string
  payment_mode: string
  status: string
  transaction_reference?: string
}

export interface MobileStudentPortalFees {
  student: {
    id: string
    name: string
    admission_number: string
    class_name?: string
  }
  total_invoiced: number
  total_paid: number
  total_due: number
  invoices: MobileFeeInvoice[]
  payments: MobileFeePayment[]
}

export interface MobileRazorpayOrderResponse {
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

export interface MobileFeeReceipt {
  payment_id: string
  receipt_number: string
  institution_name: string
  invoice_number: string
  student_name: string
  admission_number: string
  payment_date: string
  payment_mode: string
  amount_paid: number
  amount_in_words: string
  total_invoice_amount: number
  remaining_balance: number
  line_items: MobileInvoiceLineItem[]
}

export const feesMobileApi = {
  getMyFees: async (): Promise<MobileStudentPortalFees> => {
    const res = await apiClient.get<MobileStudentPortalFees>('/fees/my-fees')
    return res.data
  },

  getInvoiceDetails: async (invoiceId: string): Promise<MobileFeeInvoice> => {
    const res = await apiClient.get<MobileFeeInvoice>(`/fees/invoices/${invoiceId}`)
    return res.data
  },

  initiateFeePayment: async (invoiceId: string, amount?: number): Promise<MobileRazorpayOrderResponse> => {
    const res = await apiClient.post<MobileRazorpayOrderResponse>('/fees/payments/razorpay/order', {
      invoice_id: invoiceId,
      amount,
    })
    return res.data
  },

  verifyFeePayment: async (data: {
    payment_id: string
    razorpay_order_id: string
    razorpay_payment_id: string
    razorpay_signature: string
  }): Promise<MobileFeePayment> => {
    const res = await apiClient.post<MobileFeePayment>('/fees/payments/razorpay/verify', data)
    return res.data
  },

  getReceipt: async (paymentId: string): Promise<MobileFeeReceipt> => {
    const res = await apiClient.get<MobileFeeReceipt>(`/fees/receipts/${paymentId}`)
    return res.data
  },
}

export default feesMobileApi
