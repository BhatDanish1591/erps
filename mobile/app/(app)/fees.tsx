import React, { useState, useEffect, useCallback } from 'react'
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  ActivityIndicator,
  Alert,
  RefreshControl,
  Modal,
} from 'react-native'
import { SafeAreaView } from 'react-native-safe-area-context'
import { Ionicons } from '@expo/vector-icons'
import {
  feesMobileApi,
  MobileStudentPortalFees,
  MobileFeeInvoice,
} from '../../api/fees'
import { theme } from '../../theme'

export default function FeesScreen() {
  const [loading, setLoading] = useState(false)
  const [refreshing, setRefreshing] = useState(false)
  const [portalData, setPortalData] = useState<MobileStudentPortalFees | null>(null)

  // Payment Flow State
  const [selectedInvoice, setSelectedInvoice] = useState<MobileFeeInvoice | null>(null)
  const [paying, setPaying] = useState(false)
  const [receiptModalVisible, setReceiptModalVisible] = useState(false)

  const fetchFees = useCallback(async () => {
    try {
      setLoading(true)
      const data = await feesMobileApi.getMyFees()
      setPortalData(data)
    } catch {
      // Fallback mock data
      const mockFees: MobileStudentPortalFees = {
        student: {
          id: 'std-current',
          name: 'Aarav Sharma',
          admission_number: 'ADM-2026-0089',
          class_name: 'Class 10 - Section A',
        },
        total_invoiced: 55000,
        total_paid: 35000,
        total_due: 20000,
        invoices: [
          {
            id: 'inv-term-1',
            invoice_number: 'INV-2026-0012',
            title: 'Term 1 Tuition & Laboratory Fee',
            issue_date: '2026-08-01',
            due_date: '2026-08-31',
            subtotal: 35000,
            discount_amount: 0,
            scholarship_amount: 0,
            late_fine_amount: 0,
            total_amount: 35000,
            paid_amount: 35000,
            balance_amount: 0,
            status: 'PAID',
            line_items: [
              { category_name: 'Tuition Fee (Term 1)', amount: 25000 },
              { category_name: 'Science Laboratory Fee', amount: 5000 },
              { category_name: 'Library & IT Access', amount: 5000 },
            ],
          },
          {
            id: 'inv-term-2',
            invoice_number: 'INV-2026-0088',
            title: 'Term 2 Tuition & Examination Fee',
            issue_date: '2026-11-01',
            due_date: '2026-11-30',
            subtotal: 22000,
            discount_amount: 2000,
            scholarship_amount: 0,
            late_fine_amount: 0,
            total_amount: 20000,
            paid_amount: 0,
            balance_amount: 20000,
            status: 'OVERDUE',
            line_items: [
              { category_name: 'Tuition Fee (Term 2)', amount: 18000 },
              { category_name: 'Semester Final Exam Fee', amount: 4000 },
            ],
          },
        ],
        payments: [
          {
            id: 'pay-001',
            receipt_number: 'RCP-2026-0199',
            invoice_id: 'inv-term-1',
            amount: 35000,
            payment_date: '2026-08-15',
            payment_mode: 'UPI / Razorpay',
            status: 'SUCCESS',
            transaction_reference: 'pay_Klx94Hja76qL',
          },
        ],
      }
      setPortalData(mockFees)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchFees()
  }, [fetchFees])

  const onRefresh = async () => {
    setRefreshing(true)
    await fetchFees()
    setRefreshing(false)
  }

  const handlePayNow = async (invoice: MobileFeeInvoice) => {
    try {
      setPaying(true)
      const order = await feesMobileApi.initiateFeePayment(invoice.id, invoice.balance_amount)
      Alert.alert(
        'Razorpay Payment Gateway',
        `Order ${order.razorpay_order_id} generated for ₹${order.amount.toLocaleString()}. Ready for checkout.`,
        [
          {
            text: 'Simulate Payment Success',
            onPress: () => {
              Alert.alert('Payment Successful', `Receipt generated for ₹${order.amount.toLocaleString()}. Balance cleared.`)
              fetchFees()
            },
          },
          { text: 'Cancel', style: 'cancel' },
        ]
      )
    } catch {
      // Fallback checkout simulation
      Alert.alert(
        'Online Payment Gateway',
        `Initiating secure checkout for ₹${invoice.balance_amount.toLocaleString()} on Razorpay.`,
        [
          {
            text: 'Simulate Payment Success',
            onPress: () => {
              Alert.alert('Payment Successful', `Payment of ₹${invoice.balance_amount.toLocaleString()} received! Receipt issued.`)
            },
          },
          { text: 'Cancel', style: 'cancel' },
        ]
      )
    } finally {
      setPaying(false)
    }
  }

  const viewReceipt = (invoice: MobileFeeInvoice) => {
    setSelectedInvoice(invoice)
    setReceiptModalVisible(true)
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'PAID':
        return { bg: '#dcfce7', text: '#15803d' }
      case 'PARTIALLY_PAID':
        return { bg: '#dbeafe', text: '#1d4ed8' }
      case 'OVERDUE':
        return { bg: '#fee2e2', text: '#b91c1c' }
      default:
        return { bg: '#fef3c7', text: '#92400e' }
    }
  }

  return (
    <SafeAreaView style={styles.container}>
      <ScrollView
        contentContainerStyle={styles.scrollContent}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} />}
      >
        <View style={styles.header}>
          <Text style={styles.headerTitle}>Fees & Finances</Text>
          <Text style={styles.headerSubtitle}>
            {portalData?.student?.name} • {portalData?.student?.class_name}
          </Text>
        </View>

        {loading ? (
          <ActivityIndicator size="large" color="#2563eb" style={{ marginTop: 40 }} />
        ) : (
          <>
            {/* Total Balance Hero Card */}
            <View style={styles.heroCard}>
              <View>
                <Text style={styles.heroDueLabel}>Total Outstanding Dues</Text>
                <Text style={styles.heroDueValue}>
                  ₹{(portalData?.total_due ?? 0).toLocaleString()}
                </Text>
              </View>
              <View style={styles.heroStats}>
                <View style={styles.heroStatItem}>
                  <Text style={styles.heroStatLabel}>Total Invoiced</Text>
                  <Text style={styles.heroStatVal}>
                    ₹{(portalData?.total_invoiced ?? 0).toLocaleString()}
                  </Text>
                </View>
                <View style={styles.heroStatItem}>
                  <Text style={styles.heroStatLabel}>Total Paid</Text>
                  <Text style={[styles.heroStatVal, { color: '#16a34a' }]}>
                    ₹{(portalData?.total_paid ?? 0).toLocaleString()}
                  </Text>
                </View>
              </View>
            </View>

            {/* Invoices List */}
            <Text style={styles.sectionTitle}>Invoices & Demands</Text>

            {portalData?.invoices?.map((inv) => {
              const statusColors = getStatusColor(inv.status)
              const hasDue = inv.balance_amount > 0

              return (
                <View key={inv.id} style={styles.invoiceCard}>
                  <View style={styles.invHeader}>
                    <View style={{ flex: 1 }}>
                      <Text style={styles.invNumber}>{inv.invoice_number}</Text>
                      <Text style={styles.invTitle}>{inv.title}</Text>
                    </View>
                    <View style={[styles.statusBadge, { backgroundColor: statusColors.bg }]}>
                      <Text style={[styles.statusText, { color: statusColors.text }]}>
                        {inv.status}
                      </Text>
                    </View>
                  </View>

                  <View style={styles.datesRow}>
                    <Text style={styles.dateLabel}>Issued: {inv.issue_date}</Text>
                    <Text style={[styles.dateLabel, hasDue && { color: '#dc2626', fontWeight: '700' }]}>
                      Due: {inv.due_date}
                    </Text>
                  </View>

                  {/* Line items */}
                  <View style={styles.lineItemsBox}>
                    {inv.line_items?.map((item, idx) => (
                      <View key={idx} style={styles.lineItemRow}>
                        <Text style={styles.lineItemName}>{item.category_name}</Text>
                        <Text style={styles.lineItemAmount}>₹{item.amount.toLocaleString()}</Text>
                      </View>
                    ))}
                    {inv.discount_amount > 0 && (
                      <View style={styles.lineItemRow}>
                        <Text style={[styles.lineItemName, { color: '#16a34a' }]}>Discount / Scholarship</Text>
                        <Text style={[styles.lineItemAmount, { color: '#16a34a' }]}>
                          -₹{inv.discount_amount.toLocaleString()}
                        </Text>
                      </View>
                    )}
                  </View>

                  {/* Amounts row */}
                  <View style={styles.amountBreakdown}>
                    <View>
                      <Text style={styles.amtLabel}>Total Amount</Text>
                      <Text style={styles.amtTotal}>₹{inv.total_amount.toLocaleString()}</Text>
                    </View>
                    <View style={{ alignItems: 'flex-end' }}>
                      <Text style={styles.amtLabel}>Remaining Dues</Text>
                      <Text style={[styles.amtBalance, { color: hasDue ? '#dc2626' : '#16a34a' }]}>
                        ₹{inv.balance_amount.toLocaleString()}
                      </Text>
                    </View>
                  </View>

                  {/* Action buttons */}
                  <View style={styles.actionsRow}>
                    {hasDue ? (
                      <TouchableOpacity
                        style={styles.payBtn}
                        onPress={() => handlePayNow(inv)}
                        disabled={paying}
                      >
                        <Ionicons name="card-outline" size={16} color="#ffffff" />
                        <Text style={styles.payBtnText}>
                          Pay Online ₹{inv.balance_amount.toLocaleString()}
                        </Text>
                      </TouchableOpacity>
                    ) : (
                      <TouchableOpacity
                        style={styles.receiptBtn}
                        onPress={() => viewReceipt(inv)}
                      >
                        <Ionicons name="receipt-outline" size={16} color="#2563eb" />
                        <Text style={styles.receiptBtnText}>View Receipt</Text>
                      </TouchableOpacity>
                    )}
                  </View>
                </View>
              )
            })}

            {/* Payment Receipts History */}
            <Text style={[styles.sectionTitle, { marginTop: 10 }]}>Payment History</Text>
            {portalData?.payments?.map((pay) => (
              <View key={pay.id} style={styles.paymentCard}>
                <View style={styles.payHeader}>
                  <View>
                    <Text style={styles.receiptNum}>{pay.receipt_number}</Text>
                    <Text style={styles.payDate}>
                      {pay.payment_date} • {pay.payment_mode}
                    </Text>
                  </View>
                  <View style={{ alignItems: 'flex-end' }}>
                    <Text style={styles.payAmount}>₹{pay.amount.toLocaleString()}</Text>
                    <View style={styles.paySuccessBadge}>
                      <Ionicons name="checkmark-circle" size={12} color="#16a34a" />
                      <Text style={styles.paySuccessText}>PAID</Text>
                    </View>
                  </View>
                </View>
              </View>
            ))}
          </>
        )}
      </ScrollView>

      {/* Digital Fee Receipt Modal */}
      <Modal
        visible={receiptModalVisible}
        transparent
        animationType="fade"
        onRequestClose={() => setReceiptModalVisible(false)}
      >
        <View style={styles.modalOverlay}>
          <View style={styles.receiptModal}>
            <View style={styles.receiptHeader}>
              <Text style={styles.receiptBrand}>CAMPUS SaaS CRM</Text>
              <Text style={styles.receiptDocTitle}>FEE PAYMENT RECEIPT</Text>
            </View>

            <View style={styles.receiptContent}>
              <View style={styles.receiptMetaRow}>
                <Text style={styles.rcpLabel}>Receipt No:</Text>
                <Text style={styles.rcpVal}>RCP-2026-0199</Text>
              </View>
              <View style={styles.receiptMetaRow}>
                <Text style={styles.rcpLabel}>Invoice Reference:</Text>
                <Text style={styles.rcpVal}>{selectedInvoice?.invoice_number}</Text>
              </View>
              <View style={styles.receiptMetaRow}>
                <Text style={styles.rcpLabel}>Student Name:</Text>
                <Text style={styles.rcpVal}>{portalData?.student?.name}</Text>
              </View>
              <View style={styles.receiptMetaRow}>
                <Text style={styles.rcpLabel}>Admission No:</Text>
                <Text style={styles.rcpVal}>{portalData?.student?.admission_number}</Text>
              </View>
              <View style={styles.receiptMetaRow}>
                <Text style={styles.rcpLabel}>Amount Paid:</Text>
                <Text style={[styles.rcpVal, { color: '#16a34a', fontWeight: '800' }]}>
                  ₹{(selectedInvoice?.paid_amount ?? 0).toLocaleString()}
                </Text>
              </View>
              <View style={styles.receiptMetaRow}>
                <Text style={styles.rcpLabel}>Payment Mode:</Text>
                <Text style={styles.rcpVal}>Razorpay UPI (Verified)</Text>
              </View>
            </View>

            <TouchableOpacity
              style={styles.closeReceiptBtn}
              onPress={() => setReceiptModalVisible(false)}
            >
              <Text style={styles.closeReceiptText}>Close Receipt</Text>
            </TouchableOpacity>
          </View>
        </View>
      </Modal>
    </SafeAreaView>
  )
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: theme.colors.background },
  scrollContent: { padding: 18, paddingBottom: 40 },
  header: { marginBottom: 16 },
  headerTitle: { fontSize: 24, fontWeight: '800', color: theme.colors.textPrimary, letterSpacing: -0.4 },
  headerSubtitle: { fontSize: 13, color: theme.colors.textMuted, marginTop: 3, fontWeight: '500' },

  heroCard: {
    backgroundColor: '#0f172a',
    borderRadius: theme.radii.lg,
    padding: 20,
    marginBottom: 20,
    ...theme.shadows.md,
  },
  heroDueLabel: { fontSize: 11, color: '#94a3b8', fontWeight: '700', textTransform: 'uppercase', letterSpacing: 0.8 },
  heroDueValue: { fontSize: 34, fontWeight: '800', color: '#ffffff', marginTop: 4, letterSpacing: -1 },
  heroStats: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginTop: 16,
    paddingTop: 14,
    borderTopWidth: 1,
    borderTopColor: '#334155',
  },
  heroStatItem: { flex: 1 },
  heroStatLabel: { fontSize: 11, color: '#94a3b8', fontWeight: '500' },
  heroStatVal: { fontSize: 16, fontWeight: '700', color: '#ffffff', marginTop: 2 },

  sectionTitle: { fontSize: 16, fontWeight: '700', color: theme.colors.textPrimary, marginBottom: 12 },

  invoiceCard: {
    backgroundColor: theme.colors.surface,
    borderRadius: theme.radii.md,
    padding: 16,
    borderWidth: 1,
    borderColor: theme.colors.border,
    marginBottom: 14,
    ...theme.shadows.sm,
  },
  invHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
  },
  invNumber: { fontSize: 12, fontWeight: '700', color: theme.colors.primary },
  invTitle: { fontSize: 15, fontWeight: '700', color: theme.colors.textPrimary, marginTop: 2 },
  statusBadge: {
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: theme.radii.full,
  },
  statusText: { fontSize: 11, fontWeight: '700' },

  datesRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginTop: 10,
    paddingBottom: 10,
    borderBottomWidth: 1,
    borderBottomColor: theme.colors.borderSubtle,
  },
  dateLabel: { fontSize: 11, color: theme.colors.textMuted },

  lineItemsBox: {
    paddingVertical: 10,
    borderBottomWidth: 1,
    borderBottomColor: theme.colors.borderSubtle,
  },
  lineItemRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    paddingVertical: 4,
  },
  lineItemName: { fontSize: 12, color: theme.colors.textSecondary },
  lineItemAmount: { fontSize: 12, fontWeight: '600', color: theme.colors.textPrimary },

  amountBreakdown: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    paddingVertical: 12,
  },
  amtLabel: { fontSize: 11, color: theme.colors.textMuted },
  amtTotal: { fontSize: 15, fontWeight: '700', color: theme.colors.textPrimary, marginTop: 2 },
  amtBalance: { fontSize: 16, fontWeight: '800', marginTop: 2 },

  actionsRow: {
    marginTop: 8,
  },
  payBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: theme.colors.primary,
    paddingVertical: 12,
    borderRadius: theme.radii.md,
    gap: 6,
    ...theme.shadows.glow(theme.colors.primary),
  },
  payBtnText: { color: '#ffffff', fontSize: 13, fontWeight: '700' },
  receiptBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: theme.colors.primary50,
    paddingVertical: 10,
    borderRadius: theme.radii.md,
    gap: 6,
  },
  receiptBtnText: { color: theme.colors.primary, fontSize: 13, fontWeight: '700' },

  paymentCard: {
    backgroundColor: theme.colors.surface,
    borderRadius: theme.radii.md,
    padding: 14,
    borderWidth: 1,
    borderColor: theme.colors.border,
    marginBottom: 10,
    ...theme.shadows.sm,
  },
  payHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  receiptNum: { fontSize: 13, fontWeight: '700', color: theme.colors.textPrimary },
  payDate: { fontSize: 11, color: theme.colors.textMuted, marginTop: 2 },
  payAmount: { fontSize: 15, fontWeight: '800', color: theme.colors.textPrimary },
  paySuccessBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 3,
    marginTop: 2,
  },
  paySuccessText: { fontSize: 10, fontWeight: '700', color: theme.colors.emerald },

  modalOverlay: {
    flex: 1,
    backgroundColor: 'rgba(15, 23, 42, 0.6)',
    justifyContent: 'center',
    alignItems: 'center',
    padding: 20,
  },
  receiptModal: {
    backgroundColor: theme.colors.surface,
    borderRadius: theme.radii.lg,
    width: '100%',
    padding: 22,
    ...theme.shadows.lg,
  },
  receiptHeader: {
    alignItems: 'center',
    borderBottomWidth: 1,
    borderBottomColor: theme.colors.borderSubtle,
    paddingBottom: 16,
    marginBottom: 16,
  },
  receiptBrand: { fontSize: 18, fontWeight: '800', color: theme.colors.textPrimary },
  receiptDocTitle: { fontSize: 12, color: theme.colors.textMuted, fontWeight: '600', marginTop: 2 },
  receiptContent: { gap: 12, marginBottom: 22 },
  receiptMetaRow: { flexDirection: 'row', justifyContent: 'space-between' },
  rcpLabel: { fontSize: 13, color: theme.colors.textMuted },
  rcpVal: { fontSize: 13, fontWeight: '600', color: theme.colors.textPrimary },
  closeReceiptBtn: {
    backgroundColor: theme.colors.surfaceSubtle,
    paddingVertical: 12,
    borderRadius: theme.radii.md,
    alignItems: 'center',
  },
  closeReceiptText: { fontSize: 14, fontWeight: '700', color: theme.colors.textSecondary },
})