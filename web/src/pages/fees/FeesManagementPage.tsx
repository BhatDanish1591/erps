import { PageHeader } from '@/components/ui/PageHeader'
import { useState, useEffect, useRef } from 'react'
import {
  Box,
  Card,
  CardContent,
  Typography,
  Tabs,
  Tab,
  Button,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Chip,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  MenuItem,
  Grid,
  Alert,
  LinearProgress,
  IconButton,
  Divider,
} from '@mui/material'
import {
  AccountBalanceWallet as FinanceIcon,
  ReceiptLong as InvoiceIcon,
  Payment as PaymentIcon,
  WarningAmber as DefaultersIcon,
  SettingsSuggest as ConfigIcon,
  CardGiftcard as DiscountIcon,
  MenuBook as LedgerIcon,
  Add as AddIcon,
  Refresh as RefreshIcon,
  Print as PrintIcon,
  CheckCircle as PaidIcon,
  AttachMoney as MoneyIcon,
  TrendingUp as TrendingUpIcon,
  CreditCard as RazorpayIcon,
} from '@mui/icons-material'

import {
  feesApi,
  payFeeInvoice,
  FeeCategory,
  FeeStructure,
  FeeDiscountScholarship,
  FeeInvoice,
  FinanceDashboardStats,
  DefaulterStudent,
  CollectionLedgerItem,
  StudentPortalFeesResponse,
} from '../../api/fees'
import { useAuthStore } from '@/store/authStore'

