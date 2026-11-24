import { useState } from 'react'
import { alpha } from '@mui/material/styles'
import {
  Alert, Box, Button, Chip, Dialog, DialogContent, DialogTitle, IconButton, LinearProgress,
  MenuItem, Paper, Tab, Table, TableBody, TableCell, TableContainer, TableHead, TableRow,
  Tabs, TextField, Tooltip, Typography,
} from '@mui/material'
import BarChart from '@mui/icons-material/BarChart'
import CalendarMonth from '@mui/icons-material/CalendarMonth'
import Checklist from '@mui/icons-material/Checklist'
import Groups from '@mui/icons-material/Groups'
import MenuBook from '@mui/icons-material/MenuBook'
import PersonOutline from '@mui/icons-material/PersonOutline'
import Search from '@mui/icons-material/Search'
import VisibilityOutlined from '@mui/icons-material/VisibilityOutlined'
import WarningAmber from '@mui/icons-material/WarningAmber'
import { useQuery } from '@tanstack/react-query'
import { academicsApi, type AcademicSession, type CollegeSemester, type Course, type Department, type SchoolClass, type Section } from '@/api/academics'
import { attendanceApi, type CohortAttendanceFilters, type CohortAttendanceStudent, type CohortAttendanceSubject } from '@/api/attendance'

const eligibilityThreshold = 75
const percent = (value: number | null) => value === null ? '—' : `${value.toFixed(1)}%`

function AttendanceStatus({ value }: { value: number | null }) {
  if (value === null) return <Chip size="small" variant="outlined" label="No records" />
  const eligible = value >= eligibilityThreshold
  return <Chip size="small" color={eligible ? 'success' : 'error'} label={eligible ? 'Meets 75%' : 'Below 75%'} variant="outlined" />
}

function StudentTable({ students }: { students: CohortAttendanceStudent[] }) {
  return (
    <TableContainer component={Paper} variant="outlined">
      <Table size="small" sx={{ minWidth: 580 }}>
        <TableHead><TableRow>
          <TableCell>Student</TableCell><TableCell>Admission no.</TableCell>
          <TableCell align="right">Classes recorded</TableCell><TableCell align="right">Attended</TableCell>
          <TableCell align="right">Attendance</TableCell><TableCell>Status</TableCell>
        </TableRow></TableHead>
        <TableBody>{students.map((student) => (
          <TableRow key={student.id} hover>
            <TableCell component="th" scope="row">{student.name}</TableCell><TableCell>{student.admission_number}</TableCell>
            <TableCell align="right">{student.total}</TableCell><TableCell align="right">{student.attended}</TableCell>
            <TableCell align="right">{percent(student.percentage)}</TableCell><TableCell><AttendanceStatus value={student.percentage} /></TableCell>
          </TableRow>
        ))}</TableBody>
      </Table>
    </TableContainer>
  )
}

