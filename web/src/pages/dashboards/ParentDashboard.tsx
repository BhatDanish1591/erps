import { useState, useEffect } from 'react'
import {
  Box,
  Card,
  CardContent,
  Grid,
  Typography,
  Chip,
  Button,
  Tabs,
  Tab,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  Alert,
  CircularProgress,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Divider,
  List,
} from '@mui/material'
import FamilyRestroomIcon from '@mui/icons-material/FamilyRestroom'
import CheckCircleIcon from '@mui/icons-material/CheckCircle'
import WarningAmberIcon from '@mui/icons-material/WarningAmber'
import AccountBalanceWalletIcon from '@mui/icons-material/AccountBalanceWallet'
import AddCircleOutlineIcon from '@mui/icons-material/AddCircleOutline'
import ScheduleIcon from '@mui/icons-material/Schedule'
import SchoolIcon from '@mui/icons-material/School'
import AssignmentIcon from '@mui/icons-material/Assignment'
import ForumIcon from '@mui/icons-material/Forum'
import PaymentIcon from '@mui/icons-material/Payment'
import SendIcon from '@mui/icons-material/Send'
import { useAuthStore } from '@/store/authStore'
import { PageHeader } from '@/components/ui/PageHeader'
import { payFeeInvoice } from '@/api/fees'
import { lmsApi } from '@/api/lms'
import DownloadIcon from '@mui/icons-material/Download'

import {
  parentsApi,
  LinkedChildSummary,
  ChildDetailedProfileResponse,
  ChildAttendanceResponse,
  ChildTimetableResponse,
  ChildExaminationsResponse,
  ChildTermResultResponse,
  ChildAssignmentItem,
  ChildStudyMaterialItem,
  ChildFeesResponse,
  ChildTeacherItem,
  ParentTeacherMessageResponse,
} from '../../api/parents'

