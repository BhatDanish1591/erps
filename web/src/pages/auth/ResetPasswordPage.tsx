import { useState } from 'react'
import {
  Box,
  Card,
  CardContent,
  Typography,
  TextField,
  Button,
  CircularProgress,
} from '@mui/material'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { useSnackbar } from 'notistack'
import { resetPassword } from '@/api/auth'

export default function ResetPasswordPage() {
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [loading, setLoading] = useState(false)

  const [searchParams] = useSearchParams()
  const token = searchParams.get('token') || ''
  const navigate = useNavigate()
  const { enqueueSnackbar } = useSnackbar()

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (password !== confirmPassword) {
      enqueueSnackbar('Passwords do not match', { variant: 'error' })
      return
    }

    try {
      setLoading(true)
      await resetPassword(token, password)
      enqueueSnackbar('Password reset successfully. Please log in.', { variant: 'success' })
      navigate('/login')
    } catch (err: any) {
      enqueueSnackbar(err.message || 'Reset failed', { variant: 'error' })
    } finally {
      setLoading(false)
    }
  }

  return (
    <Box minHeight="100vh" display="flex" alignItems="center" justifyContent="center" bgcolor="#f1f5f9" px={2}>
      <Card sx={{ maxWidth: 440, width: '100%', p: 3, borderRadius: 3 }}>
        <CardContent>
          <Typography variant="h5" fontWeight={700} gutterBottom textAlign="center">
            Set New Password
          </Typography>
          <Box component="form" onSubmit={handleSubmit} display="flex" flexDirection="column" gap={2.5} mt={2}>
            <TextField
              label="New Password"
              type="password"
              fullWidth
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              helperText="Minimum 8 characters"
              required
            />
            <TextField
              label="Confirm Password"
              type="password"
              fullWidth
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              required
            />
            <Button type="submit" variant="contained" size="large" fullWidth disabled={loading}>
              {loading ? <CircularProgress size={24} color="inherit" /> : 'Update Password'}
            </Button>
          </Box>
        </CardContent>
      </Card>
    </Box>
  )
}
