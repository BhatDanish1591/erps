import React, { useRef, useState } from 'react'
import {
  Box,
  Typography,
  Card,
  CardContent,
  Grid,
  Button,
  Chip,
  LinearProgress,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  Divider,
  Alert,
  CircularProgress,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  ToggleButton,
  ToggleButtonGroup,
  Stack,
} from '@mui/material'
import CheckCircleIcon from '@mui/icons-material/CheckCircle'
import WarningAmberIcon from '@mui/icons-material/WarningAmber'
import ReceiptIcon from '@mui/icons-material/Receipt'
import VerifiedIcon from '@mui/icons-material/Verified'
import CloudDoneIcon from '@mui/icons-material/CloudDone'
import PeopleIcon from '@mui/icons-material/People'
import SchoolIcon from '@mui/icons-material/School'
import StorageIcon from '@mui/icons-material/Storage'
import NotificationsIcon from '@mui/icons-material/Notifications'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { openRazorpayCheckout } from '../../api/razorpay'
import {
  subscriptionsApi,
  SubscriptionPlanItem,
  OrderPricingBreakdown,
  CreateOrderResponse,
} from '../../api/subscriptions'

export const BillingSubscriptionPage: React.FC = () => {
  const queryClient = useQueryClient()
  const [billingCycle, setBillingCycle] = useState<'MONTHLY' | 'YEARLY'>('MONTHLY')
  const [selectedPlan, setSelectedPlan] = useState<SubscriptionPlanItem | null>(null)
  const [isCheckoutOpen, setIsCheckoutOpen] = useState(false)
  const [couponCode, setCouponCode] = useState('')
  const [appliedCoupon, setAppliedCoupon] = useState<string | null>(null)
  const [pricingBreakdown, setPricingBreakdown] = useState<OrderPricingBreakdown | null>(null)
  const [activeOrder, setActiveOrder] = useState<CreateOrderResponse | null>(null)
  const [isVerifyingPayment, setIsVerifyingPayment] = useState(false)
  const [checkoutError, setCheckoutError] = useState<string | null>(null)
  const [checkoutSuccess, setCheckoutSuccess] = useState<string | null>(null)
  const [selectedInvoiceId, setSelectedInvoiceId] = useState('')
  const invoiceFrame = useRef<HTMLIFrameElement>(null)
  const [isCancelOpen, setIsCancelOpen] = useState(false)
  const [cancelReason, setCancelReason] = useState('')

  // 1. Fetch Current Usage & Subscription
  const { data: currentUsage, isLoading: isUsageLoading } = useQuery({
    queryKey: ['subscription-current-usage'],
    queryFn: subscriptionsApi.getCurrentUsage,
  })

  // 2. Fetch Available Plans
  const { data: plans = [], isLoading: isPlansLoading } = useQuery({
    queryKey: ['subscription-plans'],
    queryFn: () => subscriptionsApi.getAvailablePlans(),
  })

  // 3. Fetch Invoices
  const { data: invoicesData } = useQuery({
    queryKey: ['subscription-invoices'],
    queryFn: () => subscriptionsApi.listInvoices({ page: 1, size: 10 }),
  })
  const invoicePreview = useQuery({
    queryKey: ['subscription-invoice-html', selectedInvoiceId],
    enabled: Boolean(selectedInvoiceId),
    queryFn: () => subscriptionsApi.getInvoiceHtml(selectedInvoiceId),
  })

  // Preview Order Mutation
  const previewMutation = useMutation({
    mutationFn: subscriptionsApi.previewOrder,
    onSuccess: (data) => {
      setPricingBreakdown(data)
      setAppliedCoupon(data.coupon_applied || null)
      setCheckoutError(null)
    },
    onError: (err: any) => {
      setCheckoutError(err.response?.data?.error?.message || 'Failed to preview order')
    },
  })

  // Create Order Mutation
  const createOrderMutation = useMutation({
    mutationFn: subscriptionsApi.createOrder,
    onSuccess: (order) => {
      if (order.order_id === 'free_activation') {
        setCheckoutSuccess('Subscription activated.')
        queryClient.invalidateQueries({ queryKey: ['subscription-current-usage'] })
        queryClient.invalidateQueries({ queryKey: ['subscription-invoices'] })
        return
      }
      setActiveOrder(order)
      setCheckoutError(null)
    },
    onError: (err: any) => {
      setCheckoutError(err.response?.data?.error?.message || 'Failed to initiate order')
    },
  })

  // Cancel Subscription Mutation
  const cancelMutation = useMutation({
    mutationFn: subscriptionsApi.cancelSubscription,
    onSuccess: () => {
      setIsCancelOpen(false)
      queryClient.invalidateQueries({ queryKey: ['subscription-current-usage'] })
    },
  })

  const handleOpenCheckout = (plan: SubscriptionPlanItem) => {
    setSelectedPlan(plan)
    setCouponCode('')
    setAppliedCoupon(null)
    setCheckoutError(null)
    setCheckoutSuccess(null)
    setPricingBreakdown(null)
    setActiveOrder(null)
    setIsCheckoutOpen(true)

    previewMutation.mutate({
      plan_id: plan.id,
      billing_cycle: billingCycle,
    })
  }

  const handleApplyCoupon = () => {
    if (!selectedPlan || !couponCode.trim()) return
    previewMutation.mutate({
      plan_id: selectedPlan.id,
      billing_cycle: billingCycle,
      coupon_code: couponCode.trim(),
    })
  }

  const handleInitiatePayment = () => {
    if (!selectedPlan) return
    createOrderMutation.mutate({
      plan_id: selectedPlan.id,
      billing_cycle: billingCycle,
      coupon_code: appliedCoupon || undefined,
    })
  }

  const handleRazorpayCheckout = async () => {
    if (!activeOrder) return
    setIsVerifyingPayment(true)
    setCheckoutError(null)
    try {
      const confirmation = await openRazorpayCheckout({
        key: activeOrder.key_id,
        order_id: activeOrder.order_id,
        amount: activeOrder.amount_paise,
        currency: activeOrder.currency,
        name: 'EduSaaS',
        description: activeOrder.plan_name,
      })
      if (!confirmation) return
      await subscriptionsApi.verifyPayment({
        ...confirmation,
        invoice_id: activeOrder.invoice_id,
      })

      setCheckoutSuccess('Subscription successfully upgraded and activated!')
      queryClient.invalidateQueries({ queryKey: ['subscription-current-usage'] })
      queryClient.invalidateQueries({ queryKey: ['subscription-invoices'] })
      setTimeout(() => {
        setIsCheckoutOpen(false)
        setActiveOrder(null)
        setCheckoutSuccess(null)
      }, 2000)
    } catch (err: any) {
      setCheckoutError(err.response?.data?.error?.message || err.message || 'Payment verification failed')
    } finally {
      setIsVerifyingPayment(false)
    }
  }

  if (isUsageLoading || isPlansLoading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', p: 8 }}>
        <CircularProgress />
      </Box>
    )
  }

  const status = currentUsage?.status || 'TRIAL'
  const isPastDue = status === 'PAST_DUE'
  const isSuspended = status === 'SUSPENDED'

  return (
    <Box>
      {/* ── Header & Status Banner ── */}
      <Box sx={{ mb: 4 }}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: 2 }}>
          <Box>
            <Typography variant="h4" fontWeight={700} gutterBottom>
              Subscription & SaaS Billing
            </Typography>
            <Typography variant="body1" color="text.secondary">
              Manage your institution tier, monitor real-time student & faculty quotas, and review tax invoices.
            </Typography>
          </Box>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
            <Chip
              label={currentUsage?.plan?.name || 'Standard Tier'}
              color="primary"
              variant="outlined"
              sx={{ fontWeight: 600, fontSize: '0.9rem', py: 1 }}
            />
            <Chip
              label={status}
              color={status === 'ACTIVE' ? 'success' : isPastDue || isSuspended ? 'error' : 'warning'}
              sx={{ fontWeight: 700 }}
            />
          </Box>
        </Box>

        {isPastDue && (
          <Alert severity="warning" sx={{ mt: 2 }} icon={<WarningAmberIcon />}>
            Your subscription payment is past due. Grace period is currently active. Please renew your plan to prevent system suspension.
          </Alert>
        )}
        {isSuspended && (
          <Alert severity="error" sx={{ mt: 2 }}>
            Your institution access has been suspended due to an expired subscription. Upgrade now to reactivate all portal services.
          </Alert>
        )}
      </Box>

      {/* ── Dynamic Usage Analytics Gauges ── */}
      <Typography variant="h6" fontWeight={700} sx={{ mb: 2 }}>
        Resource Usage & Entitlements
      </Typography>
      <Grid container spacing={3} sx={{ mb: 5 }}>
        {/* Students */}
        <Grid item xs={12} sm={6} md={3}>
          <Card sx={{ height: '100%', boxShadow: 2, borderRadius: 2 }}>
            <CardContent>
              <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 1.5 }}>
                <Typography variant="subtitle2" color="text.secondary" fontWeight={600}>
                  Students Capacity
                </Typography>
                <SchoolIcon color="primary" />
              </Stack>
              <Typography variant="h5" fontWeight={700}>
                {currentUsage?.usage.students.current || 0}
                <Typography component="span" variant="body2" color="text.secondary" sx={{ ml: 0.5 }}>
                  / {currentUsage?.usage.students.limit || 300}
                </Typography>
              </Typography>
              <LinearProgress
                variant="determinate"
                value={Math.min(currentUsage?.usage.students.percentage || 0, 100)}
                color={(currentUsage?.usage.students.percentage || 0) > 90 ? 'error' : 'primary'}
                sx={{ height: 8, borderRadius: 4, my: 1.5 }}
              />
              <Typography variant="caption" color="text.secondary">
                {currentUsage?.usage.students.remaining} student seats remaining
              </Typography>
            </CardContent>
          </Card>
        </Grid>

        {/* Teachers */}
        <Grid item xs={12} sm={6} md={3}>
          <Card sx={{ height: '100%', boxShadow: 2, borderRadius: 2 }}>
            <CardContent>
              <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 1.5 }}>
                <Typography variant="subtitle2" color="text.secondary" fontWeight={600}>
                  Teachers / Faculty
                </Typography>
                <PeopleIcon color="secondary" />
              </Stack>
              <Typography variant="h5" fontWeight={700}>
                {currentUsage?.usage.teachers.current || 0}
                <Typography component="span" variant="body2" color="text.secondary" sx={{ ml: 0.5 }}>
                  / {currentUsage?.usage.teachers.limit || 20}
                </Typography>
              </Typography>
              <LinearProgress
                variant="determinate"
                value={Math.min(currentUsage?.usage.teachers.percentage || 0, 100)}
                color={(currentUsage?.usage.teachers.percentage || 0) > 90 ? 'error' : 'secondary'}
                sx={{ height: 8, borderRadius: 4, my: 1.5 }}
              />
              <Typography variant="caption" color="text.secondary">
                {currentUsage?.usage.teachers.remaining} faculty seats remaining
              </Typography>
            </CardContent>
          </Card>
        </Grid>

        {/* Cloud Storage */}
        <Grid item xs={12} sm={6} md={3}>
          <Card sx={{ height: '100%', boxShadow: 2, borderRadius: 2 }}>
            <CardContent>
              <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 1.5 }}>
                <Typography variant="subtitle2" color="text.secondary" fontWeight={600}>
                  Cloud Storage
                </Typography>
                <StorageIcon color="info" />
              </Stack>
              <Typography variant="h5" fontWeight={700}>
                {((currentUsage?.usage.storage.used_mb || 0) / 1024).toFixed(1)} GB
                <Typography component="span" variant="body2" color="text.secondary" sx={{ ml: 0.5 }}>
                  / {currentUsage?.usage.storage.limit_gb || 10} GB
                </Typography>
              </Typography>
              <LinearProgress
                variant="determinate"
                value={Math.min(currentUsage?.usage.storage.percentage || 0, 100)}
                color="info"
                sx={{ height: 8, borderRadius: 4, my: 1.5 }}
              />
              <Typography variant="caption" color="text.secondary">
                Secure document and asset storage
              </Typography>
            </CardContent>
          </Card>
        </Grid>

        {/* Monthly Notifications */}
        <Grid item xs={12} sm={6} md={3}>
          <Card sx={{ height: '100%', boxShadow: 2, borderRadius: 2 }}>
            <CardContent>
              <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 1.5 }}>
                <Typography variant="subtitle2" color="text.secondary" fontWeight={600}>
                  Monthly SMS / Quota
                </Typography>
                <NotificationsIcon color="warning" />
              </Stack>
              <Typography variant="h5" fontWeight={700}>
                {currentUsage?.usage.notifications.used || 0}
                <Typography component="span" variant="body2" color="text.secondary" sx={{ ml: 0.5 }}>
                  / {currentUsage?.usage.notifications.quota || 1000}
                </Typography>
              </Typography>
              <LinearProgress
                variant="determinate"
                value={Math.min(currentUsage?.usage.notifications.percentage || 0, 100)}
                color="warning"
                sx={{ height: 8, borderRadius: 4, my: 1.5 }}
              />
              <Typography variant="caption" color="text.secondary">
                {currentUsage?.usage.notifications.remaining} alerts remaining this cycle
              </Typography>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* ── Plans Switcher & Upgrade Tier Cards ── */}
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3, flexWrap: 'wrap', gap: 2 }}>
        <Box>
          <Typography variant="h6" fontWeight={700}>
            Available Plans & Upgrades
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Prices configured by platform administrators with transparent capacity tiers.
          </Typography>
        </Box>

        <ToggleButtonGroup
          value={billingCycle}
          exclusive
          onChange={(_, val) => val && setBillingCycle(val)}
          size="small"
        >
          <ToggleButton value="MONTHLY" sx={{ px: 2, fontWeight: 600 }}>
            Monthly Billing
          </ToggleButton>
          <ToggleButton value="YEARLY" sx={{ px: 2, fontWeight: 600 }}>
            Annual Billing (Save 17%)
          </ToggleButton>
        </ToggleButtonGroup>
      </Box>

      <Grid container spacing={3} sx={{ mb: 6 }}>
        {plans.map((p) => {
          const isCurrent = currentUsage?.plan?.code === p.code
          const price = billingCycle === 'MONTHLY' ? p.monthly_price : p.annual_price

          return (
            <Grid item xs={12} md={4} key={p.id}>
              <Card
                sx={{
                  height: '100%',
                  display: 'flex',
                  flexDirection: 'column',
                  borderRadius: 3,
                  position: 'relative',
                  border: isCurrent ? '2px solid #0284c7' : '1px solid #e2e8f0',
                  boxShadow: isCurrent ? 4 : 1,
                }}
              >
                {isCurrent && (
                  <Chip
                    label="Current Plan"
                    color="primary"
                    size="small"
                    sx={{ position: 'absolute', top: 16, right: 16, fontWeight: 700 }}
                  />
                )}
                <CardContent sx={{ p: 3, flexGrow: 1 }}>
                  <Typography variant="h6" fontWeight={700}>
                    {p.name}
                  </Typography>
                  <Typography variant="body2" color="text.secondary" sx={{ minHeight: 40, mt: 0.5 }}>
                    {p.description}
                  </Typography>

                  <Box sx={{ my: 3 }}>
                    <Typography variant="h3" fontWeight={800} component="span">
                      ₹{price.toLocaleString()}
                    </Typography>
                    <Typography variant="body2" color="text.secondary" component="span" sx={{ ml: 1 }}>
                      / {billingCycle === 'MONTHLY' ? 'month' : 'year'}
                    </Typography>
                  </Box>

                  <Divider sx={{ my: 2 }} />

                  {/* Highlights */}
                  <Stack spacing={1.5}>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                      <CheckCircleIcon color="success" fontSize="small" />
                      <Typography variant="body2">
                        Up to <strong>{p.max_students.toLocaleString()} students</strong>
                      </Typography>
                    </Box>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                      <CheckCircleIcon color="success" fontSize="small" />
                      <Typography variant="body2">
                        Up to <strong>{p.max_teachers} teachers / faculty</strong>
                      </Typography>
                    </Box>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                      <CheckCircleIcon color="success" fontSize="small" />
                      <Typography variant="body2">
                        <strong>{p.storage_limit_gb} GB</strong> secure cloud storage
                      </Typography>
                    </Box>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                      <CheckCircleIcon color="success" fontSize="small" />
                      <Typography variant="body2">
                        <strong>{p.notification_quota.toLocaleString()}</strong> monthly notification quota
                      </Typography>
                    </Box>

                    {/* Features list */}
                    {p.features?.map((f) => (
                      <Box key={f.feature_key} sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                        <VerifiedIcon color={f.is_enabled ? 'primary' : 'disabled'} fontSize="small" />
                        <Typography
                          variant="body2"
                          color={f.is_enabled ? 'text.primary' : 'text.disabled'}
                          sx={{ textTransform: 'capitalize' }}
                        >
                          {f.feature_key.replace(/_/g, ' ')}
                        </Typography>
                      </Box>
                    ))}
                  </Stack>
                </CardContent>

                <Box sx={{ p: 3, pt: 0 }}>
                  <Button
                    fullWidth
                    variant={isCurrent ? 'outlined' : 'contained'}
                    color="primary"
                    disabled={isCurrent}
                    onClick={() => handleOpenCheckout(p)}
                    sx={{ py: 1.2, fontWeight: 700 }}
                  >
                    {isCurrent ? 'Active Plan' : 'Select Plan'}
                  </Button>
                </Box>
              </Card>
            </Grid>
          )
        })}
      </Grid>

      {/* ── Tax Invoices & Billing History ── */}
      <Box sx={{ mb: 4 }}>
        <Typography variant="h6" fontWeight={700} gutterBottom>
          Invoices & Payment History
        </Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
          Official GST-compliant tax invoices generated for your institution.
        </Typography>

        <TableContainer component={Paper} sx={{ borderRadius: 2, boxShadow: 1, overflowX: 'auto', width: '100%' }}>
          <Table sx={{ minWidth: 600 }}>
            <TableHead sx={{ bgcolor: 'grey.50' }}>
              <TableRow>
                <TableCell><strong>Invoice #</strong></TableCell>
                <TableCell><strong>Billing Cycle</strong></TableCell>
                <TableCell><strong>Date Issued</strong></TableCell>
                <TableCell><strong>Status</strong></TableCell>
                <TableCell align="right"><strong>Total Amount</strong></TableCell>
                <TableCell align="center"><strong>Receipt</strong></TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {invoicesData?.items?.map((inv) => (
                <TableRow key={inv.id} hover>
                  <TableCell sx={{ fontWeight: 600 }}>{inv.invoice_number}</TableCell>
                  <TableCell>{inv.billing_cycle}</TableCell>
                  <TableCell>{new Date(inv.created_at).toLocaleDateString()}</TableCell>
                  <TableCell>
                    <Chip
                      label={inv.status}
                      color={inv.status === 'PAID' ? 'success' : 'warning'}
                      size="small"
                      sx={{ fontWeight: 600 }}
                    />
                  </TableCell>
                  <TableCell align="right" sx={{ fontWeight: 700 }}>
                    ₹{inv.total_amount.toLocaleString(undefined, { minimumFractionDigits: 2 })}
                  </TableCell>
                  <TableCell align="center">
                    <Button
                      size="small"
                      startIcon={<ReceiptIcon />}
                      onClick={() => setSelectedInvoiceId(inv.id)}
                    >
                      View Invoice
                    </Button>
                  </TableCell>
                </TableRow>
              ))}
              {(!invoicesData?.items || invoicesData.items.length === 0) && (
                <TableRow>
                  <TableCell colSpan={6} align="center" sx={{ py: 4, color: 'text.secondary' }}>
                    No billed invoices found for this institution yet.
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </TableContainer>
      </Box>

      {/* ── Cancel Subscription Action ── */}
      {status === 'ACTIVE' && (
        <Box sx={{ mt: 6, p: 3, border: '1px solid #fee2e2', borderRadius: 2, bgcolor: '#fef2f2' }}>
          <Typography variant="subtitle1" fontWeight={700} color="error" gutterBottom>
            Cancel Subscription
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            Canceling your subscription will turn off auto-renewal. Your institution portal will remain active until the end of the current billing period.
          </Typography>
          <Button variant="outlined" color="error" onClick={() => setIsCancelOpen(true)}>
            Disable Auto-Renewal
          </Button>
        </Box>
      )}

      {/* ── Checkout & Upgrade Dialog ── */}
      <Dialog open={isCheckoutOpen} onClose={() => setIsCheckoutOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle sx={{ fontWeight: 700 }}>
          Upgrade to {selectedPlan?.name}
        </DialogTitle>
        <DialogContent dividers>
          {checkoutError && (
            <Alert severity="error" sx={{ mb: 2 }}>
              {checkoutError}
            </Alert>
          )}
          {checkoutSuccess && (
            <Alert severity="success" sx={{ mb: 2 }}>
              {checkoutSuccess}
            </Alert>
          )}

          <Typography variant="body2" color="text.secondary" gutterBottom>
            Billing Cycle: <strong>{billingCycle}</strong>
          </Typography>

          {/* Coupon input */}
          <Box sx={{ display: 'flex', gap: 1.5, my: 2 }}>
            <TextField
              size="small"
              label="Promo / Coupon Code"
              value={couponCode}
              onChange={(e) => setCouponCode(e.target.value.toUpperCase())}
              fullWidth
              placeholder="e.g. LAUNCH20"
            />
            <Button
              variant="outlined"
              onClick={handleApplyCoupon}
              disabled={previewMutation.isPending || !couponCode.trim()}
            >
              Apply
            </Button>
          </Box>

          {appliedCoupon && (
            <Chip
              label={`Coupon Applied: ${appliedCoupon}`}
              color="success"
              size="small"
              onDelete={() => {
                setAppliedCoupon(null)
                setCouponCode('')
                if (selectedPlan) {
                  previewMutation.mutate({ plan_id: selectedPlan.id, billing_cycle: billingCycle })
                }
              }}
              sx={{ mb: 2 }}
            />
          )}

          {/* Pricing Breakdown */}
          {pricingBreakdown && (
            <Box sx={{ bgcolor: 'grey.50', p: 2.5, borderRadius: 2, my: 2 }}>
              <Stack spacing={1}>
                <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                  <Typography variant="body2" color="text.secondary">Base Price:</Typography>
                  <Typography variant="body2">₹{pricingBreakdown.base_price.toFixed(2)}</Typography>
                </Box>
                {pricingBreakdown.discount_amount > 0 && (
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', color: 'success.main' }}>
                    <Typography variant="body2">Discount:</Typography>
                    <Typography variant="body2">-₹{pricingBreakdown.discount_amount.toFixed(2)}</Typography>
                  </Box>
                )}
                <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                  <Typography variant="body2" color="text.secondary">Tax (18% GST):</Typography>
                  <Typography variant="body2">₹{pricingBreakdown.tax_amount.toFixed(2)}</Typography>
                </Box>
                <Divider />
                <Box sx={{ display: 'flex', justifyContent: 'space-between', pt: 0.5 }}>
                  <Typography variant="subtitle1" fontWeight={700}>Total Payable:</Typography>
                  <Typography variant="subtitle1" fontWeight={800} color="primary.main">
                    ₹{pricingBreakdown.total_amount.toFixed(2)}
                  </Typography>
                </Box>
              </Stack>
            </Box>
          )}

          {/* Active order checkout step */}
          {activeOrder && (
            <Box sx={{ mt: 3, p: 2, border: '1px dashed #0284c7', borderRadius: 2, bgcolor: '#f0f9ff' }}>
              <Typography variant="subtitle2" fontWeight={700} color="primary" gutterBottom>
                Continue to Razorpay
              </Typography>
              <Typography variant="caption" color="text.secondary">
                Choose a payment method in the secure checkout window.
              </Typography>
            </Box>
          )}
        </DialogContent>
        <DialogActions sx={{ p: 2.5 }}>
          <Button onClick={() => setIsCheckoutOpen(false)} color="inherit">
            Cancel
          </Button>
          {!activeOrder && !checkoutSuccess && (
            <Button
              variant="contained"
              onClick={handleInitiatePayment}
              disabled={createOrderMutation.isPending || !pricingBreakdown}
            >
              {createOrderMutation.isPending ? 'Initiating Order...' : 'Proceed to Checkout'}
            </Button>
          )}
          {activeOrder && !checkoutSuccess && (
            <Button
              variant="contained"
              color="success"
              onClick={handleRazorpayCheckout}
              disabled={isVerifyingPayment}
              startIcon={isVerifyingPayment ? <CircularProgress size={16} color="inherit" /> : <CloudDoneIcon />}
            >
              {isVerifyingPayment ? 'Processing payment…' : 'Pay with Razorpay'}
            </Button>
          )}
        </DialogActions>
      </Dialog>

      {/* ── Cancel Subscription Dialog ── */}
      <Dialog open={isCancelOpen} onClose={() => setIsCancelOpen(false)}>
        <DialogTitle sx={{ fontWeight: 700 }}>Confirm Cancellation</DialogTitle>
        <DialogContent>
          <Typography variant="body2" sx={{ mb: 2 }}>
            Are you sure you want to disable auto-renewal for your subscription?
          </Typography>
          <TextField
            fullWidth
            size="small"
            label="Feedback / Reason for cancellation"
            multiline
            rows={3}
            value={cancelReason}
            onChange={(e) => setCancelReason(e.target.value)}
          />
        </DialogContent>
        <DialogActions sx={{ p: 2 }}>
          <Button onClick={() => setIsCancelOpen(false)}>Keep Subscription</Button>
          <Button
            variant="contained"
            color="error"
            onClick={() => cancelMutation.mutate({ immediate: false, reason: cancelReason })}
            disabled={cancelMutation.isPending}
          >
            Confirm
          </Button>
        </DialogActions>
      </Dialog>

      {/* ── Invoice View Modal (Iframe) ── */}
      {selectedInvoiceId && (
        <Dialog open onClose={() => setSelectedInvoiceId('')} maxWidth="md" fullWidth>
          <DialogTitle sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            Tax Invoice Document
            <Button onClick={() => invoiceFrame.current?.contentWindow?.print()} size="small" disabled={!invoicePreview.data}>
              Print
            </Button>
          </DialogTitle>
          <DialogContent dividers sx={{ p: 0, height: '70vh' }}>
            {invoicePreview.isLoading && <LinearProgress />}
            {invoicePreview.isError && <Alert severity="error">Unable to load the invoice.</Alert>}
            {invoicePreview.data && (
              <iframe
                ref={invoiceFrame}
                srcDoc={invoicePreview.data}
                sandbox="allow-same-origin allow-modals"
                style={{ width: '100%', height: '100%', border: 'none' }}
                title="Tax Invoice"
              />
            )}
          </DialogContent>
          <DialogActions>
            <Button onClick={() => setSelectedInvoiceId('')}>Close</Button>
          </DialogActions>
        </Dialog>
      )}
    </Box>
  )
}
