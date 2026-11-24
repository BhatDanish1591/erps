import { PageHeader } from '@/components/ui/PageHeader'
import { useState, useEffect } from 'react'
import {
  Box,
  Typography,
  Card,
  CardContent,
  Grid,
  Button,
  TextField,
  MenuItem,
  Chip,
  Tabs,
  Tab,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  IconButton,
  Tooltip,
  Alert,
  CircularProgress,
  Divider,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Stack,
  Switch,
  FormControlLabel,
  Checkbox,
  FormGroup,
} from '@mui/material'
import {
  CalendarMonth,
  AccessTime,
  Person,
  MeetingRoom,
  Warning,
  CheckCircle,
  PublishedWithChanges,
  SwapHoriz,
  Add,
  Delete,
  Refresh,
  FilterList,
  School,
  Schedule,
} from '@mui/icons-material'
import {
  timetableApi,
  TimetableSetting,
  TimetablePeriod,
  TimetableHoliday,
  TimetableSchedule,
  TimetableEntry,
  WeeklyTimetableResponse,
  SubstituteAssignment,
  ConflictItem,
} from '../../api/timetable'
import { academicsApi, AcademicSession, SchoolClass, Section, Subject } from '../../api/academics'
import { teachersApi, TeacherItem } from '../../api/teachers'
import { useAuthStore } from '../../store/authStore'

const DAYS_OF_WEEK = ['MONDAY', 'TUESDAY', 'WEDNESDAY', 'THURSDAY', 'FRIDAY', 'SATURDAY']

