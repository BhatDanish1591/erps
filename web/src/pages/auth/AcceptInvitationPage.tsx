import { useState, useEffect } from 'react'
import {
  Box,
  Card,
  CardContent,
  Typography,
  TextField,
  Button,
  CircularProgress,
  Alert,
  Paper,
  Chip,
  Container,
} from '@mui/material'
import SchoolIcon from '@mui/icons-material/School'
import LockOpenIcon from '@mui/icons-material/LockOpen'
import CheckCircleIcon from '@mui/icons-material/CheckCircle'
import { useSearchParams, useNavigate } from 'react-router-dom'
import { institutionsApi } from '@/api/institutions'

export default function AcceptInvitationPage() {
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const token = searchParams.get('token') || ''

  const [verifying, setVerifying] = useState(true)
  const [invitationData, setInvitationData] = useState<{
    valid: boolean
    email: string
    institution_name: string
    institution_slug: string
    role_name: string
    first_name?: string
  } | null>(null)
  const [verifyError, setVerifyError] = useState<string | null>(null)

  const [fullName, setFullName] = useState('')
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [submitError, setSubmitError] = useState<string | null>(null)
  const [completed, setCompleted] = useState(false)

  useEffect(() => {
    if (!token) {
      setVerifyError('No invitation token found in link URL.')
      setVerifying(false)
      return
    }

    institutionsApi
      .verifyInvitation(token)
      .then((data) => {
        setInvitationData(data)
        if (data.first_name) {
          setFullName(data.first_name)
        }
      })
      .catch((err: unknown) => {
        const errorObj = err as { response?: { data?: { error?: { message?: string } } } }
        setVerifyError(errorObj.response?.data?.error?.message || 'Invalid or expired invitation token.')
      })
      .finally(() => setVerifying(false))
  }, [token])

  const handleActivate = async (e: React.FormEvent) => {
    e.preventDefault()
    setSubmitError(null)

    if (password.length < 8) {
      setSubmitError('Password must be at least 8 characters long.')
      return
    }
    if (password !== confirmPassword) {
      setSubmitError('Passwords do not match.')
      return
    }

    setSubmitting(true)
    try {
      await institutionsApi.acceptInvitation({
        token,
        password,
        full_name: fullName,
      })
      setCompleted(true)
    } catch (err: unknown) {
      const errorObj = err as { response?: { data?: { error?: { message?: string } } } }
      setSubmitError(errorObj.response?.data?.error?.message || 'Failed to activate account.')
    } finally {
      setSubmitting(false)
    }
  }

  if (verifying) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="100vh">
        <CircularProgress />
      </Box>
    )
  }

  if (verifyError || !invitationData?.valid) {
    return (
      <Container maxWidth="sm" sx={{ py: 8 }}>
        <Card sx={{ p: 4, textAlign: 'center', borderRadius: 3 }}>
          <Alert severity="error" sx={{ mb: 3 }}>
            {verifyError || 'This invitation token has expired or is invalid.'}
          </Alert>
          <Button variant="contained" onClick={() => navigate('/login')}>
            Return to Login
          </Button>
        </Card>
      </Container>
    )
  }

  if (completed) {
    return (
      <Container maxWidth="sm" sx={{ py: 8 }}>
        <Card sx={{ p: 4, textAlign: 'center', borderRadius: 3 }}>
          <CheckCircleIcon color="success" sx={{ fontSize: 60, mb: 2 }} />
          <Typography variant="h4" fontWeight={700} gutterBottom>
            Account Activated!
          </Typography>
          <Typography variant="body1" color="text.secondary" mb={3}>
            Your administrator account for <strong>{invitationData.institution_name}</strong> is now ready.
          </Typography>
          <Button variant="contained" size="large" onClick={() => navigate('/login')}>
            Proceed to Login & Start Onboarding
          </Button>
        </Card>
      </Container>
    )
  }

  return (
    <Container maxWidth="sm" sx={{ py: 8 }}>
      <Card sx={{ borderRadius: 3, boxShadow: '0 10px 30px rgba(0,0,0,0.08)' }}>
        <CardContent sx={{ p: 4 }}>
          <Box display="flex" alignItems="center" gap={1.5} mb={2}>
            <SchoolIcon color="primary" sx={{ fontSize: 36 }} />
            <Box>
              <Typography variant="h5" fontWeight={700}>
                Join {invitationData.institution_name}
              </Typography>
              <Typography variant="caption" color="text.secondary">
                {invitationData.institution_slug}.edusaas.com
              </Typography>
            </Box>
          </Box>

          <Paper variant="outlined" sx={{ p: 2, bgcolor: '#f8fafc', mb: 3, borderRadius: 2 }}>
            <Box display="flex" justifyContent="space-between" alignItems="center">
              <Box>
                <Typography variant="caption" color="text.secondary" display="block">
                  INVITED EMAIL ADDRESS:
                </Typography>
                <Typography variant="body2" fontWeight={600}>
                  {invitationData.email}
                </Typography>
              </Box>
              <Chip label={invitationData.role_name} color="primary" size="small" sx={{ fontWeight: 600 }} />
            </Box>
          </Paper>

          {submitError && (
            <Alert severity="error" sx={{ mb: 3 }}>
              {submitError}
            </Alert>
          )}

          <form onSubmit={handleActivate}>
            <Box display="flex" flexDirection="column" gap={2.5}>
              <TextField
                label="Full Name"
                size="small"
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
                fullWidth
                required
              />

              <TextField
                label="Create Password"
                type="password"
                size="small"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                fullWidth
                required
                helperText="Minimum 8 characters with letters, numbers, and symbols"
              />

              <TextField
                label="Confirm Password"
                type="password"
                size="small"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                fullWidth
                required
              />

              <Button
                type="submit"
                variant="contained"
                size="large"
                startIcon={<LockOpenIcon />}
                disabled={submitting}
                sx={{ mt: 1 }}
              >
                {submitting ? <CircularProgress size={24} color="inherit" /> : 'Set Password & Activate Account'}
              </Button>
            </Box>
          </form>
        </CardContent>
      </Card>
    </Container>
  )
}
