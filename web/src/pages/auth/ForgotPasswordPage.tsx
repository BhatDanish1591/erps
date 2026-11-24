import { useState } from 'react'
import {
  Box,
  Card,
  CardContent,
  Typography,
  TextField,
  Button,
  Link,
  CircularProgress,
  Avatar,
} from '@mui/material'
import LockResetIcon from '@mui/icons-material/LockReset'
import { useNavigate } from 'react-router-dom'
import { useSnackbar } from 'notistack'
import { forgotPassword } from '@/api/auth'

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState('')
  const [loading, setLoading] = useState(false)
  const [submitted, setSubmitted] = useState(false)

  const navigate = useNavigate()
  const { enqueueSnackbar } = useSnackbar()

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!email) return

    try {
      setLoading(true)
      await forgotPassword(email)
      setSubmitted(true)
      enqueueSnackbar('Password reset instructions sent', { variant: 'info' })
    } catch (err: any) {
      enqueueSnackbar(err.message || 'Request failed', { variant: 'error' })
    } finally {
      setLoading(false)
    }
  }

  return (
    <Box minHeight="100vh" display="flex" alignItems="center" justifyContent="center" bgcolor="#f1f5f9" px={2}>
      <Card sx={{ maxWidth: 440, width: '100%', p: 3, borderRadius: 3 }}>
        <CardContent>
          <Box display="flex" flexDirection="column" alignItems="center" mb={3}>
            <Avatar sx={{ bgcolor: 'warning.main', width: 48, height: 48, mb: 1.5 }}>
              <LockResetIcon />
            </Avatar>
            <Typography variant="h5" fontWeight={700}>
              Forgot Password
            </Typography>
            <Typography variant="body2" color="text.secondary" textAlign="center">
              Enter your registered email and we'll send a password recovery link
            </Typography>
          </Box>

          {!submitted ? (
            <Box component="form" onSubmit={handleSubmit} display="flex" flexDirection="column" gap={2.5}>
              <TextField
                label="Registered Email"
                type="email"
                fullWidth
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                autoFocus
              />
              <Button type="submit" variant="contained" size="large" fullWidth disabled={loading}>
                {loading ? <CircularProgress size={24} color="inherit" /> : 'Send Recovery Link'}
              </Button>
            </Box>
          ) : (
            <Box textAlign="center" py={2}>
              <Typography variant="body2" color="text.secondary" mb={3}>
                Check your inbox for further instructions. If you don't receive an email within 5 minutes, check your spam folder.
              </Typography>
              <Button variant="outlined" onClick={() => navigate('/login')}>
                Back to Sign In
              </Button>
            </Box>
          )}

          <Box textAlign="center" mt={3}>
            <Link component="button" variant="body2" onClick={() => navigate('/login')} sx={{ textDecoration: 'none' }}>
              &larr; Back to Login
            </Link>
          </Box>
        </CardContent>
      </Card>
    </Box>
  )
}