export default function TimetablePage() {
  const { user } = useAuthStore()
  const institutionType = user?.institutions.find((institution) => institution.tenant_id === user.current_tenant_id)?.institution_type
  const [activeTab, setActiveTab] = useState(0)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)

  // Academic Sessions & Metadata
  const [sessions, setSessions] = useState<AcademicSession[]>([])
  const [selectedSessionId, setSelectedSessionId] = useState<string>('')
  const [classes, setClasses] = useState<SchoolClass[]>([])
  const [sections, setSections] = useState<Section[]>([])
  const [subjects, setSubjects] = useState<Subject[]>([])
  const [teachers, setTeachers] = useState<TeacherItem[]>([])

  // Tab 0: Grid Filters & Matrix
  const [filterClassId, setFilterClassId] = useState<string>('')
  const [filterSectionId, setFilterSectionId] = useState<string>('')
  const [filterTeacherId, setFilterTeacherId] = useState<string>('')
  const [filterRoom, setFilterRoom] = useState<string>('')
  const [weeklyMatrix, setWeeklyMatrix] = useState<WeeklyTimetableResponse | null>(null)
  const [selectedDayView, setSelectedDayView] = useState<string>('MONDAY')
  const [matrixViewMode, setMatrixViewMode] = useState<'WEEK' | 'DAY'>('WEEK')

  // Tab 1: My Personalized Timetable
  const [myTimetable, setMyTimetable] = useState<WeeklyTimetableResponse | null>(null)
  const [myDateFilter, setMyDateFilter] = useState<string>(new Date().toISOString().split('T')[0])

  // Tab 2: Schedules & Publishing
  const [schedules, setSchedules] = useState<TimetableSchedule[]>([])
  const [scheduleModalOpen, setScheduleModalOpen] = useState(false)
  const [newScheduleData, setNewScheduleData] = useState({
    name: '',
    effective_from: new Date().toISOString().split('T')[0],
    effective_to: new Date(Date.now() + 180 * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
    description: '',
  })
  const [conflictModalOpen, setConflictModalOpen] = useState(false)
  const [conflictList, setConflictList] = useState<ConflictItem[]>([])
  const [conflictScheduleName, setConflictScheduleName] = useState<string>('')

  // Tab 3: Substitute Teachers
  const [substitutes, setSubstitutes] = useState<SubstituteAssignment[]>([])
  const [substituteModalOpen, setSubstituteModalOpen] = useState(false)
  const [substituteForm, setSubstituteForm] = useState({
    timetable_entry_id: '',
    assignment_date: new Date().toISOString().split('T')[0],
    substitute_teacher_id: '',
    reason: '',
  })
  const [entriesForSub, setEntriesForSub] = useState<TimetableEntry[]>([])

  // Tab 4: Settings & Bell Schedule & Holidays
  const [settings, setSettings] = useState<TimetableSetting | null>(null)
  const [periods, setPeriods] = useState<TimetablePeriod[]>([])
  const [holidays, setHolidays] = useState<TimetableHoliday[]>([])
  const [periodModalOpen, setPeriodModalOpen] = useState(false)
  const [newPeriodData, setNewPeriodData] = useState({
    period_number: 1,
    name: 'Period 1',
    period_type: 'ACADEMIC',
    start_time: '08:30',
    end_time: '09:15',
    is_break: false,
  })
  const [holidayModalOpen, setHolidayModalOpen] = useState(false)
  const [newHolidayData, setNewHolidayData] = useState({
    title: '',
    holiday_date: new Date().toISOString().split('T')[0],
    holiday_type: 'NATIONAL',
    description: '',
    is_half_day: false,
  })

  // Add/Edit Timetable Entry Dialog
  const [entryModalOpen, setEntryModalOpen] = useState(false)
  const [entryForm, setEntryForm] = useState({
    day_of_week: 'MONDAY',
    period_number: 1,
    start_time: '08:30',
    end_time: '09:15',
    teacher_id: '',
    subject_id: '',
    class_id: '',
    section_id: '',
    room_number: '',
    entry_type: 'THEORY',
    is_practical: false,
    capacity: 40,
    notes: '',
  })
  const [entryConflictWarning, setEntryConflictWarning] = useState<string | null>(null)

  // Initial Load
  useEffect(() => {
    loadInitialData()
  }, [])

  const loadInitialData = async () => {
    setLoading(true)
    try {
      const sessRes = await academicsApi.getSessions()
      const sessList = Array.isArray(sessRes) ? sessRes : sessRes.data || []
      setSessions(sessList)
      const current = sessList.find((s: AcademicSession) => s.is_current) || sessList[0]
      if (current) {
        setSelectedSessionId(current.id)
      }

      const [clsRes, subRes, teachRes] = await Promise.all([
        academicsApi.getClasses().catch(() => []),
        academicsApi.getSubjects().catch(() => []),
        teachersApi.listTeachers().then((r) => r.items).catch(() => []),
      ])

      setClasses(Array.isArray(clsRes) ? clsRes : clsRes.data || [])
      setSubjects(Array.isArray(subRes) ? subRes : subRes.data || [])
      setTeachers(Array.isArray(teachRes) ? teachRes : [])
    } catch (err: any) {
      setError(err?.message || 'Failed to load initial timetable parameters.')
    } finally {
      setLoading(false)
    }
  }

  // Reload tab data when session changes or tab changes
  useEffect(() => {
    if (!selectedSessionId) return
    if (activeTab === 0) {
      loadWeeklyMatrix()
    } else if (activeTab === 1) {
      loadMyTimetable()
    } else if (activeTab === 2) {
      loadSchedules()
    } else if (activeTab === 3) {
      loadSubstitutes()
    } else if (activeTab === 4) {
      loadSettingsAndPeriods()
    }
  }, [selectedSessionId, activeTab])

  // Class selection updates sections
  useEffect(() => {
    if (filterClassId) {
      academicsApi.getSections({ class_id: filterClassId }).then((res) => {
        setSections(Array.isArray(res) ? res : res.data || [])
      }).catch(() => setSections([]))
    } else {
      setSections([])
    }
  }, [filterClassId])

  // ─── TAB 0: Weekly Matrix ─────────────────────────────────────────────────
  const loadWeeklyMatrix = async () => {
    setLoading(true)
    setError(null)
    try {
      const matrix = await timetableApi.getWeeklyMatrix({
        class_id: filterClassId || undefined,
        section_id: filterSectionId || undefined,
        teacher_id: filterTeacherId || undefined,
        room_number: filterRoom || undefined,
      })
      setWeeklyMatrix(matrix)
    } catch (err: any) {
      setError(err?.message || 'Failed to load weekly timetable matrix.')
    } finally {
      setLoading(false)
    }
  }

  // ─── TAB 1: My Timetable ──────────────────────────────────────────────────
  const loadMyTimetable = async () => {
    setLoading(true)
    setError(null)
    try {
      const my = await timetableApi.getMyTimetable(myDateFilter)
      setMyTimetable(my)
    } catch (err: any) {
      setError(err?.message || 'Failed to load personal timetable.')
    } finally {
      setLoading(false)
    }
  }

  // ─── TAB 2: Schedules ─────────────────────────────────────────────────────
  const loadSchedules = async () => {
    setLoading(true)
    try {
      const data = await timetableApi.listSchedules({ academic_session_id: selectedSessionId })
      setSchedules(data)
    } catch (err: any) {
      setError(err?.message || 'Failed to load schedules.')
    } finally {
      setLoading(false)
    }
  }

  const handleCreateSchedule = async () => {
    if (!newScheduleData.name.trim()) return
    setLoading(true)
    try {
      await timetableApi.createSchedule({
        academic_session_id: selectedSessionId,
        name: newScheduleData.name,
        institution_type: institutionType,
        effective_from: newScheduleData.effective_from,
        effective_to: newScheduleData.effective_to,
        description: newScheduleData.description,
      })
      setScheduleModalOpen(false)
      setSuccess('Timetable schedule created successfully in DRAFT mode.')
      loadSchedules()
    } catch (err: any) {
      setError(err?.message || 'Failed to create schedule.')
    } finally {
      setLoading(false)
    }
  }

  const handleAuditConflicts = async (schedule: TimetableSchedule) => {
    setLoading(true)
    try {
      const res = await timetableApi.getScheduleConflicts(schedule.id)
      setConflictScheduleName(schedule.name)
      setConflictList(res.conflicts)
      setConflictModalOpen(true)
    } catch (err: any) {
      setError(err?.message || 'Error running conflict detection audit.')
    } finally {
      setLoading(false)
    }
  }

  const handlePublishSchedule = async (scheduleId: string, force: boolean = false) => {
    setLoading(true)
    try {
      await timetableApi.publishSchedule(scheduleId, force)
      setSuccess('Schedule published successfully! Teachers and students are now notified.')
      loadSchedules()
    } catch (err: any) {
      setError(err?.message || 'Failed to publish schedule. Please resolve overlaps or override.')
    } finally {
      setLoading(false)
    }
  }

  // ─── TAB 3: Substitute Teachers ───────────────────────────────────────────
  const loadSubstitutes = async () => {
    setLoading(true)
    try {
      const [subs, allEntries] = await Promise.all([
        timetableApi.listSubstitutes(),
        timetableApi.listEntries({ academic_session_id: selectedSessionId }),
      ])
      setSubstitutes(subs)
      setEntriesForSub(allEntries)
    } catch (err: any) {
      setError(err?.message || 'Failed to load substitute teacher records.')
    } finally {
      setLoading(false)
    }
  }

  const handleAssignSubstitute = async () => {
    if (!substituteForm.timetable_entry_id || !substituteForm.substitute_teacher_id) {
      setError('Please select both timetable slot and substitute teacher.')
      return
    }
    setLoading(true)
    try {
      await timetableApi.assignSubstitute({
        timetable_entry_id: substituteForm.timetable_entry_id,
        assignment_date: substituteForm.assignment_date,
        substitute_teacher_id: substituteForm.substitute_teacher_id,
        reason: substituteForm.reason,
      })
      setSuccess('Substitute teacher assigned cleanly. Slot conflict validation passed!')
      setSubstituteModalOpen(false)
      loadSubstitutes()
    } catch (err: any) {
      setError(err?.message || 'Failed to assign substitute. Teacher may have a conflicting slot.')
    } finally {
      setLoading(false)
    }
  }

  // ─── TAB 4: Settings & Bell Periods ───────────────────────────────────────
  const loadSettingsAndPeriods = async () => {
    setLoading(true)
    try {
      const [sett, pers, hols] = await Promise.all([
        timetableApi.getSettings(selectedSessionId),
        timetableApi.listPeriods(selectedSessionId),
        timetableApi.listHolidays({ academic_session_id: selectedSessionId }),
      ])
      setSettings(sett)
      setPeriods(pers)
      setHolidays(hols)
    } catch (err: any) {
      setError(err?.message || 'Failed to load timetable settings.')
    } finally {
      setLoading(false)
    }
  }

  const handleSaveSettings = async () => {
    if (!settings) return
    setLoading(true)
    try {
      const updated = await timetableApi.updateSettings({
        academic_session_id: selectedSessionId,
        working_days: settings.working_days,
        periods_per_day: settings.periods_per_day,
        period_duration_minutes: settings.period_duration_minutes,
        break_duration_minutes: settings.break_duration_minutes,
        lunch_duration_minutes: settings.lunch_duration_minutes,
        school_start_time: settings.school_start_time,
      })
      setSettings(updated)
      setSuccess('Timetable bell schedule configuration saved.')
    } catch (err: any) {
      setError(err?.message || 'Failed to save timetable settings.')
    } finally {
      setLoading(false)
    }
  }

  const handleCreatePeriod = async () => {
    setLoading(true)
    try {
      await timetableApi.createPeriod({
        academic_session_id: selectedSessionId,
        period_number: Number(newPeriodData.period_number),
        name: newPeriodData.name,
        period_type: newPeriodData.period_type,
        start_time: newPeriodData.start_time,
        end_time: newPeriodData.end_time,
        is_break: newPeriodData.is_break,
      })
      setPeriodModalOpen(false)
      setSuccess('Bell period added successfully.')
      loadSettingsAndPeriods()
    } catch (err: any) {
      setError(err?.message || 'Failed to add bell period.')
    } finally {
      setLoading(false)
    }
  }

  const handleDeletePeriod = async (id: string) => {
    if (!window.confirm('Delete this bell schedule period?')) return
    try {
      await timetableApi.deletePeriod(id)
      setSuccess('Period deleted.')
      loadSettingsAndPeriods()
    } catch (err: any) {
      setError(err?.message || 'Failed to delete period.')
    }
  }

  const handleCreateHoliday = async () => {
    if (!newHolidayData.title.trim()) return
    setLoading(true)
    try {
      await timetableApi.createHoliday({
        academic_session_id: selectedSessionId,
        title: newHolidayData.title,
        holiday_date: newHolidayData.holiday_date,
        holiday_type: newHolidayData.holiday_type,
        description: newHolidayData.description,
        is_half_day: newHolidayData.is_half_day,
      })
      setHolidayModalOpen(false)
      setSuccess('Holiday added to academic calendar.')
      loadSettingsAndPeriods()
    } catch (err: any) {
      setError(err?.message || 'Failed to add holiday.')
    } finally {
      setLoading(false)
    }
  }

  const handleDeleteHoliday = async (id: string) => {
    if (!window.confirm('Remove this holiday from timetable calendar?')) return
    try {
      await timetableApi.deleteHoliday(id)
      setSuccess('Holiday removed.')
      loadSettingsAndPeriods()
    } catch (err: any) {
      setError(err?.message || 'Failed to remove holiday.')
    }
  }

  // ─── Entry Creation with Conflict Check ───────────────────────────────────
  const handleCheckAndSaveEntry = async () => {
    if (!entryForm.teacher_id || !entryForm.start_time || !entryForm.end_time) {
      setError('Teacher, Start Time, and End Time are required.')
      return
    }

    setLoading(true)
    setEntryConflictWarning(null)
    try {
      // Pre-check conflict
      const conflictCheck = await timetableApi.checkConflicts({
        day_of_week: entryForm.day_of_week,
        start_time: entryForm.start_time,
        end_time: entryForm.end_time,
        teacher_id: entryForm.teacher_id,
        room_number: entryForm.room_number || undefined,
        class_id: entryForm.class_id || undefined,
        section_id: entryForm.section_id || undefined,
      })

      if (conflictCheck.has_conflicts) {
        const msgs = conflictCheck.conflicts.map((c) => c.message).join(' | ')
        setEntryConflictWarning(`Warning Overlap: ${msgs}`)
        return
      }

      await timetableApi.createEntry({
        academic_session_id: selectedSessionId,
        day_of_week: entryForm.day_of_week,
        period_number: Number(entryForm.period_number),
        start_time: entryForm.start_time,
        end_time: entryForm.end_time,
        teacher_id: entryForm.teacher_id,
        subject_id: entryForm.subject_id || undefined,
        class_id: entryForm.class_id || undefined,
        section_id: entryForm.section_id || undefined,
        room_number: entryForm.room_number || undefined,
        entry_type: entryForm.entry_type,
        is_practical: entryForm.is_practical,
        capacity: Number(entryForm.capacity),
        notes: entryForm.notes,
      })

      setSuccess('Timetable slot allocated successfully without conflicts!')
      setEntryModalOpen(false)
      loadWeeklyMatrix()
    } catch (err: any) {
      setError(err?.message || 'Failed to save timetable slot.')
    } finally {
      setLoading(false)
    }
  }

  const handleForceSaveEntry = async () => {
    setLoading(true)
    try {
      await timetableApi.createEntry(
        {
          academic_session_id: selectedSessionId,
          day_of_week: entryForm.day_of_week,
          period_number: Number(entryForm.period_number),
          start_time: entryForm.start_time,
          end_time: entryForm.end_time,
          teacher_id: entryForm.teacher_id,
          subject_id: entryForm.subject_id || undefined,
          class_id: entryForm.class_id || undefined,
          section_id: entryForm.section_id || undefined,
          room_number: entryForm.room_number || undefined,
          entry_type: entryForm.entry_type,
          is_practical: entryForm.is_practical,
          capacity: Number(entryForm.capacity),
          notes: entryForm.notes,
        },
        true // ignore_conflicts
      )
      setSuccess('Timetable slot saved (conflicts bypassed with override).')
      setEntryModalOpen(false)
      setEntryConflictWarning(null)
      loadWeeklyMatrix()
    } catch (err: any) {
      setError(err?.message || 'Failed to save timetable slot.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <Box>
      {/* Header */}
      <Box sx={{ mb: 3 }}>
        <PageHeader
          title="Timetable"
          description="Manage teaching schedules, periods, and substitutions."
          icon={<CalendarMonth />}
        >

          <Stack direction="row" spacing={2} alignItems="center">
            <TextField
              select
              size="small"
              label="Academic Session"
              value={selectedSessionId}
              onChange={(e) => setSelectedSessionId(e.target.value)}
              sx={{ minWidth: 200 }}
            >
              {sessions.map((s) => (
                <MenuItem key={s.id} value={s.id}>
                  {s.name} {s.is_current ? '(Current)' : ''}
                </MenuItem>
              ))}
            </TextField>

            <Button
              variant="contained"
              startIcon={<Add />}
              onClick={() => setEntryModalOpen(true)}
              sx={{ textTransform: 'none' }}
            >
              Add Schedule Slot
            </Button>
          </Stack>
        </PageHeader>
      </Box>

      {/* Notifications */}
      {error && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}
      {success && (
        <Alert severity="success" sx={{ mb: 2 }} onClose={() => setSuccess(null)}>
          {success}
        </Alert>
      )}

      {/* Navigation Tabs */}
      <Paper sx={{ mb: 3 }}>
        <Tabs
          value={activeTab}
          onChange={(_, val) => setActiveTab(val)}
          variant="scrollable"
          scrollButtons="auto"
          textColor="primary"
          indicatorColor="primary"
        >
          <Tab icon={<CalendarMonth />} iconPosition="start" label="Interactive Timetable Grid" />
          <Tab icon={<Person />} iconPosition="start" label="My Timetable" />
          <Tab icon={<PublishedWithChanges />} iconPosition="start" label="Schedules & Publishing" />
          <Tab icon={<SwapHoriz />} iconPosition="start" label="Substitute Teachers" />
          <Tab icon={<Schedule />} iconPosition="start" label="Bell Schedule & Holidays" />
        </Tabs>
      </Paper>

      {/* TAB 0: Interactive Timetable Grid */}
      {activeTab === 0 && (
        <Box>
          {/* Filter Bar */}
          <Card sx={{ mb: 3 }}>
            <CardContent>
              <Stack direction="row" spacing={1} alignItems="center" sx={{ mb: 2 }}>
                <FilterList color="primary" />
                <Typography variant="subtitle1" fontWeight="bold">
                  Matrix Filters & Perspectives
                </Typography>
                <Box sx={{ flexGrow: 1 }} />
                <Button
                  size="small"
                  variant={matrixViewMode === 'WEEK' ? 'contained' : 'outlined'}
                  onClick={() => setMatrixViewMode('WEEK')}
                >
                  Weekly View
                </Button>
                <Button
                  size="small"
                  variant={matrixViewMode === 'DAY' ? 'contained' : 'outlined'}
                  onClick={() => setMatrixViewMode('DAY')}
                >
                  Daily Timeline
                </Button>
                <IconButton onClick={loadWeeklyMatrix} size="small">
                  <Refresh />
                </IconButton>
              </Stack>

              <Grid container spacing={2}>
                <Grid item xs={12} sm={3}>
                  <TextField
                    select
                    fullWidth
                    size="small"
                    label="Filter by Class"
                    value={filterClassId}
                    onChange={(e) => setFilterClassId(e.target.value)}
                  >
                    <MenuItem value="">-- All Classes --</MenuItem>
                    {classes.map((c) => (
                      <MenuItem key={c.id} value={c.id}>
                        {c.name}
                      </MenuItem>
                    ))}
                  </TextField>
                </Grid>

                <Grid item xs={12} sm={3}>
                  <TextField
                    select
                    fullWidth
                    size="small"
                    label="Filter by Section"
                    value={filterSectionId}
                    onChange={(e) => setFilterSectionId(e.target.value)}
                    disabled={!filterClassId}
                  >
                    <MenuItem value="">-- All Sections --</MenuItem>
                    {sections.map((sec) => (
                      <MenuItem key={sec.id} value={sec.id}>
                        Section {sec.name}
                      </MenuItem>
                    ))}
                  </TextField>
                </Grid>

                <Grid item xs={12} sm={3}>
                  <TextField
                    select
                    fullWidth
                    size="small"
                    label="Filter by Teacher"
                    value={filterTeacherId}
                    onChange={(e) => setFilterTeacherId(e.target.value)}
                  >
                    <MenuItem value="">-- All Teachers --</MenuItem>
                    {teachers.map((t) => (
                      <MenuItem key={t.id} value={t.id}>
                        {t.full_name || t.employee_id} ({t.employee_id})
                      </MenuItem>
                    ))}
                  </TextField>
                </Grid>

                <Grid item xs={12} sm={3}>
                  <TextField
                    fullWidth
                    size="small"
                    label="Filter by Room No."
                    placeholder="e.g. Lab 201, Hall A"
                    value={filterRoom}
                    onChange={(e) => setFilterRoom(e.target.value)}
                  />
                </Grid>
              </Grid>
            </CardContent>
          </Card>

          {/* Timetable Header Banner */}
          {weeklyMatrix && (
            <Box sx={{ mb: 2, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <Typography variant="h6" fontWeight="bold">
                {weeklyMatrix.entity_name} ({weeklyMatrix.entity_type})
              </Typography>
              {weeklyMatrix.schedule_name && (
                <Chip
                  label={`Active Schedule: ${weeklyMatrix.schedule_name}`}
                  color="primary"
                  variant="outlined"
                  size="small"
                />
              )}
            </Box>
          )}

          {/* Matrix Table */}
          {loading ? (
            <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}>
              <CircularProgress />
            </Box>
          ) : matrixViewMode === 'WEEK' ? (
            <TableContainer component={Paper} sx={{ borderRadius: 2, overflowX: 'auto', width: '100%' }}>
              <Table sx={{ minWidth: 800 }}>
                <TableHead sx={{ bgcolor: 'grey.100' }}>
                  <TableRow>
                    <TableCell sx={{ fontWeight: 'bold', width: '12%' }}>Day / Period</TableCell>
                    {DAYS_OF_WEEK.map((day) => (
                      <TableCell key={day} align="center" sx={{ fontWeight: 'bold' }}>
                        {day}
                      </TableCell>
                    ))}
                  </TableRow>
                </TableHead>
                <TableBody>
                  {weeklyMatrix?.days && weeklyMatrix.days.length > 0 ? (
                    // Group or display by day
                    <TableRow>
                      <TableCell sx={{ fontWeight: 'bold', verticalAlign: 'top' }}>
                        All Slots
                      </TableCell>
                      {DAYS_OF_WEEK.map((dayName) => {
                        const dayData = weeklyMatrix.days.find((d) => d.day_of_week === dayName)
                        if (dayData?.is_holiday) {
                          return (
                            <TableCell key={dayName} sx={{ bgcolor: '#FFF3E0', verticalAlign: 'top' }}>
                              <Box sx={{ textAlign: 'center', py: 2 }}>
                                <Chip label="HOLIDAY" color="warning" size="small" sx={{ mb: 1 }} />
                                <Typography variant="caption" display="block" fontWeight="bold">
                                  {dayData.holiday_title || 'Institutional Holiday'}
                                </Typography>
                              </Box>
                            </TableCell>
                          )
                        }

                        return (
                          <TableCell key={dayName} sx={{ verticalAlign: 'top', p: 1 }}>
                            {dayData?.entries && dayData.entries.length > 0 ? (
                              <Stack spacing={1.5}>
                                {dayData.entries.map((slot) => (
                                  <Card
                                    key={slot.id}
                                    variant="outlined"
                                    sx={{
                                      borderLeft: 4,
                                      borderLeftColor:
                                        slot.entry_type === 'PRACTICAL'
                                          ? 'secondary.main'
                                          : slot.entry_type === 'EXAM'
                                          ? 'error.main'
                                          : 'primary.main',
                                      bgcolor: slot.is_substituted ? '#E8F5E9' : 'background.paper',
                                    }}
                                  >
                                    <CardContent sx={{ p: 1.5, '&:last-child': { pb: 1.5 } }}>
                                      <Stack direction="row" justifyContent="space-between" alignItems="center">
                                        <Typography variant="subtitle2" fontWeight="bold">
                                          {slot.subject_name || slot.subject_code || 'Academic Slot'}
                                        </Typography>
                                        <Chip
                                          label={slot.entry_type}
                                          size="small"
                                          color={
                                            slot.entry_type === 'PRACTICAL'
                                              ? 'secondary'
                                              : slot.entry_type === 'EXAM'
                                              ? 'error'
                                              : 'default'
                                          }
                                          sx={{ height: 18, fontSize: '0.65rem' }}
                                        />
                                      </Stack>

                                      <Typography variant="caption" color="text.secondary" display="block">
                                        <AccessTime sx={{ fontSize: 12, verticalAlign: 'middle', mr: 0.5 }} />
                                        {slot.start_time} - {slot.end_time} (P{slot.period_number})
                                      </Typography>

                                      <Typography variant="caption" display="block" sx={{ mt: 0.5 }}>
                                        <Person sx={{ fontSize: 12, verticalAlign: 'middle', mr: 0.5 }} />
                                        {slot.is_substituted ? (
                                          <Tooltip title={`Original: ${slot.teacher_name}`}>
                                            <span style={{ color: '#2E7D32', fontWeight: 'bold' }}>
                                              Sub: {slot.active_substitute_teacher_name}
                                            </span>
                                          </Tooltip>
                                        ) : (
                                          slot.teacher_name || 'Assigned Faculty'
                                        )}
                                      </Typography>

                                      {slot.room_number && (
                                        <Typography variant="caption" color="text.secondary" display="block">
                                          <MeetingRoom sx={{ fontSize: 12, verticalAlign: 'middle', mr: 0.5 }} />
                                          Room: {slot.room_number}
                                        </Typography>
                                      )}

                                      {slot.class_name && (
                                        <Typography variant="caption" color="text.secondary" display="block">
                                          <School sx={{ fontSize: 12, verticalAlign: 'middle', mr: 0.5 }} />
                                          {slot.class_name} {slot.section_name ? `(${slot.section_name})` : ''}
                                        </Typography>
                                      )}
                                    </CardContent>
                                  </Card>
                                ))}
                              </Stack>
                            ) : (
                              <Typography variant="caption" color="text.disabled" align="center" display="block" sx={{ py: 2 }}>
                                No scheduled slots
                              </Typography>
                            )}
                          </TableCell>
                        )
                      })}
                    </TableRow>
                  ) : (
                    <TableRow>
                      <TableCell colSpan={7} align="center" sx={{ py: 4 }}>
                        <Typography color="text.secondary">No timetable records found for selected filters.</Typography>
                      </TableCell>
                    </TableRow>
                  )}
                </TableBody>
              </Table>
            </TableContainer>
          ) : (
            // Day Timeline View
            <Card>
              <CardContent>
                <Tabs
                  value={selectedDayView}
                  onChange={(_, val) => setSelectedDayView(val)}
                  sx={{ mb: 2, borderBottom: 1, borderColor: 'divider' }}
                >
                  {DAYS_OF_WEEK.map((d) => (
                    <Tab key={d} label={d} value={d} />
                  ))}
                </Tabs>

                {(() => {
                  const dayObj = weeklyMatrix?.days.find((d) => d.day_of_week === selectedDayView)
                  if (!dayObj || !dayObj.entries || dayObj.entries.length === 0) {
                    return (
                      <Typography color="text.secondary" sx={{ py: 4, textAlign: 'center' }}>
                        No timetable entries scheduled for {selectedDayView}.
                      </Typography>
                    )
                  }

                  return (
                    <Stack spacing={2}>
                      {dayObj.entries.map((entry) => (
                        <Card key={entry.id} variant="outlined" sx={{ p: 2 }}>
                          <Grid container alignItems="center" spacing={2}>
                            <Grid item xs={12} sm={3}>
                              <Typography variant="subtitle1" fontWeight="bold">
                                {entry.start_time} - {entry.end_time}
                              </Typography>
                              <Typography variant="caption" color="text.secondary">
                                Period {entry.period_number} • {entry.entry_type}
                              </Typography>
                            </Grid>
                            <Grid item xs={12} sm={4}>
                              <Typography variant="body1" fontWeight="bold">
                                {entry.subject_name || entry.subject_code || 'Academic Subject'}
                              </Typography>
                              <Typography variant="caption" color="text.secondary">
                                {entry.class_name ? `Class: ${entry.class_name} ${entry.section_name || ''}` : ''}
                              </Typography>
                            </Grid>
                            <Grid item xs={12} sm={3}>
                              <Typography variant="body2">
                                Faculty: <strong>{entry.is_substituted ? entry.active_substitute_teacher_name : entry.teacher_name}</strong>
                              </Typography>
                              {entry.is_substituted && (
                                <Chip label="Substitute Active" size="small" color="success" sx={{ mt: 0.5 }} />
                              )}
                            </Grid>
                            <Grid item xs={12} sm={2} sx={{ textAlign: { sm: 'right' } }}>
                              <Chip
                                label={`Room ${entry.room_number || 'TBA'}`}
                                color="primary"
                                variant="outlined"
                              />
                            </Grid>
                          </Grid>
                        </Card>
                      ))}
                    </Stack>
                  )
                })()}
              </CardContent>
            </Card>
          )}
        </Box>
      )}

      {/* TAB 1: My Personalized Timetable */}
      {activeTab === 1 && (
        <Box>
          <Card sx={{ mb: 3 }}>
            <CardContent>
              <Stack
                direction={{ xs: 'column', sm: 'row' }}
                justifyContent="space-between"
                alignItems={{ xs: 'flex-start', sm: 'center' }}
                spacing={2}
              >
                <Box>
                  <Typography variant="h6" fontWeight="bold">
                    Personalized Timetable for {user?.full_name || 'Current User'}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Role-tailored timetable displaying authorized classes, teaching load, and active substitute duties
                  </Typography>
                </Box>

                <Stack direction="row" spacing={2} alignItems="center">
                  <TextField
                    type="date"
                    size="small"
                    label="Target Reference Date"
                    value={myDateFilter}
                    onChange={(e) => setMyDateFilter(e.target.value)}
                    InputLabelProps={{ shrink: true }}
                  />
                  <Button variant="outlined" onClick={loadMyTimetable} startIcon={<Refresh />}>
                    Refresh
                  </Button>
                </Stack>
              </Stack>
            </CardContent>
          </Card>

          {loading ? (
            <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}>
              <CircularProgress />
            </Box>
          ) : myTimetable?.days && myTimetable.days.length > 0 ? (
            <Grid container spacing={2}>
              {myTimetable.days.map((day) => (
                <Grid item xs={12} md={6} lg={4} key={day.day_of_week}>
                  <Card sx={{ height: '100%', bgcolor: day.is_holiday ? '#FFF8E1' : 'background.paper' }}>
                    <CardContent>
                      <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 1 }}>
                        <Typography variant="subtitle1" fontWeight="bold">
                          {day.day_of_week}
                        </Typography>
                        {day.date && (
                          <Typography variant="caption" color="text.secondary">
                            {day.date}
                          </Typography>
                        )}
                      </Stack>
                      <Divider sx={{ mb: 2 }} />

                      {day.is_holiday ? (
                        <Box sx={{ textAlign: 'center', py: 3 }}>
                          <Chip label="HOLIDAY" color="warning" size="small" sx={{ mb: 1 }} />
                          <Typography variant="body2" fontWeight="bold">
                            {day.holiday_title || 'Institutional Holiday'}
                          </Typography>
                        </Box>
                      ) : day.entries && day.entries.length > 0 ? (
                        <Stack spacing={1.5}>
                          {day.entries.map((entry) => (
                            <Box
                              key={entry.id}
                              sx={{
                                p: 1.5,
                                borderRadius: 1.5,
                                border: '1px solid',
                                borderColor: 'grey.300',
                                bgcolor: entry.is_substituted ? '#E8F5E9' : 'grey.50',
                              }}
                            >
                              <Stack direction="row" justifyContent="space-between" alignItems="center">
                                <Typography variant="subtitle2" fontWeight="bold">
                                  {entry.subject_name || 'Academic Class'}
                                </Typography>
                                <Typography variant="caption" color="primary" fontWeight="bold">
                                  {entry.start_time} - {entry.end_time}
                                </Typography>
                              </Stack>

                              <Typography variant="caption" color="text.secondary" display="block">
                                Room: <strong>{entry.room_number || 'General'}</strong> • Period {entry.period_number}
                              </Typography>

                              {entry.teacher_name && (
                                <Typography variant="caption" display="block">
                                  Faculty: {entry.teacher_name}
                                </Typography>
                              )}

                              {entry.is_substituted && (
                                <Chip
                                  label={`Substitute: ${entry.active_substitute_teacher_name}`}
                                  size="small"
                                  color="success"
                                  sx={{ mt: 1, fontSize: '0.7rem' }}
                                />
                              )}
                            </Box>
                          ))}
                        </Stack>
                      ) : (
                        <Typography variant="body2" color="text.disabled" align="center" sx={{ py: 3 }}>
                          No scheduled periods for today
                        </Typography>
                      )}
                    </CardContent>
                  </Card>
                </Grid>
              ))}
            </Grid>
          ) : (
            <Paper sx={{ p: 4, textAlign: 'center' }}>
              <Typography color="text.secondary">
                No personalized timetable found. Please ensure enrollment or teacher profile is configured.
              </Typography>
            </Paper>
          )}
        </Box>
      )}

      {/* TAB 2: Schedules & Publishing */}
      {activeTab === 2 && (
        <Box>
          <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 3 }}>
            <Box>
              <Typography variant="h6" fontWeight="bold">
                Timetable Schedules & Version Publishing
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Draft, validate with conflict detection engine, and publish institution-wide timetables
              </Typography>
            </Box>

            <Button
              variant="contained"
              startIcon={<Add />}
              onClick={() => setScheduleModalOpen(true)}
            >
              Create Schedule
            </Button>
          </Stack>

          <TableContainer component={Paper} sx={{ overflowX: 'auto', width: '100%' }}>
            <Table sx={{ minWidth: 650 }}>
              <TableHead sx={{ bgcolor: 'grey.100' }}>
                <TableRow>
                  <TableCell sx={{ fontWeight: 'bold' }}>Schedule Name</TableCell>
                  <TableCell sx={{ fontWeight: 'bold' }}>Institution Type</TableCell>
                  <TableCell sx={{ fontWeight: 'bold' }}>Effective Validity</TableCell>
                  <TableCell sx={{ fontWeight: 'bold' }}>Total Entries</TableCell>
                  <TableCell sx={{ fontWeight: 'bold' }}>Status</TableCell>
                  <TableCell sx={{ fontWeight: 'bold' }}>Actions</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {schedules.map((sched) => (
                  <TableRow key={sched.id}>
                    <TableCell>
                      <Typography variant="subtitle2" fontWeight="bold">
                        {sched.name}
                      </Typography>
                      {sched.description && (
                        <Typography variant="caption" color="text.secondary">
                          {sched.description}
                        </Typography>
                      )}
                    </TableCell>
                    <TableCell>
                      <Chip label={sched.institution_type} size="small" />
                    </TableCell>
                    <TableCell>
                      <Typography variant="body2">
                        {sched.effective_from} to {sched.effective_to}
                      </Typography>
                    </TableCell>
                    <TableCell>
                      <Typography variant="body2" fontWeight="bold">
                        {sched.entries_count} slots
                      </Typography>
                    </TableCell>
                    <TableCell>
                      <Chip
                        label={sched.status}
                        size="small"
                        color={
                          sched.status === 'PUBLISHED'
                            ? 'success'
                            : sched.status === 'DRAFT'
                            ? 'warning'
                            : 'default'
                        }
                      />
                    </TableCell>
                    <TableCell>
                      <Stack direction="row" spacing={1}>
                        <Button
                          size="small"
                          variant="outlined"
                          color="info"
                          startIcon={<Warning />}
                          onClick={() => handleAuditConflicts(sched)}
                        >
                          Audit Conflicts
                        </Button>
                        {sched.status === 'DRAFT' && (
                          <Button
                            size="small"
                            variant="contained"
                            color="success"
                            startIcon={<CheckCircle />}
                            onClick={() => handlePublishSchedule(sched.id)}
                          >
                            Publish
                          </Button>
                        )}
                      </Stack>
                    </TableCell>
                  </TableRow>
                ))}
                {schedules.length === 0 && (
                  <TableRow>
                    <TableCell colSpan={6} align="center" sx={{ py: 3 }}>
                      <Typography color="text.secondary">No schedules found. Create your first timetable draft.</Typography>
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </TableContainer>
        </Box>
      )}

      {/* TAB 3: Substitute Teachers */}
      {activeTab === 3 && (
        <Box>
          <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 3 }}>
            <Box>
              <Typography variant="h6" fontWeight="bold">
                Substitute Teacher Allocations
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Assign substitute teachers for absent faculty with automated timetable clash prevention
              </Typography>
            </Box>

            <Button
              variant="contained"
              startIcon={<Add />}
              onClick={() => setSubstituteModalOpen(true)}
            >
              Assign Substitute
            </Button>
          </Stack>

          <TableContainer component={Paper} sx={{ overflowX: 'auto', width: '100%' }}>
            <Table sx={{ minWidth: 650 }}>
              <TableHead sx={{ bgcolor: 'grey.100' }}>
                <TableRow>
                  <TableCell sx={{ fontWeight: 'bold' }}>Date</TableCell>
                  <TableCell sx={{ fontWeight: 'bold' }}>Original Faculty</TableCell>
                  <TableCell sx={{ fontWeight: 'bold' }}>Substitute Faculty</TableCell>
                  <TableCell sx={{ fontWeight: 'bold' }}>Reason</TableCell>
                  <TableCell sx={{ fontWeight: 'bold' }}>Status</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {substitutes.map((sub) => (
                  <TableRow key={sub.id}>
                    <TableCell>
                      <Typography variant="body2" fontWeight="bold">
                        {sub.assignment_date}
                      </Typography>
                    </TableCell>
                    <TableCell>
                      <Typography variant="body2">{sub.original_teacher_name || 'Original Teacher'}</Typography>
                    </TableCell>
                    <TableCell>
                      <Typography variant="body2" fontWeight="bold" color="success.main">
                        {sub.substitute_teacher_name || 'Substitute Teacher'}
                      </Typography>
                    </TableCell>
                    <TableCell>
                      <Typography variant="body2" color="text.secondary">
                        {sub.reason || 'Leave substitution'}
                      </Typography>
                    </TableCell>
                    <TableCell>
                      <Chip label={sub.status} size="small" color="primary" />
                    </TableCell>
                  </TableRow>
                ))}
                {substitutes.length === 0 && (
                  <TableRow>
                    <TableCell colSpan={5} align="center" sx={{ py: 3 }}>
                      <Typography color="text.secondary">No substitute assignments recorded.</Typography>
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </TableContainer>
        </Box>
      )}

      {/* TAB 4: Bell Schedule & Holidays */}
      {activeTab === 4 && (
        <Grid container spacing={3}>
          {/* Institutional Settings */}
          <Grid item xs={12} md={6}>
            <Card sx={{ height: '100%' }}>
              <CardContent>
                <Typography variant="h6" fontWeight="bold" sx={{ mb: 2 }}>
                  Institutional Working Days & Bell Durations
                </Typography>

                {settings && (
                  <Stack spacing={2.5}>
                    <Box>
                      <Typography variant="subtitle2" sx={{ mb: 1 }}>
                        Active Working Days
                      </Typography>
                      <FormGroup row>
                        {DAYS_OF_WEEK.map((day) => (
                          <FormControlLabel
                            key={day}
                            control={
                              <Checkbox
                                checked={settings.working_days.includes(day)}
                                onChange={(e) => {
                                  const cur = settings.working_days
                                  const updated = e.target.checked
                                    ? [...cur, day]
                                    : cur.filter((d) => d !== day)
                                  setSettings({ ...settings, working_days: updated })
                                }}
                              />
                            }
                            label={day.slice(0, 3)}
                          />
                        ))}
                      </FormGroup>
                    </Box>

                    <Grid container spacing={2}>
                      <Grid item xs={6}>
                        <TextField
                          fullWidth
                          size="small"
                          label="School Start Time"
                          value={settings.school_start_time}
                          onChange={(e) => setSettings({ ...settings, school_start_time: e.target.value })}
                        />
                      </Grid>
                      <Grid item xs={6}>
                        <TextField
                          fullWidth
                          size="small"
                          type="number"
                          label="Periods Per Day"
                          value={settings.periods_per_day}
                          onChange={(e) => setSettings({ ...settings, periods_per_day: Number(e.target.value) })}
                        />
                      </Grid>
                      <Grid item xs={4}>
                        <TextField
                          fullWidth
                          size="small"
                          type="number"
                          label="Period (mins)"
                          value={settings.period_duration_minutes}
                          onChange={(e) => setSettings({ ...settings, period_duration_minutes: Number(e.target.value) })}
                        />
                      </Grid>
                      <Grid item xs={4}>
                        <TextField
                          fullWidth
                          size="small"
                          type="number"
                          label="Break (mins)"
                          value={settings.break_duration_minutes}
                          onChange={(e) => setSettings({ ...settings, break_duration_minutes: Number(e.target.value) })}
                        />
                      </Grid>
                      <Grid item xs={4}>
                        <TextField
                          fullWidth
                          size="small"
                          type="number"
                          label="Lunch (mins)"
                          value={settings.lunch_duration_minutes}
                          onChange={(e) => setSettings({ ...settings, lunch_duration_minutes: Number(e.target.value) })}
                        />
                      </Grid>
                    </Grid>

                    <Button variant="contained" onClick={handleSaveSettings} sx={{ alignSelf: 'flex-start' }}>
                      Save Bell Configurations
                    </Button>
                  </Stack>
                )}
              </CardContent>
            </Card>
          </Grid>

          {/* Bell Schedule Periods */}
          <Grid item xs={12} md={6}>
            <Card sx={{ height: '100%' }}>
              <CardContent>
                <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 2 }}>
                  <Typography variant="h6" fontWeight="bold">
                    Bell Periods Configuration
                  </Typography>
                  <Button size="small" variant="outlined" startIcon={<Add />} onClick={() => setPeriodModalOpen(true)}>
                    Add Period
                  </Button>
                </Stack>

                <TableContainer>
                  <Table size="small">
                    <TableHead>
                      <TableRow>
                        <TableCell>#</TableCell>
                        <TableCell>Name</TableCell>
                        <TableCell>Timings</TableCell>
                        <TableCell>Type</TableCell>
                        <TableCell>Action</TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {periods.map((p) => (
                        <TableRow key={p.id}>
                          <TableCell>{p.period_number}</TableCell>
                          <TableCell sx={{ fontWeight: 'bold' }}>{p.name}</TableCell>
                          <TableCell>
                            {p.start_time} - {p.end_time}
                          </TableCell>
                          <TableCell>
                            <Chip
                              label={p.is_break ? 'BREAK' : p.period_type}
                              size="small"
                              color={p.is_break ? 'warning' : 'default'}
                            />
                          </TableCell>
                          <TableCell>
                            <IconButton size="small" color="error" onClick={() => handleDeletePeriod(p.id)}>
                              <Delete fontSize="small" />
                            </IconButton>
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </TableContainer>
              </CardContent>
            </Card>
          </Grid>

          {/* Holiday Calendar */}
          <Grid item xs={12}>
            <Card>
              <CardContent>
                <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 2 }}>
                  <Box>
                    <Typography variant="h6" fontWeight="bold">
                      Institutional Holiday Calendar
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      Calendar dates marked as holidays automatically suppress regular class timetable slots
                    </Typography>
                  </Box>
                  <Button variant="contained" startIcon={<Add />} onClick={() => setHolidayModalOpen(true)}>
                    Add Holiday
                  </Button>
                </Stack>

                <TableContainer>
                  <Table size="small">
                    <TableHead>
                      <TableRow>
                        <TableCell sx={{ fontWeight: 'bold' }}>Holiday Date</TableCell>
                        <TableCell sx={{ fontWeight: 'bold' }}>Title</TableCell>
                        <TableCell sx={{ fontWeight: 'bold' }}>Type</TableCell>
                        <TableCell sx={{ fontWeight: 'bold' }}>Half Day</TableCell>
                        <TableCell sx={{ fontWeight: 'bold' }}>Description</TableCell>
                        <TableCell sx={{ fontWeight: 'bold' }}>Action</TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {holidays.map((h) => (
                        <TableRow key={h.id}>
                          <TableCell sx={{ fontWeight: 'bold' }}>{h.holiday_date}</TableCell>
                          <TableCell>{h.title}</TableCell>
                          <TableCell>
                            <Chip label={h.holiday_type} size="small" />
                          </TableCell>
                          <TableCell>{h.is_half_day ? 'Yes' : 'No'}</TableCell>
                          <TableCell color="text.secondary">{h.description || '-'}</TableCell>
                          <TableCell>
                            <IconButton size="small" color="error" onClick={() => handleDeleteHoliday(h.id)}>
                              <Delete fontSize="small" />
                            </IconButton>
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </TableContainer>
              </CardContent>
            </Card>
          </Grid>
        </Grid>
      )}

      {/* MODAL: Add Schedule Slot */}
      <Dialog open={entryModalOpen} onClose={() => setEntryModalOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle sx={{ fontWeight: 'bold' }}>Add Timetable Slot</DialogTitle>
        <DialogContent dividers>
          {entryConflictWarning && (
            <Alert severity="warning" sx={{ mb: 2 }}>
              <Typography variant="body2" fontWeight="bold">
                Conflict Detected:
              </Typography>
              <Typography variant="caption">{entryConflictWarning}</Typography>
            </Alert>
          )}

          <Grid container spacing={2}>
            <Grid item xs={6}>
              <TextField
                select
                fullWidth
                size="small"
                label="Day of Week"
                value={entryForm.day_of_week}
                onChange={(e) => setEntryForm({ ...entryForm, day_of_week: e.target.value })}
              >
                {DAYS_OF_WEEK.map((d) => (
                  <MenuItem key={d} value={d}>
                    {d}
                  </MenuItem>
                ))}
              </TextField>
            </Grid>
            <Grid item xs={6}>
              <TextField
                fullWidth
                size="small"
                type="number"
                label="Period Number"
                value={entryForm.period_number}
                onChange={(e) => setEntryForm({ ...entryForm, period_number: Number(e.target.value) })}
              />
            </Grid>

            <Grid item xs={6}>
              <TextField
                fullWidth
                size="small"
                label="Start Time (HH:MM)"
                value={entryForm.start_time}
                onChange={(e) => setEntryForm({ ...entryForm, start_time: e.target.value })}
              />
            </Grid>
            <Grid item xs={6}>
              <TextField
                fullWidth
                size="small"
                label="End Time (HH:MM)"
                value={entryForm.end_time}
                onChange={(e) => setEntryForm({ ...entryForm, end_time: e.target.value })}
              />
            </Grid>

            <Grid item xs={12}>
              <TextField
                select
                fullWidth
                size="small"
                label="Teacher *"
                value={entryForm.teacher_id}
                onChange={(e) => setEntryForm({ ...entryForm, teacher_id: e.target.value })}
              >
                {teachers.map((t) => (
                  <MenuItem key={t.id} value={t.id}>
                    {t.full_name || t.employee_id} ({t.employee_id})
                  </MenuItem>
                ))}
              </TextField>
            </Grid>

            <Grid item xs={6}>
              <TextField
                select
                fullWidth
                size="small"
                label="Subject"
                value={entryForm.subject_id}
                onChange={(e) => setEntryForm({ ...entryForm, subject_id: e.target.value })}
              >
                <MenuItem value="">-- None --</MenuItem>
                {subjects.map((s) => (
                  <MenuItem key={s.id} value={s.id}>
                    {s.name} ({s.code})
                  </MenuItem>
                ))}
              </TextField>
            </Grid>

            <Grid item xs={6}>
              <TextField
                select
                fullWidth
                size="small"
                label="Class"
                value={entryForm.class_id}
                onChange={(e) => setEntryForm({ ...entryForm, class_id: e.target.value })}
              >
                <MenuItem value="">-- None --</MenuItem>
                {classes.map((c) => (
                  <MenuItem key={c.id} value={c.id}>
                    {c.name}
                  </MenuItem>
                ))}
              </TextField>
            </Grid>

            <Grid item xs={6}>
              <TextField
                fullWidth
                size="small"
                label="Room Number"
                value={entryForm.room_number}
                onChange={(e) => setEntryForm({ ...entryForm, room_number: e.target.value })}
              />
            </Grid>

            <Grid item xs={6}>
              <TextField
                select
                fullWidth
                size="small"
                label="Slot Type"
                value={entryForm.entry_type}
                onChange={(e) => setEntryForm({ ...entryForm, entry_type: e.target.value })}
              >
                <MenuItem value="THEORY">Theory</MenuItem>
                <MenuItem value="PRACTICAL">Practical Lab</MenuItem>
                <MenuItem value="TUTORIAL">Tutorial</MenuItem>
                <MenuItem value="SEMINAR">Seminar</MenuItem>
                <MenuItem value="EXAM">Exam</MenuItem>
              </TextField>
            </Grid>

            <Grid item xs={12}>
              <FormControlLabel
                control={
                  <Switch
                    checked={entryForm.is_practical}
                    onChange={(e) => setEntryForm({ ...entryForm, is_practical: e.target.checked })}
                  />
                }
                label="Is Practical Session (Double period / Lab block)"
              />
            </Grid>
          </Grid>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setEntryModalOpen(false)}>Cancel</Button>
          {entryConflictWarning ? (
            <Button color="error" variant="contained" onClick={handleForceSaveEntry}>
              Override & Save
            </Button>
          ) : (
            <Button variant="contained" onClick={handleCheckAndSaveEntry}>
              Validate & Allocate
            </Button>
          )}
        </DialogActions>
      </Dialog>

      {/* MODAL: Conflict Audit Details */}
      <Dialog open={conflictModalOpen} onClose={() => setConflictModalOpen(false)} maxWidth="md" fullWidth>
        <DialogTitle sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <Warning color="warning" />
          Conflict Audit: {conflictScheduleName}
        </DialogTitle>
        <DialogContent dividers>
          {conflictList.length === 0 ? (
            <Alert severity="success">
              Zero scheduling conflicts detected! Timetable is clean and ready to publish.
            </Alert>
          ) : (
            <Stack spacing={1.5}>
              <Alert severity="error">
                Found {conflictList.length} potential timetable clashes (Teacher, Room, or Class overlap).
              </Alert>
              {conflictList.map((item, idx) => (
                <Card key={idx} variant="outlined" sx={{ borderLeft: 4, borderLeftColor: 'error.main', p: 1.5 }}>
                  <Typography variant="subtitle2" color="error.main" fontWeight="bold">
                    {item.conflict_type}: {item.entity_name}
                  </Typography>
                  <Typography variant="body2">{item.message}</Typography>
                  <Typography variant="caption" color="text.secondary">
                    Day: {item.day_of_week} • Slot: {item.start_time} - {item.end_time}
                  </Typography>
                </Card>
              ))}
            </Stack>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setConflictModalOpen(false)}>Close</Button>
        </DialogActions>
      </Dialog>

      {/* MODAL: Assign Substitute Teacher */}
      <Dialog open={substituteModalOpen} onClose={() => setSubstituteModalOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle sx={{ fontWeight: 'bold' }}>Assign Substitute Teacher</DialogTitle>
        <DialogContent dividers>
          <Stack spacing={2.5}>
            <TextField
              type="date"
              fullWidth
              size="small"
              label="Substitution Date"
              value={substituteForm.assignment_date}
              onChange={(e) => setSubstituteForm({ ...substituteForm, assignment_date: e.target.value })}
              InputLabelProps={{ shrink: true }}
            />

            <TextField
              select
              fullWidth
              size="small"
              label="Select Timetable Slot"
              value={substituteForm.timetable_entry_id}
              onChange={(e) => setSubstituteForm({ ...substituteForm, timetable_entry_id: e.target.value })}
            >
              {entriesForSub.map((ent) => (
                <MenuItem key={ent.id} value={ent.id}>
                  {ent.day_of_week} P{ent.period_number} ({ent.start_time}-{ent.end_time}) - {ent.subject_name || 'Class'} (Prof. {ent.teacher_name})
                </MenuItem>
              ))}
            </TextField>

            <TextField
              select
              fullWidth
              size="small"
              label="Select Substitute Faculty"
              value={substituteForm.substitute_teacher_id}
              onChange={(e) => setSubstituteForm({ ...substituteForm, substitute_teacher_id: e.target.value })}
            >
              {teachers.map((t) => (
                <MenuItem key={t.id} value={t.id}>
                  {t.full_name || t.employee_id} ({t.employee_id})
                </MenuItem>
              ))}
            </TextField>

            <TextField
              fullWidth
              size="small"
              label="Reason for Substitution"
              value={substituteForm.reason}
              onChange={(e) => setSubstituteForm({ ...substituteForm, reason: e.target.value })}
              placeholder="e.g. Medical leave, emergency leave, official duty"
            />
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setSubstituteModalOpen(false)}>Cancel</Button>
          <Button variant="contained" onClick={handleAssignSubstitute}>
            Confirm Assignment
          </Button>
        </DialogActions>
      </Dialog>

      {/* MODAL: Create Schedule */}
      <Dialog open={scheduleModalOpen} onClose={() => setScheduleModalOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle sx={{ fontWeight: 'bold' }}>Create Timetable Schedule</DialogTitle>
        <DialogContent dividers>
          <Stack spacing={2}>
            <TextField
              fullWidth
              size="small"
              label="Schedule Name *"
              value={newScheduleData.name}
              onChange={(e) => setNewScheduleData({ ...newScheduleData, name: e.target.value })}
              placeholder="e.g. Fall 2026 Regular Timetable"
            />
            <TextField
              fullWidth
              size="small"
              label="Institution Type"
              value={institutionType === 'COLLEGE' ? 'College' : institutionType === 'SCHOOL' ? 'School' : 'Registered institution'}
              slotProps={{ htmlInput: { readOnly: true } }}
            />
            <TextField
              type="date"
              fullWidth
              size="small"
              label="Effective From"
              value={newScheduleData.effective_from}
              onChange={(e) => setNewScheduleData({ ...newScheduleData, effective_from: e.target.value })}
              InputLabelProps={{ shrink: true }}
            />
            <TextField
              type="date"
              fullWidth
              size="small"
              label="Effective To"
              value={newScheduleData.effective_to}
              onChange={(e) => setNewScheduleData({ ...newScheduleData, effective_to: e.target.value })}
              InputLabelProps={{ shrink: true }}
            />
            <TextField
              fullWidth
              multiline
              rows={2}
              size="small"
              label="Description / Notes"
              value={newScheduleData.description}
              onChange={(e) => setNewScheduleData({ ...newScheduleData, description: e.target.value })}
            />
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setScheduleModalOpen(false)}>Cancel</Button>
          <Button variant="contained" onClick={handleCreateSchedule}>
            Create Draft
          </Button>
        </DialogActions>
      </Dialog>

      {/* MODAL: Add Bell Period */}
      <Dialog open={periodModalOpen} onClose={() => setPeriodModalOpen(false)} maxWidth="xs" fullWidth>
        <DialogTitle sx={{ fontWeight: 'bold' }}>Add Bell Period</DialogTitle>
        <DialogContent dividers>
          <Stack spacing={2}>
            <TextField
              fullWidth
              size="small"
              type="number"
              label="Period Number"
              value={newPeriodData.period_number}
              onChange={(e) => setNewPeriodData({ ...newPeriodData, period_number: Number(e.target.value) })}
            />
            <TextField
              fullWidth
              size="small"
              label="Period Name"
              value={newPeriodData.name}
              onChange={(e) => setNewPeriodData({ ...newPeriodData, name: e.target.value })}
            />
            <TextField
              fullWidth
              size="small"
              label="Start Time (HH:MM)"
              value={newPeriodData.start_time}
              onChange={(e) => setNewPeriodData({ ...newPeriodData, start_time: e.target.value })}
            />
            <TextField
              fullWidth
              size="small"
              label="End Time (HH:MM)"
              value={newPeriodData.end_time}
              onChange={(e) => setNewPeriodData({ ...newPeriodData, end_time: e.target.value })}
            />
            <FormControlLabel
              control={
                <Switch
                  checked={newPeriodData.is_break}
                  onChange={(e) => setNewPeriodData({ ...newPeriodData, is_break: e.target.checked })}
                />
              }
              label="Is Break / Recess / Lunch"
            />
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setPeriodModalOpen(false)}>Cancel</Button>
          <Button variant="contained" onClick={handleCreatePeriod}>
            Add Period
          </Button>
        </DialogActions>
      </Dialog>

      {/* MODAL: Add Holiday */}
      <Dialog open={holidayModalOpen} onClose={() => setHolidayModalOpen(false)} maxWidth="xs" fullWidth>
        <DialogTitle sx={{ fontWeight: 'bold' }}>Add Calendar Holiday</DialogTitle>
        <DialogContent dividers>
          <Stack spacing={2}>
            <TextField
              fullWidth
              size="small"
              label="Holiday Title *"
              value={newHolidayData.title}
              onChange={(e) => setNewHolidayData({ ...newHolidayData, title: e.target.value })}
            />
            <TextField
              type="date"
              fullWidth
              size="small"
              label="Holiday Date"
              value={newHolidayData.holiday_date}
              onChange={(e) => setNewHolidayData({ ...newHolidayData, holiday_date: e.target.value })}
              InputLabelProps={{ shrink: true }}
            />
            <TextField
              select
              fullWidth
              size="small"
              label="Holiday Type"
              value={newHolidayData.holiday_type}
              onChange={(e) => setNewHolidayData({ ...newHolidayData, holiday_type: e.target.value })}
            >
              <MenuItem value="NATIONAL">National Holiday</MenuItem>
              <MenuItem value="FESTIVAL">Festival Holiday</MenuItem>
              <MenuItem value="INSTITUTIONAL">Institutional Holiday</MenuItem>
              <MenuItem value="EMERGENCY">Emergency Closure</MenuItem>
            </TextField>
            <TextField
              fullWidth
              size="small"
              label="Description"
              value={newHolidayData.description}
              onChange={(e) => setNewHolidayData({ ...newHolidayData, description: e.target.value })}
            />
            <FormControlLabel
              control={
                <Switch
                  checked={newHolidayData.is_half_day}
                  onChange={(e) => setNewHolidayData({ ...newHolidayData, is_half_day: e.target.checked })}
                />
              }
              label="Half-Day Holiday"
            />
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setHolidayModalOpen(false)}>Cancel</Button>
          <Button variant="contained" onClick={handleCreateHoliday}>
            Add to Calendar
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  )
}
