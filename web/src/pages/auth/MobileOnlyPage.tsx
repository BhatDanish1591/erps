import { Box, Typography, Button, Card, CardContent, Chip, Stack } from '@mui/material'
import SmartphoneIcon from '@mui/icons-material/Smartphone'
import QrCode2Icon from '@mui/icons-material/QrCode2'
import LogoutIcon from '@mui/icons-material/Logout'
import { useNavigate } from 'react-router-dom'
import { useAuthStore } from '@/store/authStore'

export default function MobileOnlyPage() {
  const navigate = useNavigate()
  const { user, clearAuth } = useAuthStore()

  const handleSignOut = () => {
    clearAuth()
    navigate('/login', { replace: true })
  }

  const roleName = user?.current_role?.replace('_', ' ') || 'Student / Parent / Faculty'

  return (
    <Box
      minHeight="100vh"
      display="flex"
      alignItems="center"
      justifyContent="center"
      bgcolor="#f8fafc"
      p={3}
    >
      <Card
        sx={{
          maxWidth: 540,
          width: '100%',
          textAlign: 'center',
          p: { xs: 2.5, sm: 4 },
          borderRadius: 4,
          boxShadow: '0 8px 30px rgba(15,23,42,0.08)',
          border: '1px solid #e2e8f0',
        }}
      >
        <CardContent>
          <Box
            sx={{
              width: 80,
              height: 80,
              borderRadius: '24px',
              bgcolor: '#eff6ff',
              color: '#2563eb',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              mx: 'auto',
              mb: 2.5,
              boxShadow: '0 4px 14px rgba(37,99,235,0.15)',
            }}
          >
            <SmartphoneIcon sx={{ fontSize: 44 }} />
          </Box>

          <Chip
            label={`${roleName} Account Detected`}
            color="primary"
            variant="outlined"
            size="small"
            sx={{ fontWeight: 700, mb: 1.5, fontSize: '0.75rem' }}
          />

          <Typography variant="h4" fontWeight={800} color="#0f172a" gutterBottom>
            Mobile App Access Only
          </Typography>

          <Typography variant="body1" color="text.secondary" mb={3} lineHeight={1.6}>
            Student, Teacher, and Parent portals are exclusively supported on the{' '}
            <strong>EduSaaS Mobile Application</strong> for iOS and Android. The web portal is reserved for School and College Administrators.
          </Typography>

          {/* Feature Highlights Grid */}
          <Stack spacing={1.5} mb={3.5} sx={{ textAlign: 'left' }}>
            <Box sx={{ p: 1.5, borderRadius: 2, bgcolor: '#f1f5f9', display: 'flex', alignItems: 'center', gap: 1.5 }}>
              <Typography variant="body2" sx={{ fontSize: '1.25rem' }}>🎓</Typography>
              <Box>
                <Typography variant="subtitle2" fontWeight={700} color="#0f172a">
                  Students
                </Typography>
                <Typography variant="caption" color="text.secondary">
                  Live attendance, course materials, assignments, exam halls & report cards
                </Typography>
              </Box>
            </Box>

            <Box sx={{ p: 1.5, borderRadius: 2, bgcolor: '#f1f5f9', display: 'flex', alignItems: 'center', gap: 1.5 }}>
              <Typography variant="body2" sx={{ fontSize: '1.25rem' }}>👨‍🏫</Typography>
              <Box>
                <Typography variant="subtitle2" fontWeight={700} color="#0f172a">
                  Faculty & Teachers
                </Typography>
                <Typography variant="caption" color="text.secondary">
                  Offline roll call, cohort attendance sync, exams, and assignment evaluations
                </Typography>
              </Box>
            </Box>

            <Box sx={{ p: 1.5, borderRadius: 2, bgcolor: '#f1f5f9', display: 'flex', alignItems: 'center', gap: 1.5 }}>
              <Typography variant="body2" sx={{ fontSize: '1.25rem' }}>👨‍👩‍👦</Typography>
              <Box>
                <Typography variant="subtitle2" fontWeight={700} color="#0f172a">
                  Parents & Guardians
                </Typography>
                <Typography variant="caption" color="text.secondary">
                  Real-time absence notifications, academic progress, and instant online fee payment
                </Typography>
              </Box>
            </Box>
          </Stack>

          {/* Download & QR Action Box */}
          <Box
            sx={{
              p: 2,
              mb: 3,
              borderRadius: 2.5,
              bgcolor: '#0f172a',
              color: '#ffffff',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
            }}
          >
            <Box sx={{ textAlign: 'left' }}>
              <Typography variant="subtitle2" fontWeight={700} color="#ffffff">
                Open in Expo Go / Mobile
              </Typography>
              <Typography variant="caption" color="#94a3b8">
                Available for iPhone & Android devices
              </Typography>
            </Box>
            <QrCode2Icon sx={{ fontSize: 36, color: '#38bdf8' }} />
          </Box>

          <Button
            variant="contained"
            color="primary"
            fullWidth
            size="large"
            onClick={handleSignOut}
            startIcon={<LogoutIcon />}
            sx={{ py: 1.3, fontWeight: 700, borderRadius: 2 }}
          >
            Sign Out & Return to Admin Login
          </Button>
        </CardContent>
      </Card>
    </Box>
  )
}
