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
  InputAdornment,
  IconButton,
  Avatar,
  Divider,
  Chip,
  Paper,
} from '@mui/material'
import SchoolIcon from '@mui/icons-material/School'
import Visibility from '@mui/icons-material/Visibility'
import VisibilityOff from '@mui/icons-material/VisibilityOff'
import KeyIcon from '@mui/icons-material/Key'
import SmartphoneIcon from '@mui/icons-material/Smartphone'
import { useNavigate, useLocation } from 'react-router-dom'
import { useSnackbar } from 'notistack'
import { loginUser } from '@/api/auth'
import { useAuthStore } from '@/store/authStore'

const DEMO_ACCOUNTS = [
  { label: 'Super Admin', email: 'superadmin@edusaas.com', role: 'Platform', color: 'secondary' as const },
  { label: 'College Admin', email: 'college.admin@apex.edu', role: 'College', color: 'primary' as const },
  { label: 'Teacher', email: 'teacher@apex.edu', role: 'Faculty', color: 'info' as const },
  { label: 'Student', email: 'student@apex.edu', role: 'Student', color: 'warning' as const },
  { label: 'Parent', email: 'parent@apex.edu', role: 'Guardian', color: 'success' as const },
]

export default function LoginPage() {
  const [identifier, setIdentifier] = useState('')
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [loading, setLoading] = useState(false)

  const navigate = useNavigate()
  const location = useLocation()
  const { enqueueSnackbar } = useSnackbar()
  const setAuth = useAuthStore((s) => s.setAuth)

  const handleDemoSelect = (email: string) => {
    setIdentifier(email)
    setPassword('Password123!')
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!identifier || !password) {
      enqueueSnackbar('Please fill in both email/phone and password', { variant: 'warning' })
      return
    }

    try {
      setLoading(true)
      const data = await loginUser({ identifier, password })
      setAuth(data)
      enqueueSnackbar(`Welcome back, ${data.user.full_name}!`, { variant: 'success' })

      // Navigation target
      if (data.user.is_superadmin) {
        navigate('/super-admin')
      } else if (!data.user.current_tenant_id && data.user.institutions.length > 1) {
        navigate('/select-institution')
      } else {
        const from = (location.state as any)?.from?.pathname || '/dashboard'
        navigate(from)
      }
    } catch (err: any) {
      enqueueSnackbar(err.message || 'Login failed', { variant: 'error' })
    } finally {
      setLoading(false)
    }
  }

  return (
    <Box
      minHeight="100vh"
      display="flex"
      alignItems="center"
      justifyContent="center"
      bgcolor="#f1f5f9"
      px={2}
      py={4}
    >
      <Card sx={{ maxWidth: 480, width: '100%', p: { xs: 2, sm: 3 }, borderRadius: 3, boxShadow: '0 4px 24px rgba(0,0,0,0.08)' }}>
        <CardContent>
          <Box display="flex" flexDirection="column" alignItems="center" mb={2.5}>
            <Avatar sx={{ bgcolor: 'primary.main', width: 56, height: 56, mb: 1.5 }}>
              <SchoolIcon fontSize="medium" />
            </Avatar>
            <Typography variant="h5" fontWeight={700} color="#0f172a">
              EduSaaS CRM
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Sign in to your institution portal
            </Typography>
          </Box>

          {/* Quick Demo Credentials Bar */}
          <Paper
            variant="outlined"
            sx={{
              p: 1.5,
              mb: 2.5,
              bgcolor: '#f8fafc',
              borderColor: '#e2e8f0',
              borderRadius: 2,
            }}
          >
            <Box display="flex" alignItems="center" gap={1} mb={1}>
              <KeyIcon fontSize="small" color="primary" />
              <Typography variant="caption" fontWeight={700} color="text.primary">
                1-CLICK DEMO CREDENTIALS
              </Typography>
            </Box>
            <Box display="flex" flexWrap="wrap" gap={0.75}>
              {DEMO_ACCOUNTS.map((acc) => (
                <Chip
                  key={acc.email}
                  label={acc.label}
                  size="small"
                  color={acc.color}
                  variant={identifier === acc.email ? 'filled' : 'outlined'}
                  onClick={() => handleDemoSelect(acc.email)}
                  sx={{ cursor: 'pointer', fontWeight: 600, fontSize: '0.72rem' }}
                />
              ))}
            </Box>
            <Box
              display="flex"
              alignItems="center"
              gap={0.75}
              mt={1.25}
              pt={1}
              borderTop="1px dashed #e2e8f0"
            >
              <SmartphoneIcon sx={{ fontSize: 16, color: 'text.secondary' }} />
              <Typography variant="caption" color="text.secondary" fontWeight={500}>
                Students, Teachers & Parents: Access via <strong>EduSaaS Mobile App</strong>
              </Typography>
            </Box>
          </Paper>

          <Box component="form" onSubmit={handleSubmit} display="flex" flexDirection="column" gap={2}>
            <TextField
              label="Email or Mobile Number"
              fullWidth
              size="medium"
              value={identifier}
              onChange={(e) => setIdentifier(e.target.value)}
              placeholder="e.g. college.admin@apex.edu"
              autoFocus
              required
            />

            <TextField
              label="Password"
              type={showPassword ? 'text' : 'password'}
              fullWidth
              size="medium"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              InputProps={{
                endAdornment: (
                  <InputAdornment position="end">
                    <IconButton onClick={() => setShowPassword((v) => !v)} edge="end" size="small">
                      {showPassword ? <VisibilityOff fontSize="small" /> : <Visibility fontSize="small" />}
                    </IconButton>
                  </InputAdornment>
                ),
              }}
            />

            <Box display="flex" justifyContent="flex-end">
              <Link
                component="button"
                type="button"
                variant="caption"
                onClick={() => navigate('/forgot-password')}
                sx={{ textDecoration: 'none', fontWeight: 600 }}
              >
                Forgot Password?
              </Link>
            </Box>

            <Button
              type="submit"
              variant="contained"
              size="large"
              fullWidth
              disabled={loading}
              sx={{ py: 1.4, fontWeight: 600, fontSize: '0.95rem' }}
            >
              {loading ? <CircularProgress size={24} color="inherit" /> : 'Sign In'}
            </Button>
          </Box>

          <Divider sx={{ my: 3 }} />

          <Box textAlign="center">
            <Typography variant="body2" color="text.secondary">
              Need to register a new school or college?{' '}
              <Link
                component="button"
                variant="body2"
                onClick={() => navigate('/register-institution')}
                sx={{ fontWeight: 600, textDecoration: 'none' }}
              >
                Onboard Institution
              </Link>
            </Typography>
          </Box>
        </CardContent>
      </Card>
    </Box>
  )
}
