import {
  Box,
  Card,
  CardContent,
  Grid,
  Typography,
  Chip,
  CircularProgress,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Button,
} from '@mui/material'
import BusinessIcon from '@mui/icons-material/Business'
import PaidIcon from '@mui/icons-material/Paid'
import PeopleIcon from '@mui/icons-material/People'
import CheckCircleIcon from '@mui/icons-material/CheckCircle'
import WarningIcon from '@mui/icons-material/Warning'
import HourglassEmptyIcon from '@mui/icons-material/HourglassEmpty'
import BlockIcon from '@mui/icons-material/Block'
import RefreshIcon from '@mui/icons-material/Refresh'
import { useQuery } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import {
  AreaChart,
  Area,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts'
import { superAdminApi } from '@/api/superAdmin'

const formatCurrencyTick = (v: number) => {
  if (v <= 0) return '₹0'
  if (v >= 10000000) return `₹${(v / 10000000).toFixed(1)}Cr`
  if (v >= 100000) return `₹${(v / 100000).toFixed(1)}L`
  if (v >= 1000) return `₹${Math.round(v / 1000)}k`
  return `₹${v}`
}

export default function SuperAdminDashboard() {
  const navigate = useNavigate()

  const { data: stats, isLoading, error, refetch } = useQuery({
    queryKey: ['superAdminStats'],
    queryFn: superAdminApi.getStats,
    refetchInterval: 30000,
  })

  if (isLoading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="50vh">
        <CircularProgress />
      </Box>
    )
  }

  if (error || !stats) {
    return (
      <Box p={3}>
        <Typography color="error">Failed to load platform statistics.</Typography>
        <Button onClick={() => refetch()} sx={{ mt: 1 }} variant="outlined">
          Retry
        </Button>
      </Box>
    )
  }

  const kpis = [
    {
      title: 'Total Institutions',
      value: stats.total_institutions,
      subtitle: `${stats.active_institutions} active · ${stats.pending_institutions} pending`,
      icon: <BusinessIcon sx={{ color: 'primary.main', fontSize: 28 }} />,
      color: '#3b82f6',
    },
    {
      title: 'Monthly Recurring Revenue',
      value: `₹${stats.mrr.toLocaleString('en-IN')}`,
      subtitle: `ARR: ₹${stats.arr.toLocaleString('en-IN')}`,
      icon: <PaidIcon sx={{ color: 'success.main', fontSize: 28 }} />,
      color: '#10b981',
    },
    {
      title: 'Total Enrolled Users',
      value: stats.total_students + stats.total_teachers,
      subtitle: `${stats.total_students} students · ${stats.total_teachers} teachers`,
      icon: <PeopleIcon sx={{ color: 'info.main', fontSize: 28 }} />,
      color: '#06b6d4',
    },
    {
      title: 'Pending Approvals',
      value: stats.pending_institutions,
      subtitle: `${stats.suspended_institutions} suspended institutions`,
      icon: <HourglassEmptyIcon sx={{ color: 'warning.main', fontSize: 28 }} />,
      color: '#f59e0b',
    },
  ]

  const subKpis = [
    { label: 'Active Subscriptions', count: stats.total_subscriptions, icon: <CheckCircleIcon color="success" /> },
    { label: 'Upcoming Renewals (30d)', count: stats.subscription_renewals, icon: <RefreshIcon color="info" /> },
    { label: 'Expired Subscriptions', count: stats.expired_subscriptions, icon: <WarningIcon color="warning" /> },
    { label: 'Payment Failures', count: stats.payment_failures, icon: <BlockIcon color="error" /> },
  ]

  return (
    <Box>
      <Box mb={4} display="flex" justifyContent="space-between" alignItems="center" flexWrap="wrap" gap={2}>
        <Box>
          <Typography variant="h4" fontWeight={700}>
            Platform Control Center
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Global metrics across all registered schools and colleges
          </Typography>
        </Box>
        <Box display="flex" alignItems="center" gap={1.5}>
          <Chip label="System Active" color="success" size="small" variant="outlined" sx={{ fontWeight: 600 }} />
          <Button variant="outlined" size="small" onClick={() => refetch()} startIcon={<RefreshIcon />}>
            Refresh
          </Button>
        </Box>
      </Box>

      {/* Main KPI Cards */}
      <Grid container spacing={3} mb={3}>
        {kpis.map((kpi) => (
          <Grid item xs={12} sm={6} md={3} key={kpi.title}>
            <Card sx={{ borderLeft: `4px solid ${kpi.color}`, height: '100%' }}>
              <CardContent>
                <Box display="flex" justifyContent="space-between" alignItems="center" mb={1}>
                  <Typography variant="body2" color="text.secondary" fontWeight={500}>
                    {kpi.title}
                  </Typography>
                  {kpi.icon}
                </Box>
                <Typography variant="h4" fontWeight={700} mb={0.5}>
                  {kpi.value}
                </Typography>
                <Typography variant="caption" color="text.secondary">
                  {kpi.subtitle}
                </Typography>
              </CardContent>
            </Card>
          </Grid>
        ))}
      </Grid>

      {/* Subscription & Billing Secondary Cards */}
      <Grid container spacing={2} mb={4}>
        {subKpis.map((item) => (
          <Grid item xs={12} sm={6} md={3} key={item.label}>
            <Paper variant="outlined" sx={{ p: 2, display: 'flex', alignItems: 'center', gap: 1.5, borderRadius: 2 }}>
              {item.icon}
              <Box>
                <Typography variant="caption" color="text.secondary" display="block">
                  {item.label}
                </Typography>
                <Typography variant="h6" fontWeight={700}>
                  {item.count}
                </Typography>
              </Box>
            </Paper>
          </Grid>
        ))}
      </Grid>

      {/* Analytics Charts */}
      <Grid container spacing={3} mb={4}>
        <Grid item xs={12} md={7} sx={{ minWidth: 0 }}>
          <Card sx={{ minWidth: 0, overflow: 'hidden' }}>
            <CardContent sx={{ p: { xs: 2, sm: 2.5 } }}>
              <Typography variant="h6" fontWeight={600} mb={0.5}>
                Platform Revenue Trend (INR)
              </Typography>
              <Typography variant="caption" color="text.secondary" mb={2} display="block">
                Monthly revenue across institutional subscriptions
              </Typography>
              <Box height={280} sx={{ width: '100%', minWidth: 0 }}>
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={stats.revenue_trend} margin={{ top: 10, right: 20, left: 10, bottom: 25 }}>
                    <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e2e8f0" />
                    <XAxis dataKey="month" stroke="#64748b" fontSize={12} tickLine={false} dy={6} />
                    <YAxis
                      stroke="#64748b"
                      fontSize={12}
                      domain={[0, (dataMax: number) => (dataMax > 0 ? Math.ceil(dataMax * 1.2) : 10000)]}
                      allowDecimals={false}
                      tickFormatter={formatCurrencyTick}
                    />
                    <Tooltip formatter={(value: number) => [`₹${value.toLocaleString('en-IN')}`, 'Revenue']} />
                    <Area type="monotone" dataKey="revenue" stroke="#10b981" fill="#d1fae5" strokeWidth={2} />
                  </AreaChart>
                </ResponsiveContainer>
              </Box>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} md={5} sx={{ minWidth: 0 }}>
          <Card sx={{ minWidth: 0, overflow: 'hidden' }}>
            <CardContent sx={{ p: { xs: 2, sm: 2.5 } }}>
              <Typography variant="h6" fontWeight={600} mb={0.5}>
                Institutional Growth
              </Typography>
              <Typography variant="caption" color="text.secondary" mb={2} display="block">
                Cumulative onboarded educational institutions
              </Typography>
              <Box height={280} sx={{ width: '100%', minWidth: 0 }}>
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={stats.institution_growth} margin={{ top: 10, right: 20, left: 0, bottom: 25 }}>
                    <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e2e8f0" />
                    <XAxis dataKey="month" stroke="#64748b" fontSize={12} tickLine={false} dy={6} />
                    <YAxis stroke="#64748b" fontSize={12} allowDecimals={false} domain={[0, (dataMax: number) => Math.max(dataMax + 1, 5)]} />
                    <Tooltip formatter={(value: number) => [value, 'Institutions']} />
                    <Bar dataKey="count" fill="#3b82f6" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </Box>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Recent Registrations Table */}
      <Grid container spacing={3}>
        <Grid item xs={12}>
          <Card>
            <CardContent>
              <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
                <Typography variant="h6" fontWeight={600}>
                  Recent Institution Registrations
                </Typography>
                <Button size="small" onClick={() => navigate('/super-admin/institutions')}>
                  View All
                </Button>
              </Box>
              <TableContainer component={Paper} elevation={0} variant="outlined">
                <Table size="small">
                  <TableHead sx={{ bgcolor: 'grey.50' }}>
                    <TableRow>
                      <TableCell>Institution</TableCell>
                      <TableCell>Type</TableCell>
                      <TableCell>Status</TableCell>
                      <TableCell>Registered</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {stats.recent_institutions.map((inst) => (
                      <TableRow key={inst.id} hover sx={{ cursor: 'pointer' }} onClick={() => navigate('/super-admin/institutions')}>
                        <TableCell>
                          <Typography variant="body2" fontWeight={600}>
                            {inst.name}
                          </Typography>
                          <Typography variant="caption" color="text.secondary">
                            {inst.slug}
                          </Typography>
                        </TableCell>
                        <TableCell>
                          <Chip label={inst.institution_type} size="small" variant="outlined" />
                        </TableCell>
                        <TableCell>
                          <Chip
                            label={inst.status}
                            size="small"
                            color={
                              inst.status === 'ACTIVE'
                                ? 'success'
                                : inst.status === 'PENDING'
                                ? 'warning'
                                : inst.status === 'SUSPENDED'
                                ? 'error'
                                : 'default'
                            }
                          />
                        </TableCell>
                        <TableCell>
                          <Typography variant="caption" color="text.secondary">
                            {new Date(inst.created_at).toLocaleDateString()}
                          </Typography>
                        </TableCell>
                      </TableRow>
                    ))}
                    {stats.recent_institutions.length === 0 && (
                      <TableRow>
                        <TableCell colSpan={4} align="center">
                          <Typography variant="body2" color="text.secondary" py={2}>
                            No institutions registered yet.
                          </Typography>
                        </TableCell>
                      </TableRow>
                    )}
                  </TableBody>
                </Table>
              </TableContainer>
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Box>
  )
}
