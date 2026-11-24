import React, { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  Box,
  Typography,
  Grid,
  Card,
  CardContent,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Chip,
  Button,
  Alert,
  CircularProgress,
  List,
  ListItem,
  ListItemText,
  Divider,
} from '@mui/material'
import { TeacherDashboardSummary, teachersApi } from '../../api/teachers'

export const TeacherDashboardPage: React.FC = () => {
  const [data, setData] = useState<TeacherDashboardSummary | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const fetchDashboard = async () => {
    try {
      setLoading(true)
      setError(null)
      const res = await teachersApi.getTeacherDashboard()
      setData(res)
    } catch (err: any) {
      setError(err?.message || 'Failed to load teacher dashboard.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchDashboard()
  }, [])

  if (loading) {
    return (
      <Box sx={{ p: 4, display: 'flex', justifyContent: 'center' }}>
        <CircularProgress />
      </Box>
    )
  }

  if (error || !data) {
    return (
      <Box sx={{ p: 3 }}>
        <Alert severity="warning" action={<Button onClick={() => void fetchDashboard()}>Retry</Button>}>
          {error || 'No faculty profile linked to your account in this institution.'}
        </Alert>
      </Box>
    )
  }

  const {
    teacher,
    assigned_classes,
    assigned_subjects,
    today_timetable,
    attendance_tasks,
    upcoming_examinations,
    assignments_to_evaluate,
    notifications,
  } = data

  return (
    <Box sx={{ width: '100%' }}>
      {/* Welcome Header */}
      <Paper sx={{ p: { xs: 2, sm: 3 }, mb: 3, borderRadius: 3, bgcolor: 'primary.dark', color: 'white' }}>
        <Grid container alignItems="center" spacing={2}>
          <Grid item xs={12} sm>
            <Typography variant="h4" sx={{ fontWeight: 800 }}>
              Welcome back, {teacher.full_name}
            </Typography>
            <Typography variant="body2" sx={{ opacity: 0.9, mt: 0.5 }}>
              {teacher.designation || 'Faculty Member'} · ID: <strong>{teacher.employee_id}</strong> · {teacher.department_name || 'Academic Faculty'}
            </Typography>
          </Grid>
          <Grid item xs={12} sm="auto">
            <Chip
              label={`Status: ${teacher.status}`}
              color="success"
              sx={{ fontWeight: 700, bgcolor: 'success.light', color: 'success.dark' }}
            />
            <Button component={Link} to={`/teachers/${teacher.id}`} sx={{ color: 'white', ml: 1 }}>
              My faculty profile
            </Button>
          </Grid>
        </Grid>
      </Paper>

      {/* KPI Cards */}
      <Grid container spacing={2.5} sx={{ mb: 3 }}>
        <Grid item xs={12} sm={6} md={3}>
          <Card sx={{ borderRadius: 2 }}>
            <CardContent>
              <Typography color="text.secondary" variant="body2">
                Assigned Classes
              </Typography>
              <Typography variant="h4" sx={{ fontWeight: 800, mt: 0.5, color: 'primary.main' }}>
                {assigned_classes.length}
              </Typography>
              <Typography variant="caption" color="text.secondary">
                Active student cohorts
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Card sx={{ borderRadius: 2 }}>
            <CardContent>
              <Typography color="text.secondary" variant="body2">
                Assigned Subjects
              </Typography>
              <Typography variant="h4" sx={{ fontWeight: 800, mt: 0.5 }}>
                {assigned_subjects.length}
              </Typography>
              <Typography variant="caption" color="text.secondary">
                Curriculum courses
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Card sx={{ borderRadius: 2 }}>
            <CardContent>
              <Typography color="text.secondary" variant="body2">
                Today's Periods
              </Typography>
              <Typography variant="h4" sx={{ fontWeight: 800, mt: 0.5, color: 'secondary.main' }}>
                {today_timetable.length}
              </Typography>
              <Typography variant="caption" color="text.secondary">
                Scheduled slots today
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Card sx={{ borderRadius: 2 }}>
            <CardContent>
              <Typography color="text.secondary" variant="body2">
                Pending Evaluations
              </Typography>
              <Typography variant="h4" sx={{ fontWeight: 800, mt: 0.5, color: 'warning.main' }}>
                {assignments_to_evaluate.length}
              </Typography>
              <Typography variant="caption" color="text.secondary">
                Submissions to grade
              </Typography>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Main Grid: Today's Timetable & Attendance Tasks */}
      <Grid container spacing={3} sx={{ mb: 3 }}>
        {/* Today's Timetable */}
        <Grid item xs={12} md={7}>
          <Paper sx={{ p: 2.5, borderRadius: 2, height: '100%' }}>
            <Typography variant="h6" sx={{ fontWeight: 700, mb: 2 }}>
              Today's Teaching Schedule ({today_timetable.length} Periods)
            </Typography>
            <TableContainer>
              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell>Period</TableCell>
                    <TableCell>Time</TableCell>
                    <TableCell>Class / Section</TableCell>
                    <TableCell>Subject</TableCell>
                    <TableCell>Room</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {today_timetable.map((t) => (
                    <TableRow key={t.id} hover>
                      <TableCell sx={{ fontWeight: 700 }}>Period {t.period_number}</TableCell>
                      <TableCell>{t.start_time} - {t.end_time}</TableCell>
                      <TableCell>{t.class_name || t.course_name || 'Standard'}</TableCell>
                      <TableCell>{t.subject_name || 'Subject'}</TableCell>
                      <TableCell>{t.room_number || 'Room 1'}</TableCell>
                    </TableRow>
                  ))}
                  {today_timetable.length === 0 && (
                    <TableRow>
                      <TableCell colSpan={5} sx={{ textAlign: 'center', py: 3, color: 'text.secondary' }}>
                        No periods scheduled for today.
                      </TableCell>
                    </TableRow>
                  )}
                </TableBody>
              </Table>
            </TableContainer>
          </Paper>
        </Grid>

        {/* Attendance Tasks */}
        <Grid item xs={12} md={5}>
          <Paper sx={{ p: 2.5, borderRadius: 2, height: '100%' }}>
            <Typography variant="h6" sx={{ fontWeight: 700, mb: 1.5 }}>
              Daily Attendance Tasks
            </Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
              Mark student attendance for your assigned batches today.
            </Typography>

            <List disablePadding>
              {attendance_tasks.map((task, idx) => (
                <React.Fragment key={idx}>
                  <ListItem
                    sx={{ px: 0, py: 1.5 }}
                    secondaryAction={
                      <Button component={Link} to="/attendance?tab=roll-call" variant="outlined" size="small" color="primary">
                        Mark Attendance
                      </Button>
                    }
                  >
                    <ListItemText
                      primary={
                        <Typography variant="subtitle2" sx={{ fontWeight: 700 }}>
                          {task.class_name}
                        </Typography>
                      }
                      secondary={`Due by: ${task.due_time} | Status: ${task.status}`}
                    />
                  </ListItem>
                  {idx < attendance_tasks.length - 1 && <Divider />}
                </React.Fragment>
              ))}
              {attendance_tasks.length === 0 && (
                <Typography variant="body2" color="text.secondary" sx={{ py: 2 }}>
                  No attendance tasks pending for today.
                </Typography>
              )}
            </List>
          </Paper>
        </Grid>
      </Grid>

      {/* Secondary Grid: Upcoming Exams, Assignments to Evaluate, Notifications */}
      <Grid container spacing={3}>
        {/* Assigned Classes & Subjects Overview */}
        <Grid item xs={12} md={4}>
          <Paper sx={{ p: 2.5, borderRadius: 2 }}>
            <Typography variant="h6" sx={{ fontWeight: 700, mb: 2 }}>
              My Classes & Subjects
            </Typography>
            <Typography variant="subtitle2" color="text.secondary" sx={{ mb: 1 }}>
              Classes:
            </Typography>
            <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap', mb: 2 }}>
              {assigned_classes.map((c) => (
                <Chip
                  key={c.id}
                  label={c.is_class_teacher ? `${c.title} (Class Teacher)` : c.title}
                  color={c.is_class_teacher ? 'primary' : 'default'}
                  size="small"
                />
              ))}
            </Box>

            <Typography variant="subtitle2" color="text.secondary" sx={{ mb: 1 }}>
              Subjects:
            </Typography>
            <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
              {assigned_subjects.map((s) => (
                <Chip key={s.id} label={`${s.title} (${s.code || 'Sub'})`} variant="outlined" size="small" />
              ))}
            </Box>
          </Paper>
        </Grid>

        {/* Assignments to Evaluate */}
        <Grid item xs={12} md={4}>
          <Paper sx={{ p: 2.5, borderRadius: 2 }}>
            <Typography variant="h6" sx={{ fontWeight: 700, mb: 2 }}>
              Submissions to Evaluate
            </Typography>
            {assignments_to_evaluate.map((a, idx) => (
              <Box key={idx} sx={{ mb: 2, p: 1.5, bgcolor: 'action.hover', borderRadius: 1.5 }}>
                <Typography variant="subtitle2" fontWeight={700}>
                  {a.title}
                </Typography>
                <Typography variant="caption" color="text.secondary" display="block">
                  Class: {a.class_name} | Evaluated: {a.evaluated_count} / {a.submissions_count}
                </Typography>
                <Button component={Link} to="/lms?tab=assignments" size="small" sx={{ mt: 1 }}>
                  Grade Submissions →
                </Button>
              </Box>
            ))}
            {assignments_to_evaluate.length === 0 && <Typography color="text.secondary">No submissions awaiting review.</Typography>}
          </Paper>
        </Grid>

        {/* Upcoming Examinations & Announcements */}
        <Grid item xs={12} md={4}>
          <Paper sx={{ p: 2.5, borderRadius: 2 }}>
            <Typography variant="h6" sx={{ fontWeight: 700, mb: 2 }}>
              Your Upcoming Exams & Alerts
            </Typography>
            {upcoming_examinations.map((ex, idx) => (
              <Box key={idx} sx={{ mb: 1.5 }}>
                <Typography variant="subtitle2" fontWeight={700} color="primary.main">
                  {ex.title}
                </Typography>
                <Typography variant="caption" color="text.secondary">
                  Subject: {ex.subject} | Date: {ex.date}
                </Typography>
              </Box>
            ))}
            {upcoming_examinations.length === 0 && <Typography color="text.secondary">No exams scheduled by you.</Typography>}

            <Divider sx={{ my: 1.5 }} />

            <Typography variant="subtitle2" fontWeight={700} sx={{ mb: 1 }}>
              Staff Announcements
            </Typography>
            {notifications.map((n, idx) => (
              <Box key={idx}>
                <Typography variant="body2" fontWeight={600}>
                  {n.title}
                </Typography>
                <Typography variant="caption" color="text.secondary">
                  {n.message}
                </Typography>
              </Box>
            ))}
            {notifications.length === 0 && <Typography color="text.secondary">No staff alerts.</Typography>}
          </Paper>
        </Grid>
      </Grid>
    </Box>
  )
}
