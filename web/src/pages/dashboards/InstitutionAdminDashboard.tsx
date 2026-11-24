import {
  Box,
  Card,
  CardContent,
  Grid,
  Typography,
  Chip,
  Button,
  Alert,
  CircularProgress,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
} from '@mui/material'
import SchoolIcon from '@mui/icons-material/School'
import PeopleIcon from '@mui/icons-material/People'
import CheckCircleIcon from '@mui/icons-material/CheckCircle'
import AccountBalanceWalletIcon from '@mui/icons-material/AccountBalanceWallet'
import AssessmentIcon from '@mui/icons-material/Assessment'
import QuizIcon from '@mui/icons-material/Quiz'
import HowToRegIcon from '@mui/icons-material/HowToReg'
import MenuBookIcon from '@mui/icons-material/MenuBook'
import CalendarMonthIcon from '@mui/icons-material/CalendarMonth'
import ArrowForwardIcon from '@mui/icons-material/ArrowForward'
import { useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { reportsApi } from '@/api/reports'
import {
  AreaChart,
  Area,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip as RechartsTooltip,
  ResponsiveContainer,
} from 'recharts'

export default function InstitutionAdminDashboard() {
  const navigate = useNavigate()

  // Real institutional analytics query
  const { data: stats, isLoading, error, refetch } = useQuery({
    queryKey: ['institutionAdminDashboardStats'],
    queryFn: () => reportsApi.getInstitutionAdminAnalytics(),
    refetchInterval: 30000,
  })

  return (
    <Box>
      {/* Header */}
      <Box mb={3} display="flex" justifyContent="space-between" alignItems="center" flexWrap="wrap" gap={2}>
        <Box>
          <Typography variant="h4" fontWeight={700}>
            Institution Overview
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Live academic indicators, daily attendance, fee reconciliation, and administrative operations
          </Typography>
        </Box>
        <Box display="flex" gap={1.5} alignItems="center">
          <Chip label="Portal: Institution Admin" color="primary" sx={{ fontWeight: 600 }} />
          <Button
            variant="outlined"
            size="small"
            startIcon={<AssessmentIcon />}
            onClick={() => navigate('/reports')}
            sx={{ textTransform: 'none' }}
          >
            Detailed Analytics & Reports
          </Button>
        </Box>
      </Box>

      {isLoading && (
        <Box display="flex" justifyContent="center" alignItems="center" minHeight="40vh">
          <CircularProgress />
        </Box>
      )}

      {error && (
        <Alert severity="error" sx={{ mb: 3 }} action={<Button onClick={() => refetch()} size="small">Retry</Button>}>
          Failed to load live institution metrics. Please check network connectivity.
        </Alert>
      )}

      {stats && (
        <>
          {/* Top 4 KPI Cards */}
          <Grid container spacing={3} mb={4}>
            <Grid item xs={12} sm={6} md={3}>
              <Card sx={{ height: '100%', cursor: 'pointer' }} onClick={() => navigate('/students')}>
                <CardContent>
                  <Box display="flex" justifyContent="space-between" alignItems="center" mb={1}>
                    <Box display="flex" alignItems="center" gap={1}>
                      <SchoolIcon color="primary" />
                      <Typography variant="caption" color="text.secondary" fontWeight={600}>
                        TOTAL STUDENTS
                      </Typography>
                    </Box>
                    <ArrowForwardIcon fontSize="small" sx={{ color: 'text.secondary' }} />
                  </Box>
                  <Typography variant="h4" fontWeight={700}>
                    {stats.total_students.toLocaleString()}
                  </Typography>
                  <Typography variant="caption" color="text.secondary">
                    Across {stats.class_distribution.length} Classes / Grades
                  </Typography>
                </CardContent>
              </Card>
            </Grid>

            <Grid item xs={12} sm={6} md={3}>
              <Card sx={{ height: '100%', cursor: 'pointer' }} onClick={() => navigate('/teachers')}>
                <CardContent>
                  <Box display="flex" justifyContent="space-between" alignItems="center" mb={1}>
                    <Box display="flex" alignItems="center" gap={1}>
                      <PeopleIcon color="secondary" />
                      <Typography variant="caption" color="text.secondary" fontWeight={600}>
                        TEACHING FACULTY
                      </Typography>
                    </Box>
                    <ArrowForwardIcon fontSize="small" sx={{ color: 'text.secondary' }} />
                  </Box>
                  <Typography variant="h4" fontWeight={700}>
                    {stats.total_teachers.toLocaleString()}
                  </Typography>
                  <Typography variant="caption" color="success.main" fontWeight={500}>
                    {stats.teacher_performance.active_teachers} Active Instructors
                  </Typography>
                </CardContent>
              </Card>
            </Grid>

            <Grid item xs={12} sm={6} md={3}>
              <Card sx={{ height: '100%', cursor: 'pointer' }} onClick={() => navigate('/attendance')}>
                <CardContent>
                  <Box display="flex" justifyContent="space-between" alignItems="center" mb={1}>
                    <Box display="flex" alignItems="center" gap={1}>
                      <CheckCircleIcon color="success" />
                      <Typography variant="caption" color="text.secondary" fontWeight={600}>
                        TODAY'S ATTENDANCE
                      </Typography>
                    </Box>
                    <ArrowForwardIcon fontSize="small" sx={{ color: 'text.secondary' }} />
                  </Box>
                  <Typography variant="h4" fontWeight={700} color="success.main">
                    {stats.daily_attendance.rate_percentage}%
                  </Typography>
                  <Typography variant="caption" color="text.secondary">
                    {stats.daily_attendance.present} Present · {stats.daily_attendance.absent} Absent
                  </Typography>
                </CardContent>
              </Card>
            </Grid>

            <Grid item xs={12} sm={6} md={3}>
              <Card sx={{ height: '100%', cursor: 'pointer' }} onClick={() => navigate('/fees')}>
                <CardContent>
                  <Box display="flex" justifyContent="space-between" alignItems="center" mb={1}>
                    <Box display="flex" alignItems="center" gap={1}>
                      <AccountBalanceWalletIcon color="warning" />
                      <Typography variant="caption" color="text.secondary" fontWeight={600}>
                        FEE COLLECTION
                      </Typography>
                    </Box>
                    <ArrowForwardIcon fontSize="small" sx={{ color: 'text.secondary' }} />
                  </Box>
                  <Typography variant="h4" fontWeight={700}>
                    ₹{Number(stats.fee_collection.total_collected).toLocaleString('en-IN')}
                  </Typography>
                  <Typography variant="caption" color={Number(stats.pending_fees.total_pending) > 0 ? 'error.main' : 'text.secondary'}>
                    ₹{Number(stats.pending_fees.total_pending).toLocaleString('en-IN')} Outstanding
                  </Typography>
                </CardContent>
              </Card>
            </Grid>
          </Grid>

          {/* Charts Row */}
          <Grid container spacing={3} mb={4}>
            {/* Monthly Attendance Trend AreaChart */}
            <Grid item xs={12} md={7} sx={{ minWidth: 0 }}>
              <Card sx={{ p: { xs: 2, sm: 2.5 }, height: '100%', minWidth: 0, overflow: 'hidden' }}>
                <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
                  <Typography variant="h6" fontWeight={600}>
                    Attendance Progression Trend (%)
                  </Typography>
                  <Chip label="Academic Year" size="small" variant="outlined" />
                </Box>
                <Box height={260} sx={{ width: '100%', minWidth: 0 }}>
                  <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={stats.monthly_attendance}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis dataKey="month" />
                      <YAxis domain={[0, 100]} />
                      <RechartsTooltip />
                      <Area type="monotone" dataKey="rate_percentage" stroke="#16a34a" fill="#bbf7d0" />
                    </AreaChart>
                  </ResponsiveContainer>
                </Box>
              </Card>
            </Grid>

            {/* Students by Class BarChart */}
            <Grid item xs={12} md={5} sx={{ minWidth: 0 }}>
              <Card sx={{ p: { xs: 2, sm: 2.5 }, height: '100%', minWidth: 0, overflow: 'hidden' }}>
                <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
                  <Typography variant="h6" fontWeight={600}>
                    Enrollment by Grade / Class
                  </Typography>
                  <Chip label={`${stats.class_distribution.length} Classes`} size="small" variant="outlined" />
                </Box>
                <Box height={260} sx={{ width: '100%', minWidth: 0 }}>
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={stats.class_distribution}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis dataKey="class_name" />
                      <YAxis />
                      <RechartsTooltip />
                      <Bar dataKey="student_count" fill="#2563eb" radius={[4, 4, 0, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                </Box>
              </Card>
            </Grid>
          </Grid>

          {/* Quick Operations and Module Launchpad */}
          <Typography variant="h6" fontWeight={600} mb={2}>
            Administrative Launchpad & Workflows
          </Typography>
          <Grid container spacing={2} mb={4}>
            {[
              { label: 'Student Directory', path: '/students', icon: <SchoolIcon color="primary" />, desc: 'Rosters, enrollments, admissions & promotions' },
              { label: 'Faculty Roster', path: '/teachers', icon: <PeopleIcon color="secondary" />, desc: 'Teacher profiles, workload & subject assignments' },
              { label: 'Daily Roll Call', path: '/attendance', icon: <HowToRegIcon color="success" />, desc: 'Mark session attendance, bio/RFID & corrections' },
              { label: 'Examinations Engine', path: '/examinations', icon: <QuizIcon color="warning" />, desc: 'Question banks, test schedules & online exams' },
              { label: 'Results & Report Cards', path: '/results', icon: <AssessmentIcon color="info" />, desc: 'Marks entry, grade calculation & PDF report cards' },
              { label: 'LMS & Study Materials', path: '/lms', icon: <MenuBookIcon color="primary" />, desc: 'Curriculum uploads, assignments & student grading' },
              { label: 'Timetable Scheduling', path: '/timetable', icon: <CalendarMonthIcon color="secondary" />, desc: 'Timetables, period allocations & conflict checks' },
              { label: 'Fee Collection & Finance', path: '/fees', icon: <AccountBalanceWalletIcon color="warning" />, desc: 'Invoicing, receipts, Razorpay & defaulters' },
            ].map((mod) => (
              <Grid item xs={12} sm={6} md={3} key={mod.path}>
                <Paper
                  variant="outlined"
                  sx={{
                    p: 2,
                    cursor: 'pointer',
                    height: '100%',
                    transition: 'all 0.2s',
                    '&:hover': {
                      borderColor: 'primary.main',
                      boxShadow: 2,
                      transform: 'translateY(-2px)',
                    },
                  }}
                  onClick={() => navigate(mod.path)}
                >
                  <Box display="flex" alignItems="center" gap={1.5} mb={1}>
                    {mod.icon}
                    <Typography variant="subtitle2" fontWeight={600}>
                      {mod.label}
                    </Typography>
                  </Box>
                  <Typography variant="caption" color="text.secondary">
                    {mod.desc}
                  </Typography>
                </Paper>
              </Grid>
            ))}
          </Grid>

          {/* Bottom Grid: Fee Collection Ledger Preview & Academic Grade Spread */}
          <Grid container spacing={3}>
            <Grid item xs={12} md={6} sx={{ minWidth: 0 }}>
              <Card sx={{ p: { xs: 2, sm: 2.5 }, minWidth: 0 }}>
                <Typography variant="h6" fontWeight={600} mb={2}>
                  Payment Mode Distribution
                </Typography>
                <TableContainer sx={{ overflowX: 'auto', width: '100%' }}>
                  <Table size="small" sx={{ minWidth: 300 }}>
                    <TableHead>
                      <TableRow>
                        <TableCell>Channel</TableCell>
                        <TableCell align="right">Total Inflow (₹)</TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {Object.entries(stats.fee_collection.by_payment_mode).map(([mode, amt]) => (
                        <TableRow key={mode}>
                          <TableCell><Chip label={mode} size="small" variant="outlined" /></TableCell>
                          <TableCell align="right" sx={{ fontWeight: 600 }}>
                            ₹{Number(amt).toLocaleString('en-IN')}
                          </TableCell>
                        </TableRow>
                      ))}
                      {Object.keys(stats.fee_collection.by_payment_mode).length === 0 && (
                        <TableRow>
                          <TableCell colSpan={2} align="center" sx={{ color: 'text.secondary' }}>
                            No fee payments recorded in current session.
                          </TableCell>
                        </TableRow>
                      )}
                    </TableBody>
                  </Table>
                </TableContainer>
              </Card>
            </Grid>

            <Grid item xs={12} md={6} sx={{ minWidth: 0 }}>
              <Card sx={{ p: { xs: 2, sm: 2.5 }, minWidth: 0, overflow: 'hidden' }}>
                <Typography variant="h6" fontWeight={600} mb={2}>
                  Academic Grade Distribution
                </Typography>
                <Box height={220} sx={{ width: '100%', minWidth: 0 }}>
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={stats.academic_trends}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis dataKey="grade_label" />
                      <YAxis />
                      <RechartsTooltip />
                      <Bar dataKey="student_count" fill="#8b5cf6" radius={[4, 4, 0, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                </Box>
              </Card>
            </Grid>
          </Grid>
        </>
      )}
    </Box>
  )
}
