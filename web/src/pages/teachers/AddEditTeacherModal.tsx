import React, { useEffect, useState } from 'react'
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  TextField,
  MenuItem,
  Grid,
  Tabs,
  Tab,
  Box,
  Typography,
  Alert,
  CircularProgress,
} from '@mui/material'
import { TeacherCreatePayload, TeacherItem, teachersApi } from '../../api/teachers'

interface AddEditTeacherModalProps {
  open: boolean
  onClose: () => void
  onSuccess: () => void
  teacher?: TeacherItem | null
}

export const AddEditTeacherModal: React.FC<AddEditTeacherModalProps> = ({
  open,
  onClose,
  onSuccess,
  teacher,
}) => {
  const [tabIndex, setTabIndex] = useState(0)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const [formData, setFormData] = useState<TeacherCreatePayload>({
    full_name: '',
    email: '',
    phone: '',
    employee_id: '',
    designation: '',
    qualification: '',
    specialization: '',
    experience_years: 0,
    joining_date: new Date().toISOString().split('T')[0],
    employment_type: 'FULL_TIME',

    address_line1: '',
    address_line2: '',
    city: '',
    state: '',
    postal_code: '',
    country: 'India',

    emergency_contact_name: '',
    emergency_contact_phone: '',
    pan_number: '',
    aadhar_number: '',
    bank_name: '',
    bank_account_number: '',
    bank_ifsc: '',
  })

  useEffect(() => {
    if (teacher) {
      setFormData({
        full_name: teacher.full_name || '',
        email: teacher.email || '',
        phone: teacher.phone || '',
        employee_id: teacher.employee_id || '',
        designation: teacher.designation || '',
        qualification: teacher.qualification || '',
        specialization: teacher.specialization || '',
        experience_years: teacher.experience_years || 0,
        joining_date: teacher.joining_date || '',
        employment_type: teacher.employment_type || 'FULL_TIME',

        address_line1: teacher.address_line1 || '',
        address_line2: teacher.address_line2 || '',
        city: teacher.city || '',
        state: teacher.state || '',
        postal_code: teacher.postal_code || '',
        country: teacher.country || 'India',

        emergency_contact_name: teacher.emergency_contact_name || '',
        emergency_contact_phone: teacher.emergency_contact_phone || '',
        pan_number: teacher.pan_number || '',
        aadhar_number: teacher.aadhar_number || '',
        bank_name: teacher.bank_name || '',
        bank_account_number: teacher.bank_account_number || '',
        bank_ifsc: teacher.bank_ifsc || '',
      })
    } else {
      setFormData({
        full_name: '',
        email: '',
        phone: '',
        employee_id: '',
        designation: '',
        qualification: '',
        specialization: '',
        experience_years: 0,
        joining_date: new Date().toISOString().split('T')[0],
        employment_type: 'FULL_TIME',
        address_line1: '',
        address_line2: '',
        city: '',
        state: '',
        postal_code: '',
        country: 'India',
        emergency_contact_name: '',
        emergency_contact_phone: '',
        pan_number: '',
        aadhar_number: '',
        bank_name: '',
        bank_account_number: '',
        bank_ifsc: '',
      })
    }
    setTabIndex(0)
    setError(null)
  }, [teacher, open])

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target
    setFormData((prev) => ({
      ...prev,
      [name]: name === 'experience_years' ? parseInt(value) || 0 : value,
    }))
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!formData.full_name.trim()) {
      setError('Teacher full name is required.')
      setTabIndex(0)
      return
    }
    if (!teacher && formData.initial_password && !formData.email?.trim()) {
      setError('Enter the official email to set up staff sign-in.')
      setTabIndex(0)
      return
    }

    try {
      setSubmitting(true)
      setError(null)

      const payload = {
        ...formData,
        full_name: formData.full_name.trim(),
        email: formData.email?.trim() || undefined,
        joining_date: formData.joining_date || undefined,
        initial_password: formData.initial_password || undefined,
      }
      if (teacher) await teachersApi.updateTeacher(teacher.id, payload)
      else await teachersApi.createTeacher(payload)

      onSuccess()
      onClose()
    } catch (err: any) {
      setError(err?.message || 'Failed to save teacher details.')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <Dialog open={open} onClose={onClose} maxWidth="md" fullWidth>
      <form onSubmit={handleSubmit}>
        <DialogTitle sx={{ fontWeight: 700, pb: 1 }}>
          {teacher ? `Edit Faculty: ${teacher.full_name}` : 'Register New Faculty Member'}
          <Typography variant="body2" color="text.secondary">
            {teacher
              ? `Employee ID: ${teacher.employee_id}`
              : 'Add faculty credentials, department role, contact details, and banking information.'}
          </Typography>
        </DialogTitle>

        <Box sx={{ borderBottom: 1, borderColor: 'divider', px: 3 }}>
          <Tabs value={tabIndex} onChange={(_, val) => setTabIndex(val)}>
            <Tab label="1. Basic & Academic Info" />
            <Tab label="2. Address & Location" />
            <Tab label="3. Statutory & Banking" />
          </Tabs>
        </Box>

        <DialogContent sx={{ minHeight: 380, pt: 2.5 }}>
          {error && (
            <Alert severity="error" sx={{ mb: 2.5 }} onClose={() => setError(null)}>
              {error}
            </Alert>
          )}

          {/* TAB 0: Basic & Academic */}
          {tabIndex === 0 && (
            <Grid container spacing={2}>
              <Grid item xs={12} sm={8}>
                <TextField
                  label="Full Name *"
                  name="full_name"
                  value={formData.full_name}
                  onChange={handleChange}
                  fullWidth
                  required
                />
              </Grid>
              <Grid item xs={12} sm={4}>
                <TextField
                  label="Employment Type"
                  name="employment_type"
                  value={formData.employment_type}
                  onChange={handleChange}
                  select
                  fullWidth
                >
                  <MenuItem value="FULL_TIME">Full Time</MenuItem>
                  <MenuItem value="PART_TIME">Part Time</MenuItem>
                  <MenuItem value="CONTRACT">Contractual</MenuItem>
                  <MenuItem value="VISITING">Visiting Faculty</MenuItem>
                </TextField>
              </Grid>
              <Grid item xs={12} sm={6}>
                <TextField
                  label="Official Email"
                  name="email"
                  type="email"
                  value={formData.email || ''}
                  onChange={handleChange}
                  helperText="Leave empty to auto-generate staff internal email"
                  fullWidth
                />
              </Grid>
              <Grid item xs={12} sm={6}>
                <TextField
                  label="Contact Phone"
                  name="phone"
                  value={formData.phone || ''}
                  onChange={handleChange}
                  fullWidth
                />
              </Grid>
              {!teacher && <Grid item xs={12} sm={6}>
                <TextField
                  label="Initial sign-in password"
                  name="initial_password"
                  type="password"
                  autoComplete="new-password"
                  value={formData.initial_password || ''}
                  onChange={handleChange}
                  inputProps={{ minLength: 8, maxLength: 72 }}
                  helperText="Optional. Applies when creating a new account."
                  fullWidth
                />
              </Grid>}
              <Grid item xs={12} sm={4}>
                <TextField
                  label="Employee ID"
                  name="employee_id"
                  value={formData.employee_id || ''}
                  onChange={handleChange}
                  helperText={teacher ? 'Cannot be changed' : 'Leave empty for auto-generation'}
                  disabled={Boolean(teacher)}
                  fullWidth
                />
              </Grid>
              <Grid item xs={12} sm={4}>
                <TextField
                  label="Designation / Role"
                  name="designation"
                  value={formData.designation || ''}
                  onChange={handleChange}
                  placeholder="e.g. Senior Lecturer, PGT Physics"
                  fullWidth
                />
              </Grid>
              <Grid item xs={12} sm={4}>
                <TextField
                  label="Experience (Years)"
                  name="experience_years"
                  type="number"
                  value={formData.experience_years || 0}
                  onChange={handleChange}
                  InputProps={{ inputProps: { min: 0, max: 60 } }}
                  fullWidth
                />
              </Grid>
              <Grid item xs={12} sm={6}>
                <TextField
                  label="Highest Qualification"
                  name="qualification"
                  value={formData.qualification || ''}
                  onChange={handleChange}
                  placeholder="e.g. M.Sc., B.Ed., Ph.D."
                  fullWidth
                />
              </Grid>
              <Grid item xs={12} sm={6}>
                <TextField
                  label="Specialization / Subject Domain"
                  name="specialization"
                  value={formData.specialization || ''}
                  onChange={handleChange}
                  placeholder="e.g. Quantum Physics, Organic Chemistry"
                  fullWidth
                />
              </Grid>
              <Grid item xs={12} sm={6}>
                <TextField
                  label="Joining Date"
                  name="joining_date"
                  type="date"
                  value={formData.joining_date || ''}
                  onChange={handleChange}
                  InputLabelProps={{ shrink: true }}
                  fullWidth
                />
              </Grid>
            </Grid>
          )}

          {/* TAB 1: Address */}
          {tabIndex === 1 && (
            <Grid container spacing={2}>
              <Grid item xs={12}>
                <TextField
                  label="Address Line 1"
                  name="address_line1"
                  value={formData.address_line1 || ''}
                  onChange={handleChange}
                  fullWidth
                />
              </Grid>
              <Grid item xs={12}>
                <TextField
                  label="Address Line 2"
                  name="address_line2"
                  value={formData.address_line2 || ''}
                  onChange={handleChange}
                  fullWidth
                />
              </Grid>
              <Grid item xs={12} sm={4}>
                <TextField
                  label="City"
                  name="city"
                  value={formData.city || ''}
                  onChange={handleChange}
                  fullWidth
                />
              </Grid>
              <Grid item xs={12} sm={4}>
                <TextField
                  label="State / Province"
                  name="state"
                  value={formData.state || ''}
                  onChange={handleChange}
                  fullWidth
                />
              </Grid>
              <Grid item xs={12} sm={4}>
                <TextField
                  label="Postal / ZIP Code"
                  name="postal_code"
                  value={formData.postal_code || ''}
                  onChange={handleChange}
                  fullWidth
                />
              </Grid>
              <Grid item xs={12} sm={6}>
                <TextField
                  label="Country"
                  name="country"
                  value={formData.country || 'India'}
                  onChange={handleChange}
                  fullWidth
                />
              </Grid>
            </Grid>
          )}

          {/* TAB 2: Statutory & Banking */}
          {tabIndex === 2 && (
            <Grid container spacing={2}>
              <Grid item xs={12} sm={6}>
                <TextField
                  label="Emergency Contact Name"
                  name="emergency_contact_name"
                  value={formData.emergency_contact_name || ''}
                  onChange={handleChange}
                  fullWidth
                />
              </Grid>
              <Grid item xs={12} sm={6}>
                <TextField
                  label="Emergency Contact Phone"
                  name="emergency_contact_phone"
                  value={formData.emergency_contact_phone || ''}
                  onChange={handleChange}
                  fullWidth
                />
              </Grid>
              <Grid item xs={12} sm={6}>
                <TextField
                  label="PAN Number"
                  name="pan_number"
                  value={formData.pan_number || ''}
                  onChange={handleChange}
                  fullWidth
                />
              </Grid>
              <Grid item xs={12} sm={6}>
                <TextField
                  label="Aadhar Number"
                  name="aadhar_number"
                  value={formData.aadhar_number || ''}
                  onChange={handleChange}
                  fullWidth
                />
              </Grid>
              <Grid item xs={12} sm={4}>
                <TextField
                  label="Bank Name"
                  name="bank_name"
                  value={formData.bank_name || ''}
                  onChange={handleChange}
                  fullWidth
                />
              </Grid>
              <Grid item xs={12} sm={4}>
                <TextField
                  label="Account Number"
                  name="bank_account_number"
                  value={formData.bank_account_number || ''}
                  onChange={handleChange}
                  fullWidth
                />
              </Grid>
              <Grid item xs={12} sm={4}>
                <TextField
                  label="IFSC Code"
                  name="bank_ifsc"
                  value={formData.bank_ifsc || ''}
                  onChange={handleChange}
                  fullWidth
                />
              </Grid>
            </Grid>
          )}
        </DialogContent>

        <DialogActions sx={{ px: 3, pb: 2.5, justifyContent: 'space-between' }}>
          <Box>
            {tabIndex > 0 && (
              <Button onClick={() => setTabIndex((p) => p - 1)} disabled={submitting}>
                Back
              </Button>
            )}
            {tabIndex < 2 && (
              <Button onClick={() => setTabIndex((p) => p + 1)} sx={{ ml: 1 }}>
                Next
              </Button>
            )}
          </Box>
          <Box>
            <Button onClick={onClose} disabled={submitting} sx={{ mr: 1 }}>
              Cancel
            </Button>
            <Button
              type="submit"
              variant="contained"
              disabled={submitting}
              startIcon={submitting ? <CircularProgress size={16} color="inherit" /> : null}
            >
              {submitting ? 'Saving...' : teacher ? 'Update Faculty' : 'Register Faculty'}
            </Button>
          </Box>
        </DialogActions>
      </form>
    </Dialog>
  )
}