export default function FeesManagementPage() {
  const { hasRole } = useAuthStore()
  const isStudentOrParent = hasRole(['STUDENT', 'PARENT'])

  const [activeTab, setActiveTab] = useState<number>(isStudentOrParent ? 2 : 0)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [successMsg, setSuccessMsg] = useState<string | null>(null)

  // Data states
  const [stats, setStats] = useState<FinanceDashboardStats | null>(null)
  const [invoices, setInvoices] = useState<FeeInvoice[]>([])
  const [categories, setCategories] = useState<FeeCategory[]>([])
  const [structures, setStructures] = useState<FeeStructure[]>([])
  const [discounts, setDiscounts] = useState<FeeDiscountScholarship[]>([])
  const [defaulters, setDefaulters] = useState<DefaulterStudent[]>([])
  const [ledgerItems, setLedgerItems] = useState<CollectionLedgerItem[]>([])
  const [myFees, setMyFees] = useState<StudentPortalFeesResponse | null>(null)

  // Modals
  const [paymentDialogOpen, setPaymentDialogOpen] = useState(false)
  const [selectedInvoice, setSelectedInvoice] = useState<FeeInvoice | null>(null)
  const [payAmount, setPayAmount] = useState<number>(0)
  const [payMode, setPayMode] = useState<string>('CASH')
  const [chequeNumber, setChequeNumber] = useState('')
  const [bankName, setBankName] = useState('')
  const [transactionRef, setTransactionRef] = useState('')
  const [paymentRemarks, setPaymentRemarks] = useState('')

  // Receipt HTML preview modal
  const [receiptHtmlOpen, setReceiptHtmlOpen] = useState(false)
  const [receiptHtml, setReceiptHtml] = useState<string>('')
  const receiptFrame = useRef<HTMLIFrameElement>(null)

  // Category Modal
  const [catDialogOpen, setCatDialogOpen] = useState(false)
  const [newCatName, setNewCatName] = useState('')
  const [newCatCode, setNewCatCode] = useState('')
  const [newCatType, setNewCatType] = useState('ACADEMIC')
  const [newCatDesc, setNewCatDesc] = useState('')

  // Cohort Invoicing Dialog
  const [cohortDialogOpen, setCohortDialogOpen] = useState(false)
  const [cohortStructureId, setCohortStructureId] = useState('')
  const [cohortTitle, setCohortTitle] = useState('')
  const [cohortDueDate, setCohortDueDate] = useState('')

  const loadData = async () => {
    setLoading(true)
    setError(null)
    try {
      if (isStudentOrParent) {
        const portal = await feesApi.getMyFees()
        setMyFees(portal)
      } else {
        const [dashStats, invList, catList, structList, discList, defRep, ledgerRep] = await Promise.all([
          feesApi.getDashboardStats().catch(() => null),
          feesApi.listInvoices().catch(() => []),
          feesApi.listCategories(false).catch(() => []),
          feesApi.listStructures().catch(() => []),
          feesApi.listDiscounts().catch(() => []),
          feesApi.getDefaultersReport().catch(() => ({ total_defaulters: 0, total_overdue_amount: 0, items: [] })),
          feesApi.getCollectionLedger().catch(() => ({ total_count: 0, total_amount_collected: 0, items: [] })),
        ])
        setStats(dashStats)
        setInvoices(invList)
        setCategories(catList)
        setStructures(structList)
        setDiscounts(discList)
        setDefaulters(defRep.items || [])
        setLedgerItems(ledgerRep.items || [])
      }
    } catch (err: any) {
      setError(err?.response?.data?.error?.message || err?.message || 'Failed to load fee finance data.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadData()
  }, [isStudentOrParent])

  const handleOpenPayment = (inv: FeeInvoice) => {
    setSelectedInvoice(inv)
    setPayAmount(inv.balance_amount)
    setPayMode('CASH')
    setChequeNumber('')
    setBankName('')
    setTransactionRef('')
    setPaymentRemarks('')
    setPaymentDialogOpen(true)
  }

  const handleRecordPayment = async () => {
    if (!selectedInvoice) return
    setLoading(true)
    try {
      const payload: any = {
        invoice_id: selectedInvoice.id,
        amount: Number(payAmount),
        payment_mode: payMode,
        remarks: paymentRemarks || undefined,
      }
      if (payMode === 'CHEQUE') {
        payload.cheque_number = chequeNumber
        payload.bank_name = bankName
      } else if (['BANK_TRANSFER', 'UPI', 'POS_CARD'].includes(payMode)) {
        payload.transaction_reference = transactionRef
      }

      const res = await feesApi.recordOfflinePayment(payload)
      setSuccessMsg(`Payment recorded successfully! Receipt: ${res.receipt_number}`)
      setPaymentDialogOpen(false)
      loadData()
    } catch (err: any) {
      setError(err?.response?.data?.error?.message || err?.message || 'Failed to record payment.')
    } finally {
      setLoading(false)
    }
  }

  const handleViewReceipt = async (paymentId: string) => {
    try {
      const html = await feesApi.getReceiptHtml(paymentId)
      setReceiptHtml(html)
      setReceiptHtmlOpen(true)
    } catch (err: any) {
      setError('Failed to fetch receipt printable view.')
    }
  }

  const handlePayOnlineRazorpay = async (inv: FeeInvoice) => {
    setLoading(true)
    try {
      const payment = await payFeeInvoice(inv.id, inv.balance_amount)
      if (!payment) return
      setSuccessMsg('Online payment recorded successfully.')
      await loadData()
    } catch (err: any) {
      setError(err?.response?.data?.error?.message || err?.message || 'Failed to initialize online payment.')
    } finally {
      setLoading(false)
    }
  }

  const handleCreateCategory = async () => {
    if (!newCatName || !newCatCode) return
    setLoading(true)
    try {
      await feesApi.createCategory({
        name: newCatName,
        code: newCatCode.toUpperCase(),
        fee_type: newCatType as any,
        description: newCatDesc,
      })
      setSuccessMsg('Fee category created successfully.')
      setCatDialogOpen(false)
      setNewCatName('')
      setNewCatCode('')
      setNewCatDesc('')
      loadData()
    } catch (err: any) {
      setError(err?.response?.data?.error?.message || err?.message || 'Failed to create fee category.')
    } finally {
      setLoading(false)
    }
  }

  const handleGenerateCohort = async () => {
    if (!cohortStructureId || !cohortTitle || !cohortDueDate) return
    setLoading(true)
    try {
      const res = await feesApi.generateCohortInvoices({
        fee_structure_id: cohortStructureId,
        title: cohortTitle,
        issue_date: new Date().toISOString().split('T')[0],
        due_date: cohortDueDate,
      })
      setSuccessMsg(`Generated ${res.invoices_created} cohort invoices successfully!`)
      setCohortDialogOpen(false)
      loadData()
    } catch (err: any) {
      setError(err?.response?.data?.error?.message || err?.message || 'Failed to generate cohort invoices.')
    } finally {
      setLoading(false)
    }
  }

  const getStatusChip = (status: string) => {
    const map: Record<string, { label: string; color: any }> = {
      PAID: { label: 'Paid', color: 'success' },
      PARTIALLY_PAID: { label: 'Partially Paid', color: 'warning' },
      OVERDUE: { label: 'Overdue', color: 'error' },
      ISSUED: { label: 'Issued / Due', color: 'info' },
      DRAFT: { label: 'Draft', color: 'default' },
      CANCELLED: { label: 'Cancelled', color: 'default' },
    }
    const conf = map[status] || { label: status, color: 'default' }
    return <Chip label={conf.label} color={conf.color} size="small" variant="outlined" />
  }

  return (
    <Box>
      {/* Page Header */}
      <Box sx={{ mb: 3 }}>
        <PageHeader
          title="Fees & Finance"
          description="Manage fee structures, invoices, payments, and outstanding balances."
          icon={<FinanceIcon />}
        >
          <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
            <Button variant="outlined" startIcon={<RefreshIcon />} onClick={loadData} disabled={loading}>
              Refresh
            </Button>
            {!isStudentOrParent && (
              <>
                <Button
                  variant="outlined"
                  color="secondary"
                  startIcon={<AddIcon />}
                  onClick={() => setCatDialogOpen(true)}
                >
                  Add Category
                </Button>
                <Button
                  variant="contained"
                  color="primary"
                  startIcon={<InvoiceIcon />}
                  onClick={() => setCohortDialogOpen(true)}
                >
                  Generate Cohort Invoices
                </Button>
              </>
            )}
          </Box>
        </PageHeader>
      </Box>

      {/* Alerts */}
      {loading && <LinearProgress sx={{ mb: 2 }} />}
      {error && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}
      {successMsg && (
        <Alert severity="success" sx={{ mb: 2 }} onClose={() => setSuccessMsg(null)}>
          {successMsg}
        </Alert>
      )}

      {/* Tabs */}
      <Card sx={{ mb: 3 }}>
        <Tabs
          value={activeTab}
          onChange={(_, val) => setActiveTab(val)}
          indicatorColor="primary"
          textColor="primary"
          variant="scrollable"
          scrollButtons="auto"
        >
          {!isStudentOrParent && <Tab value={0} icon={<FinanceIcon />} label="Finance Dashboard" iconPosition="start" />}
          {!isStudentOrParent && <Tab value={1} icon={<InvoiceIcon />} label="Invoices & Collections" iconPosition="start" />}
          <Tab value={2} icon={<PaymentIcon />} label="My Fees & Receipts" iconPosition="start" />
          {!isStudentOrParent && <Tab value={3} icon={<DefaultersIcon />} label="Outstanding Dues & Defaulters" iconPosition="start" />}
          {!isStudentOrParent && <Tab value={4} icon={<ConfigIcon />} label="Fee Structures & Categories" iconPosition="start" />}
          {!isStudentOrParent && <Tab value={5} icon={<DiscountIcon />} label="Discounts & Scholarships" iconPosition="start" />}
          {!isStudentOrParent && <Tab value={6} icon={<LedgerIcon />} label="Transaction Ledger" iconPosition="start" />}
        </Tabs>
      </Card>

      {/* TAB 0: FINANCE DASHBOARD */}
      {activeTab === 0 && !isStudentOrParent && stats && (
        <Box>
          <Grid container spacing={3} sx={{ mb: 3 }}>
            <Grid item xs={12} sm={6} md={3}>
              <Card sx={{ bgcolor: 'primary.light', color: 'primary.contrastText', p: 2, borderRadius: 2 }}>
                <Typography variant="subtitle2" sx={{ opacity: 0.9 }}>Total Invoiced</Typography>
                <Typography variant="h4" fontWeight={700}>₹{stats.total_invoiced_amount.toLocaleString()}</Typography>
                <Typography variant="caption">{stats.invoices_count} Total Invoices</Typography>
              </Card>
            </Grid>
            <Grid item xs={12} sm={6} md={3}>
              <Card sx={{ bgcolor: 'success.dark', color: '#fff', p: 2, borderRadius: 2 }}>
                <Typography variant="subtitle2" sx={{ opacity: 0.9 }}>Total Collected</Typography>
                <Typography variant="h4" fontWeight={700}>₹{stats.total_collected_amount.toLocaleString()}</Typography>
                <Typography variant="caption">
                  {stats.total_invoiced_amount > 0
                    ? `${Math.round((stats.total_collected_amount / stats.total_invoiced_amount) * 100)}% Collection Rate`
                    : 'No Invoices'}
                </Typography>
              </Card>
            </Grid>
            <Grid item xs={12} sm={6} md={3}>
              <Card sx={{ bgcolor: 'error.main', color: '#fff', p: 2, borderRadius: 2 }}>
                <Typography variant="subtitle2" sx={{ opacity: 0.9 }}>Outstanding Dues</Typography>
                <Typography variant="h4" fontWeight={700}>₹{stats.total_outstanding_amount.toLocaleString()}</Typography>
                <Typography variant="caption">{stats.overdue_invoices_count} Invoices Overdue</Typography>
              </Card>
            </Grid>
            <Grid item xs={12} sm={6} md={3}>
              <Card sx={{ bgcolor: 'info.main', color: '#fff', p: 2, borderRadius: 2 }}>
                <Typography variant="subtitle2" sx={{ opacity: 0.9 }}>Today's Collection</Typography>
                <Typography variant="h4" fontWeight={700}>₹{stats.today_collection_amount.toLocaleString()}</Typography>
                <Typography variant="caption">Month: ₹{stats.month_collection_amount.toLocaleString()}</Typography>
              </Card>
            </Grid>
          </Grid>

          {/* Breakdown cards */}
          <Grid container spacing={3}>
            <Grid item xs={12} md={6}>
              <Card sx={{ p: 2 }}>
                <Typography variant="h6" fontWeight={600} sx={{ mb: 2, display: 'flex', alignItems: 'center', gap: 1 }}>
                  <TrendingUpIcon color="primary" /> Collections by Payment Mode
                </Typography>
                <Divider sx={{ mb: 2 }} />
                {Object.keys(stats.collection_by_payment_mode).length === 0 ? (
                  <Typography variant="body2" color="text.secondary">No payments collected yet.</Typography>
                ) : (
                  Object.entries(stats.collection_by_payment_mode).map(([mode, amt]) => (
                    <Box key={mode} sx={{ display: 'flex', justifyContent: 'space-between', py: 1, borderBottom: '1px solid #f0f0f0' }}>
                      <Typography variant="body2" fontWeight={500}>{mode}</Typography>
                      <Typography variant="body2" fontWeight={700}>₹{amt.toLocaleString()}</Typography>
                    </Box>
                  ))
                )}
              </Card>
            </Grid>
            <Grid item xs={12} md={6}>
              <Card sx={{ p: 2 }}>
                <Typography variant="h6" fontWeight={600} sx={{ mb: 2, display: 'flex', alignItems: 'center', gap: 1 }}>
                  <MoneyIcon color="success" /> Invoice Status Breakdown
                </Typography>
                <Divider sx={{ mb: 2 }} />
                <Box sx={{ display: 'flex', justifyContent: 'space-between', py: 1, borderBottom: '1px solid #f0f0f0' }}>
                  <Typography variant="body2">Fully Paid Invoices</Typography>
                  <Chip label={stats.paid_invoices_count} color="success" size="small" />
                </Box>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', py: 1, borderBottom: '1px solid #f0f0f0' }}>
                  <Typography variant="body2">Overdue Invoices</Typography>
                  <Chip label={stats.overdue_invoices_count} color="error" size="small" />
                </Box>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', py: 1, borderBottom: '1px solid #f0f0f0' }}>
                  <Typography variant="body2">Total Invoices Created</Typography>
                  <Chip label={stats.invoices_count} color="primary" size="small" />
                </Box>
              </Card>
            </Grid>
          </Grid>
        </Box>
      )}

      {/* TAB 1: INVOICES & COLLECTIONS */}
      {activeTab === 1 && !isStudentOrParent && (
        <Card>
          <CardContent>
            <Typography variant="h6" fontWeight={600} sx={{ mb: 2 }}>
              Student Invoices & Payment Counter
            </Typography>
            <TableContainer component={Paper} variant="outlined" sx={{ overflowX: 'auto', width: '100%' }}>
              <Table size="small" sx={{ minWidth: 600 }}>
                <TableHead sx={{ bgcolor: '#f9fafb' }}>
                  <TableRow>
                    <TableCell sx={{ fontWeight: 600 }}>Invoice #</TableCell>
                    <TableCell sx={{ fontWeight: 600 }}>Student</TableCell>
                    <TableCell sx={{ fontWeight: 600 }}>Admission #</TableCell>
                    <TableCell sx={{ fontWeight: 600 }}>Title</TableCell>
                    <TableCell sx={{ fontWeight: 600 }}>Due Date</TableCell>
                    <TableCell align="right" sx={{ fontWeight: 600 }}>Total (₹)</TableCell>
                    <TableCell align="right" sx={{ fontWeight: 600 }}>Paid (₹)</TableCell>
                    <TableCell align="right" sx={{ fontWeight: 600 }}>Balance (₹)</TableCell>
                    <TableCell sx={{ fontWeight: 600 }}>Status</TableCell>
                    <TableCell align="center" sx={{ fontWeight: 600 }}>Actions</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {invoices.length === 0 ? (
                    <TableRow>
                      <TableCell colSpan={10} align="center" sx={{ py: 3, color: 'text.secondary' }}>
                        No invoices generated yet. Click "Generate Cohort Invoices" above.
                      </TableCell>
                    </TableRow>
                  ) : (
                    invoices.map((inv) => (
                      <TableRow key={inv.id} hover>
                        <TableCell sx={{ fontWeight: 600, color: 'primary.main' }}>{inv.invoice_number}</TableCell>
                        <TableCell>{inv.student_name || '-'}</TableCell>
                        <TableCell>{inv.admission_number || '-'}</TableCell>
                        <TableCell>{inv.title}</TableCell>
                        <TableCell>{inv.due_date}</TableCell>
                        <TableCell align="right">₹{inv.total_amount.toLocaleString()}</TableCell>
                        <TableCell align="right">₹{inv.paid_amount.toLocaleString()}</TableCell>
                        <TableCell align="right" sx={{ fontWeight: 700, color: inv.balance_amount > 0 ? 'error.main' : 'success.main' }}>
                          ₹{inv.balance_amount.toLocaleString()}
                        </TableCell>
                        <TableCell>{getStatusChip(inv.status)}</TableCell>
                        <TableCell align="center">
                          {inv.balance_amount > 0 && inv.status !== 'CANCELLED' && (
                            <Button
                              size="small"
                              variant="contained"
                              color="primary"
                              startIcon={<PaidIcon />}
                              onClick={() => handleOpenPayment(inv)}
                              sx={{ mr: 1 }}
                            >
                              Collect
                            </Button>
                          )}
                        </TableCell>
                      </TableRow>
                    ))
                  )}
                </TableBody>
              </Table>
            </TableContainer>
          </CardContent>
        </Card>
      )}

      {/* TAB 2: MY FEES & RECEIPTS (STUDENT / PARENT PORTAL) */}
      {activeTab === 2 && (
        <Box>
          {myFees ? (
            <Box>
              <Grid container spacing={3} sx={{ mb: 3 }}>
                <Grid item xs={12} sm={4}>
                  <Card sx={{ bgcolor: 'primary.main', color: '#fff', p: 2, borderRadius: 2 }}>
                    <Typography variant="subtitle2">Total Billed</Typography>
                    <Typography variant="h5" fontWeight={700}>₹{myFees.total_invoiced.toLocaleString()}</Typography>
                    <Typography variant="caption">{myFees.student.name} ({myFees.student.admission_number})</Typography>
                  </Card>
                </Grid>
                <Grid item xs={12} sm={4}>
                  <Card sx={{ bgcolor: 'success.main', color: '#fff', p: 2, borderRadius: 2 }}>
                    <Typography variant="subtitle2">Total Paid</Typography>
                    <Typography variant="h5" fontWeight={700}>₹{myFees.total_paid.toLocaleString()}</Typography>
                    <Typography variant="caption">Verified receipts recorded</Typography>
                  </Card>
                </Grid>
                <Grid item xs={12} sm={4}>
                  <Card sx={{ bgcolor: myFees.total_due > 0 ? 'error.main' : 'grey.600', color: '#fff', p: 2, borderRadius: 2 }}>
                    <Typography variant="subtitle2">Outstanding Balance</Typography>
                    <Typography variant="h5" fontWeight={700}>₹{myFees.total_due.toLocaleString()}</Typography>
                    <Typography variant="caption">{myFees.total_due > 0 ? 'Payment Required' : 'All Dues Cleared'}</Typography>
                  </Card>
                </Grid>
              </Grid>

              {/* Student Invoices */}
              <Card sx={{ mb: 3 }}>
                <CardContent>
                  <Typography variant="h6" fontWeight={600} sx={{ mb: 2 }}>My Invoices</Typography>
                  <TableContainer component={Paper} variant="outlined" sx={{ overflowX: 'auto', width: '100%' }}>
                    <Table size="small" sx={{ minWidth: 600 }}>
                      <TableHead sx={{ bgcolor: '#f9fafb' }}>
                        <TableRow>
                          <TableCell sx={{ fontWeight: 600 }}>Invoice #</TableCell>
                          <TableCell sx={{ fontWeight: 600 }}>Title</TableCell>
                          <TableCell sx={{ fontWeight: 600 }}>Due Date</TableCell>
                          <TableCell align="right" sx={{ fontWeight: 600 }}>Total (₹)</TableCell>
                          <TableCell align="right" sx={{ fontWeight: 600 }}>Paid (₹)</TableCell>
                          <TableCell align="right" sx={{ fontWeight: 600 }}>Balance (₹)</TableCell>
                          <TableCell sx={{ fontWeight: 600 }}>Status</TableCell>
                          <TableCell align="center" sx={{ fontWeight: 600 }}>Action</TableCell>
                        </TableRow>
                      </TableHead>
                      <TableBody>
                        {myFees.invoices.map((inv) => (
                          <TableRow key={inv.id}>
                            <TableCell sx={{ fontWeight: 600 }}>{inv.invoice_number}</TableCell>
                            <TableCell>{inv.title}</TableCell>
                            <TableCell>{inv.due_date}</TableCell>
                            <TableCell align="right">₹{inv.total_amount.toLocaleString()}</TableCell>
                            <TableCell align="right">₹{inv.paid_amount.toLocaleString()}</TableCell>
                            <TableCell align="right" sx={{ fontWeight: 700, color: inv.balance_amount > 0 ? 'error.main' : 'success.main' }}>
                              ₹{inv.balance_amount.toLocaleString()}
                            </TableCell>
                            <TableCell>{getStatusChip(inv.status)}</TableCell>
                            <TableCell align="center">
                              {inv.balance_amount > 0 && (
                                <Button
                                  variant="contained"
                                  color="primary"
                                  size="small"
                                  startIcon={<RazorpayIcon />}
                                  onClick={() => handlePayOnlineRazorpay(inv)}
                                >
                                  Pay Online
                                </Button>
                              )}
                            </TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </TableContainer>
                </CardContent>
              </Card>

              {/* Student Payment Receipts */}
              <Card>
                <CardContent>
                  <Typography variant="h6" fontWeight={600} sx={{ mb: 2 }}>Payment Receipts</Typography>
                  <TableContainer component={Paper} variant="outlined" sx={{ overflowX: 'auto', width: '100%' }}>
                    <Table size="small" sx={{ minWidth: 600 }}>
                      <TableHead sx={{ bgcolor: '#f9fafb' }}>
                        <TableRow>
                          <TableCell sx={{ fontWeight: 600 }}>Receipt #</TableCell>
                          <TableCell sx={{ fontWeight: 600 }}>Date</TableCell>
                          <TableCell sx={{ fontWeight: 600 }}>Mode</TableCell>
                          <TableCell align="right" sx={{ fontWeight: 600 }}>Amount (₹)</TableCell>
                          <TableCell sx={{ fontWeight: 600 }}>Status</TableCell>
                          <TableCell align="center" sx={{ fontWeight: 600 }}>Print / Download</TableCell>
                        </TableRow>
                      </TableHead>
                      <TableBody>
                        {myFees.payments.length === 0 ? (
                          <TableRow>
                            <TableCell colSpan={6} align="center" sx={{ py: 3, color: 'text.secondary' }}>
                              No payments recorded yet.
                            </TableCell>
                          </TableRow>
                        ) : (
                          myFees.payments.map((p) => (
                            <TableRow key={p.id}>
                              <TableCell sx={{ fontWeight: 600 }}>{p.receipt_number}</TableCell>
                              <TableCell>{p.payment_date?.split('T')[0]}</TableCell>
                              <TableCell><Chip label={p.payment_mode} size="small" /></TableCell>
                              <TableCell align="right" sx={{ fontWeight: 700 }}>₹{p.amount.toLocaleString()}</TableCell>
                              <TableCell><Chip label={p.status} color="success" size="small" /></TableCell>
                              <TableCell align="center">
                                <IconButton color="primary" onClick={() => handleViewReceipt(p.id)}>
                                  <PrintIcon />
                                </IconButton>
                              </TableCell>
                            </TableRow>
                          ))
                        )}
                      </TableBody>
                    </Table>
                  </TableContainer>
                </CardContent>
              </Card>
            </Box>
          ) : (
            <Card sx={{ p: 4, textAlign: 'center' }}>
              <Typography color="text.secondary">Loading Student Fee Portal...</Typography>
            </Card>
          )}
        </Box>
      )}

      {/* TAB 3: DEFAULTERS & OUTSTANDING DUES */}
      {activeTab === 3 && !isStudentOrParent && (
        <Card>
          <CardContent>
            <Typography variant="h6" fontWeight={600} sx={{ mb: 2, display: 'flex', alignItems: 'center', gap: 1 }}>
              <DefaultersIcon color="error" /> Outstanding Dues & Fee Defaulters Report
            </Typography>
            <TableContainer component={Paper} variant="outlined" sx={{ overflowX: 'auto', width: '100%' }}>
              <Table size="small" sx={{ minWidth: 600 }}>
                <TableHead sx={{ bgcolor: '#fef2f2' }}>
                  <TableRow>
                    <TableCell sx={{ fontWeight: 600 }}>Student Name</TableCell>
                    <TableCell sx={{ fontWeight: 600 }}>Admission #</TableCell>
                    <TableCell sx={{ fontWeight: 600 }}>Overdue Invoices</TableCell>
                    <TableCell sx={{ fontWeight: 600 }}>Oldest Due Date</TableCell>
                    <TableCell sx={{ fontWeight: 600 }}>Days Overdue</TableCell>
                    <TableCell align="right" sx={{ fontWeight: 600 }}>Total Balance (₹)</TableCell>
                    <TableCell sx={{ fontWeight: 600 }}>Parent Contact</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {defaulters.length === 0 ? (
                    <TableRow>
                      <TableCell colSpan={7} align="center" sx={{ py: 3, color: 'text.secondary' }}>
                        No fee defaulters found. Outstanding collection is on track!
                      </TableCell>
                    </TableRow>
                  ) : (
                    defaulters.map((d) => (
                      <TableRow key={d.student_id} hover>
                        <TableCell sx={{ fontWeight: 600 }}>{d.student_name}</TableCell>
                        <TableCell>{d.admission_number}</TableCell>
                        <TableCell><Chip label={`${d.invoices_count} Invoices`} size="small" color="error" variant="outlined" /></TableCell>
                        <TableCell>{d.oldest_due_date}</TableCell>
                        <TableCell sx={{ fontWeight: 700, color: 'error.main' }}>{d.days_overdue} days</TableCell>
                        <TableCell align="right" sx={{ fontWeight: 700, color: 'error.main' }}>
                          ₹{d.total_overdue_balance.toLocaleString()}
                        </TableCell>
                        <TableCell>
                          <Typography variant="caption" display="block">{d.parent_phone || 'No phone'}</Typography>
                          <Typography variant="caption" color="text.secondary">{d.parent_email || ''}</Typography>
                        </TableCell>
                      </TableRow>
                    ))
                  )}
                </TableBody>
              </Table>
            </TableContainer>
          </CardContent>
        </Card>
      )}

      {/* TAB 4: FEE STRUCTURES & CATEGORIES */}
      {activeTab === 4 && !isStudentOrParent && (
        <Grid container spacing={3}>
          {/* Categories */}
          <Grid item xs={12} md={5}>
            <Card>
              <CardContent>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
                  <Typography variant="h6" fontWeight={600}>Fee Categories</Typography>
                  <Button size="small" variant="outlined" startIcon={<AddIcon />} onClick={() => setCatDialogOpen(true)}>
                    Add
                  </Button>
                </Box>
                <TableContainer component={Paper} variant="outlined" sx={{ overflowX: 'auto', width: '100%' }}>
                  <Table size="small" sx={{ minWidth: 600 }}>
                    <TableHead sx={{ bgcolor: '#f9fafb' }}>
                      <TableRow>
                        <TableCell sx={{ fontWeight: 600 }}>Name</TableCell>
                        <TableCell sx={{ fontWeight: 600 }}>Code</TableCell>
                        <TableCell sx={{ fontWeight: 600 }}>Type</TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {categories.map((c) => (
                        <TableRow key={c.id}>
                          <TableCell sx={{ fontWeight: 500 }}>{c.name}</TableCell>
                          <TableCell><Chip label={c.code} size="small" /></TableCell>
                          <TableCell><Chip label={c.fee_type} size="small" variant="outlined" /></TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </TableContainer>
              </CardContent>
            </Card>
          </Grid>

          {/* Fee Structures */}
          <Grid item xs={12} md={7}>
            <Card>
              <CardContent>
                <Typography variant="h6" fontWeight={600} sx={{ mb: 2 }}>Configured Fee Structures</Typography>
                <TableContainer component={Paper} variant="outlined" sx={{ overflowX: 'auto', width: '100%' }}>
                  <Table size="small" sx={{ minWidth: 600 }}>
                    <TableHead sx={{ bgcolor: '#f9fafb' }}>
                      <TableRow>
                        <TableCell sx={{ fontWeight: 600 }}>Structure Name</TableCell>
                        <TableCell sx={{ fontWeight: 600 }}>Code</TableCell>
                        <TableCell sx={{ fontWeight: 600 }}>Target</TableCell>
                        <TableCell align="right" sx={{ fontWeight: 600 }}>Total Fee (₹)</TableCell>
                        <TableCell sx={{ fontWeight: 600 }}>Status</TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {structures.length === 0 ? (
                        <TableRow>
                          <TableCell colSpan={5} align="center" sx={{ py: 3, color: 'text.secondary' }}>
                            No fee structures defined yet.
                          </TableCell>
                        </TableRow>
                      ) : (
                        structures.map((s) => (
                          <TableRow key={s.id}>
                            <TableCell sx={{ fontWeight: 600 }}>{s.name}</TableCell>
                            <TableCell><Chip label={s.code} size="small" /></TableCell>
                            <TableCell>{s.applicable_to}</TableCell>
                            <TableCell align="right" sx={{ fontWeight: 700 }}>₹{s.total_amount.toLocaleString()}</TableCell>
                            <TableCell>
                              <Chip label={s.is_active ? 'Active' : 'Inactive'} color={s.is_active ? 'success' : 'default'} size="small" />
                            </TableCell>
                          </TableRow>
                        ))
                      )}
                    </TableBody>
                  </Table>
                </TableContainer>
              </CardContent>
            </Card>
          </Grid>
        </Grid>
      )}

      {/* TAB 5: DISCOUNTS & SCHOLARSHIPS */}
      {activeTab === 5 && !isStudentOrParent && (
        <Card>
          <CardContent>
            <Typography variant="h6" fontWeight={600} sx={{ mb: 2 }}>
              Discounts, Concessions & Scholarships
            </Typography>
            <TableContainer component={Paper} variant="outlined" sx={{ overflowX: 'auto', width: '100%' }}>
              <Table size="small" sx={{ minWidth: 600 }}>
                <TableHead sx={{ bgcolor: '#f9fafb' }}>
                  <TableRow>
                    <TableCell sx={{ fontWeight: 600 }}>Scholarship / Concession Name</TableCell>
                    <TableCell sx={{ fontWeight: 600 }}>Type</TableCell>
                    <TableCell sx={{ fontWeight: 600 }}>Calculation</TableCell>
                    <TableCell align="right" sx={{ fontWeight: 600 }}>Benefit Value</TableCell>
                    <TableCell sx={{ fontWeight: 600 }}>Status</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {discounts.length === 0 ? (
                    <TableRow>
                      <TableCell colSpan={5} align="center" sx={{ py: 3, color: 'text.secondary' }}>
                        No discounts or scholarships created.
                      </TableCell>
                    </TableRow>
                  ) : (
                    discounts.map((d) => (
                      <TableRow key={d.id}>
                        <TableCell sx={{ fontWeight: 600 }}>{d.name}</TableCell>
                        <TableCell><Chip label={d.discount_type} size="small" /></TableCell>
                        <TableCell>{d.calculation_type}</TableCell>
                        <TableCell align="right" sx={{ fontWeight: 700 }}>
                          {d.calculation_type === 'PERCENTAGE' ? `${d.value}%` : `₹${d.value}`}
                        </TableCell>
                        <TableCell>
                          <Chip label={d.is_active ? 'Active' : 'Inactive'} color={d.is_active ? 'success' : 'default'} size="small" />
                        </TableCell>
                      </TableRow>
                    ))
                  )}
                </TableBody>
              </Table>
            </TableContainer>
          </CardContent>
        </Card>
      )}

      {/* TAB 6: TRANSACTION LEDGER */}
      {activeTab === 6 && !isStudentOrParent && (
        <Card>
          <CardContent>
            <Typography variant="h6" fontWeight={600} sx={{ mb: 2 }}>
              Institutional Fee Collection Ledger & Audit Trail
            </Typography>
            <TableContainer component={Paper} variant="outlined" sx={{ overflowX: 'auto', width: '100%' }}>
              <Table size="small" sx={{ minWidth: 600 }}>
                <TableHead sx={{ bgcolor: '#f9fafb' }}>
                  <TableRow>
                    <TableCell sx={{ fontWeight: 600 }}>Receipt #</TableCell>
                    <TableCell sx={{ fontWeight: 600 }}>Date</TableCell>
                    <TableCell sx={{ fontWeight: 600 }}>Student</TableCell>
                    <TableCell sx={{ fontWeight: 600 }}>Admission #</TableCell>
                    <TableCell sx={{ fontWeight: 600 }}>Invoice #</TableCell>
                    <TableCell align="right" sx={{ fontWeight: 600 }}>Amount (₹)</TableCell>
                    <TableCell sx={{ fontWeight: 600 }}>Mode</TableCell>
                    <TableCell sx={{ fontWeight: 600 }}>Reference</TableCell>
                    <TableCell sx={{ fontWeight: 600 }}>Reconciliation</TableCell>
                    <TableCell align="center" sx={{ fontWeight: 600 }}>Action</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {ledgerItems.length === 0 ? (
                    <TableRow>
                      <TableCell colSpan={10} align="center" sx={{ py: 3, color: 'text.secondary' }}>
                        No collection transactions recorded in the ledger yet.
                      </TableCell>
                    </TableRow>
                  ) : (
                    ledgerItems.map((item) => (
                      <TableRow key={item.payment_id} hover>
                        <TableCell sx={{ fontWeight: 600, color: 'primary.main' }}>{item.receipt_number}</TableCell>
                        <TableCell>{item.payment_date?.split('T')[0]}</TableCell>
                        <TableCell>{item.student_name}</TableCell>
                        <TableCell>{item.admission_number}</TableCell>
                        <TableCell>{item.invoice_number}</TableCell>
                        <TableCell align="right" sx={{ fontWeight: 700 }}>₹{item.amount.toLocaleString()}</TableCell>
                        <TableCell><Chip label={item.payment_mode} size="small" /></TableCell>
                        <TableCell><Typography variant="caption">{item.transaction_reference || '-'}</Typography></TableCell>
                        <TableCell>
                          <Chip
                            label={item.reconciliation_status}
                            size="small"
                            color={item.reconciliation_status === 'RECONCILED' ? 'success' : 'warning'}
                            variant="outlined"
                          />
                        </TableCell>
                        <TableCell align="center">
                          <IconButton size="small" color="primary" onClick={() => handleViewReceipt(item.payment_id)}>
                            <PrintIcon fontSize="small" />
                          </IconButton>
                        </TableCell>
                      </TableRow>
                    ))
                  )}
                </TableBody>
              </Table>
            </TableContainer>
          </CardContent>
        </Card>
      )}

      {/* DIALOG: Record Offline Payment */}
      <Dialog open={paymentDialogOpen} onClose={() => setPaymentDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle sx={{ fontWeight: 700 }}>
          Record Fee Payment: {selectedInvoice?.invoice_number}
        </DialogTitle>
        <DialogContent dividers>
          <Box sx={{ mb: 2 }}>
            <Typography variant="body2" color="text.secondary">
              Student: <strong>{selectedInvoice?.student_name}</strong> ({selectedInvoice?.admission_number})
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Total Invoice: <strong>₹{selectedInvoice?.total_amount}</strong> | Outstanding Balance: <strong>₹{selectedInvoice?.balance_amount}</strong>
            </Typography>
          </Box>
          <Grid container spacing={2}>
            <Grid item xs={12} sm={6}>
              <TextField
                label="Amount to Pay (₹)"
                type="number"
                fullWidth
                value={payAmount}
                onChange={(e) => setPayAmount(Number(e.target.value))}
                inputProps={{ min: 1, max: selectedInvoice?.balance_amount }}
              />
            </Grid>
            <Grid item xs={12} sm={6}>
              <TextField
                select
                label="Payment Mode"
                fullWidth
                value={payMode}
                onChange={(e) => setPayMode(e.target.value)}
              >
                <MenuItem value="CASH">Cash Counter</MenuItem>
                <MenuItem value="CHEQUE">Bank Cheque / DD</MenuItem>
                <MenuItem value="BANK_TRANSFER">Bank Transfer (NEFT/RTGS)</MenuItem>
                <MenuItem value="UPI">UPI / QR Code</MenuItem>
                <MenuItem value="POS_CARD">Debit / Credit Card (POS)</MenuItem>
              </TextField>
            </Grid>
            {payMode === 'CHEQUE' && (
              <>
                <Grid item xs={12} sm={6}>
                  <TextField
                    label="Cheque Number"
                    fullWidth
                    value={chequeNumber}
                    onChange={(e) => setChequeNumber(e.target.value)}
                  />
                </Grid>
                <Grid item xs={12} sm={6}>
                  <TextField
                    label="Bank Name"
                    fullWidth
                    value={bankName}
                    onChange={(e) => setBankName(e.target.value)}
                  />
                </Grid>
              </>
            )}
            {['BANK_TRANSFER', 'UPI', 'POS_CARD'].includes(payMode) && (
              <Grid item xs={12}>
                <TextField
                  label="UTR / Transaction Reference #"
                  fullWidth
                  value={transactionRef}
                  onChange={(e) => setTransactionRef(e.target.value)}
                />
              </Grid>
            )}
            <Grid item xs={12}>
              <TextField
                label="Remarks / Notes"
                fullWidth
                multiline
                rows={2}
                value={paymentRemarks}
                onChange={(e) => setPaymentRemarks(e.target.value)}
              />
            </Grid>
          </Grid>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setPaymentDialogOpen(false)}>Cancel</Button>
          <Button variant="contained" color="primary" onClick={handleRecordPayment} disabled={loading || payAmount <= 0}>
            Submit Payment & Generate Receipt
          </Button>
        </DialogActions>
      </Dialog>

      {/* DIALOG: Add Category */}
      <Dialog open={catDialogOpen} onClose={() => setCatDialogOpen(false)} maxWidth="xs" fullWidth>
        <DialogTitle sx={{ fontWeight: 700 }}>Add Fee Category</DialogTitle>
        <DialogContent dividers>
          <Grid container spacing={2}>
            <Grid item xs={12}>
              <TextField
                label="Category Name"
                fullWidth
                placeholder="e.g. Science Lab Consumables"
                value={newCatName}
                onChange={(e) => setNewCatName(e.target.value)}
              />
            </Grid>
            <Grid item xs={12}>
              <TextField
                label="Category Code"
                fullWidth
                placeholder="e.g. SCI_LAB"
                value={newCatCode}
                onChange={(e) => setNewCatCode(e.target.value)}
              />
            </Grid>
            <Grid item xs={12}>
              <TextField
                select
                label="Category Type"
                fullWidth
                value={newCatType}
                onChange={(e) => setNewCatType(e.target.value)}
              >
                <MenuItem value="ACADEMIC">Academic</MenuItem>
                <MenuItem value="FACILITY">Facility</MenuItem>
                <MenuItem value="ONE_TIME">One-time</MenuItem>
                <MenuItem value="OPTIONAL">Optional</MenuItem>
                <MenuItem value="CUSTOM">Custom</MenuItem>
              </TextField>
            </Grid>
            <Grid item xs={12}>
              <TextField
                label="Description"
                fullWidth
                multiline
                rows={2}
                value={newCatDesc}
                onChange={(e) => setNewCatDesc(e.target.value)}
              />
            </Grid>
          </Grid>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setCatDialogOpen(false)}>Cancel</Button>
          <Button variant="contained" onClick={handleCreateCategory} disabled={!newCatName || !newCatCode}>
            Create Category
          </Button>
        </DialogActions>
      </Dialog>

      {/* DIALOG: Generate Cohort Invoices */}
      <Dialog open={cohortDialogOpen} onClose={() => setCohortDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle sx={{ fontWeight: 700 }}>Generate Cohort Fee Invoices</DialogTitle>
        <DialogContent dividers>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            This generates sequential invoices for all students enrolled under the selected fee structure.
          </Typography>
          <Grid container spacing={2}>
            <Grid item xs={12}>
              <TextField
                select
                label="Select Fee Structure"
                fullWidth
                value={cohortStructureId}
                onChange={(e) => setCohortStructureId(e.target.value)}
              >
                {structures.map((s) => (
                  <MenuItem key={s.id} value={s.id}>
                    {s.name} ({s.code}) - ₹{s.total_amount}
                  </MenuItem>
                ))}
              </TextField>
            </Grid>
            <Grid item xs={12}>
              <TextField
                label="Invoice Title"
                fullWidth
                placeholder="e.g. Annual Term 1 Tuition & Activity Fee"
                value={cohortTitle}
                onChange={(e) => setCohortTitle(e.target.value)}
              />
            </Grid>
            <Grid item xs={12}>
              <TextField
                label="Due Date"
                type="date"
                fullWidth
                InputLabelProps={{ shrink: true }}
                value={cohortDueDate}
                onChange={(e) => setCohortDueDate(e.target.value)}
              />
            </Grid>
          </Grid>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setCohortDialogOpen(false)}>Cancel</Button>
          <Button variant="contained" color="primary" onClick={handleGenerateCohort} disabled={!cohortStructureId || !cohortTitle || !cohortDueDate}>
            Generate Invoices
          </Button>
        </DialogActions>
      </Dialog>

      {/* DIALOG: Printable Receipt HTML Preview */}
      <Dialog open={receiptHtmlOpen} onClose={() => setReceiptHtmlOpen(false)} maxWidth="md" fullWidth>
        <DialogTitle sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          Official Fee Receipt
          <Button
            variant="contained"
            startIcon={<PrintIcon />}
            onClick={() => {
              receiptFrame.current?.contentWindow?.print()
            }}
          >
            Print
          </Button>
        </DialogTitle>
        <DialogContent dividers sx={{ p: 0, height: '70vh' }}>
          <iframe
            ref={receiptFrame}
            srcDoc={receiptHtml}
            sandbox="allow-same-origin allow-modals"
            style={{ width: '100%', height: '100%', border: 0 }}
            title="Fee receipt"
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setReceiptHtmlOpen(false)}>Close</Button>
        </DialogActions>
      </Dialog>
    </Box>
  )
}
