import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Alert, Box, Button, Chip, Dialog, DialogActions, DialogContent, DialogTitle, IconButton, LinearProgress, MenuItem, Paper, Stack, Table, TableBody, TableCell, TableContainer, TableHead, TableRow, TextField, Tooltip, Typography } from '@mui/material'
import Add from '@mui/icons-material/Add'
import DeleteOutline from '@mui/icons-material/DeleteOutline'
import EditOutlined from '@mui/icons-material/EditOutlined'
import MenuBookOutlined from '@mui/icons-material/MenuBookOutlined'
import { academicsApi, type AcademicSession, type AcademicSubjectMapping, type CollegeSemester, type Course, type Department, type Subject } from '@/api/academics'
import { useAuthStore } from '@/store/authStore'

type SubjectForm = { name: string; code: string; department_id: string; subject_type: string; credits: number; hours_per_week: number; description: string }
const blankSubject: SubjectForm = { name: '', code: '', department_id: '', subject_type: 'THEORY', credits: 3, hours_per_week: 4, description: '' }
function message(error: unknown) { return (error as { message?: string })?.message || 'Something went wrong. Please try again.' }

export default function SubjectsPage() {
  const user = useAuthStore((state) => state.user)
  const tenant = user?.current_tenant_id
  const institution = user?.institutions.find((item) => item.tenant_id === tenant)
  const queryClient = useQueryClient()
  const [search, setSearch] = useState('')
  const [department, setDepartment] = useState('')
  const [form, setForm] = useState<SubjectForm>(blankSubject)
  const [editing, setEditing] = useState<Subject | null>(null)
  const [formOpen, setFormOpen] = useState(false)
  const [deleteSubject, setDeleteSubject] = useState<Subject | null>(null)
  const [assigning, setAssigning] = useState<Subject | null>(null)
  const [removeMapping, setRemoveMapping] = useState<AcademicSubjectMapping | null>(null)
  const [course, setCourse] = useState('')
  const [semester, setSemester] = useState('')
  const [session, setSession] = useState('')
  const isCollege = institution?.institution_type === 'COLLEGE'
  const scope = ['college-subjects', tenant]
  const catalog = useQuery({ queryKey: [...scope, 'catalog'], enabled: isCollege, queryFn: async () => (await academicsApi.getSubjects()).data as Subject[] })
  const departments = useQuery({ queryKey: [...scope, 'departments'], enabled: isCollege, queryFn: async () => (await academicsApi.getDepartments()).data as Department[] })
  const courses = useQuery({ queryKey: [...scope, 'courses'], enabled: isCollege, queryFn: async () => (await academicsApi.getCourses()).data as Course[] })
  const sessions = useQuery({ queryKey: [...scope, 'sessions'], enabled: isCollege, queryFn: async () => (await academicsApi.getSessions()).data as AcademicSession[] })
  const mappings = useQuery({ queryKey: [...scope, 'mappings'], enabled: isCollege, queryFn: async () => (await academicsApi.getSubjectMappings()).data as AcademicSubjectMapping[] })
  const semesters = useQuery({ queryKey: [...scope, 'semesters', course], enabled: Boolean(isCollege && course && assigning), queryFn: async () => (await academicsApi.getSemesters(course)).data as CollegeSemester[] })
  const invalidate = () => queryClient.invalidateQueries({ queryKey: scope })
  const save = useMutation({ mutationFn: () => {
    const payload = { ...form, name: form.name.trim(), code: form.code.trim().toUpperCase(), is_elective: form.subject_type === 'ELECTIVE' }
    return editing ? academicsApi.updateSubject(editing.id, payload) : academicsApi.createSubject(payload)
  }, onSuccess: async () => { await invalidate(); setFormOpen(false) } })
  const remove = useMutation({ mutationFn: () => academicsApi.deleteSubject(deleteSubject!.id), onSuccess: async () => { await invalidate(); setDeleteSubject(null) } })
  const assign = useMutation({ mutationFn: () => academicsApi.createSubjectMapping({
    subject_id: assigning!.id, academic_session_id: session, course_id: course, semester_id: semester,
    credits: assigning!.credits ?? 0, weekly_hours: assigning!.hours_per_week, is_elective: assigning!.is_elective,
  }), onSuccess: async () => { await invalidate(); setAssigning(null) } })
  const unassign = useMutation({ mutationFn: () => academicsApi.deleteSubjectMapping(removeMapping!.id), onSuccess: async () => { await invalidate(); setRemoveMapping(null) } })
  if (!isCollege) return <Alert severity="info">Subjects for this page are available to college administrators.</Alert>
  const items = (catalog.data || []).filter((item) => (!department || item.department_id === department) && (item.name + ' ' + item.code).toLowerCase().includes(search.toLowerCase().trim()))
  const loading = [catalog, departments, courses, sessions, mappings].some((query) => query.isLoading)
  const failed = [catalog, departments, courses, sessions, mappings].some((query) => query.isError)
  return <Stack spacing={2.5}>
    <Stack direction={{ xs: 'column', sm: 'row' }} alignItems={{ sm: 'center' }} justifyContent="space-between" gap={2}>
      <Stack direction="row" spacing={1.5} alignItems="center"><MenuBookOutlined color="primary" /><Box><Typography component="h1" variant="h4" fontWeight={700}>Subjects</Typography><Typography color="text.secondary">Manage subjects and assign them to courses and semesters.</Typography></Box></Stack>
      <Button variant="contained" startIcon={<Add />} onClick={() => { save.reset(); setEditing(null); setForm(blankSubject); setFormOpen(true) }}>Add subject</Button>
    </Stack>
    <Paper variant="outlined" sx={{ p: 2 }}><Stack direction={{ xs: 'column', sm: 'row' }} spacing={2}><TextField size="small" label="Search subjects" value={search} onChange={(event) => setSearch(event.target.value)} fullWidth /><TextField select size="small" label="Department" value={department} onChange={(event) => setDepartment(event.target.value)} fullWidth><MenuItem value="">All departments</MenuItem>{departments.data?.map((item) => <MenuItem key={item.id} value={item.id}>{item.name}</MenuItem>)}</TextField></Stack></Paper>
    {loading && <LinearProgress aria-label="Loading subjects" />}
    {failed && <Alert severity="error" action={<Button onClick={() => void invalidate()}>Retry</Button>}>Unable to load academic records.</Alert>}
    <TableContainer component={Paper} variant="outlined"><Table sx={{ minWidth: 720 }} aria-label="Subjects"><TableHead><TableRow><TableCell>Subject</TableCell><TableCell>Department</TableCell><TableCell>Type</TableCell><TableCell>Credits</TableCell><TableCell>Course assignments</TableCell><TableCell align="right">Actions</TableCell></TableRow></TableHead><TableBody>
      {items.map((subject) => <TableRow key={subject.id} hover><TableCell><Typography fontWeight={700}>{subject.name}</Typography><Typography variant="caption" color="text.secondary">{subject.code}</Typography></TableCell><TableCell>{subject.department_name || '—'}</TableCell><TableCell>{subject.subject_type}</TableCell><TableCell>{subject.credits ?? '—'}</TableCell><TableCell><Stack direction="row" gap={0.5} flexWrap="wrap">{mappings.data?.filter((mapping) => mapping.subject_id === subject.id).map((mapping) => <Chip key={mapping.id} size="small" label={mapping.course_name ? `${mapping.course_name} · ${mapping.semester_number ? 'Semester ' + mapping.semester_number : 'All semesters'} · ${sessions.data?.find((s) => s.id === mapping.academic_session_id)?.name || 'Session'}` : mapping.class_name || 'Assignment'} onDelete={() => { unassign.reset(); setRemoveMapping(mapping) }} />)}<Button size="small" onClick={() => { assign.reset(); setCourse(''); setSemester(''); setSession(sessions.data?.find((item) => item.is_current)?.id || ''); setAssigning(subject) }}>Assign</Button></Stack></TableCell><TableCell align="right"><Tooltip title="Edit"><IconButton aria-label={`Edit ${subject.name}`} size="small" onClick={() => { save.reset(); setEditing(subject); setForm({ name: subject.name, code: subject.code, department_id: subject.department_id || '', subject_type: subject.subject_type, credits: subject.credits ?? 0, hours_per_week: subject.hours_per_week, description: subject.description || '' }); setFormOpen(true) }}><EditOutlined fontSize="small" /></IconButton></Tooltip><Tooltip title="Delete"><IconButton aria-label={`Delete ${subject.name}`} size="small" color="error" onClick={() => { remove.reset(); setDeleteSubject(subject) }}><DeleteOutline fontSize="small" /></IconButton></Tooltip></TableCell></TableRow>)}
      {!loading && !failed && items.length === 0 && <TableRow><TableCell colSpan={6} align="center" sx={{ py: 5 }}>No subjects found.</TableCell></TableRow>}
    </TableBody></Table></TableContainer>
    <Dialog open={formOpen} onClose={() => { if (!save.isPending) setFormOpen(false) }} fullWidth maxWidth="sm"><Box component="form" onSubmit={(event) => { event.preventDefault(); save.mutate() }}><DialogTitle>{editing ? 'Edit subject' : 'Add subject'}</DialogTitle><DialogContent dividers><Stack spacing={2} sx={{ pt: 1 }}>
      {save.isError && <Alert severity="error">{message(save.error)}</Alert>}
      <TextField label="Subject name" required value={form.name} onChange={(event) => setForm({ ...form, name: event.target.value })} />
      <TextField label="Subject code" required value={form.code} onChange={(event) => setForm({ ...form, code: event.target.value })} />
      <TextField select label="Department" required value={form.department_id} onChange={(event) => setForm({ ...form, department_id: event.target.value })}>{departments.data?.map((item) => <MenuItem key={item.id} value={item.id}>{item.name}</MenuItem>)}</TextField>
      <TextField select label="Type" value={form.subject_type} onChange={(event) => setForm({ ...form, subject_type: event.target.value })}>{['THEORY', 'LAB', 'PRACTICAL', 'ELECTIVE', 'VOCATIONAL'].map((item) => <MenuItem key={item} value={item}>{item}</MenuItem>)}</TextField>
      <Stack direction="row" spacing={2}><TextField type="number" label="Credits" required inputProps={{ min: 0, max: 20 }} value={form.credits} onChange={(event) => setForm({ ...form, credits: Number(event.target.value) })} fullWidth /><TextField type="number" label="Hours per week" required inputProps={{ min: 1, max: 40 }} value={form.hours_per_week} onChange={(event) => setForm({ ...form, hours_per_week: Number(event.target.value) })} fullWidth /></Stack>
      <TextField label="Description" multiline minRows={2} value={form.description} onChange={(event) => setForm({ ...form, description: event.target.value })} />
    </Stack></DialogContent><DialogActions><Button onClick={() => setFormOpen(false)} disabled={save.isPending}>Cancel</Button><Button type="submit" variant="contained" disabled={save.isPending || !form.department_id || !form.name.trim() || !form.code.trim()}>Save</Button></DialogActions></Box></Dialog>
    <Dialog open={Boolean(assigning)} onClose={() => { if (!assign.isPending) setAssigning(null) }} fullWidth maxWidth="xs"><Box component="form" onSubmit={(event) => { event.preventDefault(); assign.mutate() }}><DialogTitle>Assign {assigning?.name}</DialogTitle><DialogContent dividers><Stack spacing={2} sx={{ pt: 1 }}>
      {assign.isError && <Alert severity="error">{message(assign.error)}</Alert>}{semesters.isError && <Alert severity="error">Unable to load semesters.</Alert>}
      <TextField select label="Academic session" required value={session} onChange={(event) => setSession(event.target.value)}>{sessions.data?.map((item) => <MenuItem key={item.id} value={item.id}>{item.name}</MenuItem>)}</TextField>
      <TextField select label="Course" required value={course} onChange={(event) => { setCourse(event.target.value); setSemester('') }}>{courses.data?.map((item) => <MenuItem key={item.id} value={item.id}>{item.name}</MenuItem>)}</TextField>
      <TextField select label="Semester" required value={semester} disabled={!course || semesters.isFetching} onChange={(event) => setSemester(event.target.value)}>{semesters.data?.map((item) => <MenuItem key={item.id} value={item.id}>{item.name}</MenuItem>)}</TextField>
    </Stack></DialogContent><DialogActions><Button onClick={() => setAssigning(null)} disabled={assign.isPending}>Cancel</Button><Button type="submit" variant="contained" disabled={assign.isPending || !session || !course || !semester}>Assign</Button></DialogActions></Box></Dialog>
    <Dialog open={Boolean(deleteSubject)} onClose={() => { if (!remove.isPending) setDeleteSubject(null) }}><DialogTitle>Delete subject?</DialogTitle><DialogContent><Typography>Delete {deleteSubject?.name}?</Typography>{remove.isError && <Alert severity="error">{message(remove.error)}</Alert>}</DialogContent><DialogActions><Button onClick={() => setDeleteSubject(null)} disabled={remove.isPending}>Cancel</Button><Button color="error" disabled={remove.isPending} onClick={() => remove.mutate()}>Delete</Button></DialogActions></Dialog>
    <Dialog open={Boolean(removeMapping)} onClose={() => { if (!unassign.isPending) setRemoveMapping(null) }}><DialogTitle>Remove course assignment?</DialogTitle><DialogContent><Typography>Remove {removeMapping?.subject_name} from this course and session?</Typography>{unassign.isError && <Alert severity="error">{message(unassign.error)}</Alert>}</DialogContent><DialogActions><Button onClick={() => setRemoveMapping(null)} disabled={unassign.isPending}>Cancel</Button><Button color="error" disabled={unassign.isPending} onClick={() => unassign.mutate()}>Remove</Button></DialogActions></Dialog>
  </Stack>
}
