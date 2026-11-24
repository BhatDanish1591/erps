import { AttendanceCohortReport } from './AttendanceCohortReport'
import { PageHeader } from '@/components/ui/PageHeader'
import { useState, useEffect } from 'react'
import { useSearchParams } from 'react-router-dom'
import {
  Box,
  Card,
  CardContent,
  Typography,
  Tabs,
  Tab,
  Button,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Chip,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  MenuItem,
  Grid,
  Alert,
  Switch,
  FormControlLabel,
} from '@mui/material'
import {
  CheckCircle as PresentIcon,
  Cancel as AbsentIcon,
  AccessTime as LateIcon,
  EventBusy as LeaveIcon,
  QrCode as QrIcon,
  History as HistoryIcon,
  Warning as WarningIcon,
  AssignmentTurnedIn as RollCallIcon,
  Dashboard as DashboardIcon,
  LocationOn as GpsIcon,
  Refresh as RefreshIcon,
} from '@mui/icons-material'

import {
  attendanceApi,
  AdminAttendanceOverview,
  AttendanceRosterStudent,
  LowAttendanceAlertItem,
  AttendanceCorrectionLog,
  StudentMonthlyAttendanceReport,
  TeacherAttendanceRecord,
  QRCodeAttendanceResponse,
} from '../../api/attendance'
import { academicsApi, AcademicSession, CollegeSemester, Course, Department, SchoolClass, Section, Subject } from '../../api/academics'
import { useAuthStore } from '@/store/authStore'

