import { Box, Typography, Button, Card, CardContent } from '@mui/material'
import ShieldAlertIcon from '@mui/icons-material/Security'
import { useNavigate } from 'react-router-dom'
import { useAuthStore } from '@/store/authStore'

export default function UnauthorizedPage() {
  const navigate = useNavigate()
  const { user } = useAuthStore()

  return (
    <Box
      minHeight="100vh"
      display="flex"
      alignItems="center"
      justifyContent="center"
      bgcolor="#f8fafc"
      p={3}
    >
      <Card sx={{ maxWidth: 480, textAlign: 'center', p: 4, borderRadius: 3 }}>
        <CardContent>
          <ShieldAlertIcon sx={{ fontSize: 64, color: 'error.main', mb: 2 }} />
          <Typography variant="h4" fontWeight={700} gutterBottom>
            Access Denied
          </Typography>
          <Typography variant="body1" color="text.secondary" mb={3}>
            You do not have permission to view or manage this institutional module.
            Your current assigned role is <strong>{user?.current_role || 'Guest'}</strong>.
          </Typography>
          <Box display="flex" gap={2} justifyContent="center">
            <Button variant="outlined" onClick={() => navigate(-1)}>
              Go Back
            </Button>
            <Button variant="contained" onClick={() => navigate('/dashboard')}>
              Return to Dashboard
            </Button>
          </Box>
        </CardContent>
      </Card>
    </Box>
  )
}
