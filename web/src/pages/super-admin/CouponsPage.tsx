import React, { useState } from 'react'
import {
  Box,
  Typography,
  Button,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Chip,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  MenuItem,
  CircularProgress,
  Alert,
} from '@mui/material'
import AddIcon from '@mui/icons-material/Add'
import LocalOfferIcon from '@mui/icons-material/LocalOffer'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { superAdminApi, CouponItem } from '../../api/superAdmin'

export const CouponsPage: React.FC = () => {
  const queryClient = useQueryClient()
  const [isCreateOpen, setIsCreateOpen] = useState(false)
  const [formError, setFormError] = useState<string | null>(null)

  const [formData, setFormData] = useState({
    code: '',
    description: '',
    discount_type: 'PERCENTAGE' as 'PERCENTAGE' | 'FIXED_AMOUNT',
    discount_value: 20,
    max_redemptions: 100,
    valid_until: '',
    applicable_institution_type: '',
  })

  const { data: coupons = [], isLoading } = useQuery({
    queryKey: ['superadmin-coupons'],
    queryFn: superAdminApi.listCoupons,
  })

  const createMutation = useMutation({
    mutationFn: superAdminApi.createCoupon,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['superadmin-coupons'] })
      setIsCreateOpen(false)
      setFormData({
        code: '',
        description: '',
        discount_type: 'PERCENTAGE',
        discount_value: 20,
        max_redemptions: 100,
        valid_until: '',
        applicable_institution_type: '',
      })
    },
    onError: (err: any) => {
      setFormError(err.response?.data?.error?.message || err.response?.data?.detail || 'Failed to create coupon')
    },
  })

  const deactivateMutation = useMutation({
    mutationFn: superAdminApi.deactivateCoupon,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['superadmin-coupons'] })
    },
  })

  const handleCreate = () => {
    setFormError(null)
    if (!formData.code.trim()) {
      setFormError('Coupon code is required')
      return
    }
    createMutation.mutate({
      code: formData.code.trim().toUpperCase(),
      description: formData.description || undefined,
      discount_type: formData.discount_type,
      discount_value: Number(formData.discount_value),
      max_redemptions: formData.max_redemptions ? Number(formData.max_redemptions) : undefined,
      valid_until: formData.valid_until ? new Date(formData.valid_until).toISOString() : undefined,
      applicable_institution_type: formData.applicable_institution_type || undefined,
    })
  }

  return (
    <Box sx={{ p: { xs: 2, md: 4 } }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 4, flexWrap: 'wrap', gap: 2 }}>
        <Box>
          <Typography variant="h4" fontWeight={700} gutterBottom>
            Promotional Coupons
          </Typography>
          <Typography variant="body1" color="text.secondary">
            Manage promotional discount codes and redemption limits for SaaS subscriptions.
          </Typography>
        </Box>
        <Button
          variant="contained"
          startIcon={<AddIcon />}
          onClick={() => setIsCreateOpen(true)}
          sx={{ fontWeight: 600 }}
        >
          Create Coupon
        </Button>
      </Box>

      {isLoading ? (
        <Box sx={{ display: 'flex', justifyContent: 'center', p: 8 }}>
          <CircularProgress />
        </Box>
      ) : (
        <TableContainer component={Paper} sx={{ borderRadius: 2, boxShadow: 1, overflowX: 'auto', width: '100%' }}>
          <Table sx={{ minWidth: 600 }}>
            <TableHead sx={{ bgcolor: 'grey.50' }}>
              <TableRow>
                <TableCell><strong>Code</strong></TableCell>
                <TableCell><strong>Description</strong></TableCell>
                <TableCell><strong>Discount</strong></TableCell>
                <TableCell><strong>Scope</strong></TableCell>
                <TableCell><strong>Redemptions</strong></TableCell>
                <TableCell><strong>Status</strong></TableCell>
                <TableCell align="right"><strong>Actions</strong></TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {coupons.map((c: CouponItem) => (
                <TableRow key={c.id} hover>
                  <TableCell>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                      <LocalOfferIcon color="primary" fontSize="small" />
                      <Typography fontWeight={700}>{c.code}</Typography>
                    </Box>
                  </TableCell>
                  <TableCell>{c.description || '—'}</TableCell>
                  <TableCell>
                    <Chip
                      label={
                        c.discount_type === 'PERCENTAGE'
                          ? `${c.discount_value}% OFF`
                          : `₹${c.discount_value} OFF`
                      }
                      color="primary"
                      variant="outlined"
                      size="small"
                      sx={{ fontWeight: 600 }}
                    />
                  </TableCell>
                  <TableCell>{c.applicable_institution_type || 'All Institutions'}</TableCell>
                  <TableCell>
                    {c.times_redeemed} / {c.max_redemptions ? c.max_redemptions : '∞'}
                  </TableCell>
                  <TableCell>
                    <Chip
                      label={c.is_active ? 'Active' : 'Inactive'}
                      color={c.is_active ? 'success' : 'default'}
                      size="small"
                    />
                  </TableCell>
                  <TableCell align="right">
                    {c.is_active && (
                      <Button
                        size="small"
                        color="error"
                        onClick={() => deactivateMutation.mutate(c.id)}
                        disabled={deactivateMutation.isPending}
                      >
                        Deactivate
                      </Button>
                    )}
                  </TableCell>
                </TableRow>
              ))}
              {coupons.length === 0 && (
                <TableRow>
                  <TableCell colSpan={7} align="center" sx={{ py: 6, color: 'text.secondary' }}>
                    No coupons created yet. Click 'Create Coupon' to add one.
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </TableContainer>
      )}

      {/* ── Create Coupon Dialog ── */}
      <Dialog open={isCreateOpen} onClose={() => setIsCreateOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle sx={{ fontWeight: 700 }}>Create New Coupon</DialogTitle>
        <DialogContent dividers>
          {formError && (
            <Alert severity="error" sx={{ mb: 2 }}>
              {formError}
            </Alert>
          )}

          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2.5, mt: 1 }}>
            <TextField
              label="Coupon Code *"
              value={formData.code}
              onChange={(e) => setFormData({ ...formData, code: e.target.value.toUpperCase() })}
              placeholder="e.g. SUMMER50"
              fullWidth
            />

            <TextField
              label="Description"
              value={formData.description}
              onChange={(e) => setFormData({ ...formData, description: e.target.value })}
              fullWidth
            />

            <Box sx={{ display: 'flex', gap: 2 }}>
              <TextField
                select
                label="Discount Type"
                value={formData.discount_type}
                onChange={(e) => setFormData({ ...formData, discount_type: e.target.value as any })}
                sx={{ width: '50%' }}
              >
                <MenuItem value="PERCENTAGE">Percentage (%)</MenuItem>
                <MenuItem value="FIXED_AMOUNT">Fixed Amount (₹)</MenuItem>
              </TextField>

              <TextField
                type="number"
                label="Discount Value *"
                value={formData.discount_value}
                onChange={(e) => setFormData({ ...formData, discount_value: Number(e.target.value) })}
                sx={{ width: '50%' }}
              />
            </Box>

            <Box sx={{ display: 'flex', gap: 2 }}>
              <TextField
                type="number"
                label="Max Redemptions"
                value={formData.max_redemptions}
                onChange={(e) => setFormData({ ...formData, max_redemptions: Number(e.target.value) })}
                sx={{ width: '50%' }}
                helperText="Leave empty for unlimited"
              />

              <TextField
                select
                label="Applicable Institution"
                value={formData.applicable_institution_type}
                onChange={(e) => setFormData({ ...formData, applicable_institution_type: e.target.value })}
                sx={{ width: '50%' }}
              >
                <MenuItem value="">Both Schools & Colleges</MenuItem>
                <MenuItem value="SCHOOL">School Only</MenuItem>
                <MenuItem value="COLLEGE">College Only</MenuItem>
              </TextField>
            </Box>

            <TextField
              type="date"
              label="Valid Until"
              value={formData.valid_until}
              onChange={(e) => setFormData({ ...formData, valid_until: e.target.value })}
              InputLabelProps={{ shrink: true }}
              fullWidth
            />
          </Box>
        </DialogContent>
        <DialogActions sx={{ p: 2.5 }}>
          <Button onClick={() => setIsCreateOpen(false)}>Cancel</Button>
          <Button
            variant="contained"
            onClick={handleCreate}
            disabled={createMutation.isPending}
          >
            {createMutation.isPending ? 'Creating...' : 'Create Coupon'}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  )
}