export function AttendanceCohortReport({ isCollege, tenantId, sessions, departments, courses, classes }: {
  isCollege: boolean
  tenantId?: string | null
  sessions: AcademicSession[]
  departments: Department[]
  courses: Course[]
  classes: SchoolClass[]
}) {
  const [department, setDepartment] = useState('')
  const [course, setCourse] = useState('')
  const [semester, setSemester] = useState('')
  const [classId, setClassId] = useState('')
  const [section, setSection] = useState('')
  const [session, setSession] = useState('')
  const [tab, setTab] = useState(isCollege ? 'subject' : 'student')
  const [submitted, setSubmitted] = useState<CohortAttendanceFilters>()
  const [selectedSubject, setSelectedSubject] = useState<CohortAttendanceSubject>()

  const selectedSession = session || sessions.find((item) => item.is_current)?.id || sessions[0]?.id || ''
  const semesters = useQuery<CollegeSemester[]>({
    queryKey: ['attendance-report-semesters', tenantId, course],
    enabled: isCollege && Boolean(course),
    queryFn: async () => (await academicsApi.getSemesters(course)).data ?? [],
  })
  const sections = useQuery<Section[]>({
    queryKey: ['attendance-report-sections', tenantId, classId],
    enabled: !isCollege && Boolean(classId),
    queryFn: async () => (await academicsApi.getSections({ class_id: classId })).data ?? [],
  })
  const report = useQuery({
    queryKey: ['attendance-cohort-report', tenantId, submitted],
    enabled: Boolean(submitted),
    queryFn: () => attendanceApi.getCohortReport(submitted!),
  })
  const data = report.data
  const belowThreshold = data?.students.filter(({ percentage }) => percentage !== null && percentage < eligibilityThreshold).length ?? 0
  const metrics = data && [
    { label: 'Total students', value: data.students.length, icon: Groups, tone: 'secondary' as const },
    { label: 'Average attendance', value: percent(data.overview.percentage), icon: Checklist, tone: 'success' as const },
    { label: 'Students below 75%', value: belowThreshold, icon: WarningAmber, tone: 'error' as const },
    { label: 'Subjects with records', value: data.subjects.filter((subject) => subject.id !== null).length, icon: CalendarMonth, tone: 'info' as const },
  ]

  return (
    <Box sx={{ display: 'grid', gap: 2, minWidth: 0 }}>
      <Paper component="form" variant="outlined" onSubmit={(event) => {
        event.preventDefault()
        const filters = {
          academic_session_id: selectedSession,
          ...(isCollege ? { department_id: department, course_id: course, semester_id: semester } : {
            class_id: classId, section_id: section || undefined,
          }),
        }
        if (JSON.stringify(filters) === JSON.stringify(submitted)) void report.refetch()
        else setSubmitted(filters)
      }} sx={{
        p: 2, display: 'grid', gap: 1.5, alignItems: 'center',
        gridTemplateColumns: {
          xs: 'minmax(0, 1fr)', sm: 'repeat(2, minmax(0, 1fr))',
          lg: isCollege ? 'minmax(0,2fr) minmax(0,1.25fr) minmax(0,1fr) minmax(0,1.4fr) auto'
            : 'repeat(3, minmax(0,1fr)) auto',
        },
      }}>
        {isCollege ? <>
          <TextField label="Department" select size="small" value={department} onChange={(event) => {
            setDepartment(event.target.value); setCourse(''); setSemester(''); setSubmitted(undefined)
          }}>
            <MenuItem value="" disabled>Select department</MenuItem>
            {departments.map((item) => <MenuItem key={item.id} value={item.id}>{item.name}</MenuItem>)}
          </TextField>
          <TextField label="Course" select size="small" value={course} disabled={!department} onChange={(event) => {
            setCourse(event.target.value); setSemester(''); setSubmitted(undefined)
          }}>
            <MenuItem value="" disabled>Select course</MenuItem>
            {courses.filter((item) => item.department_id === department).map((item) => <MenuItem key={item.id} value={item.id}>{item.name}</MenuItem>)}
          </TextField>
          <TextField label="Semester" select size="small" value={semester} disabled={!course || semesters.isFetching}
            onChange={(event) => { setSemester(event.target.value); setSubmitted(undefined) }}>
            <MenuItem value="" disabled>Select semester</MenuItem>
            {semesters.data?.map((item) => <MenuItem key={item.id} value={item.id}>{item.name}</MenuItem>)}
          </TextField>
        </> : <>
          <TextField label="Class" select size="small" value={classId} onChange={(event) => {
            setClassId(event.target.value); setSection(''); setSubmitted(undefined)
          }}>
            <MenuItem value="" disabled>Select class</MenuItem>
            {classes.map((item) => <MenuItem key={item.id} value={item.id}>{item.name}</MenuItem>)}
          </TextField>
          <TextField label="Section" select size="small" value={section} disabled={!classId || sections.isFetching}
            onChange={(event) => { setSection(event.target.value); setSubmitted(undefined) }}>
            <MenuItem value="">All sections</MenuItem>
            {sections.data?.map((item) => <MenuItem key={item.id} value={item.id}>{item.name}</MenuItem>)}
          </TextField>
        </>}
        <TextField label="Session" select size="small" value={selectedSession}
          onChange={(event) => { setSession(event.target.value); setSubmitted(undefined) }}>
          <MenuItem value="" disabled>Select session</MenuItem>
          {sessions.map((item) => <MenuItem key={item.id} value={item.id}>{item.name}</MenuItem>)}
        </TextField>
        <Button color="secondary" variant="contained" type="submit" startIcon={<Search />}
          disabled={!selectedSession || report.isFetching || (isCollege ? !department || !course || !semester : !classId)}
          sx={{ minHeight: 40 }}>
          View
        </Button>
      </Paper>

      <Tabs value={tab} onChange={(_, next) => setTab(next)} aria-label="Attendance report views"
        textColor="secondary" sx={(theme) => ({
          bgcolor: alpha(theme.palette.secondary.main, 0.08), borderRadius: 2, width: 'fit-content', maxWidth: '100%',
          '& .MuiTabs-indicator': { display: 'none' },
          '& .MuiTab-root': { borderRadius: 2, minWidth: 'auto' },
          '& .MuiTab-root.Mui-selected': { bgcolor: 'secondary.main', color: 'secondary.contrastText' },
        })}>
        <Tab value="subject" label="Subject-wise" icon={<MenuBook />} iconPosition="start" />
        <Tab value="student" label="Student-wise" icon={<PersonOutline />} iconPosition="start" />
        <Tab value="overview" label="Overview" icon={<BarChart />} iconPosition="start" />
      </Tabs>
      {(semesters.isError || sections.isError) && <Alert severity="error">Unable to load the selected group’s options.</Alert>}
      {!submitted && <Alert severity="info">Select a group and session, then choose View.</Alert>}
      {submitted && report.isPending && <LinearProgress aria-label="Loading attendance report" />}
      {report.isError && <Alert severity="error">{(report.error as { message?: string })?.message || 'Unable to load attendance for this group.'}</Alert>}
      {metrics && (
        <Box sx={{ display: 'grid', gap: 1.5, gridTemplateColumns: { xs: 'repeat(2, minmax(0,1fr))', lg: 'repeat(4, minmax(0,1fr))' } }}>
          {metrics.map(({ label, value, icon: Icon, tone }) => (
            <Box key={label} sx={(theme) => ({
              display: 'flex', gap: 1.5, alignItems: 'center', minWidth: 0, p: { xs: 1.25, sm: 1.75 },
              borderRadius: 2, bgcolor: alpha(theme.palette[tone].main, 0.10),
            })}>
              <Box sx={(theme) => ({
                display: { xs: 'none', sm: 'grid' }, placeItems: 'center', flexShrink: 0, width: 40, height: 40,
                color: theme.palette[tone].main, bgcolor: alpha(theme.palette[tone].main, 0.12), borderRadius: 1.5,
              })}><Icon fontSize="small" /></Box>
              <Box><Typography variant="h5" fontWeight={800}>{value}</Typography><Typography variant="caption">{label}</Typography></Box>
            </Box>
          ))}
        </Box>
      )}
      {data && tab === 'subject' && (data.subjects.length ? (
        <TableContainer component={Paper} variant="outlined">
          <Table size="small" sx={{ minWidth: 690 }}>
            <TableHead sx={{ '& .MuiTableCell-head': { bgcolor: (theme) => alpha(theme.palette.secondary.main, 0.12) } }}>
              <TableRow>
                <TableCell>#</TableCell><TableCell>Subject</TableCell><TableCell align="right">Total classes</TableCell>
                <TableCell align="right">Attendance recorded</TableCell><TableCell align="right">Attendance %</TableCell>
                <TableCell>Status</TableCell><TableCell align="center">Actions</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>{data.subjects.map((subject, index) => (
              <TableRow key={subject.id ?? 'daily'} hover>
                <TableCell>{index + 1}</TableCell><TableCell component="th" scope="row">{subject.name}</TableCell>
                <TableCell align="right">{subject.classes}</TableCell>
                <TableCell align="right">{subject.attended} / {subject.total}</TableCell>
                <TableCell align="right">{percent(subject.percentage)}</TableCell>
                <TableCell><AttendanceStatus value={subject.percentage} /></TableCell>
                <TableCell align="center"><Tooltip title="View students">
                  <IconButton aria-label={`View students for ${subject.name}`} size="small" color="secondary" onClick={() => setSelectedSubject(subject)}>
                    <VisibilityOutlined fontSize="small" />
                  </IconButton>
                </Tooltip></TableCell>
              </TableRow>
            ))}</TableBody>
          </Table>
        </TableContainer>
      ) : <Box sx={{ display: 'grid', gap: 1.5 }}>
        <Alert severity="info">No submitted attendance records for this group and session.</Alert>
        {data.students.length > 0 && <StudentTable students={data.students} />}
      </Box>)}
      {data && tab === 'student' && (data.students.length ? <StudentTable students={data.students} />
        : <Alert severity="info">No students are enrolled in this group and session.</Alert>)}
      {data && tab === 'overview' && <Paper variant="outlined" sx={{ p: 2 }}>
        <Typography variant="h6">Cohort attendance</Typography>
        <Typography sx={{ my: 1 }}>{data.overview.attended} attended out of {data.overview.total} recorded student-class entries.</Typography>
        <Typography variant="body2" color="text.secondary">
          Present and late marks count as attended. Students with no marks are excluded from the average and the below-75% count.
        </Typography>
      </Paper>}
      <Dialog open={Boolean(selectedSubject)} onClose={() => setSelectedSubject(undefined)} fullWidth maxWidth="md" aria-labelledby="subject-attendance-title">
        <DialogTitle id="subject-attendance-title">{selectedSubject?.name}</DialogTitle>
        <DialogContent dividers>{selectedSubject && <StudentTable students={selectedSubject.students} />}</DialogContent>
      </Dialog>
    </Box>
  )
}
