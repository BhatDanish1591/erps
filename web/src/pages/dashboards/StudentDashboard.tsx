import {
  Box,
  Card,
  CardContent,
  Grid,
  Typography,
  Chip,
  LinearProgress,
  CircularProgress,
  Button,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Alert,
} from '@mui/material'
import MenuBookIcon from '@mui/icons-material/MenuBook'
import EventNoteIcon from '@mui/icons-material/EventNote'
import AssignmentIcon from '@mui/icons-material/Assignment'
import AccountBalanceWalletIcon from '@mui/icons-material/AccountBalanceWallet'
import LocalLibraryIcon from '@mui/icons-material/LocalLibrary'
import TrendingUpIcon from '@mui/icons-material/TrendingUp'
import AssessmentIcon from '@mui/icons-material/Assessment'
import CalendarMonthIcon from '@mui/icons-material/CalendarMonth'
import { useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { reportsApi } from '@/api/reports'
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip as RechartsTooltip,
  ResponsiveContainer,
} from 'recharts'

export default function StudentDashboard() {
  const navigate = useNavigate()

  const { data: student, isLoading, error, refetch } = useQuery({
    queryKey: ['studentDashboardData'],
    queryFn: () => reportsApi.getStudentAnalytics(),
    refetchInterval: 30000,
  })

  if (isLoading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="50vh">
        <CircularProgress />
      </Box>
    )
  }

  if (error || !student) {
    return (
      <Box p={3}>
        <Alert severity="warning" sx={{ mb: 2 }}>
          Unable to locate a student profile associated with your user account in this institution.
        </Alert>
        <Button variant="outlined" onClick={() => refetch()}>
          Retry
        </Button>
      </Box>
    )
  }

  const attRate = student.attendance_percentage
  const isEligible = attRate >= 75.0

  return (
    <Box>
      {/* Student Banner */}
      <Box mb={4} display="flex" justifyContent="space-between" alignItems="center" flexWrap="wrap" gap={2}>
        <Box>
          <Box display="flex" alignItems="center" gap={1.5}>
            <Typography variant="h4" fontWeight={700}>
              Welcome, {student.student_name}
            </Typography>
            <Chip label="Student Portal" color="primary" sx={{ fontWeight: 600 }} />
          </Box>
          <Typography variant="body2" color="text.secondary">
            Admission No: <strong>{student.admission_number || 'Enrolled'}</strong> · Academic overview, assignments & results
          </Typography>
        </Box>

        <Box display="flex" gap={1}>
          <Button
            variant="outlined"
            size="small"
            startIcon={<AssessmentIcon />}
            onClick={() => navigate('/results')}
            sx={{ textTransform: 'none' }}
          >
            My Report Card
          </Button>
          <Button
            variant="contained"
            size="small"
            startIcon={<MenuBookIcon />}
            onClick={() => navigate('/lms')}
            sx={{ textTransform: 'none' }}
          >
            Study Materials
          </Button>
        </Box>
      </Box>

      {/* Top 4 Metric Cards */}
      <Grid container spacing={3} mb={4}>
        {/* Attendance Rate */}
        <Grid item xs={12} sm={6} md={3}>
          <Card sx={{ height: '100%', cursor: 'pointer' }} onClick={() => navigate('/attendance')}>
            <CardContent>
              <Box display="flex" justifyContent="space-between" alignItems="center" mb={1}>
                <Typography variant="caption" color="text.secondary" fontWeight={600}>
                  ATTENDANCE RATE
                </Typography>
                <Chip
                  label={isEligible ? 'Eligible' : 'Low Attendance'}
                  size="small"
                  color={isEligible ? 'success' : 'error'}
                />
              </Box>
              <Typography variant="h4" fontWeight={700} color={isEligible ? 'success.main' : 'error.main'}>
                {attRate}%
              </Typography>
              <LinearProgress
                variant="determinate"
                value={Math.min(attRate, 100)}
                color={isEligible ? 'success' : 'error'}
                sx={{ height: 8, borderRadius: 4, my: 1 }}
              />
              <Typography variant="caption" color="text.secondary">
                {student.attendance_breakdown.present} Present of {student.attendance_breakdown.total_sessions} Sessions
              </Typography>
            </CardContent>
          </Card>
        </Grid>

        {/* Enrolled Subjects */}
        <Grid item xs={12} sm={6} md={3}>
          <Card sx={{ height: '100%' }}>
            <CardContent>
              <Box display="flex" alignItems="center" gap={1.5} mb={1}>
                <MenuBookIcon color="primary" />
                <Typography variant="caption" color="text.secondary" fontWeight={600}>
                  ENROLLED SUBJECTS
                </Typography>
              </Box>
              <Typography variant="h4" fontWeight={700}>
                {student.subject_marks.length} Subjects
              </Typography>
              <Typography variant="caption" color="text.secondary">
                Curriculum syllabus active
              </Typography>
            </CardContent>
          </Card>
        </Grid>

        {/* Assignment Completion */}
        <Grid item xs={12} sm={6} md={3}>
          <Card sx={{ height: '100%', cursor: 'pointer' }} onClick={() => navigate('/lms')}>
            <CardContent>
              <Box display="flex" alignItems="center" gap={1.5} mb={1}>
                <AssignmentIcon color="warning" />
                <Typography variant="caption" color="text.secondary" fontWeight={600}>
                  ASSIGNMENT COMPLETION
                </Typography>
              </Box>
              <Typography variant="h4" fontWeight={700}>
                {student.assignment_completion.completion_rate}%
              </Typography>
              <Typography variant="caption" color="text.secondary">
                {student.assignment_completion.total_submitted} Submitted / {student.assignment_completion.total_assigned} Assigned
              </Typography>
            </CardContent>
          </Card>
        </Grid>

        {/* Examinations Taken */}
        <Grid item xs={12} sm={6} md={3}>
          <Card sx={{ height: '100%', cursor: 'pointer' }} onClick={() => navigate('/examinations')}>
            <CardContent>
              <Box display="flex" alignItems="center" gap={1.5} mb={1}>
                <EventNoteIcon color="info" />
                <Typography variant="caption" color="text.secondary" fontWeight={600}>
                  ASSESSMENTS TAKEN
                </Typography>
              </Box>
              <Typography variant="h4" fontWeight={700}>
                {student.examination_history.length} Exams
              </Typography>
              <Typography variant="caption" color="text.secondary">
                Evaluated test attempts
              </Typography>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Progress Chart & Subject Marks */}
      <Grid container spacing={3} mb={4}>
        {/* Academic Progress Trend */}
        <Grid item xs={12} md={7} sx={{ minWidth: 0 }}>
          <Card sx={{ p: 2.5, height: '100%', minWidth: 0, overflow: 'hidden' }}>
            <Box display="flex" justifyContent="space-between" alignItems="center" mb={2} flexWrap="wrap" gap={1}>
              <Box display="flex" alignItems="center" gap={1}>
                <TrendingUpIcon color="primary" />
                <Typography variant="h6" fontWeight={600}>
                  Academic Score Progression (%)
                </Typography>
              </Box>
              <Chip label="Recent Assessments" size="small" variant="outlined" />
            </Box>
            <Box height={260} sx={{ width: '100%', minWidth: 0 }}>
              {student.academic_progress_trend.length > 0 ? (
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={student.academic_progress_trend}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="label" />
                    <YAxis domain={[0, 100]} />
                    <RechartsTooltip />
                    <Area type="monotone" dataKey="percentage" stroke="#2563eb" fill="#93c5fd" />
                  </AreaChart>
                </ResponsiveContainer>
              ) : (
                <Box display="flex" justifyContent="center" alignItems="center" height="100%" color="text.secondary">
                  Assessment results will appear here as terms complete.
                </Box>
              )}
            </Box>
          </Card>
        </Grid>

        {/* Subject-Wise Marks & Grade Table */}
        <Grid item xs={12} md={5} sx={{ minWidth: 0 }}>
          <Card sx={{ p: 2.5, height: '100%', minWidth: 0, overflow: 'hidden' }}>
            <Typography variant="h6" fontWeight={600} mb={2}>
              Subject Performance Ledger
            </Typography>
            <TableContainer sx={{ overflowX: 'auto', width: '100%' }}>
              <Table size="small" sx={{ minWidth: 320 }}>
                <TableHead>
                  <TableRow>
                    <TableCell>Subject</TableCell>
                    <TableCell align="right">Score</TableCell>
                    <TableCell align="right">Grade</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {student.subject_marks.map((sm, idx) => (
                    <TableRow key={idx}>
                      <TableCell sx={{ fontWeight: 500 }}>{sm.subject_name}</TableCell>
                      <TableCell align="right">
                        {sm.marks_obtained} / {sm.max_marks}
                      </TableCell>
                      <TableCell align="right">
                        <Chip
                          label={sm.grade || 'PASS'}
                          size="small"
                          color={sm.percentage >= 75 ? 'success' : sm.percentage >= 40 ? 'primary' : 'error'}
                          variant="outlined"
                        />
                      </TableCell>
                    </TableRow>
                  ))}
                  {student.subject_marks.length === 0 && (
                    <TableRow>
                      <TableCell colSpan={3} align="center" sx={{ color: 'text.secondary', py: 3 }}>
                        No published subject results found yet.
                      </TableCell>
                    </TableRow>
                  )}
                </TableBody>
              </Table>
            </TableContainer>
          </Card>
        </Grid>
      </Grid>

      {/* Student Quick Action Navigation Bar */}
      <Typography variant="h6" fontWeight={600} mb={2}>
        Student Quick Services
      </Typography>
      <Grid container spacing={2}>
        {[
          { label: 'Class Timetable', path: '/timetable', icon: <CalendarMonthIcon color="primary" />, desc: 'Weekly schedule & classroom allocations' },
          { label: 'Study Materials & Notes', path: '/lms', icon: <MenuBookIcon color="secondary" />, desc: 'Teacher notes, PDF slides & recorded lectures' },
          { label: 'Exams & Mock Tests', path: '/examinations', icon: <EventNoteIcon color="warning" />, desc: 'Take online tests & review past submissions' },
          { label: 'Academic Results', path: '/results', icon: <AssessmentIcon color="info" />, desc: 'Semester scorecards & downloadable PDF report cards' },
          { label: 'Fee Dues & Receipts', path: '/fees', icon: <AccountBalanceWalletIcon color="success" />, desc: 'Check invoice balance & download payment receipts' },
          { label: 'Library Catalog', path: '/library', icon: <LocalLibraryIcon color="primary" />, desc: 'Search book inventory & check borrowing due dates' },
        ].map((item) => (
          <Grid item xs={12} sm={6} md={4} key={item.path}>
            <Paper
              variant="outlined"
              sx={{
                p: 2,
                cursor: 'pointer',
                transition: 'all 0.2s',
                '&:hover': {
                  borderColor: 'primary.main',
                  boxShadow: 2,
                  transform: 'translateY(-2px)',
                },
              }}
              onClick={() => navigate(item.path)}
            >
              <Box display="flex" alignItems="center" gap={1.5} mb={0.5}>
                {item.icon}
                <Typography variant="subtitle2" fontWeight={600}>
                  {item.label}
                </Typography>
              </Box>
              <Typography variant="caption" color="text.secondary">
                {item.desc}
              </Typography>
            </Paper>
          </Grid>
        ))}
      </Grid>
    </Box>
  )
}
