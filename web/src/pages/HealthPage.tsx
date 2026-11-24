import {
  Box, Card, CardContent, Typography, Grid, Chip, CircularProgress, Button,
} from '@mui/material'
import CheckCircleIcon from '@mui/icons-material/CheckCircle'
import ErrorIcon from '@mui/icons-material/Error'
import RefreshIcon from '@mui/icons-material/Refresh'
import { useDetailedHealth } from '@/hooks/useHealth'

function StatusIndicator({ ok }: { ok: boolean }) {
  return ok ? (
    <CheckCircleIcon sx={{ color: 'success.main' }} />
  ) : (
    <ErrorIcon sx={{ color: 'error.main' }} />
  )
}

export default function HealthPage() {
  const { data, isLoading, isError, refetch } = useDetailedHealth()

  return (
    <Box maxWidth={640} mx="auto" mt={4}>
      <Box display="flex" alignItems="center" justifyContent="space-between" mb={3}>
        <Box>
          <Typography variant="h5" fontWeight={700}>System Health</Typography>
          <Typography variant="body2" color="text.secondary">
            Backend API and dependency status
          </Typography>
        </Box>
        <Button variant="outlined" size="small" startIcon={<RefreshIcon />} onClick={() => refetch()}>
          Refresh
        </Button>
      </Box>

      {isLoading && (
        <Box display="flex" justifyContent="center" py={6}>
          <CircularProgress />
        </Box>
      )}

      {isError && (
        <Card>
          <CardContent>
            <Box display="flex" alignItems="center" gap={1.5}>
              <ErrorIcon color="error" />
              <Box>
                <Typography fontWeight={600} color="error">API Unreachable</Typography>
                <Typography variant="body2" color="text.secondary">
                  Could not connect to the backend. Make sure it is running on port 8000.
                </Typography>
              </Box>
            </Box>
          </CardContent>
        </Card>
      )}

      {data && (
        <Grid container spacing={2}>
          <Grid item xs={12}>
            <Card>
              <CardContent>
                <Box display="flex" alignItems="center" justifyContent="space-between">
                  <Box display="flex" alignItems="center" gap={1.5}>
                    <StatusIndicator ok={data.status === 'healthy'} />
                    <Box>
                      <Typography fontWeight={600}>Backend API</Typography>
                      <Typography variant="body2" color="text.secondary">
                        v{data.version} &middot; {data.environment}
                      </Typography>
                    </Box>
                  </Box>
                  <Chip
                    label={data.status}
                    color={data.status === 'healthy' ? 'success' : 'warning'}
                    size="small"
                  />
                </Box>
              </CardContent>
            </Card>
          </Grid>

          {data.dependencies &&
            Object.entries(data.dependencies).map(([name, status]) => (
              <Grid item xs={12} sm={6} key={name}>
                <Card>
                  <CardContent>
                    <Box display="flex" alignItems="center" justifyContent="space-between">
                      <Box display="flex" alignItems="center" gap={1.5}>
                        <StatusIndicator ok={status === 'ok'} />
                        <Typography fontWeight={500} sx={{ textTransform: 'capitalize' }}>
                          {name}
                        </Typography>
                      </Box>
                      <Chip
                        label={status}
                        color={status === 'ok' ? 'success' : 'error'}
                        size="small"
                      />
                    </Box>
                  </CardContent>
                </Card>
              </Grid>
            ))}

          <Grid item xs={12}>
            <Typography variant="caption" color="text.disabled">
              Last checked: {new Date(data.timestamp).toLocaleString()}
            </Typography>
          </Grid>
        </Grid>
      )}
    </Box>
  )
}
