import { useState } from 'react'
import {
  Box,
  Card,
  CardContent,
  Typography,
  TextField,
  Button,
  Grid,
  CircularProgress,
  Alert,
  Paper,
  Chip,
  Container,
} from '@mui/material'
import SchoolIcon from '@mui/icons-material/School'
import AccountBalanceIcon from '@mui/icons-material/AccountBalance'
import CheckCircleIcon from '@mui/icons-material/CheckCircle'
import ArrowForwardIcon from '@mui/icons-material/ArrowForward'
import { useNavigate } from 'react-router-dom'
import { useQueryClient } from '@tanstack/react-query'
import { institutionsApi } from '@/api/institutions'

export default function InstitutionRegistrationPage({ onClose }: { onClose?: () => void }) {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const handleCancel = onClose ?? (() => navigate('/login'))

  // Form states
  const [institutionType, setInstitutionType] = useState<'SCHOOL' | 'COLLEGE'>('SCHOOL')
  const [name, setName] = useState('')
  const [slug, setSlug] = useState('')
  const [slugStatus, setSlugStatus] = useState<{ checked: boolean; available: boolean; suggestion?: string } | null>(null)
  const [slugChecking, setSlugChecking] = useState(false)

  const [email, setEmail] = useState('')
  const [phone, setPhone] = useState('')
  const [city, setCity] = useState('')
  const [state, setState] = useState('')
  const [address, setAddress] = useState('')

  const [principalName, setPrincipalName] = useState('')
  const [principalEmail, setPrincipalEmail] = useState('')
  const [principalPhone, setPrincipalPhone] = useState('')

  const [loading, setLoading] = useState(false)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)
  const [successData, setSuccessData] = useState<{ tenant_id: string; slug: string; invitation_token: string } | null>(null)

  const handleNameChange = (val: string) => {
    setName(val)
    if (!slug || slugStatus === null) {
      const generatedSlug = val
        .toLowerCase()
        .replace(/[^a-z0-9]+/g, '-')
        .replace(/^-|-$/g, '')
      setSlug(generatedSlug)
    }
  }

  const handleCheckSlug = async () => {
    if (!slug) return
    setSlugChecking(true)
    try {
      const res = await institutionsApi.checkSubdomain(slug)
      setSlugStatus({ checked: true, available: res.available, suggestion: res.suggestion })
    } catch {
      setSlugStatus(null)
    } finally {
      setSlugChecking(false)
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setErrorMessage(null)
    setLoading(true)

    try {
      const res = await institutionsApi.register({
        name,
        slug,
        institution_type: institutionType,
        email,
        phone,
        city,
        state,
        address,
        principal_name: principalName,
        principal_email: principalEmail,
        principal_phone: principalPhone,
      })
      setSuccessData(res)
      if (onClose) {
        void queryClient.invalidateQueries({ queryKey: ['superAdminInstitutions'] })
        void queryClient.invalidateQueries({ queryKey: ['superAdminStats'] })
      }
    } catch (err: unknown) {
      const errorObj = err as { response?: { data?: { error?: { message?: string } } } }
      setErrorMessage(errorObj.response?.data?.error?.message || 'Failed to submit registration. Please verify details.')
    } finally {
      setLoading(false)
    }
  }

  if (successData && onClose) {
    const setupUrl = new URL('/accept-invitation', window.location.origin)
    setupUrl.searchParams.set('token', successData.invitation_token)
    return (
      <Box sx={{ display: 'grid', gap: 2, py: 1 }}>
        <Alert severity="success">{name} was added and is pending approval.</Alert>
        <Typography variant="body2" color="text.secondary">
          Approve the institution from the Institutions list. Share the setup link privately with {principalEmail}.
        </Typography>
        <TextField
          label="Administrator setup link"
          value={setupUrl.href}
          slotProps={{ htmlInput: { readOnly: true } }}
          onFocus={(event) => event.target.select()}
          fullWidth
        />
        <Box display="flex" justifyContent="flex-end">
          <Button variant="contained" onClick={onClose}>Done</Button>
        </Box>
      </Box>
    )
  }

  if (successData) {
    return (
      <Container maxWidth="sm" sx={{ py: 8 }}>
        <Card sx={{ p: 4, textAlign: 'center', borderRadius: 3, boxShadow: '0 10px 30px rgba(0,0,0,0.08)' }}>
          <CheckCircleIcon color="success" sx={{ fontSize: 64, mb: 2 }} />
          <Typography variant="h4" fontWeight={700} gutterBottom>
            Application Submitted!
          </Typography>
          <Typography variant="body1" color="text.secondary" mb={3}>
            <strong>{name}</strong> has been registered with pending status.
          </Typography>

          <Paper variant="outlined" sx={{ p: 2.5, bgcolor: '#f8fafc', mb: 3, textAlign: 'left' }}>
            <Typography variant="caption" color="text.secondary" display="block">
              INSTITUTION PORTAL DOMAIN:
            </Typography>
            <Typography variant="subtitle1" fontWeight={700} color="primary.main" gutterBottom>
              https://{successData.slug}.edusaas.com
            </Typography>
            <Typography variant="caption" color="text.secondary" display="block">
              ADMINISTRATOR INVITATION DISPATCHED TO:
            </Typography>
            <Typography variant="body2" fontWeight={600}>
              {principalEmail}
            </Typography>
          </Paper>

          <Alert severity="info" sx={{ mb: 3, textAlign: 'left' }}>
            The SaaS Platform Super Admin has been notified to review and approve your institution. Once approved, click the link sent to your email to set your administrator password and start onboarding.
          </Alert>

          <Box display="flex" gap={2} justifyContent="center">
            <Button
              variant="contained"
              onClick={() => navigate(`/accept-invitation?token=${successData.invitation_token}`)}
              endIcon={<ArrowForwardIcon />}
            >
              Activate Admin Account (Demo Token)
            </Button>
            <Button variant="outlined" onClick={() => navigate('/login')}>
              Back to Login
            </Button>
          </Box>
        </Card>
      </Container>
    )
  }

  const registrationForm = (
    <>
      {errorMessage && (
        <Alert severity="error" sx={{ mb: 3 }}>
          {errorMessage}
        </Alert>
      )}

      <form onSubmit={handleSubmit}>
        {/* Step 1: Select Type */}
        <Typography variant="h6" fontWeight={700} mb={2}>
          1. Institution Type
        </Typography>
        <Grid container spacing={2} mb={4}>
          <Grid item xs={12} sm={6}>
            <Paper
              component="button"
              type="button"
              aria-pressed={institutionType === 'SCHOOL'}
              variant="outlined"
              onClick={() => setInstitutionType('SCHOOL')}
              sx={{
                p: 2.5,
                width: '100%',
                textAlign: 'left',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: 2,
                borderRadius: 2,
                borderColor: institutionType === 'SCHOOL' ? 'primary.main' : 'divider',
                bgcolor: institutionType === 'SCHOOL' ? 'action.selected' : 'background.paper',
              }}
            >
              <SchoolIcon color={institutionType === 'SCHOOL' ? 'primary' : 'action'} sx={{ fontSize: 36 }} />
              <Box>
                <Typography variant="subtitle1" fontWeight={700}>
                  K-12 School / Academy
                </Typography>
                <Typography variant="caption" color="text.secondary">
                  Classes, Sections, Subjects, Academic Sessions
                </Typography>
              </Box>
            </Paper>
          </Grid>
          <Grid item xs={12} sm={6}>
            <Paper
              component="button"
              type="button"
              aria-pressed={institutionType === 'COLLEGE'}
              variant="outlined"
              onClick={() => setInstitutionType('COLLEGE')}
              sx={{
                p: 2.5,
                width: '100%',
                textAlign: 'left',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: 2,
                borderRadius: 2,
                borderColor: institutionType === 'COLLEGE' ? 'primary.main' : 'divider',
                bgcolor: institutionType === 'COLLEGE' ? 'action.selected' : 'background.paper',
              }}
            >
              <AccountBalanceIcon color={institutionType === 'COLLEGE' ? 'primary' : 'action'} sx={{ fontSize: 36 }} />
              <Box>
                <Typography variant="subtitle1" fontWeight={700}>
                  College / University
                </Typography>
                <Typography variant="caption" color="text.secondary">
                  Departments, Degree Courses, Semesters, Batches
                </Typography>
              </Box>
            </Paper>
          </Grid>
        </Grid>

        {/* Step 2: Institution Profile */}
        <Typography variant="h6" fontWeight={700} mb={2}>
          2. Institution Information
        </Typography>
        <Grid container spacing={2} mb={4}>
          <Grid item xs={12} sm={8}>
            <TextField
              label="Official Institution Name"
              placeholder="e.g. Greenwood International School"
              value={name}
              onChange={(e) => handleNameChange(e.target.value)}
              fullWidth
              required
              size="small"
            />
          </Grid>
          <Grid item xs={12} sm={4}>
            <TextField
              label="Official Email"
              type="email"
              placeholder="contact@school.edu"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              fullWidth
              required
              size="small"
            />
          </Grid>

          {/* Subdomain Input with live check */}
          <Grid item xs={12}>
            <Box display="flex" gap={1.5} alignItems="center">
              <TextField
                label="Desired Subdomain (Slug)"
                placeholder="greenwood"
                value={slug}
                onChange={(e) => {
                  setSlug(e.target.value.toLowerCase().replace(/[^a-z0-9-]/g, ''))
                  setSlugStatus(null)
                }}
                onBlur={handleCheckSlug}
                fullWidth
                required
                size="small"
                helperText="Your institution portal will be hosted at https://{subdomain}.edusaas.com"
              />
              <Button
                variant="outlined"
                onClick={handleCheckSlug}
                disabled={slugChecking || !slug}
                sx={{ height: 40, whiteSpace: 'nowrap' }}
              >
                {slugChecking ? <CircularProgress size={20} /> : 'Check Availability'}
              </Button>
            </Box>
            {slugStatus && (
              <Box mt={1}>
                {slugStatus.available ? (
                  <Chip label={`Subdomain "${slug}.edusaas.com" is available!`} color="success" size="small" />
                ) : (
                  <Chip
                    label={`Subdomain taken. Try suggestion: ${slugStatus.suggestion}`}
                    color="error"
                    size="small"
                    onClick={() => slugStatus.suggestion && setSlug(slugStatus.suggestion)}
                    sx={{ cursor: 'pointer' }}
                  />
                )}
              </Box>
            )}
          </Grid>

          <Grid item xs={12} sm={6}>
            <TextField
              label="Contact Phone"
              placeholder="+91 98765 43210"
              value={phone}
              onChange={(e) => setPhone(e.target.value)}
              fullWidth
              size="small"
            />
          </Grid>
          <Grid item xs={12} sm={3}>
            <TextField
              label="City"
              value={city}
              onChange={(e) => setCity(e.target.value)}
              fullWidth
              size="small"
            />
          </Grid>
          <Grid item xs={12} sm={3}>
            <TextField
              label="State / Province"
              value={state}
              onChange={(e) => setState(e.target.value)}
              fullWidth
              size="small"
            />
          </Grid>
          <Grid item xs={12}>
            <TextField
              label="Campus Street Address"
              value={address}
              onChange={(e) => setAddress(e.target.value)}
              fullWidth
              size="small"
            />
          </Grid>
        </Grid>

        {/* Step 3: Principal / Director Details */}
        <Typography variant="h6" fontWeight={700} mb={2}>
          3. Principal / Director Details (First Administrator)
        </Typography>
        <Grid container spacing={2} mb={4}>
          <Grid item xs={12} sm={4}>
            <TextField
              label="Full Name & Title"
              placeholder="e.g. Dr. Eleanor Vance"
              value={principalName}
              onChange={(e) => setPrincipalName(e.target.value)}
              fullWidth
              required
              size="small"
            />
          </Grid>
          <Grid item xs={12} sm={4}>
            <TextField
              label="Administrator Email (For Invitation)"
              type="email"
              placeholder="principal@school.edu"
              value={principalEmail}
              onChange={(e) => setPrincipalEmail(e.target.value)}
              fullWidth
              required
              size="small"
              helperText="Secure account invitation will be dispatched here"
            />
          </Grid>
          <Grid item xs={12} sm={4}>
            <TextField
              label="Mobile Number"
              placeholder="+91 98765 00000"
              value={principalPhone}
              onChange={(e) => setPrincipalPhone(e.target.value)}
              fullWidth
              size="small"
            />
          </Grid>
        </Grid>

        {/* Step 4: Plan Choice */}
        <Typography variant="h6" fontWeight={700} mb={2}>
          4. Commercial Subscription Plan
        </Typography>
        <Paper variant="outlined" sx={{ p: 2, mb: 4, bgcolor: '#f0fdf4', borderColor: '#bbf7d0', borderRadius: 2 }}>
          <Box display="flex" justifyContent="space-between" alignItems="center">
            <Box>
              <Typography variant="subtitle1" fontWeight={700} color="success.dark">
                30-Day Enterprise Full Access Trial Included
              </Typography>
              <Typography variant="caption" color="text.secondary">
                Includes all core modules, attendance, examinations, fee engine, and notifications. No credit card required upfront.
              </Typography>
            </Box>
            <Chip label="Free Trial" color="success" sx={{ fontWeight: 600 }} />
          </Box>
        </Paper>

        <Box display="flex" justifyContent="flex-end" gap={2}>
          <Button variant="outlined" onClick={handleCancel} disabled={loading}>
            Cancel
          </Button>
          <Button
            type="submit"
            variant="contained"
            size="large"
            disabled={loading || !name || !slug || !principalEmail}
            sx={{ px: 4 }}
          >
            {loading ? <CircularProgress size={24} color="inherit" /> : onClose ? 'Add Institution' : 'Submit Registration Application'}
          </Button>
        </Box>
      </form>
    </>
  )

  if (onClose) return registrationForm

  return (
    <Container maxWidth="md" sx={{ py: 6 }}>
      <Box textAlign="center" mb={4}>
        <Typography variant="h3" fontWeight={800} gutterBottom>
          Register Your Institution
        </Typography>
        <Typography variant="body1" color="text.secondary">
          Power your campus with EduSaaS multi-tenant school and college management system
        </Typography>
      </Box>
      <Card sx={{ borderRadius: 3, boxShadow: '0 4px 20px rgba(0,0,0,0.06)' }}>
        <CardContent sx={{ p: 4 }}>
          {registrationForm}
        </CardContent>
      </Card>
    </Container>
  )
}
