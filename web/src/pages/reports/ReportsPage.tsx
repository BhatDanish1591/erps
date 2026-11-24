import { PageHeader } from '@/components/ui/PageHeader'
import { useState } from 'react'
import {
  Box,
  Card,
  CardContent,
  Grid,
  Typography,
  Chip,
  CircularProgress,
  Button,
  Tabs,
  Tab,
  TextField,
  MenuItem,
  IconButton,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Alert,
  Tooltip,
} from '@mui/material'
import PictureAsPdfIcon from '@mui/icons-material/PictureAsPdf'
import TableViewIcon from '@mui/icons-material/TableView'
import ScheduleIcon from '@mui/icons-material/Schedule'
import PlayArrowIcon from '@mui/icons-material/PlayArrow'
import DeleteOutlineIcon from '@mui/icons-material/DeleteOutline'
import AssessmentIcon from '@mui/icons-material/Assessment'
import PeopleIcon from '@mui/icons-material/People'
import AccountBalanceWalletIcon from '@mui/icons-material/AccountBalanceWallet'
import HowToRegIcon from '@mui/icons-material/HowToReg'
import TrendingUpIcon from '@mui/icons-material/TrendingUp'
import CheckCircleOutlineIcon from '@mui/icons-material/CheckCircleOutline'
import WarningAmberIcon from '@mui/icons-material/WarningAmber'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
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
import { reportsApi, AnalyticsFilterParams, ScheduledReportCreate } from '@/api/reports'
import { useAuthStore } from '@/store/authStore'
import { useSnackbar } from 'notistack'