export default function AttendancePage() {
  const isCollege = useAuthStore(({ user }) => user?.institutions.some(
    (institution) => institution.tenant_id === user.current_tenant_id && institution.institution_type === 'COLLEGE',
  ) ?? false)
  const user = useAuthStore((state) => state.user)
  const isAdmin = Boolean(user?.is_superadmin || user?.current_role === 'INSTITUTION_ADMIN')
  const isTeacher = user?.current_role === 'TEACHER'
  const teacherCollege = isTeacher && isCollege
  const [params] = useSearchParams()
  const requestedTab = params.get('tab')
  const [currentTab, setCurrentTab] = useState(isTeacher || requestedTab === 'roll-call' ? 1 : 0)
  useEffect(() => { if (requestedTab === 'roll-call') setCurrentTab(1) }, [requestedTab])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [successMsg, setSuccessMsg] = useState<string | null>(null)

  // Academic dependencies
  const [sessions, setSessions] = useState<AcademicSession[]>([])
  const [classes, setClasses] = useState<SchoolClass[]>([])
  const [departments, setDepartments] = useState<Department[]>([])
  const [courses, setCourses] = useState<Course[]>([])
  const [semesters, setSemesters] = useState<CollegeSemester[]>([])
  const [sections, setSections] = useState<Section[]>([])
  const [subjects, setSubjects] = useState<Subject[]>([])

  // Tab 0: Admin Overview
  const [overviewDate, setOverviewDate] = useState(new Date().toISOString().split('T')[0])
  const [overview, setOverview] = useState<AdminAttendanceOverview | null>(null)
  const [lowAttendanceList, setLowAttendanceList] = useState<LowAttendanceAlertItem[]>([])

  // Tab 1: Roll Call / Teacher Marking
  const [selectedSessionId, setSelectedSessionId] = useState<string>('')
  const [selectedClassId, setSelectedClassId] = useState<string>('')
  const [selectedDepartmentId, setSelectedDepartmentId] = useState('')
  const [selectedCourseId, setSelectedCourseId] = useState('')
  const [selectedSemesterId, setSelectedSemesterId] = useState('')
  const [selectedSectionId, setSelectedSectionId] = useState<string>('')
  const [selectedSubjectId, setSelectedSubjectId] = useState<string>('')
  const [selectedPeriod, setSelectedPeriod] = useState<number>(1)
  const [markingDate, setMarkingDate] = useState(() => {
    const today = new Date()
    return new Date(today.getTime() - today.getTimezoneOffset() * 60_000).toISOString().slice(0, 10)
  })
  const [markingType, setMarkingType] = useState('DAILY')
  const [sessionRemarks, setSessionRemarks] = useState('')
  const [notifyParents, setNotifyParents] = useState(false)
  const [loadedRoster, setLoadedRoster] = useState<{ key: string; students: AttendanceRosterStudent[] }>()
  const [studentStatuses, setStudentStatuses] = useState<{ [studentId: string]: 'PRESENT' | 'ABSENT' | 'LATE' | 'LEAVE' }>({})
  const [studentRemarks, setStudentRemarks] = useState<{ [studentId: string]: string }>({})
  const [isSessionSubmitted, setIsSessionSubmitted] = useState(false)

  // Tab 2: Corrections
  const [correctionLogs, setCorrectionLogs] = useState<AttendanceCorrectionLog[]>([])
  const [correctionDialogOpen, setCorrectionDialogOpen] = useState(false)
  const [correctionEntryId, setCorrectionEntryId] = useState('')
  const [correctionNewStatus, setCorrectionNewStatus] = useState('PRESENT')
  const [correctionReason, setCorrectionReason] = useState('')

  // Tab 3: Monthly Student Report
  const [searchStudentId, setSearchStudentId] = useState('')
  const [reportYear, setReportYear] = useState(new Date().getFullYear())
  const [reportMonth, setReportMonth] = useState(new Date().getMonth() + 1)
  const [monthlyReport, setMonthlyReport] = useState<StudentMonthlyAttendanceReport | null>(null)

  // Tab 4: QR & Teacher Punch
  const [generatedQR, setGeneratedQR] = useState<QRCodeAttendanceResponse | null>(null)
  const [qrValidityMinutes, setQrValidityMinutes] = useState(15)
  const [scanTokenInput, setScanTokenInput] = useState('')
  const [teacherPunchRecord, setTeacherPunchRecord] = useState<TeacherAttendanceRecord | null>(null)

  const sessionType = isTeacher ? 'PERIOD_WISE' : markingType
  const schoolClassId = isTeacher ? sections.find((section) => section.id === selectedSectionId)?.class_id : selectedClassId
  const cohort = {
    class_id: isCollege ? undefined : schoolClassId || undefined,
    course_id: isCollege ? selectedCourseId || undefined : undefined,
    semester_id: isCollege ? selectedSemesterId || undefined : undefined,
    section_id: selectedSectionId || undefined,
    subject_id: sessionType === 'DAILY' ? undefined : selectedSubjectId || undefined,
    period_number: sessionType === 'PERIOD_WISE' ? selectedPeriod : undefined,
  }
  const rosterRequest = {
    academic_session_id: selectedSessionId,
    session_date: markingDate,
    session_type: sessionType,
    ...cohort,
  }
  const rosterKey = JSON.stringify(rosterRequest)
  const roster = loadedRoster?.key === rosterKey ? loadedRoster.students : []
  const cohortSelected = isCollege ? Boolean(selectedCourseId && selectedSemesterId) : Boolean(schoolClassId)
  const rosterReady = Boolean(selectedSessionId && markingDate && cohortSelected &&
    (!(isTeacher || sessionType === 'SUBJECT_WISE') || selectedSubjectId) &&
    (sessionType !== 'PERIOD_WISE' || (Number.isInteger(selectedPeriod) && selectedPeriod > 0)))

  // Initial load
  useEffect(() => {
    loadAcademics()
    if (!isAdmin && !isTeacher) loadOverview()
  }, [])

  const loadAcademics = async () => {
    try {
      const [sessRes, clsRes, subRes, departmentRes, courseRes] = await Promise.all([
        academicsApi.getSessions(),
        isCollege ? null : academicsApi.getClasses(),
        academicsApi.getSubjects(),
        isCollege ? academicsApi.getDepartments() : null,
        isCollege ? academicsApi.getCourses() : null,
      ])
      const sessList = sessRes.data || sessRes || []
      const clsList = clsRes?.data || clsRes || []
      const subList = subRes.data || subRes || []

      setSessions(sessList)
      setClasses(clsList)
      setSubjects(subList)
      setDepartments(departmentRes?.data || [])
      setCourses(courseRes?.data || [])

      const activeSess = sessList.find((s: AcademicSession) => s.is_current) || sessList[0]
      if (activeSess) setSelectedSessionId(activeSess.id)
      if (!isTeacher && clsList.length > 0) {
        setSelectedClassId(clsList[0].id)
      }
    } catch (err: any) {
      setError(err?.response?.data?.error?.message || 'Failed to load attendance groups')
    }
  }

  useEffect(() => {
    setSemesters([])
    if (!isCollege || !selectedCourseId) return
    let active = true
    academicsApi.getSemesters(selectedCourseId).then((response) => {
      if (active) setSemesters(response.data || [])
    }).catch(() => {
      if (active) setError('Failed to load semesters for this course')
    })
    return () => { active = false }
  }, [isCollege, selectedCourseId])

  const sectionSemesterId = teacherCollege ? '' : selectedSemesterId
  useEffect(() => {
    setSections([])
    if (isCollege ? !selectedCourseId || (!teacherCollege && !sectionSemesterId) : !isTeacher && !selectedClassId) return
    let active = true
    const filters = isCollege
      ? { course_id: selectedCourseId, semester_id: sectionSemesterId || undefined }
      : isTeacher ? undefined : { class_id: selectedClassId }
    academicsApi.getSections(filters).then((response) => {
      if (!active) return
      const nextSections: Section[] = response.data || []
      setSections(nextSections)
      if (!isCollege && !isTeacher) setSelectedSectionId(nextSections[0]?.id || '')
    }).catch(() => {
      if (active) setError('Failed to load sections')
    })
    return () => { active = false }
  }, [isCollege, isTeacher, teacherCollege, selectedClassId, selectedCourseId, sectionSemesterId])

  const selectCourse = (courseId: string) => {
    setSelectedCourseId(courseId)
    setSelectedSemesterId('')
    setSelectedSectionId('')
    setSelectedSubjectId('')
    setSemesters([])
    setSections([])
  }

  const selectSemester = (semesterId: string, sectionId = '') => {
    setSelectedSemesterId(semesterId)
    setSelectedSectionId(sectionId)
    if (isTeacher) setSelectedSubjectId('')
    if (!teacherCollege) setSections([])
  }

  const selectClass = (classId: string) => {
    setSelectedClassId(classId)
    setSelectedSectionId('')
    setSections([])
  }

  const loadOverview = async () => {
    setLoading(true)
    setError(null)
    try {
      const [ovData, lowData] = await Promise.all([
        attendanceApi.getOverview(overviewDate),
        attendanceApi.getLowAttendanceAlerts(75.0),
      ])
      setOverview(ovData)
      setLowAttendanceList(lowData)
    } catch (err: any) {
      setError(err?.response?.data?.error?.message || 'Failed to load attendance overview')
    } finally {
      setLoading(false)
    }
  }

  const loadRoster = async () => {
    if (!rosterReady) {
      setError('Complete the attendance group and session details first.')
      return
    }
    setLoading(true)
    setError(null)
    try {
      const res = await attendanceApi.getRoster(rosterRequest)

      setLoadedRoster({ key: rosterKey, students: res.students })
      setIsSessionSubmitted(res.is_submitted)

      // Initialize status mapping
      const statusMap: { [studentId: string]: 'PRESENT' | 'ABSENT' | 'LATE' | 'LEAVE' } = {}
      const remarkMap: { [studentId: string]: string } = {}

      res.students.forEach((s) => {
        statusMap[s.student_id] = (s.current_status as any) || 'PRESENT'
        if (s.remarks) remarkMap[s.student_id] = s.remarks
      })

      setStudentStatuses(statusMap)
      setStudentRemarks(remarkMap)
    } catch (err: any) {
      setError(err?.response?.data?.error?.message || 'Failed to load student roster')
    } finally {
      setLoading(false)
    }
  }

  const handleMarkAll = (status: 'PRESENT' | 'ABSENT') => {
    const updated: { [studentId: string]: 'PRESENT' | 'ABSENT' | 'LATE' | 'LEAVE' } = {}
    roster.forEach((s) => {
      updated[s.student_id] = status
    })
    setStudentStatuses(updated)
  }

  const handleStatusChange = (studentId: string, status: 'PRESENT' | 'ABSENT' | 'LATE' | 'LEAVE') => {
    setStudentStatuses((prev) => ({ ...prev, [studentId]: status }))
  }

  const handleSubmitRollCall = async () => {
    if (roster.length === 0) {
      setError('Roster is empty. Please load enrolled students first.')
      return
    }

    setLoading(true)
    setError(null)
    try {
      const entries = roster.map((s) => ({
        student_id: s.student_id,
        status: studentStatuses[s.student_id] || 'PRESENT',
        remarks: studentRemarks[s.student_id] || undefined,
        marked_via: 'WEB',
      }))

      await attendanceApi.submitSession({
        ...rosterRequest,
        remarks: sessionRemarks || undefined,
        entries,
        notify_absent_parents: notifyParents,
      })

      setSuccessMsg('Attendance session successfully recorded and submitted!')
      setIsSessionSubmitted(true)
      loadOverview()
    } catch (err: any) {
      setError(err?.response?.data?.error?.message || 'Failed to submit attendance session')
    } finally {
      setLoading(false)
    }
  }

  const loadCorrections = async () => {
    setLoading(true)
    try {
      const logs = await attendanceApi.getCorrectionLogs()
      setCorrectionLogs(logs)
    } catch (err: any) {
      setError(err?.response?.data?.error?.message || 'Failed to load correction logs')
    } finally {
      setLoading(false)
    }
  }

  const handleExecuteCorrection = async () => {
    if (!correctionEntryId.trim() || !correctionReason.trim()) {
      setError('Please provide entry ID and a valid reason')
      return
    }
    setLoading(true)
    try {
      await attendanceApi.correctEntry({
        entry_id: correctionEntryId.trim(),
        new_status: correctionNewStatus,
        reason: correctionReason.trim(),
      })
      setSuccessMsg('Attendance record corrected and audit log persisted!')
      setCorrectionDialogOpen(false)
      setCorrectionReason('')
      setCorrectionEntryId('')
      loadCorrections()
      loadOverview()
    } catch (err: any) {
      setError(err?.response?.data?.error?.message || 'Correction failed')
    } finally {
      setLoading(false)
    }
  }

  const handleLoadMonthlyReport = async () => {
    if (!searchStudentId.trim()) {
      setError('Please enter a valid Student ID')
      return
    }
    setLoading(true)
    try {
      const rep = await attendanceApi.getStudentMonthlyReport(searchStudentId.trim(), reportYear, reportMonth)
      setMonthlyReport(rep)
    } catch (err: any) {
      setError(err?.response?.data?.error?.message || 'Failed to load monthly student report')
    } finally {
      setLoading(false)
    }
  }

  const handleGenerateQR = async () => {
    if (!selectedSessionId || !cohortSelected) {
      setError('Select the academic session and attendance group in Roll Call first.')
      return
    }
    setLoading(true)
    try {
      const res = await attendanceApi.generateQR(selectedSessionId, {
        ...cohort,
        validity_minutes: qrValidityMinutes,
      })
      setGeneratedQR(res)
      setSuccessMsg(`QR Attendance token generated! Valid for ${qrValidityMinutes} minutes.`)
    } catch (err: any) {
      setError(err?.response?.data?.error?.message || 'Failed to generate QR attendance')
    } finally {
      setLoading(false)
    }
  }

  const handleScanQR = async () => {
    if (!scanTokenInput.trim()) {
      setError('Please enter a QR token')
      return
    }
    setLoading(true)
    try {
      await attendanceApi.scanQR({ qr_token: scanTokenInput.trim() })
      setSuccessMsg('Attendance successfully marked via QR token!')
      setScanTokenInput('')
      loadOverview()
    } catch (err: any) {
      setError(err?.response?.data?.error?.message || 'QR Scan submission failed')
    } finally {
      setLoading(false)
    }
  }

  const handleTeacherCheckIn = async () => {
    setLoading(true)
    try {
      let lat: number | undefined
      let lon: number | undefined
      if (navigator.geolocation) {
        navigator.geolocation.getCurrentPosition(
          (pos) => {
            lat = pos.coords.latitude
            lon = pos.coords.longitude
          },
          () => {}
        )
      }

      const res = await attendanceApi.teacherCheckIn({
        check_in_method: 'WEB',
        latitude: lat,
        longitude: lon,
        notes: 'Instructor web portal check-in',
      })
      setTeacherPunchRecord(res)
      setSuccessMsg('Teacher daily check-in recorded successfully!')
    } catch (err: any) {
      setError(err?.response?.data?.error?.message || 'Teacher check-in failed')
    } finally {
      setLoading(false)
    }
  }

  const handleTeacherCheckOut = async () => {
    setLoading(true)
    try {
      const res = await attendanceApi.teacherCheckOut({
        notes: 'Instructor web portal check-out',
      })
      setTeacherPunchRecord(res)
      setSuccessMsg('Teacher daily check-out recorded successfully!')
    } catch (err: any) {
      setError(err?.response?.data?.error?.message || 'Teacher check-out failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
      {/* Top Header */}
      <PageHeader
        title="Attendance"
        description={isAdmin ? (
          isCollege ? 'Monitor student attendance across departments and courses.' : 'Monitor student attendance across classes and sections.'
        ) : 'Take roll call, review attendance, and manage corrections.'}
        icon={<RollCallIcon />}
      >

        {isAdmin ? (
          <TextField select size="small" label="Attendance tools" value={currentTab} sx={{ minWidth: 190 }}
            onChange={(event) => {
              const next = Number(event.target.value)
              setCurrentTab(next)
              if (next === 2) void loadCorrections()
            }}>
            <MenuItem value={0}>Attendance reports</MenuItem>
            <MenuItem value={1}>Teacher roll call</MenuItem>
            <MenuItem value={2}>Corrections & audit</MenuItem>
            <MenuItem value={3}>Student monthly history</MenuItem>
            <MenuItem value={4}>QR & faculty punch</MenuItem>
          </TextField>
        ) : isTeacher && currentTab === 1 ? null : (
        <Box className="flex items-center gap-3">
          <Button
            variant="outlined"
            startIcon={<RefreshIcon />}
            onClick={() => {
              if (currentTab === 0) loadOverview()
              if (currentTab === 1) loadRoster()
              if (currentTab === 2) loadCorrections()
            }}
          >
            Refresh
          </Button>
        </Box>
        )}
      </PageHeader>

      {/* Notifications */}
      {error && (
        <Alert severity="error" onClose={() => setError(null)}>
          {error}
        </Alert>
      )}
      {successMsg && (
        <Alert severity="success" onClose={() => setSuccessMsg(null)}>
          {successMsg}
        </Alert>
      )}

      {/* Navigation Tabs */}
      {!isAdmin && <Tabs
        value={currentTab}
        onChange={(_, val) => {
          setCurrentTab(val)
          if (val === 0 && !overview) void loadOverview()
          if (val === 2) loadCorrections()
        }}
        variant="scrollable"
        scrollButtons="auto"
        className="border-b border-gray-200"
      >
        <Tab
          icon={<DashboardIcon />}
          iconPosition="start"
          label="Attendance overview"
        />
        <Tab icon={<RollCallIcon />} iconPosition="start" label="Teacher Roll Call" />
        <Tab icon={<HistoryIcon />} iconPosition="start" label="Corrections & Audit" />
        <Tab icon={<LeaveIcon />} iconPosition="start" label="Student Monthly History" />
        <Tab icon={<QrIcon />} iconPosition="start" label="QR & Faculty Punch" />
      </Tabs>}

      {isAdmin && (
        <Box hidden={currentTab !== 0}>
          <AttendanceCohortReport key={user?.current_tenant_id} tenantId={user?.current_tenant_id}
            isCollege={isCollege} sessions={sessions} departments={departments} courses={courses} classes={classes} />
        </Box>
      )}

      {currentTab === 0 && !isAdmin && (
          <Box className="space-y-6">
            <Box className="flex items-center gap-4 bg-white p-4 rounded-xl border border-gray-200 shadow-sm">
              <Typography variant="subtitle2" className="font-semibold text-gray-700">
                Select Attendance Date:
              </Typography>
              <TextField
                type="date"
                size="small"
                value={overviewDate}
                onChange={(e) => setOverviewDate(e.target.value)}
              />
              <Button variant="contained" onClick={loadOverview} disabled={loading}>
                Load Metrics
              </Button>
            </Box>

            {/* Metric Cards */}
            <Grid container spacing={3}>
              <Grid item xs={12} sm={6} md={3}>
                <Card className="border border-blue-200 bg-blue-50/50 shadow-sm">
                  <CardContent className="p-4">
                    <Typography variant="caption" className="text-blue-700 uppercase font-bold tracking-wider">
                      Total Enrolled Students
                    </Typography>
                    <Typography variant="h4" className="font-extrabold text-blue-900 mt-1">
                      {overview?.total_students_enrolled ?? 0}
                    </Typography>
                    <Typography variant="caption" className="text-gray-500">
                      Active registered profiles
                    </Typography>
                  </CardContent>
                </Card>
              </Grid>

              <Grid item xs={12} sm={6} md={3}>
                <Card className="border border-green-200 bg-green-50/50 shadow-sm">
                  <CardContent className="p-4">
                    <Typography variant="caption" className="text-green-700 uppercase font-bold tracking-wider">
                      Attendance Rate Today
                    </Typography>
                    <Typography variant="h4" className="font-extrabold text-green-900 mt-1">
                      {overview?.overall_attendance_rate_today ?? 0}%
                    </Typography>
                    <Typography variant="caption" className="text-gray-500">
                      {overview?.total_present_today ?? 0} Present + {overview?.total_late_today ?? 0} Late
                    </Typography>
                  </CardContent>
                </Card>
              </Grid>

              <Grid item xs={12} sm={6} md={3}>
                <Card className="border border-red-200 bg-red-50/50 shadow-sm">
                  <CardContent className="p-4">
                    <Typography variant="caption" className="text-red-700 uppercase font-bold tracking-wider">
                      Total Absentees Today
                    </Typography>
                    <Typography variant="h4" className="font-extrabold text-red-900 mt-1">
                      {overview?.total_absent_today ?? 0}
                    </Typography>
                    <Typography variant="caption" className="text-gray-500">
                      {overview?.total_leave_today ?? 0} on official leave
                    </Typography>
                  </CardContent>
                </Card>
              </Grid>

              <Grid item xs={12} sm={6} md={3}>
                <Card className="border border-amber-200 bg-amber-50/50 shadow-sm">
                  <CardContent className="p-4">
                    <Typography variant="caption" className="text-amber-800 uppercase font-bold tracking-wider flex items-center gap-1">
                      <WarningIcon fontSize="small" /> Low Attendance Alerts
                    </Typography>
                    <Typography variant="h4" className="font-extrabold text-amber-900 mt-1">
                      {overview?.low_attendance_students_count ?? 0}
                    </Typography>
                    <Typography variant="caption" className="text-gray-500">
                      Students below 75% threshold
                    </Typography>
                  </CardContent>
                </Card>
              </Grid>
            </Grid>

            {/* Low Attendance Alert Table */}
            <Card className="border border-gray-200 shadow-sm">
              <CardContent className="p-4 space-y-4">
                <Box className="flex items-center justify-between">
                  <div>
                    <Typography variant="h6" className="font-bold text-gray-900 flex items-center gap-2">
                      <WarningIcon color="warning" /> Defaulter & Low Attendance Watchlist (&lt;75%)
                    </Typography>
                    <Typography variant="caption" className="text-gray-500">
                      Students whose recorded attendance is below the reporting threshold.
                    </Typography>
                  </div>
                  <Chip label={`${lowAttendanceList.length} At-Risk Students`} color="warning" size="small" />
                </Box>

                <TableContainer component={Paper} variant="outlined" sx={{ overflowX: 'auto', width: '100%' }}>
                  <Table size="small" sx={{ minWidth: 650 }}>
                    <TableHead className="bg-gray-50">
                      <TableRow>
                        <TableCell className="font-bold">Admission No</TableCell>
                        <TableCell className="font-bold">Student Name</TableCell>
                        <TableCell className="font-bold">Conducted Sessions</TableCell>
                        <TableCell className="font-bold">Attended Sessions</TableCell>
                        <TableCell className="font-bold">Attendance %</TableCell>
                        <TableCell className="font-bold">Parent Contact</TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {lowAttendanceList.length === 0 ? (
                        <TableRow>
                          <TableCell colSpan={6} align="center" className="py-6 text-gray-500">
                            No students currently below the 75% attendance threshold. Excellent!
                          </TableCell>
                        </TableRow>
                      ) : (
                        lowAttendanceList.map((stu) => (
                          <TableRow key={stu.student_id} hover>
                            <TableCell className="font-mono font-bold text-indigo-700">{stu.admission_number}</TableCell>
                            <TableCell className="font-medium text-gray-900">{stu.full_name}</TableCell>
                            <TableCell>{stu.total_sessions}</TableCell>
                            <TableCell className="font-semibold text-green-700">{stu.attended_sessions}</TableCell>
                            <TableCell>
                              <Chip
                                label={`${stu.attendance_percentage}%`}
                                size="small"
                                color={stu.attendance_percentage < 50 ? 'error' : 'warning'}
                                className="font-bold"
                              />
                            </TableCell>
                            <TableCell className="text-gray-600">
                              {stu.parent_name || 'Guardian'} {stu.parent_phone ? `(${stu.parent_phone})` : ''}
                            </TableCell>
                          </TableRow>
                        ))
                      )}
                    </TableBody>
                  </Table>
                </TableContainer>
              </CardContent>
            </Card>
          </Box>
      )}

      {/* ──────────────── TAB 1: TEACHER ROLL CALL ──────────────── */}
      {currentTab === 1 && (
        <Box className="space-y-6">
          {/* Filter Bar */}
          <Card className="border border-gray-200 shadow-sm bg-gray-50/50">
            <CardContent className="p-4 space-y-4">
              <Typography variant="subtitle2" className="font-bold text-gray-800">
                Roll Call Session Selector
              </Typography>
              {isTeacher ? (
                <Grid container spacing={2} alignItems="center">
                  {isCollege && (
                    <>
                      <Grid item xs={12} sm={6} lg>
                        <TextField select fullWidth size="small" label="Course" value={selectedCourseId}
                          onChange={(event) => selectCourse(event.target.value)}
                        >
                          {courses.map((course) => <MenuItem key={course.id} value={course.id}>{course.name}</MenuItem>)}
                        </TextField>
                      </Grid>
                      <Grid item xs={12} sm={6} lg>
                        <TextField select fullWidth size="small" label="Semester"
                          value={selectedSectionId ? `section:${selectedSectionId}` : selectedSemesterId}
                          disabled={!selectedCourseId}
                          onChange={(event) => {
                            const value = event.target.value
                            const section = sections.find((item) => `section:${item.id}` === value)
                            selectSemester(section?.semester_id || value, section?.id)
                          }}
                        >
                          {semesters.flatMap((semester) => [
                            <MenuItem key={semester.id} value={semester.id}>{semester.name}</MenuItem>,
                            ...sections.filter((section) => section.semester_id === semester.id).map((section) => (
                              <MenuItem key={section.id} value={`section:${section.id}`}>{semester.name} · {section.name}</MenuItem>
                            )),
                          ])}
                        </TextField>
                      </Grid>
                    </>
                  )}
                  <Grid item xs={12} sm={6} lg>
                    <TextField select fullWidth size="small" label="Subject" value={selectedSubjectId}
                      disabled={isCollege && !selectedSemesterId}
                      onChange={(event) => setSelectedSubjectId(event.target.value)}
                    >
                      {subjects.filter((subject) => !isCollege || !subject.department_id ||
                        subject.department_id === courses.find((course) => course.id === selectedCourseId)?.department_id
                      ).map((subject) => <MenuItem key={subject.id} value={subject.id}>{subject.name}</MenuItem>)}
                    </TextField>
                  </Grid>
                  {!isCollege && (
                    <Grid item xs={12} sm={6} lg>
                      <TextField select fullWidth size="small" label="Section" value={selectedSectionId}
                        onChange={(event) => setSelectedSectionId(event.target.value)}
                      >
                        {sections.filter((section) => section.class_id).map((section) => (
                          <MenuItem key={section.id} value={section.id}>
                            {section.class_name || classes.find((schoolClass) => schoolClass.id === section.class_id)?.name} {section.name}
                          </MenuItem>
                        ))}
                      </TextField>
                    </Grid>
                  )}
                  <Grid item xs={12} sm={6} lg>
                    <TextField fullWidth size="small" type="number" label="Time (period)"
                      value={selectedPeriod || ''} inputProps={{ min: 1, step: 1 }}
                      onChange={(event) => setSelectedPeriod(Number(event.target.value))}
                    />
                  </Grid>
                  <Grid item xs={12} sm="auto">
                    <Button fullWidth variant="contained" onClick={loadRoster} disabled={loading || !rosterReady}>View</Button>
                  </Grid>
                </Grid>
              ) : (
              <Grid container spacing={2}>
                <Grid item xs={12} sm={6} md={3}>
                  <TextField
                    select
                    fullWidth
                    size="small"
                    label="Academic Session"
                    value={selectedSessionId}
                    onChange={(e) => setSelectedSessionId(e.target.value)}
                  >
                    {sessions.map((s) => (
                      <MenuItem key={s.id} value={s.id}>
                        {s.name} {s.is_current ? '(Current)' : ''}
                      </MenuItem>
                    ))}
                  </TextField>
                </Grid>

                <Grid item xs={12} sm={6} md={2}>
                  <TextField
                    type="date"
                    fullWidth
                    size="small"
                    label="Date"
                    InputLabelProps={{ shrink: true }}
                    value={markingDate}
                    onChange={(e) => setMarkingDate(e.target.value)}
                  />
                </Grid>

                <Grid item xs={12} sm={6} md={2}>
                  <TextField
                    select
                    fullWidth
                    size="small"
                    label="Session Type"
                    value={markingType}
                    onChange={(e) => setMarkingType(e.target.value)}
                  >
                    <MenuItem value="DAILY">Daily Attendance</MenuItem>
                    <MenuItem value="PERIOD_WISE">Period-wise</MenuItem>
                    <MenuItem value="SUBJECT_WISE">Subject-wise</MenuItem>
                  </TextField>
                </Grid>

                <Grid item xs={12} sm={6} md={2}>
                  {isCollege ? (
                    <TextField select fullWidth size="small" label="Department" value={selectedDepartmentId}
                      onChange={(event) => {
                        setSelectedDepartmentId(event.target.value)
                        selectCourse('')
                      }}
                    >
                      {departments.map((department) => <MenuItem key={department.id} value={department.id}>{department.name}</MenuItem>)}
                    </TextField>
                  ) : (
                    <TextField select fullWidth size="small" label="Class" value={selectedClassId}
                      onChange={(event) => selectClass(event.target.value)}
                    >
                      {classes.map((schoolClass) => <MenuItem key={schoolClass.id} value={schoolClass.id}>{schoolClass.name}</MenuItem>)}
                    </TextField>
                  )}
                </Grid>

                {isCollege && (
                  <>
                    <Grid item xs={12} sm={6} md={2}>
                      <TextField select fullWidth size="small" label="Course" value={selectedCourseId}
                        disabled={!selectedDepartmentId}
                        onChange={(event) => selectCourse(event.target.value)}
                      >
                        {courses.filter((course) => course.department_id === selectedDepartmentId).map((course) => (
                          <MenuItem key={course.id} value={course.id}>{course.name}</MenuItem>
                        ))}
                      </TextField>
                    </Grid>
                    <Grid item xs={12} sm={6} md={2}>
                      <TextField select fullWidth size="small" label="Semester" value={selectedSemesterId}
                        disabled={!selectedCourseId}
                        onChange={(event) => selectSemester(event.target.value)}
                      >
                        {semesters.map((semester) => <MenuItem key={semester.id} value={semester.id}>{semester.name}</MenuItem>)}
                      </TextField>
                    </Grid>
                  </>
                )}

                <Grid item xs={12} sm={6} md={1.5}>
                  <TextField
                    select
                    fullWidth
                    size="small"
                    label="Section"
                    value={selectedSectionId}
                    disabled={!cohortSelected || sections.length === 0}
                    onChange={(e) => setSelectedSectionId(e.target.value)}
                  >
                    <MenuItem value="">All sections</MenuItem>
                    {sections.map((sec) => (
                      <MenuItem key={sec.id} value={sec.id}>
                        {sec.name}
                      </MenuItem>
                    ))}
                  </TextField>
                </Grid>

                <Grid item xs={12} sm={6} md={2}>
                  <TextField
                    select
                    fullWidth
                    size="small"
                    label={markingType === 'SUBJECT_WISE' ? 'Subject' : 'Subject (optional)'}
                    value={selectedSubjectId}
                    disabled={markingType === 'DAILY'}
                    onChange={(e) => setSelectedSubjectId(e.target.value)}
                  >
                    <MenuItem value="">None / General</MenuItem>
                    {subjects.filter((sub) => !isCollege || !sub.department_id || sub.department_id === selectedDepartmentId).map((sub) => (
                      <MenuItem key={sub.id} value={sub.id}>
                        {sub.name}
                      </MenuItem>
                    ))}
                  </TextField>
                </Grid>

                <Grid item xs={12} sm={6} md={1}>
                  <TextField
                    type="number"
                    fullWidth
                    size="small"
                    label="Period"
                    value={selectedPeriod}
                    onChange={(e) => setSelectedPeriod(Number(e.target.value))}
                    disabled={markingType !== 'PERIOD_WISE'}
                  />
                </Grid>

                <Grid item xs={12} sm={6} md={3}>
                  <TextField
                    fullWidth
                    size="small"
                    label="Session Remarks"
                    placeholder="e.g. Morning roll call"
                    value={sessionRemarks}
                    onChange={(e) => setSessionRemarks(e.target.value)}
                  />
                </Grid>
              </Grid>
              )}

              <Box className="flex flex-wrap items-center justify-between gap-3 pt-2">
                <Box className="flex items-center gap-2">
                  {!isTeacher && <Button variant="contained" color="primary" onClick={loadRoster} disabled={loading || !rosterReady}>
                    Load Student Roster
                  </Button>}
                  {isSessionSubmitted && loadedRoster?.key === rosterKey && (
                    <Chip label="Session Already Conducted (Update Mode)" color="success" size="small" />
                  )}
                </Box>

                {roster.length > 0 && (
                  <Box className="flex items-center gap-2">
                    <Button size="small" variant="outlined" color="success" onClick={() => handleMarkAll('PRESENT')}>
                      Mark All Present
                    </Button>
                    <Button size="small" variant="outlined" color="error" onClick={() => handleMarkAll('ABSENT')}>
                      Mark All Absent
                    </Button>
                  </Box>
                )}
              </Box>
            </CardContent>
          </Card>

          {/* Roster Table */}
          {roster.length > 0 ? (
            <Card className="border border-gray-200 shadow-sm">
              <CardContent className="p-4 space-y-4">
                <TableContainer component={Paper} variant="outlined" sx={{ overflowX: 'auto', width: '100%' }}>
                  <Table size="small" sx={{ minWidth: 650 }}>
                    <TableHead className="bg-gray-100">
                      <TableRow>
                        <TableCell className="font-bold">Roll No</TableCell>
                        <TableCell className="font-bold">Admission No</TableCell>
                        <TableCell className="font-bold">Student Name</TableCell>
                        <TableCell className="font-bold text-center">Status Selection</TableCell>
                        <TableCell className="font-bold">Remarks / Notes</TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {roster.map((student) => {
                        const status = studentStatuses[student.student_id] || 'PRESENT'
                        return (
                          <TableRow key={student.student_id} hover>
                            <TableCell className="font-mono">{student.roll_number || '—'}</TableCell>
                            <TableCell className="font-mono font-bold text-indigo-700">{student.admission_number}</TableCell>
                            <TableCell className="font-medium text-gray-900">{student.full_name}</TableCell>
                            <TableCell align="center">
                              <Box className="flex items-center justify-center gap-1">
                                <Button
                                  size="small"
                                  variant={status === 'PRESENT' ? 'contained' : 'outlined'}
                                  color="success"
                                  startIcon={<PresentIcon />}
                                  onClick={() => handleStatusChange(student.student_id, 'PRESENT')}
                                >
                                  Present
                                </Button>
                                <Button
                                  size="small"
                                  variant={status === 'ABSENT' ? 'contained' : 'outlined'}
                                  color="error"
                                  startIcon={<AbsentIcon />}
                                  onClick={() => handleStatusChange(student.student_id, 'ABSENT')}
                                >
                                  Absent
                                </Button>
                                <Button
                                  size="small"
                                  variant={status === 'LATE' ? 'contained' : 'outlined'}
                                  color="warning"
                                  startIcon={<LateIcon />}
                                  onClick={() => handleStatusChange(student.student_id, 'LATE')}
                                >
                                  Late
                                </Button>
                                <Button
                                  size="small"
                                  variant={status === 'LEAVE' ? 'contained' : 'outlined'}
                                  color="info"
                                  startIcon={<LeaveIcon />}
                                  onClick={() => handleStatusChange(student.student_id, 'LEAVE')}
                                >
                                  Leave
                                </Button>
                              </Box>
                            </TableCell>
                            <TableCell>
                              <TextField
                                size="small"
                                placeholder="Optional remarks..."
                                value={studentRemarks[student.student_id] || ''}
                                onChange={(e) =>
                                  setStudentRemarks((prev) => ({ ...prev, [student.student_id]: e.target.value }))
                                }
                                fullWidth
                              />
                            </TableCell>
                          </TableRow>
                        )
                      })}
                    </TableBody>
                  </Table>
                </TableContainer>

                <Box className="flex flex-col sm:flex-row items-center justify-between gap-4 pt-4 border-t border-gray-100">
                  <Box className="flex items-center gap-4">
                    <FormControlLabel
                      control={
                        <Switch
                          checked={notifyParents}
                          onChange={(e) => setNotifyParents(e.target.checked)}
                          color="primary"
                        />
                      }
                      label="Dispatch absence alerts to parents via SMS / WhatsApp"
                    />
                  </Box>

                  <Button
                    variant="contained"
                    color="primary"
                    size="large"
                    startIcon={<RollCallIcon />}
                    onClick={handleSubmitRollCall}
                    disabled={loading}
                    className="font-bold px-8 shadow-md"
                  >
                    {isSessionSubmitted ? 'Update Attendance Session' : 'Submit Roll Call Attendance'}
                  </Button>
                </Box>
              </CardContent>
            </Card>
          ) : (
            <Card className="border border-dashed border-gray-300 p-12 text-center">
              <Typography variant="body1" className="text-gray-500">
                {loadedRoster?.key === rosterKey
                  ? 'No enrolled students were found for this selection.'
                  : isTeacher
                    ? 'Choose your teaching group, subject, and period, then select View.'
                    : 'Select an attendance group and date, then load the student roster.'}
              </Typography>
            </Card>
          )}
        </Box>
      )}

      {/* ──────────────── TAB 2: CORRECTIONS & AUDIT LOG ──────────────── */}
      {currentTab === 2 && (
        <Box className="space-y-6">
          <Box className="flex items-center justify-between">
            <div>
              <Typography variant="h6" className="font-bold text-gray-900">
                Attendance Correction & Audit Log
              </Typography>
              <Typography variant="caption" className="text-gray-500">
                All retroactive attendance amendments require mandatory justification and are cryptographically tracked.
              </Typography>
            </div>
            <Button
              variant="contained"
              color="secondary"
              startIcon={<HistoryIcon />}
              onClick={() => setCorrectionDialogOpen(true)}
            >
              Amend / Correct Record
            </Button>
          </Box>

          <TableContainer component={Paper} variant="outlined" sx={{ overflowX: 'auto', width: '100%' }}>
            <Table size="small" sx={{ minWidth: 650 }}>
              <TableHead className="bg-gray-50">
                <TableRow>
                  <TableCell className="font-bold">Log ID</TableCell>
                  <TableCell className="font-bold">Entry ID</TableCell>
                  <TableCell className="font-bold">Previous Status</TableCell>
                  <TableCell className="font-bold">New Status</TableCell>
                  <TableCell className="font-bold">Justification / Reason</TableCell>
                  <TableCell className="font-bold">Timestamp</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {correctionLogs.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={6} align="center" className="py-6 text-gray-500">
                      No correction audit events found.
                    </TableCell>
                  </TableRow>
                ) : (
                  correctionLogs.map((log) => (
                    <TableRow key={log.id} hover>
                      <TableCell className="font-mono text-xs text-gray-500">{log.id.slice(0, 8)}...</TableCell>
                      <TableCell className="font-mono text-xs text-indigo-700">{log.entry_id.slice(0, 8)}...</TableCell>
                      <TableCell>
                        <Chip label={log.previous_status} size="small" color="error" variant="outlined" />
                      </TableCell>
                      <TableCell>
                        <Chip label={log.new_status} size="small" color="success" />
                      </TableCell>
                      <TableCell className="font-medium text-gray-800">{log.reason}</TableCell>
                      <TableCell className="text-xs text-gray-500">
                        {new Date(log.corrected_at).toLocaleString()}
                      </TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          </TableContainer>

          {/* Correction Dialog */}
          <Dialog open={correctionDialogOpen} onClose={() => setCorrectionDialogOpen(false)} maxWidth="sm" fullWidth>
            <DialogTitle className="font-bold">Make Attendance Correction</DialogTitle>
            <DialogContent className="space-y-4 pt-2">
              <TextField
                fullWidth
                size="small"
                label="Student Attendance Entry UUID"
                placeholder="Paste entry UUID..."
                value={correctionEntryId}
                onChange={(e) => setCorrectionEntryId(e.target.value)}
              />
              <TextField
                select
                fullWidth
                size="small"
                label="Corrected Status"
                value={correctionNewStatus}
                onChange={(e) => setCorrectionNewStatus(e.target.value)}
              >
                <MenuItem value="PRESENT">PRESENT</MenuItem>
                <MenuItem value="ABSENT">ABSENT</MenuItem>
                <MenuItem value="LATE">LATE</MenuItem>
                <MenuItem value="LEAVE">LEAVE</MenuItem>
              </TextField>
              <TextField
                fullWidth
                multiline
                rows={3}
                label="Mandatory Correction Reason"
                placeholder="e.g. Doctor certificate provided, principal approved absence waiver..."
                value={correctionReason}
                onChange={(e) => setCorrectionReason(e.target.value)}
              />
            </DialogContent>
            <DialogActions>
              <Button onClick={() => setCorrectionDialogOpen(false)}>Cancel</Button>
              <Button variant="contained" color="primary" onClick={handleExecuteCorrection} disabled={loading}>
                Save Correction & Audit
              </Button>
            </DialogActions>
          </Dialog>
        </Box>
      )}

      {/* ──────────────── TAB 3: STUDENT MONTHLY HISTORY ──────────────── */}
      {currentTab === 3 && (
        <Box className="space-y-6">
          <Card className="border border-gray-200 shadow-sm p-4">
            <Typography variant="subtitle2" className="font-bold text-gray-800 mb-3">
              Individual Student Monthly Attendance Calendar
            </Typography>
            <Box className="flex flex-wrap items-center gap-4">
              <TextField
                size="small"
                label="Student UUID"
                placeholder="Paste Student UUID..."
                value={searchStudentId}
                onChange={(e) => setSearchStudentId(e.target.value)}
                className="w-80"
              />
              <TextField
                type="number"
                size="small"
                label="Year"
                value={reportYear}
                onChange={(e) => setReportYear(Number(e.target.value))}
                className="w-28"
              />
              <TextField
                type="number"
                size="small"
                label="Month (1-12)"
                value={reportMonth}
                onChange={(e) => setReportMonth(Number(e.target.value))}
                className="w-28"
              />
              <Button variant="contained" onClick={handleLoadMonthlyReport} disabled={loading}>
                Generate Report
              </Button>
            </Box>
          </Card>

          {monthlyReport && (
            <Box className="space-y-4">
              {/* Summary KPIs */}
              <Grid container spacing={2}>
                <Grid item xs={6} sm={3}>
                  <Paper className="p-3 text-center border border-gray-200">
                    <Typography variant="caption" className="text-gray-500 uppercase">Conducted Days</Typography>
                    <Typography variant="h5" className="font-bold text-gray-900">{monthlyReport.conducted_days}</Typography>
                  </Paper>
                </Grid>
                <Grid item xs={6} sm={3}>
                  <Paper className="p-3 text-center border border-green-200 bg-green-50/50">
                    <Typography variant="caption" className="text-green-700 uppercase">Present Days</Typography>
                    <Typography variant="h5" className="font-bold text-green-900">{monthlyReport.present_days}</Typography>
                  </Paper>
                </Grid>
                <Grid item xs={6} sm={3}>
                  <Paper className="p-3 text-center border border-red-200 bg-red-50/50">
                    <Typography variant="caption" className="text-red-700 uppercase">Absent Days</Typography>
                    <Typography variant="h5" className="font-bold text-red-900">{monthlyReport.absent_days}</Typography>
                  </Paper>
                </Grid>
                <Grid item xs={6} sm={3}>
                  <Paper className="p-3 text-center border border-indigo-200 bg-indigo-50/50">
                    <Typography variant="caption" className="text-indigo-700 uppercase">Monthly Rate</Typography>
                    <Typography variant="h5" className="font-bold text-indigo-900">{monthlyReport.percentage}%</Typography>
                  </Paper>
                </Grid>
              </Grid>

              {/* Records List */}
              <TableContainer component={Paper} variant="outlined" sx={{ overflowX: 'auto', width: '100%' }}>
                <Table size="small" sx={{ minWidth: 650 }}>
                  <TableHead className="bg-gray-50">
                    <TableRow>
                      <TableCell className="font-bold">Date</TableCell>
                      <TableCell className="font-bold">Period</TableCell>
                      <TableCell className="font-bold">Subject</TableCell>
                      <TableCell className="font-bold">Status</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {monthlyReport.records.map((r, i) => (
                      <TableRow key={i} hover>
                        <TableCell className="font-mono">{r.date}</TableCell>
                        <TableCell>{r.period_number ?? 'Full Day'}</TableCell>
                        <TableCell>{r.subject_name || 'General'}</TableCell>
                        <TableCell>
                          <Chip
                            label={r.status}
                            size="small"
                            color={
                              r.status === 'PRESENT'
                                ? 'success'
                                : r.status === 'ABSENT'
                                ? 'error'
                                : r.status === 'LATE'
                                ? 'warning'
                                : 'info'
                            }
                          />
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </TableContainer>
            </Box>
          )}
        </Box>
      )}

      {/* ──────────────── TAB 4: QR & FACULTY PUNCH ──────────────── */}
      {currentTab === 4 && (
        <Grid container spacing={3}>
          {/* QR Generator Card */}
          <Grid item xs={12} md={6}>
            <Card className="border border-gray-200 shadow-sm h-full">
              <CardContent className="p-5 space-y-4">
                <Typography variant="h6" className="font-bold text-gray-900 flex items-center gap-2">
                  <QrIcon color="primary" /> Dynamic QR Attendance Generator
                </Typography>
                <Typography variant="body2" className="text-gray-500">
                  Generate a time-limited check-in token for the group selected in Roll Call.
                </Typography>

                <Box className="flex items-center gap-3">
                  <TextField
                    type="number"
                    size="small"
                    label="Validity (Minutes)"
                    value={qrValidityMinutes}
                    onChange={(e) => setQrValidityMinutes(Number(e.target.value))}
                    className="w-40"
                  />
                  <Button variant="contained" color="primary" onClick={handleGenerateQR} disabled={loading || !cohortSelected}>
                    Generate Token
                  </Button>
                </Box>

                {generatedQR && (
                  <Paper className="p-4 bg-indigo-50/50 border border-indigo-200 rounded-xl space-y-2">
                    <Typography variant="caption" className="font-bold text-indigo-900 uppercase">
                      Active QR Code Token
                    </Typography>
                    <Box className="p-3 bg-white border border-gray-300 rounded font-mono text-center font-bold text-lg text-indigo-700 tracking-wider">
                      {generatedQR.qr_token}
                    </Box>
                    <Typography variant="caption" className="text-gray-600 block">
                      Expires At: {new Date(generatedQR.expires_at).toLocaleTimeString()}
                    </Typography>
                  </Paper>
                )}

                <Box className="pt-2 border-t border-gray-100 space-y-2">
                  <Typography variant="caption" className="font-bold text-gray-700 uppercase">
                    Student Scan Simulation
                  </Typography>
                  <Box className="flex items-center gap-2">
                    <TextField
                      size="small"
                      placeholder="Paste QR-ATT-... token"
                      value={scanTokenInput}
                      onChange={(e) => setScanTokenInput(e.target.value)}
                      fullWidth
                    />
                    <Button variant="outlined" color="primary" onClick={handleScanQR} disabled={loading}>
                      Simulate Scan
                    </Button>
                  </Box>
                </Box>
              </CardContent>
            </Card>
          </Grid>

          {/* Teacher Daily Punch Card */}
          <Grid item xs={12} md={6}>
            <Card className="border border-gray-200 shadow-sm h-full">
              <CardContent className="p-5 space-y-4">
                <Typography variant="h6" className="font-bold text-gray-900 flex items-center gap-2">
                  <GpsIcon color="primary" /> Faculty Daily Attendance Punch
                </Typography>
                <Typography variant="body2" className="text-gray-500">
                  Daily staff check-in and check-out with automated timestamping, GPS geo-tagging, and working hours calculation.
                </Typography>

                <Box className="flex items-center gap-4">
                  <Button
                    variant="contained"
                    color="success"
                    size="large"
                    startIcon={<PresentIcon />}
                    onClick={handleTeacherCheckIn}
                    disabled={loading}
                  >
                    Staff Check-in
                  </Button>
                  <Button
                    variant="outlined"
                    color="error"
                    size="large"
                    startIcon={<AbsentIcon />}
                    onClick={handleTeacherCheckOut}
                    disabled={loading}
                  >
                    Staff Check-out
                  </Button>
                </Box>

                {teacherPunchRecord && (
                  <Paper className="p-4 bg-green-50/50 border border-green-200 rounded-xl space-y-2">
                    <Typography variant="caption" className="font-bold text-green-900 uppercase">
                      Today's Faculty Punch Record
                    </Typography>
                    <Typography variant="body2" className="text-gray-800">
                      <strong>Date:</strong> {teacherPunchRecord.attendance_date} | <strong>Status:</strong> {teacherPunchRecord.status}
                    </Typography>
                    <Typography variant="body2" className="text-gray-800">
                      <strong>Check-in:</strong> {teacherPunchRecord.check_in_time || '—'} | <strong>Check-out:</strong> {teacherPunchRecord.check_out_time || '—'}
                    </Typography>
                    {teacherPunchRecord.notes && (
                      <Typography variant="caption" className="text-gray-600 block">
                        Notes: {teacherPunchRecord.notes}
                      </Typography>
                    )}
                  </Paper>
                )}
              </CardContent>
            </Card>
          </Grid>
        </Grid>
      )}
    </Box>
  )
}
