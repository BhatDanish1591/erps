import React, { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import {
  Box,
  Typography,
  Button,
  Tabs,
  Tab,
  Paper,
  Grid,
  Chip,
  Avatar,
  Alert,
  CircularProgress,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  MenuItem,
  FormControlLabel,
  Checkbox,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Card,
  CardContent,
} from '@mui/material'
import {
  staffRoleLabels,
  TeacherItem,
  TimetableEntry,
  teachersApi,
} from '../../api/teachers'
import { AddEditTeacherModal } from './AddEditTeacherModal'
import { useAuthStore } from '@/store/authStore'
import { useQuery } from '@tanstack/react-query'
import { academicsApi } from '@/api/academics'
import type { Course, SchoolClass, Section, Subject } from '@/api/academics'

export const TeacherProfilePage: React.FC = () => {
  const { teacherId } = useParams<{ teacherId: string }>()
  const navigate = useNavigate()
  const user = useAuthStore((state) => state.user)
  const canManage = Boolean(user?.is_superadmin || user?.current_role === 'INSTITUTION_ADMIN')

  const [teacher, setTeacher] = useState<TeacherItem | null>(null)
  const [timetable, setTimetable] = useState<TimetableEntry[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [tabIndex, setTabIndex] = useState(0)

  // Dialog states
  const [editOpen, setEditOpen] = useState(false)
  const [assignOpen, setAssignOpen] = useState(false)
  const [timetableOpen, setTimetableOpen] = useState(false)
  const [leaveOpen, setLeaveOpen] = useState(false)
  const [attendanceOpen, setAttendanceOpen] = useState(false)

  // Forms
  const [assignForm, setAssignForm] = useState({
    cohort: '',
    section: '',
    subject: '',
    is_class_teacher: false,
  })
  const [assigning, setAssigning] = useState(false)
  const [assignmentError, setAssignmentError] = useState('')
  const [cohortType, cohortId] = assignForm.cohort.split(':')
  const resources = useQuery({
    queryKey: ['teacher-assignment-resources', user?.id, user?.current_tenant_id],
    enabled: assignOpen && canManage,
    queryFn: async () => {
      const [classes, courses, subjects] = await Promise.all([academicsApi.getClasses(), academicsApi.getCourses(), academicsApi.getSubjects()])
      return { classes: classes.data as SchoolClass[], courses: courses.data as Course[], subjects: subjects.data as Subject[] }
    },
  })
  const availableSections = useQuery({
    queryKey: ['teacher-assignment-sections', user?.id, user?.current_tenant_id, assignForm.cohort],
    enabled: assignOpen && Boolean(cohortId),
    queryFn: async () => (await academicsApi.getSections(cohortType === 'class' ? { class_id: cohortId } : { course_id: cohortId })).data as Section[],
  })

  const [ttForm, setTtForm] = useState({
    day_of_week: 'MONDAY',
    period_number: 1,
    start_time: '09:00',
    end_time: '09:45',
    room_number: 'Room 101',
  })

  const [leaveForm, setLeaveForm] = useState({
    leave_type: 'CASUAL',
    start_date: new Date().toISOString().split('T')[0],
    end_date: new Date().toISOString().split('T')[0],
    days_count: 1.0,
    reason: '',
  })

  const [attendanceForm, setAttendanceForm] = useState({
    attendance_date: new Date().toISOString().split('T')[0],
    status: 'PRESENT',
    check_in_time: '09:00',
    check_out_time: '16:00',
    remarks: 'Regular attendance',
  })

  const loadData = async () => {
    if (!teacherId) return
    try {
      setLoading(true)
      setError(null)
      const data = await teachersApi.getTeacher(teacherId)
      setTeacher(data)
      const tt = await teachersApi.getTimetable(teacherId)
      setTimetable(tt)
    } catch (err: any) {
      setError(err?.message || 'Failed to fetch teacher profile.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadData()
  }, [teacherId])

  const handleToggleStatus = async () => {
    if (!teacherId || !teacher) return
    const newStatus = teacher.status === 'ACTIVE' ? 'INACTIVE' : 'ACTIVE'
    const confirmed = window.confirm(`Change teacher status to ${newStatus}?`)
    if (!confirmed) return

    try {
      await teachersApi.setTeacherStatus(teacherId, newStatus)
      await loadData()
    } catch (err: any) {
      alert(err?.message || 'Failed to update status')
    }
  }

  const handleAssignResource = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!teacherId || (!cohortId && !assignForm.subject)) return
    try {
      setAssigning(true)
      setAssignmentError('')
      await teachersApi.assignResource(teacherId, {
        class_id: cohortType === 'class' ? cohortId : undefined,
        course_id: cohortType === 'course' ? cohortId : undefined,
        section_id: assignForm.section || undefined,
        subject_id: assignForm.subject || undefined,
        is_class_teacher: assignForm.is_class_teacher,
      })
      setAssignOpen(false)
      setAssignForm({ cohort: '', section: '', subject: '', is_class_teacher: false })
      await loadData()
    } catch (err: any) {
      setAssignmentError(err?.message || 'Failed to assign resource.')
    } finally {
      setAssigning(false)
    }
  }

  const handleRemoveAssignment = async (assignmentId: string) => {
    if (!teacherId) return
    const confirmed = window.confirm('Remove this academic assignment?')
    if (!confirmed) return
    try {
      await teachersApi.removeAssignment(teacherId, assignmentId)
      await loadData()
    } catch (err: any) {
      alert(err?.message || 'Failed to remove assignment')
    }
  }

  const handleCreateTimetable = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!teacherId) return
    try {
      await teachersApi.createTimetableEntry(teacherId, ttForm)
      setTimetableOpen(false)
      await loadData()
    } catch (err: any) {
      alert(err?.message || 'Failed to create timetable slot')
    }
  }

  const handleApplyLeave = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!teacherId || !leaveForm.reason.trim()) return
    try {
      await teachersApi.applyLeave(teacherId, leaveForm)
      setLeaveOpen(false)
      setLeaveForm({
        leave_type: 'CASUAL',
        start_date: new Date().toISOString().split('T')[0],
        end_date: new Date().toISOString().split('T')[0],
        days_count: 1.0,
        reason: '',
      })
      await loadData()
      alert('Leave application submitted successfully.')
    } catch (err: any) {
      alert(err?.message || 'Failed to apply for leave')
    }
  }

  const handleRecordAttendance = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!teacherId) return
    try {
      await teachersApi.recordAttendance(teacherId, attendanceForm)
      setAttendanceOpen(false)
      await loadData()
      alert('Attendance punched successfully.')
    } catch (err: any) {
      alert(err?.message || 'Failed to record attendance')
    }
  }

  if (loading) {
    return (
      <Box sx={{ p: 4, display: 'flex', justifyContent: 'center' }}>
        <CircularProgress />
      </Box>
    )
  }

  if (error || !teacher) {
    return (
      <Box sx={{ p: 3 }}>
        <Alert severity="error">{error || 'Faculty member not found.'}</Alert>
        <Button sx={{ mt: 2 }} onClick={() => navigate('/teachers')}>
          Back to Faculty List
        </Button>
      </Box>
    )
  }

  return (
    <Box>
      <Button size="small" onClick={() => navigate('/teachers')} sx={{ mb: 1 }}>
        ← Back to Faculty List
      </Button>

      {/* Header Profile Card */}
      <Paper sx={{ p: 3, mb: 3, borderRadius: 2 }}>
        <Grid container spacing={3} alignItems="center">
          <Grid item>
            <Avatar
              src={teacher.photo_url || undefined}
              sx={{ width: 84, height: 84, bgcolor: 'secondary.main', fontSize: 32, fontWeight: 700 }}
            >
              {teacher.full_name.charAt(0)}
            </Avatar>
          </Grid>
          <Grid item xs>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5, flexWrap: 'wrap' }}>
              <Typography variant="h5" sx={{ fontWeight: 800 }}>
                {teacher.full_name}
              </Typography>
              <Chip
                label={teacher.status}
                color={teacher.status === 'ACTIVE' ? 'success' : 'default'}
                size="small"
                sx={{ fontWeight: 700 }}
              />
              <Chip
                label={teacher.employment_type.replace('_', ' ')}
                size="small"
                variant="outlined"
              />
            </Box>
            <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
              Employee ID: <strong>{teacher.employee_id}</strong> | Role:{' '}
              <strong>{teacher.staff_role ? staffRoleLabels[teacher.staff_role] : (teacher.designation || 'Faculty')}</strong> | Department:{' '}
              <strong>{teacher.department_name || 'General Faculty'}</strong>
            </Typography>
            <Typography variant="caption" color="text.secondary">
              Email: {teacher.email || '—'} | Phone: {teacher.phone || '—'} | Experience:{' '}
              {teacher.experience_years} years
            </Typography>
          </Grid>
          {canManage && <Grid item>
            <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1.5 }}>
              <Button variant="outlined" onClick={() => setAttendanceOpen(true)}>
                Record Punch
              </Button>
              <Button variant="outlined" onClick={() => setEditOpen(true)}>
                Edit Profile
              </Button>
              <Button
                variant="outlined"
                color={teacher.status === 'ACTIVE' ? 'error' : 'success'}
                onClick={handleToggleStatus}
              >
                {teacher.status === 'ACTIVE' ? 'Deactivate' : 'Activate'}
              </Button>
            </Box>
          </Grid>}
        </Grid>
      </Paper>

      {/* Navigation Tabs */}
      <Box sx={{ borderBottom: 1, borderColor: 'divider', mb: 3 }}>
        <Tabs value={tabIndex} onChange={(_, val) => setTabIndex(val)} variant="scrollable" scrollButtons="auto" allowScrollButtonsMobile>
          <Tab label="Overview & Workload" />
          <Tab label="Assigned Classes & Subjects" />
          <Tab label="Weekly Timetable" />
          <Tab label="Attendance & Leaves" />
        </Tabs>
      </Box>

      {/* TAB 0: Overview & Workload */}
      {tabIndex === 0 && (
        <Grid container spacing={3}>
          {/* Workload Highlights */}
          <Grid item xs={12}>
            <Card sx={{ borderRadius: 2, bgcolor: 'action.hover' }}>
              <CardContent>
                <Typography variant="subtitle1" sx={{ fontWeight: 700, mb: 1.5 }}>
                  Faculty Workload & Performance Metrics
                </Typography>
                <Grid container spacing={2}>
                  <Grid item xs={6} sm={2.4}>
                    <Typography color="text.secondary" variant="caption">Classes Assigned</Typography>
                    <Typography variant="h5" fontWeight={800}>{teacher.workload?.total_classes_assigned ?? 0}</Typography>
                  </Grid>
                  <Grid item xs={6} sm={2.4}>
                    <Typography color="text.secondary" variant="caption">Subjects Taught</Typography>
                    <Typography variant="h5" fontWeight={800}>{teacher.workload?.total_subjects_assigned ?? 0}</Typography>
                  </Grid>
                  <Grid item xs={6} sm={2.4}>
                    <Typography color="text.secondary" variant="caption">Weekly Periods</Typography>
                    <Typography variant="h5" fontWeight={800}>{teacher.workload?.weekly_periods_count ?? 0}</Typography>
                  </Grid>
                  <Grid item xs={6} sm={2.4}>
                    <Typography color="text.secondary" variant="caption">Approved Leave This Year</Typography>
                    <Typography variant="h5" fontWeight={800}>{teacher.workload?.approved_leave_days ?? 0} days</Typography>
                  </Grid>
                  <Grid item xs={6} sm={2.4}>
                    <Typography color="text.secondary" variant="caption">Attendance Rate</Typography>
                    <Typography variant="h5" fontWeight={800} color="success.main">
                      {teacher.workload?.attendance_rate_percentage == null ? '—' : `${teacher.workload.attendance_rate_percentage}%`}
                    </Typography>
                  </Grid>
                </Grid>
              </CardContent>
            </Card>
          </Grid>

          {/* Academic Profile */}
          <Grid item xs={12} md={6}>
            <Paper sx={{ p: 2.5, borderRadius: 2 }}>
              <Typography variant="subtitle1" sx={{ fontWeight: 700, mb: 2 }}>
                Academic & Professional Details
              </Typography>
              <Grid container spacing={1.5}>
                <Grid item xs={5}><Typography color="text.secondary">Highest Degree:</Typography></Grid>
                <Grid item xs={7}><Typography fontWeight={600}>{teacher.qualification || '—'}</Typography></Grid>
                <Grid item xs={5}><Typography color="text.secondary">Specialization:</Typography></Grid>
                <Grid item xs={7}><Typography fontWeight={600}>{teacher.specialization || '—'}</Typography></Grid>
                <Grid item xs={5}><Typography color="text.secondary">Joining Date:</Typography></Grid>
                <Grid item xs={7}><Typography fontWeight={600}>{teacher.joining_date || '—'}</Typography></Grid>
                <Grid item xs={5}><Typography color="text.secondary">Class Teacher Role:</Typography></Grid>
                <Grid item xs={7}>
                  <Typography fontWeight={600} color={teacher.workload?.is_class_teacher_of ? 'primary.main' : 'text.secondary'}>
                    {teacher.workload?.is_class_teacher_of || 'None assigned'}
                  </Typography>
                </Grid>
              </Grid>
            </Paper>
          </Grid>

          {/* Address & Statutory */}
          <Grid item xs={12} md={6}>
            <Paper sx={{ p: 2.5, borderRadius: 2 }}>
              <Typography variant="subtitle1" sx={{ fontWeight: 700, mb: 2 }}>
                Contact & Statutory
              </Typography>
              <Grid container spacing={1.5}>
                <Grid item xs={5}><Typography color="text.secondary">Address:</Typography></Grid>
                <Grid item xs={7}>
                  <Typography fontWeight={600}>
                    {teacher.city ? `${teacher.address_line1 || ''}, ${teacher.city}, ${teacher.state || ''}` : '—'}
                  </Typography>
                </Grid>
                <Grid item xs={5}><Typography color="text.secondary">Emergency Contact:</Typography></Grid>
                <Grid item xs={7}>
                  <Typography fontWeight={600}>
                    {teacher.emergency_contact_name ? `${teacher.emergency_contact_name} (${teacher.emergency_contact_phone || ''})` : '—'}
                  </Typography>
                </Grid>
                <Grid item xs={5}><Typography color="text.secondary">PAN / Aadhar:</Typography></Grid>
                <Grid item xs={7}><Typography fontWeight={600}>{teacher.pan_number || teacher.aadhar_number || '—'}</Typography></Grid>
                <Grid item xs={5}><Typography color="text.secondary">Bank & Account:</Typography></Grid>
                <Grid item xs={7}><Typography fontWeight={600}>{teacher.bank_name ? `${teacher.bank_name} - ${teacher.bank_account_number || ''}` : '—'}</Typography></Grid>
              </Grid>
            </Paper>
          </Grid>
        </Grid>
      )}

      {/* TAB 1: Assigned Classes & Subjects */}
      {tabIndex === 1 && (
        <Paper sx={{ p: 3, borderRadius: 2 }}>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
            <Typography variant="subtitle1" sx={{ fontWeight: 700 }}>
              Academic Resource Assignments ({teacher.assignments.length})
            </Typography>
            {canManage && <Button variant="contained" size="small" onClick={() => setAssignOpen(true)}>
              + Assign Class / Subject
            </Button>}
          </Box>

          <TableContainer>
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell>Class / Course</TableCell>
                  <TableCell>Section / Sem</TableCell>
                  <TableCell>Subject</TableCell>
                  <TableCell>Class Teacher</TableCell>
                  <TableCell align="right">Actions</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {teacher.assignments.map((a) => (
                  <TableRow key={a.id} hover>
                    <TableCell sx={{ fontWeight: 600 }}>{a.class_name || a.course_name || 'Standard'}</TableCell>
                    <TableCell>{a.section_name ? `Sec ${a.section_name}` : a.semester ? `Sem ${a.semester}` : '—'}</TableCell>
                    <TableCell>{a.subject_name || 'All Subjects'}</TableCell>
                    <TableCell>
                      {a.is_class_teacher ? <Chip label="Class Teacher" size="small" color="primary" /> : '—'}
                    </TableCell>
                    <TableCell align="right">
                      {canManage && <Button size="small" color="error" onClick={() => handleRemoveAssignment(a.id)}>
                        Unlink
                      </Button>}
                    </TableCell>
                  </TableRow>
                ))}
                {teacher.assignments.length === 0 && (
                  <TableRow>
                    <TableCell colSpan={5} sx={{ textAlign: 'center', py: 4 }}>
                      No academic assignments linked yet.
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </TableContainer>
        </Paper>
      )}

      {/* TAB 2: Weekly Timetable */}
      {tabIndex === 2 && (
        <Paper sx={{ p: 3, borderRadius: 2 }}>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
            <Typography variant="subtitle1" sx={{ fontWeight: 700 }}>
              Weekly Timetable Schedule ({timetable.length} periods)
            </Typography>
            {canManage && <Button variant="contained" size="small" onClick={() => setTimetableOpen(true)}>
              + Add Period
            </Button>}
          </Box>

          <TableContainer>
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell>Day</TableCell>
                  <TableCell>Period</TableCell>
                  <TableCell>Time Slot</TableCell>
                  <TableCell>Class / Course</TableCell>
                  <TableCell>Section</TableCell>
                  <TableCell>Subject</TableCell>
                  <TableCell>Room</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {timetable.map((t) => (
                  <TableRow key={t.id} hover>
                    <TableCell sx={{ fontWeight: 700 }}>{t.day_of_week}</TableCell>
                    <TableCell>Period {t.period_number}</TableCell>
                    <TableCell>{t.start_time} - {t.end_time}</TableCell>
                    <TableCell>{t.class_name || t.course_name || 'General'}</TableCell>
                    <TableCell>{t.section_name ? `Sec ${t.section_name}` : '—'}</TableCell>
                    <TableCell>{t.subject_name || 'Subject'}</TableCell>
                    <TableCell>{t.room_number || '—'}</TableCell>
                  </TableRow>
                ))}
                {timetable.length === 0 && (
                  <TableRow>
                    <TableCell colSpan={7} sx={{ textAlign: 'center', py: 4 }}>
                      No timetable slots configured for this faculty member yet.
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </TableContainer>
        </Paper>
      )}

      {/* TAB 3: Attendance & Leaves */}
      {tabIndex === 3 && (
        <Paper sx={{ p: 3, borderRadius: 2 }}>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
            <Typography variant="subtitle1" sx={{ fontWeight: 700 }}>
              Leave Applications & Attendance
            </Typography>
            {(canManage || user?.id === teacher.user_id) && <Button variant="contained" size="small" onClick={() => setLeaveOpen(true)}>
              + Apply for Leave
            </Button>}
          </Box>
          <TableContainer>
            <Table size="small" aria-label="Recent leave requests">
              <TableHead><TableRow><TableCell>Leave type</TableCell><TableCell>Dates</TableCell><TableCell>Days</TableCell><TableCell>Status</TableCell></TableRow></TableHead>
              <TableBody>
                {teacher.leave_history?.map((item) => (
                  <TableRow key={item.id}>
                    <TableCell>{item.leave_type.replaceAll('_', ' ')}</TableCell>
                    <TableCell>{item.start_date} to {item.end_date}</TableCell>
                    <TableCell>{item.days_count}</TableCell>
                    <TableCell>
                      <Chip size="small" variant="outlined" label={item.status} color={item.status === 'APPROVED' ? 'success' : item.status === 'REJECTED' ? 'error' : 'default'} />
                      {item.rejection_reason && <Typography variant="caption" display="block">{item.rejection_reason}</Typography>}
                    </TableCell>
                  </TableRow>
                ))}
                {!teacher.leave_history?.length && <TableRow><TableCell colSpan={4} align="center">No leave requests recorded.</TableCell></TableRow>}
              </TableBody>
            </Table>
          </TableContainer>
          <Typography variant="subtitle1" fontWeight={700} mt={3} mb={1}>Recent attendance</Typography>
          <TableContainer>
            <Table size="small" aria-label="Recent staff attendance">
              <TableHead><TableRow><TableCell>Date</TableCell><TableCell>Status</TableCell><TableCell>Check in</TableCell><TableCell>Check out</TableCell></TableRow></TableHead>
              <TableBody>
                {teacher.attendance_history?.map((item) => (
                  <TableRow key={item.id}>
                    <TableCell>{item.attendance_date}</TableCell><TableCell>{item.status.replaceAll('_', ' ')}</TableCell>
                    <TableCell>{item.check_in_time || '—'}</TableCell><TableCell>{item.check_out_time || '—'}</TableCell>
                  </TableRow>
                ))}
                {!teacher.attendance_history?.length && <TableRow><TableCell colSpan={4} align="center">No attendance records.</TableCell></TableRow>}
              </TableBody>
            </Table>
          </TableContainer>
        </Paper>
      )}

      {/* Edit Modal */}
      <AddEditTeacherModal
        open={editOpen}
        onClose={() => setEditOpen(false)}
        onSuccess={loadData}
        teacher={teacher}
      />

      {/* Assign Resource Dialog */}
      <Dialog open={assignOpen} onClose={() => setAssignOpen(false)} maxWidth="sm" fullWidth>
        <form onSubmit={handleAssignResource}>
          <DialogTitle sx={{ fontWeight: 700 }}>Assign Academic Resource</DialogTitle>
          <DialogContent>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
              Link this teacher to classes, batches, or subjects.
            </Typography>
            {assignmentError && <Alert severity="error" sx={{ mb: 2 }}>{assignmentError}</Alert>}
            {resources.isError && <Alert severity="error" sx={{ mb: 2 }}>Academic resources could not be loaded.</Alert>}
            {availableSections.isError && <Alert severity="error" sx={{ mb: 2 }}>Sections could not be loaded for this cohort.</Alert>}
            <Grid container spacing={2} mb={1}>
              <Grid item xs={12}>
                <TextField select fullWidth label="Class or course" value={assignForm.cohort}
                  onChange={(e) => setAssignForm((previous) => ({ ...previous, cohort: e.target.value, section: '' }))}>
                  <MenuItem value="">Subject only</MenuItem>
                  {resources.data?.classes.map((item) => <MenuItem value={`class:${item.id}`} key={item.id}>{item.name} · Class</MenuItem>)}
                  {resources.data?.courses.map((item) => <MenuItem value={`course:${item.id}`} key={item.id}>{item.name} · Course</MenuItem>)}
                </TextField>
              </Grid>
              <Grid item xs={12} sm={6}>
                <TextField select fullWidth label="Section" value={assignForm.section} disabled={!cohortId || !availableSections.isSuccess}
                  onChange={(e) => setAssignForm((previous) => ({ ...previous, section: e.target.value }))}>
                  <MenuItem value="">All sections</MenuItem>
                  {availableSections.data?.map((item) => <MenuItem value={item.id} key={item.id}>{item.name}</MenuItem>)}
                </TextField>
              </Grid>
              <Grid item xs={12} sm={6}>
                <TextField select fullWidth label="Subject" value={assignForm.subject}
                  onChange={(e) => setAssignForm((previous) => ({ ...previous, subject: e.target.value }))}>
                  <MenuItem value="">No specific subject</MenuItem>
                  {resources.data?.subjects.map((item) => <MenuItem value={item.id} key={item.id}>{item.name}</MenuItem>)}
                </TextField>
              </Grid>
            </Grid>
            <FormControlLabel
              control={
                <Checkbox
                  checked={assignForm.is_class_teacher}
                  disabled={!cohortId}
                  onChange={(e) => setAssignForm((p) => ({ ...p, is_class_teacher: e.target.checked }))}
                />
              }
              label="Designate as Section / Class Teacher"
            />
          </DialogContent>
          <DialogActions sx={{ px: 3, pb: 2.5 }}>
            <Button onClick={() => setAssignOpen(false)}>Cancel</Button>
            <Button type="submit" variant="contained" disabled={assigning || (!cohortId && !assignForm.subject)}>Assign</Button>
          </DialogActions>
        </form>
      </Dialog>

      {/* Timetable Period Dialog */}
      <Dialog open={timetableOpen} onClose={() => setTimetableOpen(false)} maxWidth="sm" fullWidth>
        <form onSubmit={handleCreateTimetable}>
          <DialogTitle sx={{ fontWeight: 700 }}>Add Timetable Period</DialogTitle>
          <DialogContent>
            <Grid container spacing={2} sx={{ mt: 0.5 }}>
              <Grid item xs={6}>
                <TextField
                  label="Day of Week"
                  select
                  fullWidth
                  value={ttForm.day_of_week}
                  onChange={(e) => setTtForm((p) => ({ ...p, day_of_week: e.target.value }))}
                >
                  <MenuItem value="MONDAY">Monday</MenuItem>
                  <MenuItem value="TUESDAY">Tuesday</MenuItem>
                  <MenuItem value="WEDNESDAY">Wednesday</MenuItem>
                  <MenuItem value="THURSDAY">Thursday</MenuItem>
                  <MenuItem value="FRIDAY">Friday</MenuItem>
                  <MenuItem value="SATURDAY">Saturday</MenuItem>
                </TextField>
              </Grid>
              <Grid item xs={6}>
                <TextField
                  label="Period Number"
                  type="number"
                  fullWidth
                  value={ttForm.period_number}
                  onChange={(e) => setTtForm((p) => ({ ...p, period_number: parseInt(e.target.value) || 1 }))}
                />
              </Grid>
              <Grid item xs={6}>
                <TextField
                  label="Start Time"
                  fullWidth
                  value={ttForm.start_time}
                  onChange={(e) => setTtForm((p) => ({ ...p, start_time: e.target.value }))}
                />
              </Grid>
              <Grid item xs={6}>
                <TextField
                  label="End Time"
                  fullWidth
                  value={ttForm.end_time}
                  onChange={(e) => setTtForm((p) => ({ ...p, end_time: e.target.value }))}
                />
              </Grid>
              <Grid item xs={12}>
                <TextField
                  label="Room Number"
                  fullWidth
                  value={ttForm.room_number}
                  onChange={(e) => setTtForm((p) => ({ ...p, room_number: e.target.value }))}
                />
              </Grid>
            </Grid>
          </DialogContent>
          <DialogActions sx={{ px: 3, pb: 2.5 }}>
            <Button onClick={() => setTimetableOpen(false)}>Cancel</Button>
            <Button type="submit" variant="contained">Save Slot</Button>
          </DialogActions>
        </form>
      </Dialog>

      {/* Apply Leave Dialog */}
      <Dialog open={leaveOpen} onClose={() => setLeaveOpen(false)} maxWidth="sm" fullWidth>
        <form onSubmit={handleApplyLeave}>
          <DialogTitle sx={{ fontWeight: 700 }}>Apply for Leave</DialogTitle>
          <DialogContent>
            <Grid container spacing={2} sx={{ mt: 0.5 }}>
              <Grid item xs={6}>
                <TextField
                  label="Leave Type"
                  select
                  fullWidth
                  value={leaveForm.leave_type}
                  onChange={(e) => setLeaveForm((p) => ({ ...p, leave_type: e.target.value }))}
                >
                  <MenuItem value="CASUAL">Casual Leave</MenuItem>
                  <MenuItem value="SICK">Sick Leave</MenuItem>
                  <MenuItem value="MATERNITY">Maternity Leave</MenuItem>
                  <MenuItem value="EARNED">Earned Leave</MenuItem>
                  <MenuItem value="UNPAID">Leave Without Pay</MenuItem>
                </TextField>
              </Grid>
              <Grid item xs={6}>
                <TextField
                  label="Days Count"
                  type="number"
                  fullWidth
                  value={leaveForm.days_count}
                  onChange={(e) => setLeaveForm((p) => ({ ...p, days_count: parseFloat(e.target.value) || 1.0 }))}
                  InputProps={{ inputProps: { min: 0.5, step: 0.5 } }}
                />
              </Grid>
              <Grid item xs={6}>
                <TextField
                  label="Start Date"
                  type="date"
                  fullWidth
                  value={leaveForm.start_date}
                  onChange={(e) => setLeaveForm((p) => ({ ...p, start_date: e.target.value }))}
                  InputLabelProps={{ shrink: true }}
                />
              </Grid>
              <Grid item xs={6}>
                <TextField
                  label="End Date"
                  type="date"
                  fullWidth
                  value={leaveForm.end_date}
                  onChange={(e) => setLeaveForm((p) => ({ ...p, end_date: e.target.value }))}
                  InputLabelProps={{ shrink: true }}
                />
              </Grid>
              <Grid item xs={12}>
                <TextField
                  label="Reason for Leave"
                  required
                  multiline
                  rows={3}
                  fullWidth
                  value={leaveForm.reason}
                  onChange={(e) => setLeaveForm((p) => ({ ...p, reason: e.target.value }))}
                />
              </Grid>
            </Grid>
          </DialogContent>
          <DialogActions sx={{ px: 3, pb: 2.5 }}>
            <Button onClick={() => setLeaveOpen(false)}>Cancel</Button>
            <Button type="submit" variant="contained">Submit Application</Button>
          </DialogActions>
        </form>
      </Dialog>

      {/* Record Punch Dialog */}
      <Dialog open={attendanceOpen} onClose={() => setAttendanceOpen(false)} maxWidth="sm" fullWidth>
        <form onSubmit={handleRecordAttendance}>
          <DialogTitle sx={{ fontWeight: 700 }}>Record Attendance Punch</DialogTitle>
          <DialogContent>
            <Grid container spacing={2} sx={{ mt: 0.5 }}>
              <Grid item xs={6}>
                <TextField
                  label="Date"
                  type="date"
                  fullWidth
                  value={attendanceForm.attendance_date}
                  onChange={(e) => setAttendanceForm((p) => ({ ...p, attendance_date: e.target.value }))}
                  InputLabelProps={{ shrink: true }}
                />
              </Grid>
              <Grid item xs={6}>
                <TextField
                  label="Status"
                  select
                  fullWidth
                  value={attendanceForm.status}
                  onChange={(e) => setAttendanceForm((p) => ({ ...p, status: e.target.value }))}
                >
                  <MenuItem value="PRESENT">Present</MenuItem>
                  <MenuItem value="ABSENT">Absent</MenuItem>
                  <MenuItem value="HALF_DAY">Half Day</MenuItem>
                  <MenuItem value="LATE">Late Arrival</MenuItem>
                  <MenuItem value="ON_LEAVE">On Approved Leave</MenuItem>
                </TextField>
              </Grid>
              <Grid item xs={6}>
                <TextField
                  label="Check-in Time"
                  fullWidth
                  value={attendanceForm.check_in_time}
                  onChange={(e) => setAttendanceForm((p) => ({ ...p, check_in_time: e.target.value }))}
                />
              </Grid>
              <Grid item xs={6}>
                <TextField
                  label="Check-out Time"
                  fullWidth
                  value={attendanceForm.check_out_time}
                  onChange={(e) => setAttendanceForm((p) => ({ ...p, check_out_time: e.target.value }))}
                />
              </Grid>
              <Grid item xs={12}>
                <TextField
                  label="Remarks"
                  fullWidth
                  value={attendanceForm.remarks}
                  onChange={(e) => setAttendanceForm((p) => ({ ...p, remarks: e.target.value }))}
                />
              </Grid>
            </Grid>
          </DialogContent>
          <DialogActions sx={{ px: 3, pb: 2.5 }}>
            <Button onClick={() => setAttendanceOpen(false)}>Cancel</Button>
            <Button type="submit" variant="contained">Save Punch</Button>
          </DialogActions>
        </form>
      </Dialog>
    </Box>
  )
}
