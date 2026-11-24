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
  ToggleButton,
  ToggleButtonGroup,
  Avatar,
  Divider,
} from '@mui/material'
import SchoolIcon from '@mui/icons-material/School'
import AccountBalanceIcon from '@mui/icons-material/AccountBalance'
import { useNavigate } from 'react-router-dom'
import { useSnackbar } from 'notistack'
import { registerUser } from '@/api/auth'
import { useAuthStore } from '@/store/authStore'

export default function RegisterPage() {
  const [fullName, setFullName] = useState('')
  const [email, setEmail] = useState('')
  const [phone, setPhone] = useState('')
  const [password, setPassword] = useState('')
  const [institutionName, setInstitutionName] = useState('')
  const [institutionType, setInstitutionType] = useState<'SCHOOL' | 'COLLEGE'>('SCHOOL')
  const [loading, setLoading] = useState(false)

  const navigate = useNavigate()
  const { enqueueSnackbar } = useSnackbar()
  const setAuth = useAuthStore((s) => s.setAuth)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!email || !password || !fullName || !institutionName) {
      enqueueSnackbar('Please fill in all required fields', { variant: 'warning' })
      return
    }

    try {
      setLoading(true)
      const data = await registerUser({
        full_name: fullName,
        email,
        phone,
        password,
        institution_name: institutionName,
        institution_type: institutionType,
      })
      setAuth(data)
      enqueueSnackbar('Institution registered successfully! Welcome aboard.', { variant: 'success' })
      navigate('/dashboard')
    } catch (err: any) {
      enqueueSnackbar(err.message || 'Registration failed', { variant: 'error' })
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
      py={6}
      px={2}
    >
      <Card sx={{ maxWidth: 500, width: '100%', p: { xs: 2, sm: 3 }, borderRadius: 3, boxShadow: '0 4px 20px rgba(0,0,0,0.08)' }}>
        <CardContent>
          <Box display="flex" flexDirection="column" alignItems="center" mb={3}>
            <Avatar sx={{ bgcolor: 'primary.main', width: 52, height: 52, mb: 1.5 }}>
              <SchoolIcon fontSize="medium" />
            </Avatar>
            <Typography variant="h5" fontWeight={700} color="#0f172a">
              Register Institution
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Set up your Multi-Tenant School or College SaaS Portal
            </Typography>
          </Box>

          <Box component="form" onSubmit={handleSubmit} display="flex" flexDirection="column" gap={2}>
            {/* Institution Type Switcher */}
            <Box display="flex" flexDirection="column" gap={0.5}>
              <Typography variant="caption" fontWeight={600} color="text.secondary">
                INSTITUTION TYPE
              </Typography>
              <ToggleButtonGroup
                value={institutionType}
                exclusive
                onChange={(_, val) => val && setInstitutionType(val)}
                fullWidth
                size="small"
              >
                <ToggleButton value="SCHOOL" sx={{ py: 1, gap: 1 }}>
                  <SchoolIcon fontSize="small" /> School
                </ToggleButton>
                <ToggleButton value="COLLEGE" sx={{ py: 1, gap: 1 }}>
                  <AccountBalanceIcon fontSize="small" /> College / University
                </ToggleButton>
              </ToggleButtonGroup>
            </Box>

            <TextField
              label="Institution Name"
              fullWidth
              size="small"
              value={institutionName}
              onChange={(e) => setInstitutionName(e.target.value)}
              placeholder="e.g. St. Jude Academy or Greenfield College"
              required
            />

            <TextField
              label="Administrator Full Name"
              fullWidth
              size="small"
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
              placeholder="e.g. Dr. Arthur Pendelton"
              required
            />

            <TextField
              label="Official Email"
              type="email"
              fullWidth
              size="small"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="admin@institution.edu"
              required
            />

            <TextField
              label="Mobile Phone"
              fullWidth
              size="small"
              value={phone}
              onChange={(e) => setPhone(e.target.value)}
              placeholder="+919876543210"
            />

            <TextField
              label="Password"
              type="password"
              fullWidth
              size="small"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              helperText="Minimum 8 characters with letters and numbers"
              required
            />

            <Button
              type="submit"
              variant="contained"
              size="large"
              fullWidth
              disabled={loading}
              sx={{ mt: 1, py: 1.4, fontWeight: 600 }}
            >
              {loading ? <CircularProgress size={24} color="inherit" /> : 'Launch Institution'}
            </Button>
          </Box>

          <Divider sx={{ my: 3 }} />

          <Box textAlign="center">
            <Typography variant="body2" color="text.secondary">
              Already have an account?{' '}
              <Link
                component="button"
                variant="body2"
                onClick={() => navigate('/login')}
                sx={{ fontWeight: 600, textDecoration: 'none' }}
              >
                Sign In
              </Link>
            </Typography>
          </Box>
        </CardContent>
      </Card>
    </Box>
  )
}
