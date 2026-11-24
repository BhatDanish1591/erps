import { useState } from 'react'
import {
  Box,
  Card,
  CardContent,
  Typography,
  Button,
  Grid,
  Chip,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  MenuItem,
  CircularProgress,
  Divider,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  Stack,
} from '@mui/material'
import AddIcon from '@mui/icons-material/Add'
import CheckCircleIcon from '@mui/icons-material/CheckCircle'
import EditIcon from '@mui/icons-material/Edit'
import SyncIcon from '@mui/icons-material/Sync'
import SchoolIcon from '@mui/icons-material/School'
import PeopleIcon from '@mui/icons-material/People'
import StorageIcon from '@mui/icons-material/Storage'
import NotificationsIcon from '@mui/icons-material/Notifications'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { superAdminApi, SubscriptionPlanItem } from '@/api/superAdmin'

export default function SubscriptionPlansPage() {
  const queryClient = useQueryClient()
  const [createOpen, setCreateOpen] = useState(false)
  const [editPlan, setEditPlan] = useState<SubscriptionPlanItem | null>(null)

  // Form states
  const [name, setName] = useState('')
  const [code, setCode] = useState('')
  const [description, setDescription] = useState('')
  const [monthlyPrice, setMonthlyPrice] = useState('999')
  const [annualPrice, setAnnualPrice] = useState('9990')
  const [billingCycle, setBillingCycle] = useState('MONTHLY')
  const [institutionType, setInstitutionType] = useState('SCHOOL')
  const [maxStudents, setMaxStudents] = useState('300')
  const [maxTeachers, setMaxTeachers] = useState('20')
  const [storageLimitGb, setStorageLimitGb] = useState('10')
  const [notificationQuota, setNotificationQuota] = useState('1000')
  const [trialDays, setTrialDays] = useState('30')

  const { data: plans, isLoading } = useQuery({
    queryKey: ['superAdminPlans'],
    queryFn: superAdminApi.listPlans,
  })

  const createMutation = useMutation({
    mutationFn: superAdminApi.createPlan,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['superAdminPlans'] })
      setCreateOpen(false)
      setName('')
      setCode('')
      setDescription('')
    },
  })

  const updateMutation = useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: { price?: number; monthly_price?: number; annual_price?: number; is_active?: boolean } }) =>
      superAdminApi.updatePlan(id, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['superAdminPlans'] })
      setEditPlan(null)
    },
  })

  const seedMutation = useMutation({
    mutationFn: superAdminApi.seedPlans,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['superAdminPlans'] })
    },
  })

  const handleCreate = () => {
    createMutation.mutate({
      name,
      code,
      description,
      price: parseFloat(monthlyPrice) || 0,
      monthly_price: parseFloat(monthlyPrice) || 0,
      annual_price: parseFloat(annualPrice) || 0,
      billing_cycle: billingCycle,
      institution_type: institutionType === 'ALL' ? undefined : institutionType,
      max_students: parseInt(maxStudents, 10) || 300,
      max_teachers: parseInt(maxTeachers, 10) || 20,
      storage_limit_gb: parseInt(storageLimitGb, 10) || 10,
      notification_quota: parseInt(notificationQuota, 10) || 1000,
      trial_days: parseInt(trialDays, 10) || 30,
      features: [
        { feature_key: 'custom_domain', feature_value: { enabled: true }, is_enabled: true },
        { feature_key: 'bulk_import_export', feature_value: { enabled: true }, is_enabled: true },
        { feature_key: 'advanced_analytics', feature_value: { enabled: true }, is_enabled: true },
        { feature_key: 'sms_notifications', feature_value: { enabled: true }, is_enabled: true },
      ],
    })
  }

  return (
    <Box sx={{ p: { xs: 2, md: 4 } }}>
      <Box mb={4} display="flex" justifyContent="space-between" alignItems="center" flexWrap="wrap" gap={2}>
        <Box>
          <Typography variant="h4" fontWeight={700}>
            Subscription Plans & Quotas
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Configure commercial pricing tiers, capacity limits, and student/faculty quotas.
          </Typography>
        </Box>
        <Box sx={{ display: 'flex', gap: 1.5 }}>
          <Button
            variant="outlined"
            startIcon={<SyncIcon />}
            onClick={() => seedMutation.mutate()}
            disabled={seedMutation.isPending}
          >
            {seedMutation.isPending ? 'Syncing...' : 'Reset Default Plans'}
          </Button>
          <Button variant="contained" startIcon={<AddIcon />} onClick={() => setCreateOpen(true)}>
            Create Plan
          </Button>
        </Box>
      </Box>

      {isLoading ? (
        <Box display="flex" justifyContent="center" py={5}>
          <CircularProgress />
        </Box>
      ) : (
        <Grid container spacing={3}>
          {plans?.map((plan) => (
            <Grid item xs={12} sm={6} md={4} key={plan.id}>
              <Card sx={{ height: '100%', display: 'flex', flexDirection: 'column', borderRadius: 3, position: 'relative' }}>
                <CardContent sx={{ flex: 1, p: 3 }}>
                  <Box display="flex" justifyContent="space-between" alignItems="center" mb={1}>
                    <Typography variant="h6" fontWeight={700}>
                      {plan.name}
                    </Typography>
                    <Chip
                      label={plan.is_active ? 'ACTIVE' : 'INACTIVE'}
                      size="small"
                      color={plan.is_active ? 'success' : 'default'}
                      sx={{ fontWeight: 600 }}
                    />
                  </Box>

                  <Typography variant="caption" color="text.secondary" display="block" mb={2}>
                    Code: <code>{plan.code}</code> • Scope: <strong>{plan.institution_type || 'ALL'}</strong>
                  </Typography>

                  <Box display="flex" alignItems="baseline" gap={1} mb={0.5}>
                    <Typography variant="h4" fontWeight={800} color="primary.main">
                      ₹{(plan.monthly_price || plan.price).toLocaleString('en-IN')}
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      / month
                    </Typography>
                  </Box>
                  <Typography variant="caption" color="text.secondary" display="block" mb={2}>
                    Annual: ₹{(plan.annual_price || plan.price * 10).toLocaleString('en-IN')} / year
                  </Typography>

                  <Typography variant="body2" color="text.secondary" mb={2} sx={{ minHeight: 40 }}>
                    {plan.description || 'Comprehensive campus management suite for educational institutions.'}
                  </Typography>

                  <Divider sx={{ my: 1.5 }} />

                  {/* Limits */}
                  <Stack spacing={1} sx={{ mb: 2 }}>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                      <SchoolIcon color="primary" fontSize="small" />
                      <Typography variant="body2">
                        Max Students: <strong>{plan.max_students?.toLocaleString() || 300}</strong>
                      </Typography>
                    </Box>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                      <PeopleIcon color="secondary" fontSize="small" />
                      <Typography variant="body2">
                        Max Teachers: <strong>{plan.max_teachers || 20}</strong>
                      </Typography>
                    </Box>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                      <StorageIcon color="info" fontSize="small" />
                      <Typography variant="body2">
                        Storage: <strong>{plan.storage_limit_gb || 10} GB</strong>
                      </Typography>
                    </Box>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                      <NotificationsIcon color="warning" fontSize="small" />
                      <Typography variant="body2">
                        Alert Quota: <strong>{plan.notification_quota?.toLocaleString() || 1000}</strong>
                      </Typography>
                    </Box>
                  </Stack>

                  <Divider sx={{ my: 1.5 }} />

                  <Typography variant="caption" fontWeight={600} color="text.secondary">
                    INCLUDED FEATURES:
                  </Typography>
                  <List dense disablePadding sx={{ mt: 1 }}>
                    {plan.features?.map((f) => (
                      <ListItem key={f.feature_key} disableGutters>
                        <ListItemIcon sx={{ minWidth: 28 }}>
                          <CheckCircleIcon color="success" fontSize="small" />
                        </ListItemIcon>
                        <ListItemText
                          primary={f.feature_key.replace(/_/g, ' ').toUpperCase()}
                          primaryTypographyProps={{ fontSize: '0.85rem', fontWeight: 500 }}
                        />
                      </ListItem>
                    ))}
                  </List>
                </CardContent>

                <Box p={2.5} pt={0} display="flex" justifyContent="flex-end">
                  <Button
                    size="small"
                    startIcon={<EditIcon />}
                    variant="outlined"
                    onClick={() => setEditPlan(plan)}
                  >
                    Edit Pricing
                  </Button>
                </Box>
              </Card>
            </Grid>
          ))}
          {plans?.length === 0 && (
            <Grid item xs={12}>
              <Typography color="text.secondary" align="center" py={4}>
                No subscription plans configured yet. Click "Reset Default Plans" to seed standard School and College plans.
              </Typography>
            </Grid>
          )}
        </Grid>
      )}

      {/* Create Plan Dialog */}
      <Dialog open={createOpen} onClose={() => setCreateOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle sx={{ fontWeight: 700 }}>Create Commercial Subscription Plan</DialogTitle>
        <DialogContent dividers>
          <Box display="flex" flexDirection="column" gap={2} pt={1}>
            <TextField
              label="Plan Name"
              size="small"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g. Starter School"
              fullWidth
              required
            />
            <TextField
              label="Plan Code"
              size="small"
              value={code}
              onChange={(e) => setCode(e.target.value.toUpperCase())}
              placeholder="e.g. STARTER_SCHOOL"
              fullWidth
              required
            />
            <TextField
              label="Description"
              size="small"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              multiline
              rows={2}
              fullWidth
            />
            <Grid container spacing={2}>
              <Grid item xs={6}>
                <TextField
                  label="Monthly Price (₹)"
                  size="small"
                  type="number"
                  value={monthlyPrice}
                  onChange={(e) => setMonthlyPrice(e.target.value)}
                  fullWidth
                />
              </Grid>
              <Grid item xs={6}>
                <TextField
                  label="Annual Price (₹)"
                  size="small"
                  type="number"
                  value={annualPrice}
                  onChange={(e) => setAnnualPrice(e.target.value)}
                  fullWidth
                />
              </Grid>
            </Grid>

            <Grid container spacing={2}>
              <Grid item xs={6}>
                <TextField
                  select
                  label="Institution Scope"
                  size="small"
                  value={institutionType}
                  onChange={(e) => setInstitutionType(e.target.value)}
                  fullWidth
                >
                  <MenuItem value="ALL">All (Schools & Colleges)</MenuItem>
                  <MenuItem value="SCHOOL">School Plans Only</MenuItem>
                  <MenuItem value="COLLEGE">College Plans Only</MenuItem>
                </TextField>
              </Grid>
              <Grid item xs={6}>
                <TextField
                  select
                  label="Primary Billing Cycle"
                  size="small"
                  value={billingCycle}
                  onChange={(e) => setBillingCycle(e.target.value)}
                  fullWidth
                >
                  <MenuItem value="MONTHLY">Monthly</MenuItem>
                  <MenuItem value="YEARLY">Yearly</MenuItem>
                </TextField>
              </Grid>
            </Grid>

            <Grid container spacing={2}>
              <Grid item xs={6}>
                <TextField
                  label="Max Students"
                  size="small"
                  type="number"
                  value={maxStudents}
                  onChange={(e) => setMaxStudents(e.target.value)}
                  fullWidth
                />
              </Grid>
              <Grid item xs={6}>
                <TextField
                  label="Max Teachers"
                  size="small"
                  type="number"
                  value={maxTeachers}
                  onChange={(e) => setMaxTeachers(e.target.value)}
                  fullWidth
                />
              </Grid>
            </Grid>

            <Grid container spacing={2}>
              <Grid item xs={6}>
                <TextField
                  label="Cloud Storage (GB)"
                  size="small"
                  type="number"
                  value={storageLimitGb}
                  onChange={(e) => setStorageLimitGb(e.target.value)}
                  fullWidth
                />
              </Grid>
              <Grid item xs={6}>
                <TextField
                  label="Notification Quota"
                  size="small"
                  type="number"
                  value={notificationQuota}
                  onChange={(e) => setNotificationQuota(e.target.value)}
                  fullWidth
                />
              </Grid>
            </Grid>

            <TextField
              label="Trial Days"
              size="small"
              type="number"
              value={trialDays}
              onChange={(e) => setTrialDays(e.target.value)}
              fullWidth
            />
          </Box>
        </DialogContent>
        <DialogActions sx={{ p: 2.5 }}>
          <Button onClick={() => setCreateOpen(false)}>Cancel</Button>
          <Button
            variant="contained"
            onClick={handleCreate}
            disabled={!name || !code || createMutation.isPending}
          >
            {createMutation.isPending ? <CircularProgress size={20} /> : 'Save Plan'}
          </Button>
        </DialogActions>
      </Dialog>

      {/* Edit Plan Dialog */}
      <Dialog open={!!editPlan} onClose={() => setEditPlan(null)} maxWidth="xs" fullWidth>
        <DialogTitle sx={{ fontWeight: 700 }}>Edit Plan: {editPlan?.name}</DialogTitle>
        <DialogContent dividers>
          <Box pt={1} display="flex" flexDirection="column" gap={2}>
            <TextField
              label="Monthly Price (₹)"
              size="small"
              type="number"
              defaultValue={editPlan?.monthly_price || editPlan?.price}
              id="edit-monthly-price"
              fullWidth
            />
            <TextField
              label="Annual Price (₹)"
              size="small"
              type="number"
              defaultValue={editPlan?.annual_price || (editPlan?.price || 0) * 10}
              id="edit-annual-price"
              fullWidth
            />
            <TextField
              select
              label="Active Status"
              size="small"
              defaultValue={editPlan?.is_active ? 'true' : 'false'}
              id="edit-status-input"
              fullWidth
            >
              <MenuItem value="true">Active (Available for purchase)</MenuItem>
              <MenuItem value="false">Inactive (Archived)</MenuItem>
            </TextField>
          </Box>
        </DialogContent>
        <DialogActions sx={{ p: 2 }}>
          <Button onClick={() => setEditPlan(null)}>Cancel</Button>
          <Button
            variant="contained"
            onClick={() => {
              if (!editPlan) return
              const mPrice = (document.getElementById('edit-monthly-price') as HTMLInputElement)?.value
              const aPrice = (document.getElementById('edit-annual-price') as HTMLInputElement)?.value
              const activeVal = (document.getElementById('edit-status-input') as HTMLInputElement)?.value
              updateMutation.mutate({
                id: editPlan.id,
                payload: {
                  price: mPrice ? parseFloat(mPrice) : undefined,
                  monthly_price: mPrice ? parseFloat(mPrice) : undefined,
                  annual_price: aPrice ? parseFloat(aPrice) : undefined,
                  is_active: activeVal === 'true',
                },
              })
            }}
          >
            Save Changes
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  )
}