export default function ParentDashboard() {
  const tenantId = useAuthStore((state) => state.user?.current_tenant_id)
  const switchInstitution = useAuthStore((state) => state.switchInstitution)
  const [loadedChildId, setLoadedChildId] = useState('')
  const [paying, setPaying] = useState(false)
  const [refreshChild, setRefreshChild] = useState(0)
  const [children, setChildren] = useState<LinkedChildSummary[]>([])
  const [selectedChildId, setSelectedChildId] = useState<string>('')
  const [loading, setLoading] = useState<boolean>(true)
  const [tabIndex, setTabIndex] = useState<number>(0)
  const [errorMsg, setErrorMsg] = useState<string | null>(null)
  const [successMsg, setSuccessMsg] = useState<string | null>(null)

  // Child detailed data states
  const [profile, setProfile] = useState<ChildDetailedProfileResponse | null>(null)
  const [attendance, setAttendance] = useState<ChildAttendanceResponse | null>(null)
  const [timetable, setTimetable] = useState<ChildTimetableResponse | null>(null)
  const [exams, setExams] = useState<ChildExaminationsResponse | null>(null)
  const [results, setResults] = useState<ChildTermResultResponse[]>([])
  const [assignments, setAssignments] = useState<ChildAssignmentItem[]>([])
  const [materials, setMaterials] = useState<ChildStudyMaterialItem[]>([])
  const [fees, setFees] = useState<ChildFeesResponse | null>(null)
  const [teachers, setTeachers] = useState<ChildTeacherItem[]>([])
  const [messages, setMessages] = useState<ParentTeacherMessageResponse[]>([])

  // Link Child Dialog State
  const [openLinkDialog, setOpenLinkDialog] = useState<boolean>(false)
  const [admissionNumber, setAdmissionNumber] = useState<string>('')
  const [verificationCode, setVerificationCode] = useState<string>('')
  const [relationshipType, setRelationshipType] = useState<string>('FATHER')
  const [linkingSubmitting, setLinkingSubmitting] = useState<boolean>(false)

  // Teacher Message State
  const [messageTeacherId, setMessageTeacherId] = useState<string>('')
  const [messageSubject, setMessageSubject] = useState<string>('')
  const [messageBody, setMessageBody] = useState<string>('')
  const [sendingMessage, setSendingMessage] = useState<boolean>(false)

  // Initial load
  useEffect(() => {
    loadChildren()
  }, [])

  const loadChildren = async () => {
    setLoading(true)
    setErrorMsg(null)
    try {
      const data = await parentsApi.listChildren()
      setChildren(data)
      if (data.length > 0) {
        // Select first verified child, or first child
        const available = data.filter((child) => child.institution_id === tenantId)
        const verified = available.find((child) => child.verification_status === 'VERIFIED')
        setSelectedChildId(verified?.student_id ?? available[0]?.student_id ?? '')
      }
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to load linked children.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    const child = children.find((item) => item.student_id === selectedChildId)
    if (!child || child.verification_status !== 'VERIFIED' || child.institution_id !== tenantId) return
    let active = true
    const studentId = child.student_id
    setLoadedChildId('')
    setMessageTeacherId('')
    Promise.allSettled([
      parentsApi.getChildProfile(studentId),
      parentsApi.getChildAttendance(studentId),
      parentsApi.getChildTimetable(studentId),
      parentsApi.getChildExaminations(studentId),
      child.can_view_grades ? parentsApi.getChildResults(studentId) : Promise.resolve([]),
      parentsApi.getChildAssignments(studentId),
      parentsApi.getChildMaterials(studentId),
      child.can_pay_fees ? parentsApi.getChildFees(studentId) : Promise.resolve(null),
      parentsApi.getChildTeachers(studentId),
      parentsApi.listMessages(studentId),
    ] as const).then((responses) => {
      if (!active) return
      const [prof, att, tt, ex, res, asgn, mat, feeData, tchr, msgs] = responses
      setProfile(prof.status === 'fulfilled' ? prof.value : null)
      setAttendance(att.status === 'fulfilled' ? att.value : null)
      setTimetable(tt.status === 'fulfilled' ? tt.value : null)
      setExams(ex.status === 'fulfilled' ? ex.value : null)
      setResults(res.status === 'fulfilled' ? res.value : [])
      setAssignments(asgn.status === 'fulfilled' ? asgn.value : [])
      setMaterials(mat.status === 'fulfilled' ? mat.value : [])
      setFees(feeData.status === 'fulfilled' ? feeData.value : null)
      setTeachers(tchr.status === 'fulfilled' ? tchr.value : [])
      setMessages(msgs.status === 'fulfilled' ? msgs.value : [])
      setLoadedChildId(studentId)
      if (responses.some((response) => response.status === 'rejected')) {
        setErrorMsg('Some records could not be loaded for this student.')
      }
    })
    return () => { active = false }
  }, [selectedChildId, children, tenantId, refreshChild])

  const selectChild = async (studentId: string) => {
    const child = children.find((item) => item.student_id === studentId)
    if (!child) return
    setErrorMsg(null)
    try {
      if (child.institution_id !== tenantId) await switchInstitution(child.institution_id)
      setSelectedChildId(studentId)
    } catch {
      setErrorMsg('Unable to switch to this student’s institution.')
    }
  }

  const payInvoice = async (invoiceId: string, balance: number) => {
    setPaying(true)
    setErrorMsg(null)
    setSuccessMsg(null)
    try {
      if (await payFeeInvoice(invoiceId, balance)) {
        setSuccessMsg('Fee payment recorded successfully.')
        setRefreshChild((previous) => previous + 1)
      }
    } catch (error: any) {
      setErrorMsg(error.response?.data?.error?.message || error.message || 'Unable to complete the fee payment.')
    } finally {
      setPaying(false)
    }
  }

  const downloadMaterial = async (materialId: string) => {
    try {
      const response = await lmsApi.getDownloadUrl(materialId)
      const link = document.createElement('a')
      link.href = response.data.url
      link.rel = 'noopener noreferrer'
      link.target = '_blank'
      link.click()
    } catch {
      setErrorMsg('Unable to download this material.')
    }
  }

  const handleLinkChildSubmit = async () => {
    if (!admissionNumber) {
      setErrorMsg('Please enter student admission number.')
      return
    }
    setLinkingSubmitting(true)
    setErrorMsg(null)
    setSuccessMsg(null)
    try {
      const res = await parentsApi.requestLinkChild({
        admission_number: admissionNumber,
        relation_type: relationshipType,
        verification_code: verificationCode.trim() || undefined,
      })

      setSuccessMsg(res.message)
      setOpenLinkDialog(false)
      setAdmissionNumber('')
      setVerificationCode('')
      loadChildren()
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to submit link request.')
    } finally {
      setLinkingSubmitting(false)
    }
  }

  const handleSendMessage = async () => {
    if (!messageTeacherId || !messageSubject || !messageBody) {
      setErrorMsg('Please fill in teacher, subject, and message.')
      return
    }
    setSendingMessage(true)
    setErrorMsg(null)
    try {
      await parentsApi.sendMessage({
        teacher_user_id: messageTeacherId,
        student_id: selectedChildId,
        subject: messageSubject,
        message: messageBody,
      })
      setSuccessMsg('Message sent successfully.')
      setMessageSubject('')
      setMessageBody('')
      const updatedMsgs = await parentsApi.listMessages(selectedChildId)
      setMessages(updatedMsgs)
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to send message.')
    } finally {
      setSendingMessage(false)
    }
  }

  const activeChild = children.find((c) => c.student_id === selectedChildId)
  const isVerified = activeChild?.verification_status === 'VERIFIED'

  return (
    <Box>
      {/* Header Banner */}
      <Box mb={3}>
        <PageHeader title="Parent Portal" description="View your child’s attendance, coursework, fees, and messages." icon={<FamilyRestroomIcon />}>
        <Box display="flex" alignItems="center" gap={2}>
          {children.length > 0 && (
            <FormControl size="small" sx={{ width: { xs: '100%', sm: 240 }, minWidth: 0 }}>
              <InputLabel id="child-select-label">Select Ward / Child</InputLabel>
              <Select
                labelId="child-select-label"
                value={selectedChildId}
                label="Select Ward / Child"
                onChange={(event) => void selectChild(event.target.value)}
                disabled={paying}
              >
                {children.map((child) => (
                  <MenuItem key={child.student_id} value={child.student_id}>
                    <Box display="flex" alignItems="center" gap={1}>
                      <Typography fontWeight={600} variant="body2">
                        {child.student_name}
                      </Typography>
                      <Chip
                        size="small"
                        label={child.institution_name}
                        color="primary"
                        variant="outlined"
                        sx={{ fontSize: '0.65rem', height: 20 }}
                      />
                      {child.verification_status !== 'VERIFIED' && (
                        <Chip
                          size="small"
                          label={child.verification_status}
                          color="warning"
                          sx={{ fontSize: '0.65rem', height: 20 }}
                        />
                      )}
                    </Box>
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
          )}

          <Button
            variant="contained"
            color="primary"
            startIcon={<AddCircleOutlineIcon />}
            onClick={() => setOpenLinkDialog(true)}
          >
            Link Another Child
          </Button>
        </Box>
        </PageHeader>
      </Box>

      {/* Feedback Alerts */}
      {errorMsg && (
        <Alert severity="error" sx={{ mb: 3 }} onClose={() => setErrorMsg(null)}>
          {errorMsg}
        </Alert>
      )}
      {successMsg && (
        <Alert severity="success" sx={{ mb: 3 }} onClose={() => setSuccessMsg(null)}>
          {successMsg}
        </Alert>
      )}

      {loading ? (
        <Box display="flex" justifyContent="center" py={8}>
          <CircularProgress />
        </Box>
      ) : children.length === 0 ? (
        <Card sx={{ p: 4, textAlign: 'center' }}>
          <FamilyRestroomIcon sx={{ fontSize: 64, color: 'text.secondary', mb: 2 }} />
          <Typography variant="h6" fontWeight={600} gutterBottom>
            No Linked Wards Found
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ maxWidth: 500, mx: 'auto', mb: 3 }}>
            To protect student privacy, children cannot be linked by phone number or name alone. You must
            request linking using your child's student admission number and optional institution verification code.
          </Typography>
          <Button
            variant="contained"
            startIcon={<AddCircleOutlineIcon />}
            onClick={() => setOpenLinkDialog(true)}
          >
            Link Your Child Now
          </Button>
        </Card>
      ) : !activeChild ? (
        <Alert severity="info">Select a student to view their records.</Alert>
      ) : !isVerified ? (
        <Alert severity="warning" icon={<WarningAmberIcon />} sx={{ mb: 3 }}>
          <Typography fontWeight={600}>Verification Required</Typography>
          Your link request for <strong>{activeChild?.student_name}</strong> is currently{' '}
          <strong>{activeChild?.verification_status}</strong>. In accordance with strict student data privacy regulations,
          academic records, attendance, and exam scores are locked until an institution administrator approves the
          association.
        </Alert>
      ) : loadedChildId !== selectedChildId ? (
        <Box display="flex" justifyContent="center" py={8}>
          <CircularProgress aria-label="Loading student records" />
        </Box>
      ) : (
        <>
          {/* Quick Metrics Bar */}
          <Grid container spacing={3} mb={4}>
            {/* Ward Summary */}
            <Grid item xs={12} sm={6} md={3}>
              <Card>
                <CardContent>
                  <Box display="flex" alignItems="center" gap={1.5} mb={1}>
                    <FamilyRestroomIcon color="primary" />
                    <Typography variant="caption" color="text.secondary" fontWeight={600}>
                      WARD & INSTITUTION
                    </Typography>
                  </Box>
                  <Typography variant="h6" fontWeight={700}>
                    {activeChild.student_name}
                  </Typography>
                  <Typography variant="caption" color="text.secondary">
                    {activeChild.class_name || activeChild.course_name || 'Enrolled'} · Adm: {activeChild.admission_number}
                  </Typography>
                  <Box mt={0.5}>
                    <Chip
                      size="small"
                      label={activeChild.institution_name}
                      color="secondary"
                      sx={{ fontSize: '0.7rem' }}
                    />
                  </Box>
                </CardContent>
              </Card>
            </Grid>

            {/* Attendance Status */}
            <Grid item xs={12} sm={6} md={3}>
              <Card>
                <CardContent>
                  <Box display="flex" alignItems="center" gap={1.5} mb={1}>
                    <CheckCircleIcon
                      color={attendance?.low_attendance_alert ? 'error' : 'success'}
                    />
                    <Typography variant="caption" color="text.secondary" fontWeight={600}>
                      ATTENDANCE PERCENTAGE
                    </Typography>
                  </Box>
                  <Typography
                    variant="h5"
                    fontWeight={700}
                    color={attendance?.low_attendance_alert ? 'error.main' : 'success.main'}
                  >
                    {attendance ? `${attendance.overall_percentage}%` : 'N/A'}
                  </Typography>
                  <Typography variant="caption" color="text.secondary">
                    {attendance?.present_days ?? 0} Present / {attendance?.total_days ?? 0} Recorded Sessions
                  </Typography>
                  {attendance?.low_attendance_alert && (
                    <Box mt={0.5}>
                      <Chip
                        size="small"
                        label="LOW ATTENDANCE (<75%)"
                        color="error"
                        sx={{ fontSize: '0.65rem' }}
                      />
                    </Box>
                  )}
                </CardContent>
              </Card>
            </Grid>

            {/* Pending Fee Dues */}
            <Grid item xs={12} sm={6} md={3}>
              <Card>
                <CardContent>
                  <Box display="flex" alignItems="center" gap={1.5} mb={1}>
                    <AccountBalanceWalletIcon color={activeChild.total_due_fees > 0 ? 'warning' : 'success'} />
                    <Typography variant="caption" color="text.secondary" fontWeight={600}>
                      FEE DUES
                    </Typography>
                  </Box>
                  <Typography
                    variant="h5"
                    fontWeight={700}
                    color={activeChild.total_due_fees > 0 ? 'warning.main' : 'success.main'}
                  >
                    ₹{activeChild.total_due_fees.toLocaleString()}
                  </Typography>
                  <Typography variant="caption" color="text.secondary">
                    {activeChild.total_due_fees > 0 ? 'Pending dues require settlement' : 'All term fees settled'}
                  </Typography>
                </CardContent>
              </Card>
            </Grid>

            {/* Verification Status */}
            <Grid item xs={12} sm={6} md={3}>
              <Card>
                <CardContent>
                  <Box display="flex" alignItems="center" gap={1.5} mb={1}>
                    <SchoolIcon color="info" />
                    <Typography variant="caption" color="text.secondary" fontWeight={600}>
                      RELATIONSHIP & ACCESS
                    </Typography>
                  </Box>
                  <Typography variant="h6" fontWeight={700}>
                    {activeChild.relation_type}
                  </Typography>
                  <Typography variant="caption" color="success.main" fontWeight={600}>
                    ✓ Verified Legal Guardian
                  </Typography>
                </CardContent>
              </Card>
            </Grid>
          </Grid>

          {/* Module Navigation Tabs */}
          <Box sx={{ borderBottom: 1, borderColor: 'divider', mb: 3 }}>
            <Tabs
              value={tabIndex}
              onChange={(_, val) => setTabIndex(val)}
              variant="scrollable"
              scrollButtons="auto"
            >
              <Tab icon={<FamilyRestroomIcon />} iconPosition="start" label="Profile" />
              <Tab icon={<CheckCircleIcon />} iconPosition="start" label="Attendance" />
              <Tab icon={<ScheduleIcon />} iconPosition="start" label="Timetable" />
              <Tab icon={<SchoolIcon />} iconPosition="start" label="Exams & Results" />
              <Tab icon={<AssignmentIcon />} iconPosition="start" label="Assignments & LMS" />
              <Tab icon={<PaymentIcon />} iconPosition="start" label="Fees & Payments" />
              <Tab icon={<ForumIcon />} iconPosition="start" label="Teacher Messages" />
            </Tabs>
          </Box>

          {/* TAB 0: Detailed Profile */}
          {tabIndex === 0 && (
            <Card>
              <CardContent>
                <Typography variant="h6" fontWeight={600} gutterBottom>
                  Child Academic & Personal Information
                </Typography>
                <Divider sx={{ mb: 2 }} />
                <Grid container spacing={3}>
                  <Grid item xs={12} sm={6} md={4}>
                    <Typography variant="caption" color="text.secondary">Full Name</Typography>
                    <Typography variant="body1" fontWeight={600}>{profile?.full_name}</Typography>
                  </Grid>
                  <Grid item xs={12} sm={6} md={4}>
                    <Typography variant="caption" color="text.secondary">Admission Number</Typography>
                    <Typography variant="body1" fontWeight={600}>{profile?.admission_number}</Typography>
                  </Grid>
                  <Grid item xs={12} sm={6} md={4}>
                    <Typography variant="caption" color="text.secondary">Institution</Typography>
                    <Typography variant="body1" fontWeight={600}>{profile?.institution_name}</Typography>
                  </Grid>
                  <Grid item xs={12} sm={6} md={4}>
                    <Typography variant="caption" color="text.secondary">Class / Course</Typography>
                    <Typography variant="body1" fontWeight={600}>{profile?.class_name || profile?.course_name || 'N/A'}</Typography>
                  </Grid>
                  <Grid item xs={12} sm={6} md={4}>
                    <Typography variant="caption" color="text.secondary">Section</Typography>
                    <Typography variant="body1" fontWeight={600}>{profile?.section_name || 'N/A'}</Typography>
                  </Grid>
                  <Grid item xs={12} sm={6} md={4}>
                    <Typography variant="caption" color="text.secondary">Academic Session</Typography>
                    <Typography variant="body1" fontWeight={600}>{profile?.academic_session_name || 'Current'}</Typography>
                  </Grid>
                  <Grid item xs={12} sm={6} md={4}>
                    <Typography variant="caption" color="text.secondary">Gender / Blood Group</Typography>
                    <Typography variant="body1" fontWeight={600}>{profile?.gender || 'N/A'} · {profile?.blood_group || 'N/A'}</Typography>
                  </Grid>
                  <Grid item xs={12} sm={6} md={4}>
                    <Typography variant="caption" color="text.secondary">Date of Birth</Typography>
                    <Typography variant="body1" fontWeight={600}>{profile?.date_of_birth || 'N/A'}</Typography>
                  </Grid>
                  <Grid item xs={12} sm={6} md={4}>
                    <Typography variant="caption" color="text.secondary">Emergency Contact</Typography>
                    <Typography variant="body1" fontWeight={600}>{profile?.emergency_contact ? 'Yes' : 'No'}</Typography>
                  </Grid>
                </Grid>
              </CardContent>
            </Card>
          )}

          {/* TAB 1: Attendance */}
          {tabIndex === 1 && (
            <Box>
              {attendance?.low_attendance_alert && (
                <Alert severity="error" sx={{ mb: 3 }}>
                  <strong>Low Attendance Alert:</strong> Your child's attendance is currently{' '}
                  {attendance.overall_percentage}%, which is below the mandatory 75% threshold. Please
                  contact the class teacher.
                </Alert>
              )}

              <Grid container spacing={3} mb={3}>
                <Grid item xs={6} sm={3}>
                  <Card sx={{ bgcolor: 'success.light', color: 'success.contrastText' }}>
                    <CardContent sx={{ textAlign: 'center' }}>
                      <Typography variant="h4" fontWeight={700}>{attendance?.present_days ?? 0}</Typography>
                      <Typography variant="caption">Present Days</Typography>
                    </CardContent>
                  </Card>
                </Grid>
                <Grid item xs={6} sm={3}>
                  <Card sx={{ bgcolor: 'error.light', color: 'error.contrastText' }}>
                    <CardContent sx={{ textAlign: 'center' }}>
                      <Typography variant="h4" fontWeight={700}>{attendance?.absent_days ?? 0}</Typography>
                      <Typography variant="caption">Absences</Typography>
                    </CardContent>
                  </Card>
                </Grid>
                <Grid item xs={6} sm={3}>
                  <Card sx={{ bgcolor: 'warning.light', color: 'warning.contrastText' }}>
                    <CardContent sx={{ textAlign: 'center' }}>
                      <Typography variant="h4" fontWeight={700}>{attendance?.late_days ?? 0}</Typography>
                      <Typography variant="caption">Late Arrivals</Typography>
                    </CardContent>
                  </Card>
                </Grid>
                <Grid item xs={6} sm={3}>
                  <Card sx={{ bgcolor: 'info.light', color: 'info.contrastText' }}>
                    <CardContent sx={{ textAlign: 'center' }}>
                      <Typography variant="h4" fontWeight={700}>{attendance ? Math.max(0, attendance.total_days - attendance.present_days - attendance.absent_days - attendance.late_days) : 0}</Typography>
                      <Typography variant="caption">Other statuses</Typography>
                    </CardContent>
                  </Card>
                </Grid>
              </Grid>

              <TableContainer component={Paper} sx={{ overflowX: 'auto', width: '100%' }}>
                <Table size="small" sx={{ minWidth: 480 }}>
                  <TableHead>
                    <TableRow sx={{ bgcolor: 'action.hover' }}>
                      <TableCell><strong>Date</strong></TableCell>
                      <TableCell><strong>Status</strong></TableCell>
                      <TableCell><strong>Period / Subject</strong></TableCell>
                      <TableCell><strong>Remarks</strong></TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {attendance?.recent_entries && attendance.recent_entries.length > 0 ? (
                      attendance.recent_entries.map((entry, index) => (
                        <TableRow key={`${entry.date}-${entry.period_number ?? index}`}>
                          <TableCell>{entry.date}</TableCell>
                          <TableCell>
                            <Chip
                              size="small"
                              label={entry.status}
                              color={
                                entry.status === 'PRESENT'
                                  ? 'success'
                                  : entry.status === 'ABSENT'
                                  ? 'error'
                                  : 'warning'
                              }
                            />
                          </TableCell>
                          <TableCell>
                            {entry.period_number ? `Period ${entry.period_number}` : 'Daily'}{' '}
                            {entry.subject_name && `(${entry.subject_name})`}
                          </TableCell>
                          <TableCell>{entry.remarks || '—'}</TableCell>
                        </TableRow>
                      ))
                    ) : (
                      <TableRow>
                        <TableCell colSpan={4} align="center">No attendance records found.</TableCell>
                      </TableRow>
                    )}
                  </TableBody>
                </Table>
              </TableContainer>
            </Box>
          )}

          {/* TAB 2: Timetable */}
          {tabIndex === 2 && (
            <Card>
              <CardContent>
                <Typography variant="h6" fontWeight={600} gutterBottom>
                  Weekly Class Timetable
                </Typography>
                <TableContainer component={Paper} sx={{ mt: 2, overflowX: 'auto', width: '100%' }}>
                  <Table size="small" sx={{ minWidth: 600 }}>
                    <TableHead>
                      <TableRow sx={{ bgcolor: 'action.hover' }}>
                        <TableCell><strong>Day</strong></TableCell>
                        <TableCell><strong>Period</strong></TableCell>
                        <TableCell><strong>Time</strong></TableCell>
                        <TableCell><strong>Subject</strong></TableCell>
                        <TableCell><strong>Teacher</strong></TableCell>
                        <TableCell><strong>Room</strong></TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {timetable?.schedule.some((day) => day.entries.length) ? (
                        timetable.schedule.flatMap((day) => day.entries.map((period, index) => (
                          <TableRow key={`${day.day_of_week}-${period.period_number}-${index}`}>
                            <TableCell sx={{ textTransform: 'capitalize' }}>{day.day_of_week.toLowerCase()}</TableCell>
                            <TableCell>{period.period_number}</TableCell>
                            <TableCell>{period.start_time} – {period.end_time}</TableCell>
                            <TableCell>{period.subject_name}</TableCell>
                            <TableCell>{period.teacher_name || '—'}</TableCell>
                            <TableCell>{period.room_number || '—'}</TableCell>
                          </TableRow>
                        )))
                      ) : (
                        <TableRow>
                          <TableCell colSpan={6} align="center">No timetable schedule published yet.</TableCell>
                        </TableRow>
                      )}
                    </TableBody>
                  </Table>
                </TableContainer>
              </CardContent>
            </Card>
          )}

          {/* TAB 3: Exams & Results */}
          {tabIndex === 3 && (
            <Box>
              <Typography variant="h6" fontWeight={600} gutterBottom>
                Upcoming Examinations Schedule
              </Typography>
              <TableContainer component={Paper} sx={{ mb: 4, overflowX: 'auto', width: '100%' }}>
                <Table size="small" sx={{ minWidth: 600 }}>
                  <TableHead>
                    <TableRow sx={{ bgcolor: 'action.hover' }}>
                      <TableCell><strong>Exam Title</strong></TableCell>
                      <TableCell><strong>Subject</strong></TableCell>
                      <TableCell><strong>Mode</strong></TableCell>
                      <TableCell><strong>Schedule Window</strong></TableCell>
                      <TableCell><strong>Duration</strong></TableCell>
                      <TableCell><strong>Total / Pass</strong></TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {exams?.upcoming_exams && exams.upcoming_exams.length > 0 ? (
                      exams.upcoming_exams.map((ex) => (
                        <TableRow key={ex.exam_id}>
                          <TableCell><strong>{ex.title}</strong></TableCell>
                          <TableCell>{ex.subject_name || 'General'}</TableCell>
                          <TableCell><Chip size="small" label={ex.is_online ? 'Online' : 'In person'} /></TableCell>
                          <TableCell>{ex.exam_date} · {ex.start_time}</TableCell>
                          <TableCell>{ex.duration_minutes} mins</TableCell>
                          <TableCell>{ex.total_marks} / {ex.passing_marks}</TableCell>
                        </TableRow>
                      ))
                    ) : (
                      <TableRow>
                        <TableCell colSpan={6} align="center">No upcoming examinations scheduled.</TableCell>
                      </TableRow>
                    )}
                  </TableBody>
                </Table>
              </TableContainer>

              <Typography variant="h6" fontWeight={600} gutterBottom>
                Published Term Report Cards
              </Typography>
              {results.length > 0 ? (
                results.map((termRes) => (
                  <Card key={termRes.result_id} sx={{ mb: 3 }}>
                    <CardContent>
                      <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
                        <Box>
                          <Typography variant="h6" fontWeight={700}>
                            {termRes.examination_title}
                          </Typography>
                          <Typography variant="caption" color="text.secondary">
                            {termRes.academic_session_name}
                          </Typography>
                        </Box>
                        <Box display="flex" gap={1}>
                          <Chip
                            label={`Score: ${termRes.total_marks_obtained}/${termRes.max_marks_possible} (${termRes.percentage}%)`}
                            color="primary"
                          />
                          <Chip
                            label={termRes.result_status === 'PASS' ? 'PASSED' : 'NEEDS IMPROVEMENT'}
                            color={termRes.result_status === 'PASS' ? 'success' : 'error'}
                          />
                          {termRes.cgpa && <Chip label={`CGPA: ${termRes.cgpa}`} color="secondary" />}
                        </Box>
                      </Box>

                      <TableContainer component={Paper} variant="outlined" sx={{ overflowX: 'auto', width: '100%' }}>
                        <Table size="small" sx={{ minWidth: 550 }}>
                          <TableHead>
                            <TableRow sx={{ bgcolor: 'action.hover' }}>
                              <TableCell><strong>Subject</strong></TableCell>
                              <TableCell align="right"><strong>Theory</strong></TableCell>
                              <TableCell align="right"><strong>Practical</strong></TableCell>
                              <TableCell align="right"><strong>Assignment</strong></TableCell>
                              <TableCell align="right"><strong>Obtained / Max</strong></TableCell>
                              <TableCell align="right"><strong>Grade</strong></TableCell>
                              <TableCell align="center"><strong>Status</strong></TableCell>
                            </TableRow>
                          </TableHead>
                          <TableBody>
                            {termRes.subjects.map((sub) => (
                              <TableRow key={sub.subject_code}>
                                <TableCell><strong>{sub.subject_name}</strong></TableCell>
                                <TableCell align="right">{sub.theory_marks ?? '—'}</TableCell>
                                <TableCell align="right">{sub.practical_marks ?? '—'}</TableCell>
                                <TableCell align="right">{sub.assignment_marks ?? '—'}</TableCell>
                                <TableCell align="right">{sub.total_marks} / {sub.max_marks}</TableCell>
                                <TableCell align="right"><strong>{sub.grade || '—'}</strong></TableCell>
                                <TableCell align="center">
                                  <Chip
                                    size="small"
                                    label={sub.is_pass ? 'PASS' : 'FAIL'}
                                    color={sub.is_pass ? 'success' : 'error'}
                                  />
                                </TableCell>
                              </TableRow>
                            ))}
                          </TableBody>
                        </Table>
                      </TableContainer>
                    </CardContent>
                  </Card>
                ))
              ) : (
                <Alert severity="info">No published report cards available yet.</Alert>
              )}
            </Box>
          )}

          {/* TAB 4: Assignments & LMS */}
          {tabIndex === 4 && (
            <Box>
              <Typography variant="h6" fontWeight={600} gutterBottom>
                Homework & Assignments
              </Typography>
              <TableContainer component={Paper} sx={{ mb: 4, overflowX: 'auto', width: '100%' }}>
                <Table size="small" sx={{ minWidth: 600 }}>
                  <TableHead>
                    <TableRow sx={{ bgcolor: 'action.hover' }}>
                      <TableCell><strong>Assignment Title</strong></TableCell>
                      <TableCell><strong>Subject</strong></TableCell>
                      <TableCell><strong>Teacher</strong></TableCell>
                      <TableCell><strong>Due Date</strong></TableCell>
                      <TableCell><strong>Submission Status</strong></TableCell>
                      <TableCell><strong>Score</strong></TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {assignments.length > 0 ? (
                      assignments.map((asgn) => {
                        const assignmentStatus = asgn.score != null ? 'GRADED'
                          : asgn.is_late ? 'LATE' : asgn.is_submitted ? 'SUBMITTED' : 'NOT SUBMITTED'
                        return (
                        <TableRow key={asgn.id}>
                          <TableCell>
                            <Typography variant="body2" fontWeight={600}>{asgn.title}</Typography>
                            {asgn.teacher_feedback && (
                              <Typography variant="caption" color="text.secondary">
                                Teacher feedback: {asgn.teacher_feedback}
                              </Typography>
                            )}
                          </TableCell>
                          <TableCell>{asgn.subject_name}</TableCell>
                          <TableCell>{asgn.teacher_name}</TableCell>
                          <TableCell>{new Date(asgn.due_date).toLocaleDateString()}</TableCell>
                          <TableCell>
                            <Chip
                              size="small"
                              label={assignmentStatus}
                              color={
                                assignmentStatus === 'GRADED' || assignmentStatus === 'SUBMITTED'
                                  ? 'success'
                                  : assignmentStatus === 'LATE'
                                  ? 'warning'
                                  : 'default'
                              }
                            />
                          </TableCell>
                          <TableCell>
                            {asgn.score !== null && asgn.score !== undefined
                              ? `${asgn.score} / ${asgn.max_score}`
                              : 'Pending'}
                          </TableCell>
                        </TableRow>
                        )
                      })
                    ) : (
                      <TableRow>
                        <TableCell colSpan={6} align="center">No active assignments for this class.</TableCell>
                      </TableRow>
                    )}
                  </TableBody>
                </Table>
              </TableContainer>

              <Typography variant="h6" fontWeight={600} gutterBottom>
                Course Study Materials
              </Typography>
              <TableContainer component={Paper} sx={{ overflowX: 'auto', width: '100%' }}>
                <Table size="small" sx={{ minWidth: 480 }}>
                  <TableHead>
                    <TableRow sx={{ bgcolor: 'action.hover' }}>
                      <TableCell><strong>Material Title</strong></TableCell>
                      <TableCell><strong>Subject</strong></TableCell>
                      <TableCell><strong>Category</strong></TableCell>
                      <TableCell><strong>Uploaded</strong></TableCell>
                      <TableCell align="center"><strong>Action</strong></TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {materials.length > 0 ? (
                      materials.map((mat) => (
                        <TableRow key={mat.id}>
                          <TableCell><strong>{mat.title}</strong></TableCell>
                          <TableCell>{mat.subject_name}</TableCell>
                          <TableCell><Chip size="small" label={mat.material_type} /></TableCell>
                          <TableCell>{new Date(mat.created_at).toLocaleDateString()}</TableCell>
                          <TableCell align="center">
                            <Button
                              size="small"
                              variant="outlined"
                              startIcon={<DownloadIcon />}
                              disabled={!mat.download_url && !mat.external_url}
                              onClick={() => {
                                if (mat.download_url) void downloadMaterial(mat.id)
                                else if (mat.external_url && /^https?:\/\//.test(mat.external_url)) {
                                  window.open(mat.external_url, '_blank', 'noopener,noreferrer')
                                }
                              }}
                            >
                              Download
                            </Button>
                          </TableCell>
                        </TableRow>
                      ))
                    ) : (
                      <TableRow>
                        <TableCell colSpan={5} align="center">No study materials published yet.</TableCell>
                      </TableRow>
                    )}
                  </TableBody>
                </Table>
              </TableContainer>
            </Box>
          )}

          {/* TAB 5: Fees & Payments */}
          {tabIndex === 5 && (
            <Box>
              <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
                <Typography variant="h6" fontWeight={600}>
                  Institutional Fee Invoices & Payment Receipts
                </Typography>
                <Chip
                  label={`Total Outstanding: ₹${fees?.total_due?.toLocaleString() ?? 0}`}
                  color={fees && fees.total_due > 0 ? 'warning' : 'success'}
                  sx={{ fontWeight: 700 }}
                />
              </Box>

              <TableContainer component={Paper} sx={{ mb: 4, overflowX: 'auto', width: '100%' }}>
                <Table size="small" sx={{ minWidth: 600 }}>
                  <TableHead>
                    <TableRow sx={{ bgcolor: 'action.hover' }}>
                      <TableCell><strong>Invoice #</strong></TableCell>
                      <TableCell><strong>Title</strong></TableCell>
                      <TableCell><strong>Due Date</strong></TableCell>
                      <TableCell align="right"><strong>Total Amount</strong></TableCell>
                      <TableCell align="right"><strong>Paid</strong></TableCell>
                      <TableCell align="right"><strong>Pending Balance</strong></TableCell>
                      <TableCell><strong>Status</strong></TableCell>
                      <TableCell align="center"><strong>Pay Online</strong></TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {fees?.invoices && fees.invoices.length > 0 ? (
                      fees.invoices.map((inv) => (
                        <TableRow key={inv.id}>
                          <TableCell><strong>{inv.invoice_number}</strong></TableCell>
                          <TableCell>{inv.title}</TableCell>
                          <TableCell>{new Date(inv.due_date).toLocaleDateString()}</TableCell>
                          <TableCell align="right">₹{inv.total_amount.toLocaleString()}</TableCell>
                          <TableCell align="right">₹{inv.paid_amount.toLocaleString()}</TableCell>
                          <TableCell align="right" sx={{ color: inv.balance_amount > 0 ? 'error.main' : 'text.primary', fontWeight: 600 }}>
                            ₹{inv.balance_amount.toLocaleString()}
                          </TableCell>
                          <TableCell>
                            <Chip
                              size="small"
                              label={inv.status}
                              color={inv.status === 'PAID' ? 'success' : inv.status === 'PARTIALLY_PAID' ? 'info' : 'warning'}
                            />
                          </TableCell>
                          <TableCell align="center">
                            {inv.balance_amount > 0 ? (
                              <Button
                                size="small"
                                variant="contained"
                                color="success"
                                startIcon={<PaymentIcon />}
                                disabled={paying}
                                onClick={() => void payInvoice(inv.id, inv.balance_amount)}
                              >
                                Pay Now
                              </Button>
                            ) : (
                              <Chip size="small" label="Settled" color="success" variant="outlined" />
                            )}
                          </TableCell>
                        </TableRow>
                      ))
                    ) : (
                      <TableRow>
                        <TableCell colSpan={8} align="center">No fee invoices issued.</TableCell>
                      </TableRow>
                    )}
                  </TableBody>
                </Table>
              </TableContainer>

              <Typography variant="h6" fontWeight={600} gutterBottom>
                Payment Ledger & Official Receipts
              </Typography>
              <TableContainer component={Paper} sx={{ overflowX: 'auto', width: '100%' }}>
                <Table size="small" sx={{ minWidth: 480 }}>
                  <TableHead>
                    <TableRow sx={{ bgcolor: 'action.hover' }}>
                      <TableCell><strong>Receipt #</strong></TableCell>
                      <TableCell><strong>Payment Date</strong></TableCell>
                      <TableCell><strong>Payment Method</strong></TableCell>
                      <TableCell><strong>Reference / Txn ID</strong></TableCell>
                      <TableCell align="right"><strong>Amount Paid</strong></TableCell>
                      <TableCell><strong>Status</strong></TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {fees?.payments && fees.payments.length > 0 ? (
                      fees.payments.map((p) => (
                        <TableRow key={p.id}>
                          <TableCell><strong>{p.receipt_number}</strong></TableCell>
                          <TableCell>{new Date(p.payment_date).toLocaleDateString()}</TableCell>
                          <TableCell><Chip size="small" label={p.payment_mode} /></TableCell>
                          <TableCell>{p.transaction_reference || '—'}</TableCell>
                          <TableCell align="right"><strong>₹{p.amount.toLocaleString()}</strong></TableCell>
                          <TableCell><Chip size="small" label={p.status} color="success" /></TableCell>
                        </TableRow>
                      ))
                    ) : (
                      <TableRow>
                        <TableCell colSpan={6} align="center">No completed payments recorded.</TableCell>
                      </TableRow>
                    )}
                  </TableBody>
                </Table>
              </TableContainer>
            </Box>
          )}

          {/* TAB 6: Teacher Messages */}
          {tabIndex === 6 && (
            <Grid container spacing={3}>
              <Grid item xs={12} md={5}>
                <Card>
                  <CardContent>
                    <Typography variant="h6" fontWeight={600} gutterBottom>
                      Send Message to Faculty
                    </Typography>
                    <Divider sx={{ mb: 2 }} />

                    <FormControl fullWidth size="small" sx={{ mb: 2 }}>
                      <InputLabel id="teacher-select-label">Select Teacher</InputLabel>
                      <Select
                        labelId="teacher-select-label"
                        value={messageTeacherId}
                        label="Select Teacher"
                        onChange={(e) => setMessageTeacherId(e.target.value)}
                      >
                        {teachers.map((t) => (
                          <MenuItem key={`${t.teacher_user_id}-${t.subject_name}`} value={t.teacher_user_id}>
                            {t.teacher_name} ({t.subject_name})
                          </MenuItem>
                        ))}
                      </Select>
                    </FormControl>

                    <TextField
                      fullWidth
                      size="small"
                      label="Subject"
                      value={messageSubject}
                      onChange={(e) => setMessageSubject(e.target.value)}
                      sx={{ mb: 2 }}
                    />

                    <TextField
                      fullWidth
                      multiline
                      rows={4}
                      size="small"
                      label="Message Content"
                      value={messageBody}
                      onChange={(e) => setMessageBody(e.target.value)}
                      placeholder="Write your inquiry or feedback regarding your child's academics..."
                      sx={{ mb: 2 }}
                    />

                    <Button
                      fullWidth
                      variant="contained"
                      startIcon={<SendIcon />}
                      disabled={sendingMessage || !messageTeacherId}
                      onClick={handleSendMessage}
                    >
                      {sendingMessage ? 'Sending...' : 'Send Message'}
                    </Button>
                  </CardContent>
                </Card>
              </Grid>

              <Grid item xs={12} md={7}>
                <Card>
                  <CardContent>
                    <Typography variant="h6" fontWeight={600} gutterBottom>
                      Communication History
                    </Typography>
                    <Divider sx={{ mb: 2 }} />

                    {messages.length > 0 ? (
                      <List sx={{ width: '100%' }}>
                        {messages.map((m) => (
                          <Paper key={m.id} variant="outlined" sx={{ p: 2, mb: 2 }}>
                            <Box display="flex" justifyContent="space-between" alignItems="center" mb={1}>
                              <Typography variant="subtitle2" fontWeight={700}>
                                {m.subject}
                              </Typography>
                              <Chip
                                size="small"
                                label={m.sender_role === 'PARENT' ? 'Sent by You' : `From ${m.teacher_name}`}
                                color={m.sender_role === 'PARENT' ? 'primary' : 'secondary'}
                                sx={{ fontSize: '0.7rem' }}
                              />
                            </Box>
                            <Typography variant="body2" sx={{ mb: 1, whiteSpace: 'pre-wrap' }}>
                              {m.message}
                            </Typography>
                            <Typography variant="caption" color="text.secondary">
                              Sent on {new Date(m.created_at).toLocaleString()}
                            </Typography>

                            {/* Replies */}
                            {m.replies && m.replies.length > 0 && (
                              <Box sx={{ mt: 2, pl: 2, borderLeft: 2, borderColor: 'primary.main' }}>
                                {m.replies.map((r) => (
                                  <Box key={r.id} sx={{ mb: 1 }}>
                                    <Typography variant="caption" fontWeight={600} color="primary">
                                      {r.sender_role === 'PARENT' ? r.parent_name : r.teacher_name} ({r.sender_role}):
                                    </Typography>
                                    <Typography variant="body2">{r.message}</Typography>
                                  </Box>
                                ))}
                              </Box>
                            )}
                          </Paper>
                        ))}
                      </List>
                    ) : (
                      <Alert severity="info">No messages exchanged yet with teachers.</Alert>
                    )}
                  </CardContent>
                </Card>
              </Grid>
            </Grid>
          )}
        </>
      )}

      {/* Link Child Modal */}
      <Dialog open={openLinkDialog} onClose={() => setOpenLinkDialog(false)} maxWidth="sm" fullWidth>
        <DialogTitle sx={{ fontWeight: 700 }}>
          Link Child / Student
        </DialogTitle>
        <DialogContent dividers>
          <Alert severity="info" sx={{ mb: 3 }}>
            <strong>Security Notice:</strong> To prevent unauthorized access, linking requires an exact
            student Admission Number and either an administrator-provided one-time verification code or subsequent
            institution administrator approval.
          </Alert>

          <TextField
            fullWidth
            required
            label="Student Admission Number"
            placeholder="e.g. ADM-2026-001"
            value={admissionNumber}
            onChange={(e) => setAdmissionNumber(e.target.value)}
            sx={{ mb: 2 }}
          />

          <FormControl fullWidth sx={{ mb: 2 }}>
            <InputLabel id="relationship-type-label">Relationship to Student</InputLabel>
            <Select
              labelId="relationship-type-label"
              value={relationshipType}
              label="Relationship to Student"
              onChange={(e) => setRelationshipType(e.target.value)}
            >
              <MenuItem value="FATHER">Father</MenuItem>
              <MenuItem value="MOTHER">Mother</MenuItem>
              <MenuItem value="GUARDIAN">Legal Guardian</MenuItem>
              <MenuItem value="OTHER">Other</MenuItem>
            </Select>
          </FormControl>

          <TextField
            fullWidth
            label="Verification Code (Optional)"
            placeholder="e.g. LNK-9A8B7C (obtained from institution admin)"
            helperText="If provided, your child will be verified immediately. Otherwise, it will require manual school admin approval."
            value={verificationCode}
            onChange={(e) => setVerificationCode(e.target.value)}
          />
        </DialogContent>
        <DialogActions sx={{ px: 3, py: 2 }}>
          <Button onClick={() => setOpenLinkDialog(false)} disabled={linkingSubmitting}>
            Cancel
          </Button>
          <Button
            variant="contained"
            onClick={handleLinkChildSubmit}
            disabled={linkingSubmitting || !admissionNumber}
          >
            {linkingSubmitting ? 'Submitting...' : 'Submit Link Request'}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  )
}