export default function ReportsPage() {
  const { user } = useAuthStore()
  const { enqueueSnackbar } = useSnackbar()
  const queryClient = useQueryClient()

  const [currentTab, setCurrentTab] = useState(0)
  const [filterStartDate, setFilterStartDate] = useState('')
  const [filterEndDate, setFilterEndDate] = useState('')
  const [filterClassId, setFilterClassId] = useState('')
  const [selectedReportType, setSelectedReportType] = useState('INSTITUTION_OVERVIEW')

  // Scheduled Report Dialog state
  const [scheduleDialogOpen, setScheduleDialogOpen] = useState(false)
  const [schedTitle, setSchedTitle] = useState('')
  const [schedType, setSchedType] = useState('INSTITUTION_OVERVIEW')
  const [schedFreq, setSchedFreq] = useState('WEEKLY')
  const [schedFormat, setSchedFormat] = useState('PDF')
  const [schedRecipients, setSchedRecipients] = useState('')

  const isSuperAdmin = Boolean(user?.is_superadmin)
  const isTeacher = user?.current_role === 'TEACHER'
  const isStudent = user?.current_role === 'STUDENT'
  const isParent = user?.current_role === 'PARENT'

  const filterParams: AnalyticsFilterParams = {
    start_date: filterStartDate || undefined,
    end_date: filterEndDate || undefined,
    class_id: filterClassId || undefined,
  }

  // 1. Institution Admin Analytics Query
  const {
    data: instData,
    isLoading: isInstLoading,
    refetch: refetchInst,
  } = useQuery({
    queryKey: ['institutionAdminAnalytics', filterParams],
    queryFn: () => reportsApi.getInstitutionAdminAnalytics(filterParams),
    enabled: !isSuperAdmin && !isStudent && !isParent,
  })

  // 2. Super Admin Analytics Query
  const {
    data: saData,
    isLoading: isSaLoading,
  } = useQuery({
    queryKey: ['superAdminAnalytics'],
    queryFn: reportsApi.getSuperAdminAnalytics,
    enabled: isSuperAdmin,
  })

  // 3. Teacher Analytics Query
  const {
    data: teacherData,
    isLoading: isTeacherLoading,
  } = useQuery({
    queryKey: ['teacherAnalytics'],
    queryFn: () => reportsApi.getTeacherAnalytics(),
    enabled: isTeacher,
  })

  // 4. Student Analytics Query
  const {
    data: studentData,
    isLoading: isStudentLoading,
  } = useQuery({
    queryKey: ['studentAnalytics'],
    queryFn: () => reportsApi.getStudentAnalytics(),
    enabled: isStudent,
  })

  // 5. Parent Analytics Query
  const {
    data: parentData,
    isLoading: isParentLoading,
  } = useQuery({
    queryKey: ['parentAnalytics'],
    queryFn: () => reportsApi.getParentAnalytics(),
    enabled: isParent,
  })

  // 6. Scheduled Reports List Query
  const {
    data: schedules = [],
  } = useQuery({
    queryKey: ['scheduledReports'],
    queryFn: reportsApi.listScheduledReports,
    enabled: !isStudent && !isParent,
  })

  // Export handlers
  const handleExportPdf = async () => {
    try {
      const type = isSuperAdmin ? 'SUPER_ADMIN_GROWTH' : selectedReportType
      const blob = await reportsApi.exportPdf(type, filterParams)
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `report_${type.toLowerCase()}_${new Date().toISOString().slice(0, 10)}.pdf`
      a.click()
      window.URL.revokeObjectURL(url)
      enqueueSnackbar('PDF report generated and downloaded successfully', { variant: 'success' })
    } catch {
      enqueueSnackbar('Failed to download PDF report', { variant: 'error' })
    }
  }

  const handleExportExcel = async () => {
    try {
      const type = isSuperAdmin ? 'SUPER_ADMIN_GROWTH' : selectedReportType
      const blob = await reportsApi.exportExcel(type, filterParams)
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `report_${type.toLowerCase()}_${new Date().toISOString().slice(0, 10)}.xlsx`
      a.click()
      window.URL.revokeObjectURL(url)
      enqueueSnackbar('Excel spreadsheet exported successfully', { variant: 'success' })
    } catch {
      enqueueSnackbar('Failed to download Excel report', { variant: 'error' })
    }
  }

  // Scheduled report mutation
  const createScheduleMutation = useMutation({
    mutationFn: (data: ScheduledReportCreate) => reportsApi.createScheduledReport(data),
    onSuccess: () => {
      enqueueSnackbar('Scheduled automated report created', { variant: 'success' })
      queryClient.invalidateQueries({ queryKey: ['scheduledReports'] })
      setScheduleDialogOpen(false)
      setSchedTitle('')
      setSchedRecipients('')
    },
    onError: () => {
      enqueueSnackbar('Failed to configure scheduled report', { variant: 'error' })
    },
  })

  const triggerScheduleMutation = useMutation({
    mutationFn: (id: string) => reportsApi.triggerScheduledReport(id),
    onSuccess: () => {
      enqueueSnackbar('Report dispatch job triggered immediately', { variant: 'success' })
      queryClient.invalidateQueries({ queryKey: ['scheduledReports'] })
    },
  })

  const deleteScheduleMutation = useMutation({
    mutationFn: (id: string) => reportsApi.deleteScheduledReport(id),
    onSuccess: () => {
      enqueueSnackbar('Scheduled report removed', { variant: 'info' })
      queryClient.invalidateQueries({ queryKey: ['scheduledReports'] })
    },
  })

  const handleCreateScheduleSubmit = () => {
    if (!schedTitle.trim()) {
      enqueueSnackbar('Title is required for scheduled report', { variant: 'warning' })
      return
    }
    const recipientsList = schedRecipients
      .split(',')
      .map((e) => e.trim())
      .filter(Boolean)
    createScheduleMutation.mutate({
      title: schedTitle,
      report_type: schedType,
      frequency: schedFreq,
      format: schedFormat,
      recipients: recipientsList,
      filters: filterParams,
    })
  }

  const isLoading =
    isInstLoading || isSaLoading || isTeacherLoading || isStudentLoading || isParentLoading

  return (
    <Box>
      {/* Header */}
      <Box sx={{ mb: 3 }}>
        <PageHeader
          title="Reports & Analytics"
          description="Review performance across the institution and export reports."
          icon={<AssessmentIcon />}
        >

          {/* Global Export & Action Buttons */}
          <Box display="flex" gap={1.5} alignItems="center">
            <Button
              variant="outlined"
              startIcon={<PictureAsPdfIcon color="error" />}
              onClick={handleExportPdf}
              sx={{ textTransform: 'none' }}
            >
              Export PDF
            </Button>
            <Button
              variant="outlined"
              startIcon={<TableViewIcon color="success" />}
              onClick={handleExportExcel}
              sx={{ textTransform: 'none' }}
            >
              Export Excel
            </Button>
            {!isStudent && !isParent && (
              <Button
                variant="contained"
                startIcon={<ScheduleIcon />}
                onClick={() => setScheduleDialogOpen(true)}
                sx={{ textTransform: 'none' }}
              >
                Schedule Digest
              </Button>
            )}
          </Box>
        </PageHeader>
      </Box>

      {/* Filter Toolbar (Admins / Teachers) */}
      {!isStudent && !isParent && (
        <Card sx={{ mb: 3, p: 2 }}>
          <Grid container spacing={2} alignItems="center">
            <Grid item xs={12} sm={3}>
              <TextField
                select
                fullWidth
                size="small"
                label="Report Focus Type"
                value={selectedReportType}
                onChange={(e) => setSelectedReportType(e.target.value)}
              >
                <MenuItem value="INSTITUTION_OVERVIEW">Institution Overview</MenuItem>
                <MenuItem value="ATTENDANCE_SUMMARY">Attendance Summary</MenuItem>
                <MenuItem value="FEE_COLLECTION">Fee Collection Ledger</MenuItem>
                <MenuItem value="EXAM_PERFORMANCE">Examination Performance</MenuItem>
              </TextField>
            </Grid>
            <Grid item xs={12} sm={3}>
              <TextField
                fullWidth
                size="small"
                type="date"
                label="Start Date"
                InputLabelProps={{ shrink: true }}
                value={filterStartDate}
                onChange={(e) => setFilterStartDate(e.target.value)}
              />
            </Grid>
            <Grid item xs={12} sm={3}>
              <TextField
                fullWidth
                size="small"
                type="date"
                label="End Date"
                InputLabelProps={{ shrink: true }}
                value={filterEndDate}
                onChange={(e) => setFilterEndDate(e.target.value)}
              />
            </Grid>
            <Grid item xs={12} sm={3} display="flex" gap={1}>
              <Button
                variant="contained"
                onClick={() => refetchInst()}
                fullWidth
                sx={{ textTransform: 'none' }}
              >
                Apply Filters
              </Button>
              <Button
                variant="text"
                onClick={() => {
                  setFilterStartDate('')
                  setFilterEndDate('')
                  setFilterClassId('')
                }}
                sx={{ textTransform: 'none' }}
              >
                Reset
              </Button>
            </Grid>
          </Grid>
        </Card>
      )}

      {/* Tabs */}
      <Tabs value={currentTab} onChange={(_, val) => setCurrentTab(val)} sx={{ mb: 3 }}>
        <Tab label={isSuperAdmin ? 'Platform Overview' : 'Institution Overview'} />
        {(isTeacher || !isStudent) && <Tab label="Academic & Teacher Analytics" />}
        {(isStudent || isParent || !isSuperAdmin) && <Tab label="Student & Parent Progress" />}
        {!isStudent && !isParent && <Tab label="Scheduled Recurring Reports" />}
      </Tabs>

      {isLoading && (
        <Box display="flex" justifyContent="center" alignItems="center" minHeight="40vh">
          <CircularProgress />
        </Box>
      )}

      {/* ── Tab 0: Institution / Super Admin Overview ───────────────────────── */}
      {currentTab === 0 && !isLoading && (
        <Box>
          {isSuperAdmin && saData && (
            <Grid container spacing={3}>
              <Grid item xs={12} sm={6} md={3}>
                <Card>
                  <CardContent>
                    <Typography color="text.secondary" variant="caption">Total Institutions</Typography>
                    <Typography variant="h4" fontWeight={700}>{saData.total_institutions}</Typography>
                    <Chip label="All Tenants" size="small" color="primary" sx={{ mt: 1 }} />
                  </CardContent>
                </Card>
              </Grid>
              <Grid item xs={12} sm={6} md={3}>
                <Card>
                  <CardContent>
                    <Typography color="text.secondary" variant="caption">Active Subscriptions</Typography>
                    <Typography variant="h4" fontWeight={700}>{saData.active_subscriptions}</Typography>
                    <Typography variant="caption" color="error">{saData.expired_subscriptions} Expired</Typography>
                  </CardContent>
                </Card>
              </Grid>
              <Grid item xs={12} sm={6} md={3}>
                <Card>
                  <CardContent>
                    <Typography color="text.secondary" variant="caption">Monthly Recurring Revenue (MRR)</Typography>
                    <Typography variant="h4" fontWeight={700}>₹{Number(saData.monthly_recurring_revenue).toLocaleString()}</Typography>
                    <Typography variant="caption" color="text.secondary">ARR: ₹{Number(saData.annual_recurring_revenue).toLocaleString()}</Typography>
                  </CardContent>
                </Card>
              </Grid>
              <Grid item xs={12} sm={6} md={3}>
                <Card>
                  <CardContent>
                    <Typography color="text.secondary" variant="caption">Total Platform Users</Typography>
                    <Typography variant="h4" fontWeight={700}>{saData.user_statistics.total_users}</Typography>
                    <Typography variant="caption" color="text.secondary">Across all roles</Typography>
                  </CardContent>
                </Card>
              </Grid>

              {/* Institution Growth Chart */}
              <Grid item xs={12} md={8} sx={{ minWidth: 0 }}>
                <Card sx={{ p: 2, minWidth: 0, overflow: 'hidden' }}>
                  <Typography variant="h6" fontWeight={600} mb={2}>Tenant Growth History</Typography>
                  <Box height={280} sx={{ width: '100%', minWidth: 0 }}>
                    <ResponsiveContainer width="100%" height="100%">
                      <AreaChart data={saData.institution_growth}>
                        <CartesianGrid strokeDasharray="3 3" />
                        <XAxis dataKey="month" />
                        <YAxis />
                        <RechartsTooltip />
                        <Area type="monotone" dataKey="total_institutions" stroke="#2563eb" fill="#93c5fd" />
                      </AreaChart>
                    </ResponsiveContainer>
                  </Box>
                </Card>
              </Grid>

              {/* Plan Distribution */}
              <Grid item xs={12} md={4} sx={{ minWidth: 0 }}>
                <Card sx={{ p: 2, minWidth: 0, overflow: 'hidden' }}>
                  <Typography variant="h6" fontWeight={600} mb={2}>Subscription Plans</Typography>
                  <Box height={280} sx={{ width: '100%', minWidth: 0 }}>
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart data={saData.subscription_plan_distribution}>
                        <CartesianGrid strokeDasharray="3 3" />
                        <XAxis dataKey="plan_code" />
                        <YAxis />
                        <RechartsTooltip />
                        <Bar dataKey="count" fill="#4f46e5" />
                      </BarChart>
                    </ResponsiveContainer>
                  </Box>
                </Card>
              </Grid>
            </Grid>
          )}

          {!isSuperAdmin && instData && (
            <Grid container spacing={3}>
              {/* Institution Admin KPI Cards */}
              <Grid item xs={12} sm={6} md={3}>
                <Card>
                  <CardContent>
                    <Box display="flex" justifyContent="space-between" alignItems="center">
                      <Typography color="text.secondary" variant="caption">Total Enrolled Students</Typography>
                      <PeopleIcon color="primary" />
                    </Box>
                    <Typography variant="h4" fontWeight={700}>{instData.total_students}</Typography>
                    <Typography variant="caption" color="text.secondary">{instData.total_teachers} Active Faculty</Typography>
                  </CardContent>
                </Card>
              </Grid>

              <Grid item xs={12} sm={6} md={3}>
                <Card>
                  <CardContent>
                    <Box display="flex" justifyContent="space-between" alignItems="center">
                      <Typography color="text.secondary" variant="caption">Daily Attendance Rate</Typography>
                      <HowToRegIcon color="success" />
                    </Box>
                    <Typography variant="h4" fontWeight={700}>{instData.daily_attendance.rate_percentage}%</Typography>
                    <Typography variant="caption" color="text.secondary">
                      {instData.daily_attendance.present} Present / {instData.daily_attendance.absent} Absent
                    </Typography>
                  </CardContent>
                </Card>
              </Grid>

              <Grid item xs={12} sm={6} md={3}>
                <Card>
                  <CardContent>
                    <Box display="flex" justifyContent="space-between" alignItems="center">
                      <Typography color="text.secondary" variant="caption">Pass Percentage</Typography>
                      <TrendingUpIcon color="info" />
                    </Box>
                    <Typography variant="h4" fontWeight={700}>{instData.pass_percentage}%</Typography>
                    <Typography variant="caption" color="text.secondary">
                      Avg Score: {instData.examination_performance.average_score_percentage}%
                    </Typography>
                  </CardContent>
                </Card>
              </Grid>

              <Grid item xs={12} sm={6} md={3}>
                <Card>
                  <CardContent>
                    <Box display="flex" justifyContent="space-between" alignItems="center">
                      <Typography color="text.secondary" variant="caption">Fee Collection</Typography>
                      <AccountBalanceWalletIcon color="warning" />
                    </Box>
                    <Typography variant="h4" fontWeight={700}>₹{Number(instData.fee_collection.total_collected).toLocaleString()}</Typography>
                    <Typography variant="caption" color="error">
                      ₹{Number(instData.pending_fees.total_pending).toLocaleString()} Pending
                    </Typography>
                  </CardContent>
                </Card>
              </Grid>

              {/* Monthly Attendance Trend */}
              <Grid item xs={12} md={7} sx={{ minWidth: 0 }}>
                <Card sx={{ p: 2, minWidth: 0, overflow: 'hidden' }}>
                  <Typography variant="h6" fontWeight={600} mb={2}>Monthly Attendance Trend (%)</Typography>
                  <Box height={260} sx={{ width: '100%', minWidth: 0 }}>
                    <ResponsiveContainer width="100%" height="100%">
                      <AreaChart data={instData.monthly_attendance}>
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

              {/* Class Enrollment Breakdown */}
              <Grid item xs={12} md={5} sx={{ minWidth: 0 }}>
                <Card sx={{ p: 2, minWidth: 0, overflow: 'hidden' }}>
                  <Typography variant="h6" fontWeight={600} mb={2}>Students by Class / Grade</Typography>
                  <Box height={260} sx={{ width: '100%', minWidth: 0 }}>
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart data={instData.class_distribution}>
                        <CartesianGrid strokeDasharray="3 3" />
                        <XAxis dataKey="class_name" />
                        <YAxis />
                        <RechartsTooltip />
                        <Bar dataKey="student_count" fill="#2563eb" />
                      </BarChart>
                    </ResponsiveContainer>
                  </Box>
                </Card>
              </Grid>

              {/* Academic Grade Distribution */}
              <Grid item xs={12} md={6} sx={{ minWidth: 0 }}>
                <Card sx={{ p: 2, minWidth: 0, overflow: 'hidden' }}>
                  <Typography variant="h6" fontWeight={600} mb={2}>Academic Grade Distribution</Typography>
                  <Box height={240} sx={{ width: '100%', minWidth: 0 }}>
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart data={instData.academic_trends}>
                        <CartesianGrid strokeDasharray="3 3" />
                        <XAxis dataKey="grade_label" />
                        <YAxis />
                        <RechartsTooltip />
                        <Bar dataKey="student_count" fill="#8b5cf6" />
                      </BarChart>
                    </ResponsiveContainer>
                  </Box>
                </Card>
              </Grid>

              {/* Fee Collection by Payment Mode */}
              <Grid item xs={12} md={6}>
                <Card sx={{ p: 2 }}>
                  <Typography variant="h6" fontWeight={600} mb={2}>Collection Breakdown by Payment Mode</Typography>
                  <TableContainer sx={{ overflowX: 'auto', width: '100%' }}>
                    <Table size="small" sx={{ minWidth: 350 }}>
                      <TableHead>
                        <TableRow>
                          <TableCell>Payment Mode</TableCell>
                          <TableCell align="right">Amount (₹)</TableCell>
                        </TableRow>
                      </TableHead>
                      <TableBody>
                        {Object.entries(instData.fee_collection.by_payment_mode).map(([mode, amt]) => (
                          <TableRow key={mode}>
                            <TableCell><Chip label={mode} size="small" variant="outlined" /></TableCell>
                            <TableCell align="right" sx={{ fontWeight: 600 }}>₹{Number(amt).toLocaleString()}</TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </TableContainer>
                </Card>
              </Grid>
            </Grid>
          )}
        </Box>
      )}

      {/* ── Tab 1: Academic & Teacher Analytics ────────────────────────────── */}
      {currentTab === 1 && !isLoading && (
        <Box>
          {teacherData && (
            <Grid container spacing={3}>
              <Grid item xs={12} sm={4}>
                <Card>
                  <CardContent>
                    <Typography color="text.secondary" variant="caption">Faculty Assigned</Typography>
                    <Typography variant="h5" fontWeight={700}>{teacherData.teacher_name}</Typography>
                    <Typography variant="caption" color="text.secondary">{teacherData.assigned_students} Students Assigned</Typography>
                  </CardContent>
                </Card>
              </Grid>
              <Grid item xs={12} sm={4}>
                <Card>
                  <CardContent>
                    <Typography color="text.secondary" variant="caption">Class Attendance Rate</Typography>
                    <Typography variant="h5" fontWeight={700}>{teacherData.class_attendance_percentage}%</Typography>
                    <Typography variant="caption" color="text.secondary">Teacher Cohorts</Typography>
                  </CardContent>
                </Card>
              </Grid>
              <Grid item xs={12} sm={4}>
                <Card>
                  <CardContent>
                    <Typography color="text.secondary" variant="caption">Pending Assignment Evaluations</Typography>
                    <Typography variant="h5" fontWeight={700} color={teacherData.pending_assignment_evaluation > 0 ? 'warning.main' : 'text.primary'}>
                      {teacherData.pending_assignment_evaluation}
                    </Typography>
                    <Typography variant="caption" color="text.secondary">Awaiting Marks / Feedback</Typography>
                  </CardContent>
                </Card>
              </Grid>

              {/* Subject Performance Breakdown */}
              <Grid item xs={12}>
                <Card sx={{ p: 2 }}>
                  <Typography variant="h6" fontWeight={600} mb={2}>Assigned Subject Performance</Typography>
                  <TableContainer sx={{ overflowX: 'auto', width: '100%' }}>
                    <Table size="small" sx={{ minWidth: 350 }}>
                      <TableHead>
                        <TableRow>
                          <TableCell>Subject</TableCell>
                          <TableCell>Class / Section</TableCell>
                          <TableCell align="right">Students</TableCell>
                          <TableCell align="right">Avg Score (%)</TableCell>
                          <TableCell align="right">Pass Rate (%)</TableCell>
                        </TableRow>
                      </TableHead>
                      <TableBody>
                        {teacherData.subject_performance.map((s) => (
                          <TableRow key={s.subject_id}>
                            <TableCell sx={{ fontWeight: 600 }}>{s.subject_name}</TableCell>
                            <TableCell>{s.class_name}</TableCell>
                            <TableCell align="right">{s.student_count}</TableCell>
                            <TableCell align="right">{s.average_score}%</TableCell>
                            <TableCell align="right">
                              <Chip
                                label={`${s.pass_percentage}%`}
                                size="small"
                                color={s.pass_percentage >= 75 ? 'success' : s.pass_percentage >= 40 ? 'warning' : 'error'}
                              />
                            </TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </TableContainer>
                </Card>
              </Grid>
            </Grid>
          )}
          {!teacherData && (
            <Alert severity="info">
              Detailed teacher and cohort analytics are available for assigned instructors and academic administrators.
            </Alert>
          )}
        </Box>
      )}

      {/* ── Tab 2: Student & Parent Progress ───────────────────────────────── */}
      {currentTab === 2 && !isLoading && (
        <Box>
          {/* Student Self Analytics */}
          {studentData && (
            <Grid container spacing={3}>
              <Grid item xs={12} sm={6} md={3}>
                <Card>
                  <CardContent>
                    <Typography color="text.secondary" variant="caption">Student Name</Typography>
                    <Typography variant="h6" fontWeight={700}>{studentData.student_name}</Typography>
                    <Typography variant="caption" color="text.secondary">Adm: {studentData.admission_number || 'N/A'}</Typography>
                  </CardContent>
                </Card>
              </Grid>
              <Grid item xs={12} sm={6} md={3}>
                <Card>
                  <CardContent>
                    <Typography color="text.secondary" variant="caption">Attendance Rate</Typography>
                    <Typography variant="h4" fontWeight={700}>{studentData.attendance_percentage}%</Typography>
                    <Typography variant="caption" color="text.secondary">
                      {studentData.attendance_breakdown.present} Present of {studentData.attendance_breakdown.total_sessions}
                    </Typography>
                  </CardContent>
                </Card>
              </Grid>
              <Grid item xs={12} sm={6} md={3}>
                <Card>
                  <CardContent>
                    <Typography color="text.secondary" variant="caption">Assignment Completion</Typography>
                    <Typography variant="h4" fontWeight={700}>{studentData.assignment_completion.completion_rate}%</Typography>
                    <Typography variant="caption" color="text.secondary">
                      {studentData.assignment_completion.total_submitted} / {studentData.assignment_completion.total_assigned} Submitted
                    </Typography>
                  </CardContent>
                </Card>
              </Grid>
              <Grid item xs={12} sm={6} md={3}>
                <Card>
                  <CardContent>
                    <Typography color="text.secondary" variant="caption">Exams Taken</Typography>
                    <Typography variant="h4" fontWeight={700}>{studentData.examination_history.length}</Typography>
                    <Typography variant="caption" color="text.secondary">Evaluated assessments</Typography>
                  </CardContent>
                </Card>
              </Grid>

              {/* Progress Trend */}
              <Grid item xs={12} md={7} sx={{ minWidth: 0 }}>
                <Card sx={{ p: 2, minWidth: 0, overflow: 'hidden' }}>
                  <Typography variant="h6" fontWeight={600} mb={2}>Examination Score Trend (%)</Typography>
                  <Box height={240} sx={{ width: '100%', minWidth: 0 }}>
                    <ResponsiveContainer width="100%" height="100%">
                      <AreaChart data={studentData.academic_progress_trend}>
                        <CartesianGrid strokeDasharray="3 3" />
                        <XAxis dataKey="label" />
                        <YAxis domain={[0, 100]} />
                        <RechartsTooltip />
                        <Area type="monotone" dataKey="percentage" stroke="#3b82f6" fill="#bfdbfe" />
                      </AreaChart>
                    </ResponsiveContainer>
                  </Box>
                </Card>
              </Grid>

              {/* Subject Marks Table */}
              <Grid item xs={12} md={5}>
                <Card sx={{ p: 2 }}>
                  <Typography variant="h6" fontWeight={600} mb={2}>Subject-wise Scores</Typography>
                  <TableContainer sx={{ overflowX: 'auto', width: '100%' }}>
                    <Table size="small" sx={{ minWidth: 350 }}>
                      <TableHead>
                        <TableRow>
                          <TableCell>Subject</TableCell>
                          <TableCell align="right">Score</TableCell>
                          <TableCell align="right">Grade</TableCell>
                        </TableRow>
                      </TableHead>
                      <TableBody>
                        {studentData.subject_marks.map((sm, idx) => (
                          <TableRow key={idx}>
                            <TableCell>{sm.subject_name}</TableCell>
                            <TableCell align="right">{sm.marks_obtained} / {sm.max_marks}</TableCell>
                            <TableCell align="right"><Chip label={sm.grade || 'A'} size="small" color="primary" variant="outlined" /></TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </TableContainer>
                </Card>
              </Grid>
            </Grid>
          )}

          {/* Parent Linked Children Analytics */}
          {parentData && (
            <Box>
              <Typography variant="h6" fontWeight={600} mb={2}>
                Linked Children Academic & Fee Status ({parentData.children_count})
              </Typography>
              <Grid container spacing={3}>
                {parentData.children.map((child) => (
                  <Grid item xs={12} md={6} key={child.student_id}>
                    <Card sx={{ borderLeft: child.fee_overdue ? '4px solid #ef4444' : '4px solid #10b981' }}>
                      <CardContent>
                        <Box display="flex" justifyContent="space-between" alignItems="flex-start">
                          <Box>
                            <Typography variant="h6" fontWeight={700}>{child.student_name}</Typography>
                            <Typography variant="caption" color="text.secondary">
                              Class: {child.class_name || 'General'} • Adm: {child.admission_number || 'N/A'}
                            </Typography>
                          </Box>
                          {child.fee_overdue ? (
                            <Chip icon={<WarningAmberIcon />} label="Fee Overdue" color="error" size="small" />
                          ) : (
                            <Chip icon={<CheckCircleOutlineIcon />} label="Fees Current" color="success" size="small" />
                          )}
                        </Box>

                        <Grid container spacing={2} sx={{ mt: 2 }}>
                          <Grid item xs={4}>
                            <Typography variant="caption" color="text.secondary">Attendance</Typography>
                            <Typography variant="body1" fontWeight={600}>{child.attendance_percentage}%</Typography>
                          </Grid>
                          <Grid item xs={4}>
                            <Typography variant="caption" color="text.secondary">Latest Score</Typography>
                            <Typography variant="body1" fontWeight={600}>
                              {child.latest_exam_score != null ? `${child.latest_exam_score}%` : 'N/A'}
                            </Typography>
                          </Grid>
                          <Grid item xs={4}>
                            <Typography variant="caption" color="text.secondary">Fee Dues</Typography>
                            <Typography variant="body1" fontWeight={600} color={Number(child.total_fee_dues) > 0 ? 'error.main' : 'text.primary'}>
                              ₹{Number(child.total_fee_dues).toLocaleString()}
                            </Typography>
                          </Grid>
                        </Grid>
                      </CardContent>
                    </Card>
                  </Grid>
                ))}
              </Grid>
            </Box>
          )}

          {!studentData && !parentData && (
            <Alert severity="info">
              Student progress charts and parent multi-child ledgers will display here for logged-in parents or students.
            </Alert>
          )}
        </Box>
      )}

      {/* ── Tab 3: Scheduled Reports Management ─────────────────────────────── */}
      {currentTab === 3 && !isLoading && (
        <Card sx={{ p: 3 }}>
          <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
            <Box>
              <Typography variant="h6" fontWeight={600}>Scheduled Automated Reports</Typography>
              <Typography variant="body2" color="text.secondary">
                Configure background recurring email digests (Daily, Weekly, Monthly) in PDF or Excel
              </Typography>
            </Box>
            <Button
              variant="contained"
              startIcon={<ScheduleIcon />}
              onClick={() => setScheduleDialogOpen(true)}
              sx={{ textTransform: 'none' }}
            >
              Add Schedule
            </Button>
          </Box>

          <TableContainer component={Paper} variant="outlined" sx={{ overflowX: 'auto', width: '100%' }}>
            <Table size="small" sx={{ minWidth: 600 }}>
              <TableHead>
                <TableRow>
                  <TableCell>Report Title</TableCell>
                  <TableCell>Type</TableCell>
                  <TableCell>Frequency</TableCell>
                  <TableCell>Format</TableCell>
                  <TableCell>Recipients</TableCell>
                  <TableCell>Next Run</TableCell>
                  <TableCell align="right">Actions</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {schedules.map((s) => (
                  <TableRow key={s.id}>
                    <TableCell sx={{ fontWeight: 600 }}>{s.title}</TableCell>
                    <TableCell><Chip label={s.report_type} size="small" variant="outlined" /></TableCell>
                    <TableCell><Chip label={s.frequency} size="small" color="primary" /></TableCell>
                    <TableCell><Chip label={s.format} size="small" color={s.format === 'PDF' ? 'error' : 'success'} /></TableCell>
                    <TableCell>{s.recipients.join(', ') || 'No recipients'}</TableCell>
                    <TableCell>{s.next_run_at ? new Date(s.next_run_at).toLocaleDateString() : 'Pending'}</TableCell>
                    <TableCell align="right">
                      <Tooltip title="Trigger Dispatch Now">
                        <IconButton
                          color="primary"
                          size="small"
                          onClick={() => triggerScheduleMutation.mutate(s.id)}
                        >
                          <PlayArrowIcon />
                        </IconButton>
                      </Tooltip>
                      <Tooltip title="Delete Schedule">
                        <IconButton
                          color="error"
                          size="small"
                          onClick={() => deleteScheduleMutation.mutate(s.id)}
                        >
                          <DeleteOutlineIcon />
                        </IconButton>
                      </Tooltip>
                    </TableCell>
                  </TableRow>
                ))}
                {schedules.length === 0 && (
                  <TableRow>
                    <TableCell colSpan={7} align="center" sx={{ py: 3, color: 'text.secondary' }}>
                      No automated report schedules configured yet. Click "Add Schedule" to create one.
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </TableContainer>
        </Card>
      )}

      {/* ── Dialog: Create Scheduled Report ─────────────────────────────────── */}
      <Dialog open={scheduleDialogOpen} onClose={() => setScheduleDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Configure Recurring Report Digest</DialogTitle>
        <DialogContent dividers>
          <Box display="flex" flexDirection="column" gap={2} pt={1}>
            <TextField
              label="Schedule Title"
              fullWidth
              size="small"
              value={schedTitle}
              onChange={(e) => setSchedTitle(e.target.value)}
              placeholder="e.g. Weekly Management Attendance & Fee Digest"
            />
            <TextField
              select
              label="Report Type"
              fullWidth
              size="small"
              value={schedType}
              onChange={(e) => setSchedType(e.target.value)}
            >
              <MenuItem value="INSTITUTION_OVERVIEW">Institution Overview</MenuItem>
              <MenuItem value="ATTENDANCE_SUMMARY">Attendance Summary</MenuItem>
              <MenuItem value="FEE_COLLECTION">Fee Collection</MenuItem>
              <MenuItem value="EXAM_PERFORMANCE">Exam Performance</MenuItem>
            </TextField>
            <Grid container spacing={2}>
              <Grid item xs={6}>
                <TextField
                  select
                  label="Frequency"
                  fullWidth
                  size="small"
                  value={schedFreq}
                  onChange={(e) => setSchedFreq(e.target.value)}
                >
                  <MenuItem value="DAILY">Daily</MenuItem>
                  <MenuItem value="WEEKLY">Weekly</MenuItem>
                  <MenuItem value="MONTHLY">Monthly</MenuItem>
                </TextField>
              </Grid>
              <Grid item xs={6}>
                <TextField
                  select
                  label="Format"
                  fullWidth
                  size="small"
                  value={schedFormat}
                  onChange={(e) => setSchedFormat(e.target.value)}
                >
                  <MenuItem value="PDF">PDF Document</MenuItem>
                  <MenuItem value="EXCEL">Excel Spreadsheet (.xlsx)</MenuItem>
                </TextField>
              </Grid>
            </Grid>
            <TextField
              label="Recipients (comma separated emails)"
              fullWidth
              size="small"
              value={schedRecipients}
              onChange={(e) => setSchedRecipients(e.target.value)}
              placeholder="principal@sterling.edu, finance@sterling.edu"
            />
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setScheduleDialogOpen(false)} color="inherit">
            Cancel
          </Button>
          <Button
            variant="contained"
            onClick={handleCreateScheduleSubmit}
            disabled={createScheduleMutation.isPending}
          >
            Create Schedule
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  )
}
