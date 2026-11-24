import {
  Box,
  Card,
  CardContent,
  Typography,
  Grid,
  Chip,
  Button,
  Avatar,
} from '@mui/material'
import SchoolIcon from '@mui/icons-material/School'
import AccountBalanceIcon from '@mui/icons-material/AccountBalance'
import ArrowForwardIcon from '@mui/icons-material/ArrowForward'
import { useNavigate } from 'react-router-dom'
import { useSnackbar } from 'notistack'
import { useAuthStore } from '@/store/authStore'

export default function InstitutionSelectPage() {
  const { user, switchInstitution } = useAuthStore()
  const navigate = useNavigate()
  const { enqueueSnackbar } = useSnackbar()

  const handleSelect = async (tenantId: string, name: string) => {
    try {
      await switchInstitution(tenantId)
      enqueueSnackbar(`Switched to ${name}`, { variant: 'success' })
      navigate('/dashboard')
    } catch (err: any) {
      enqueueSnackbar(err.message || 'Failed to switch institution', { variant: 'error' })
    }
  }

  return (
    <Box
      minHeight="100vh"
      display="flex"
      flexDirection="column"
      alignItems="center"
      justifyContent="center"
      bgcolor="#f8fafc"
      px={2}
      py={6}
    >
      <Box maxWidth={720} width="100%">
        <Box textAlign="center" mb={4}>
          <Typography variant="h4" fontWeight={700} color="#0f172a" gutterBottom>
            Select Institution
          </Typography>
          <Typography variant="body1" color="text.secondary">
            You hold active memberships in multiple institutions. Choose an institution to continue.
          </Typography>
        </Box>

        <Grid container spacing={3}>
          {user?.institutions.map((inst) => {
            const isSchool = inst.institution_type === 'SCHOOL'
            const isSelected = inst.tenant_id === user.current_tenant_id

            return (
              <Grid item xs={12} sm={6} key={inst.tenant_id}>
                <Card
                  sx={{
                    height: '100%',
                    display: 'flex',
                    flexDirection: 'column',
                    justifyContent: 'space-between',
                    border: isSelected ? '2px solid #2563eb' : '1px solid #e2e8f0',
                    transition: 'all 0.2s ease',
                    '&:hover': {
                      transform: 'translateY(-2px)',
                      boxShadow: '0 8px 24px rgba(0,0,0,0.08)',
                    },
                  }}
                >
                  <CardContent sx={{ p: 3 }}>
                    <Box display="flex" alignItems="center" gap={1.5} mb={2}>
                      <Avatar sx={{ bgcolor: isSchool ? 'primary.main' : 'secondary.main', width: 44, height: 44 }}>
                        {isSchool ? <SchoolIcon /> : <AccountBalanceIcon />}
                      </Avatar>
                      <Box>
                        <Typography variant="h6" fontWeight={600} lineHeight={1.2}>
                          {inst.institution_name}
                        </Typography>
                        <Typography variant="caption" color="text.secondary">
                          {inst.institution_type}
                        </Typography>
                      </Box>
                    </Box>

                    <Box display="flex" alignItems="center" gap={1} mb={3}>
                      <Chip
                        label={`Role: ${inst.role_name}`}
                        size="small"
                        color="primary"
                        variant="outlined"
                        sx={{ fontWeight: 600 }}
                      />
                      <Chip
                        label={inst.status}
                        size="small"
                        color="success"
                        sx={{ fontWeight: 500 }}
                      />
                    </Box>

                    <Button
                      variant={isSelected ? 'contained' : 'outlined'}
                      fullWidth
                      endIcon={<ArrowForwardIcon />}
                      onClick={() => handleSelect(inst.tenant_id, inst.institution_name)}
                    >
                      {isSelected ? 'Active Context' : 'Enter Portal'}
                    </Button>
                  </CardContent>
                </Card>
              </Grid>
            )
          })}
        </Grid>
      </Box>
    </Box>
  )
}
