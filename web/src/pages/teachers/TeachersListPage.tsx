import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  Alert, Avatar, Box, Button, Chip, Dialog, DialogActions, DialogContent, DialogTitle, Divider,
  LinearProgress, MenuItem, Paper, Stack, Tab, Table, TableBody, TableCell, TableContainer,
  TableHead, TablePagination, TableRow, Tabs, TextField, Typography,
} from '@mui/material'
import Add from '@mui/icons-material/Add'
import Badge from '@mui/icons-material/BadgeOutlined'
import OpenInNew from '@mui/icons-material/OpenInNew'
import Search from '@mui/icons-material/Search'
import { staffRoleLabels, teachersApi } from '@/api/teachers'
import type { StaffRole, TeacherItem, TeacherLeaveItem } from '@/api/teachers'
import { useAuthStore } from '@/store/authStore'
import { AddEditTeacherModal } from './AddEditTeacherModal'

const PAGE_SIZE = 15

function errorMessage(error: unknown, fallback: string) {
  return typeof error === 'object' && error && 'message' in error && typeof error.message === 'string'
    ? error.message
    : fallback
}

export function TeachersListPage() {
  const user = useAuthStore((state) => state.user)
  const isSchool = user?.institutions.some((item) => item.tenant_id === user.current_tenant_id && item.institution_type === 'SCHOOL')
  const canManage = Boolean(user?.is_superadmin || user?.current_role === 'INSTITUTION_ADMIN')
  const departmentScope = user?.current_role === 'HOD'
  const queryClient = useQueryClient()
  const scope = [user?.id, user?.current_tenant_id, user?.current_role]
  const [view, setView] = useState<'directory' | 'leave'>('directory')
  const [searchInput, setSearchInput] = useState('')
  const [search, setSearch] = useState('')
  const [department, setDepartment] = useState('')
  const [status, setStatus] = useState('')
  const [employment, setEmployment] = useState('')
  const [page, setPage] = useState(0)
  const [addOpen, setAddOpen] = useState(false)
  const [accessTarget, setAccessTarget] = useState<TeacherItem | null>(null)
  const [deleteTarget, setDeleteTarget] = useState<TeacherItem | null>(null)
  const [reviewTarget, setReviewTarget] = useState<TeacherLeaveItem | null>(null)
  const [role, setRole] = useState<StaffRole>('TEACHER')
  const [accessDepartment, setAccessDepartment] = useState('')
  const [decision, setDecision] = useState<'APPROVED' | 'REJECTED'>('APPROVED')
  const [reason, setReason] = useState('')

  const departments = useQuery({
    queryKey: ['staff-departments', ...scope],
    queryFn: teachersApi.listDepartments,
  })
  const directory = useQuery({
    queryKey: ['staff-directory', ...scope, search, department, status, employment, page],
    queryFn: () => teachersApi.listTeachers({
      search: search || undefined,
      department_id: department || undefined,
      status: status || undefined,
      employment_type: employment || undefined,
      page: page + 1,
      size: PAGE_SIZE,
    }),
    enabled: view === 'directory',
  })
  const leaves = useQuery({
    queryKey: ['staff-leaves', ...scope],
    queryFn: teachersApi.listPendingLeaves,
    enabled: view === 'leave',
  })
  const refreshDirectory = () => queryClient.invalidateQueries({ queryKey: ['staff-directory', ...scope] })
  const deleteTeacher = useMutation({
    mutationFn: () => teachersApi.deleteTeacher(deleteTarget!.id),
    onSuccess: async () => {
      await refreshDirectory()
      setDeleteTarget(null)
    },
  })
  const updateAccess = useMutation({
    mutationFn: () => teachersApi.updateStaffAccess(accessTarget!.id, {
      role,
      department_id: accessDepartment || undefined,
    }),
    onSuccess: async () => {
      await refreshDirectory()
      setAccessTarget(null)
    },
  })
  const reviewLeave = useMutation({
    mutationFn: () => teachersApi.reviewLeave(reviewTarget!.id, {
      status: decision,
      rejection_reason: decision === 'REJECTED' ? reason.trim() || undefined : undefined,
    }),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['staff-leaves', ...scope] })
      setReviewTarget(null)
    },
  })
  const currentQuery = view === 'directory' ? directory : leaves

  return (
    <Stack spacing={2.5}>
      <Stack direction={{ xs: 'column', sm: 'row' }} justifyContent="space-between" alignItems={{ sm: 'center' }} gap={2}>
        <Stack direction="row" spacing={1.5} alignItems="center">
          <Avatar variant="rounded" sx={{ bgcolor: 'action.selected', color: 'primary.main', width: 48, height: 48 }}>
            <Badge />
          </Avatar>
          <Box>
            <Typography component="h1" variant="h4">Faculty & Staff</Typography>
            <Typography color="text.secondary">
              {departmentScope ? 'View faculty and review leave in your assigned departments.' : 'Browse faculty records and review pending leave requests.'}
            </Typography>
          </Box>
        </Stack>
        {canManage && <Button variant="contained" startIcon={<Add />} onClick={() => setAddOpen(true)}>Add faculty</Button>}
      </Stack>

      <Paper variant="outlined" sx={{ overflow: 'hidden' }}>
        <Tabs value={view} onChange={(_, next: 'directory' | 'leave') => setView(next)} aria-label="Staff workspace">
          <Tab value="directory" label="Faculty directory" />
          <Tab value="leave" label="Leave requests" />
        </Tabs>
        <Divider />
        {view === 'directory' && (
          <Box component="form" onSubmit={(event) => {
            event.preventDefault()
            setPage(0)
            setSearch(searchInput.trim())
          }} sx={{ p: 2, display: 'grid', gap: 1.5, gridTemplateColumns: { xs: '1fr', sm: 'minmax(160px, 2fr) 1fr', lg: 'minmax(180px, 2fr) 1fr 1fr 1fr auto' } }}>
            <TextField size="small" label="Name, employee ID or designation" value={searchInput} onChange={(event) => setSearchInput(event.target.value)} />
            <TextField select size="small" label="Department" value={department} onChange={(event) => { setDepartment(event.target.value); setPage(0) }}>
              <MenuItem value="">All departments</MenuItem>
              {departments.data?.map((item) => <MenuItem key={item.id} value={item.id}>{item.name}</MenuItem>)}
            </TextField>
            <TextField select size="small" label="Status" value={status} onChange={(event) => { setStatus(event.target.value); setPage(0) }}>
              <MenuItem value="">All statuses</MenuItem><MenuItem value="ACTIVE">Active</MenuItem><MenuItem value="INACTIVE">Inactive</MenuItem>
            </TextField>
            <TextField select size="small" label="Employment" value={employment} onChange={(event) => { setEmployment(event.target.value); setPage(0) }}>
              <MenuItem value="">All employment types</MenuItem><MenuItem value="FULL_TIME">Full-time</MenuItem>
              <MenuItem value="PART_TIME">Part-time</MenuItem><MenuItem value="CONTRACT">Contract</MenuItem><MenuItem value="VISITING">Visiting</MenuItem>
            </TextField>
            <Button type="submit" variant="outlined" startIcon={<Search />}>Search</Button>
          </Box>
        )}
        {departments.isError && view === 'directory' && (
          <Alert severity="warning" sx={{ mx: 2, mb: 2 }} action={<Button onClick={() => void departments.refetch()}>Retry</Button>}>
            Department filters could not be loaded.
          </Alert>
        )}
        {currentQuery.isFetching && <LinearProgress aria-label="Loading staff records" />}
        {currentQuery.isError ? (
          <Alert severity="error" sx={{ m: 2 }} action={<Button onClick={() => void currentQuery.refetch()}>Retry</Button>}>
            {errorMessage(currentQuery.error, 'Unable to load staff records.')}
          </Alert>
        ) : view === 'directory' ? (
          <>
            <TableContainer>
              <Table aria-label="Faculty directory" sx={{ minWidth: 590 }}>
                <TableHead><TableRow>
                  <TableCell>Faculty member</TableCell><TableCell>Department</TableCell><TableCell>Access role</TableCell><TableCell>Status</TableCell><TableCell align="right">Actions</TableCell>
                </TableRow></TableHead>
                <TableBody>
                  {directory.data?.items.map((teacher) => (
                    <TableRow key={teacher.id} hover>
                      <TableCell>
                        <Stack direction="row" alignItems="center" spacing={1.25}>
                          <Avatar src={teacher.photo_url || undefined} sx={{ width: 34, height: 34 }}>{teacher.full_name.charAt(0)}</Avatar>
                          <Box>
                            <Typography fontWeight={700}>{teacher.full_name}</Typography>
                            <Typography variant="caption" color="text.secondary">{teacher.employee_id}{teacher.designation ? ` · ${teacher.designation}` : ''}</Typography>
                          </Box>
                        </Stack>
                      </TableCell>
                      <TableCell>{teacher.department_name || 'Unassigned'}</TableCell>
                      <TableCell>{teacher.staff_role ? staffRoleLabels[teacher.staff_role] : '—'}</TableCell>
                      <TableCell><Chip size="small" variant="outlined" label={teacher.status === 'ACTIVE' ? 'Active' : 'Inactive'} color={teacher.status === 'ACTIVE' ? 'success' : 'default'} /></TableCell>
                      <TableCell align="right">
                        <Stack direction="row" justifyContent="flex-end" spacing={0.5}>
                          {canManage && teacher.staff_role && (
                            <Button size="small" onClick={() => {
                              updateAccess.reset()
                              setRole(teacher.staff_role!)
                              setAccessDepartment(teacher.department_id ?? '')
                              setAccessTarget(teacher)
                            }}>Manage access</Button>
                          )}
                          <Button component={Link} to={`/teachers/${teacher.id}`} size="small" endIcon={<OpenInNew fontSize="inherit" />}>Profile</Button>
                          {canManage && <Button size="small" color="error" onClick={() => { deleteTeacher.reset(); setDeleteTarget(teacher) }}>Delete</Button>}
                        </Stack>
                      </TableCell>
                    </TableRow>
                  ))}
                  {directory.data?.items.length === 0 && <TableRow><TableCell colSpan={5} align="center" sx={{ py: 5, color: 'text.secondary' }}>No faculty match these filters.</TableCell></TableRow>}
                </TableBody>
              </Table>
            </TableContainer>
            <TablePagination component="div" count={directory.data?.total ?? -1} page={page} rowsPerPage={PAGE_SIZE}
              rowsPerPageOptions={[PAGE_SIZE]} onPageChange={(_, next) => setPage(next)} />
          </>
        ) : (
          <Stack divider={<Divider />} aria-label="Pending leave requests">
            {leaves.data?.map((leave) => (
              <Stack key={leave.id} direction={{ xs: 'column', sm: 'row' }} justifyContent="space-between" alignItems={{ sm: 'center' }} gap={1.5} p={2}>
                <Box sx={{ minWidth: 0 }}>
                  <Typography fontWeight={700}>{leave.teacher_name}</Typography>
                  <Typography variant="body2" color="text.secondary">
                    {leave.leave_type.replaceAll('_', ' ')} · {leave.start_date} to {leave.end_date} · {leave.days_count} day(s)
                  </Typography>
                  <Typography variant="body2" sx={{ mt: 0.5, overflowWrap: 'anywhere' }}>{leave.reason}</Typography>
                </Box>
                <Button variant="outlined" onClick={() => {
                  reviewLeave.reset()
                  setDecision('APPROVED')
                  setReason('')
                  setReviewTarget(leave)
                }}>Review</Button>
              </Stack>
            ))}
            {leaves.data?.length === 0 && <Typography color="text.secondary" textAlign="center" p={5}>No pending leave requests in your scope.</Typography>}
          </Stack>
        )}
      </Paper>

      {canManage && <AddEditTeacherModal open={addOpen} onClose={() => setAddOpen(false)} onSuccess={() => void refreshDirectory()} />}
      <Dialog open={Boolean(deleteTarget)} onClose={() => { if (!deleteTeacher.isPending) setDeleteTarget(null) }}>
        <DialogTitle>Delete faculty member?</DialogTitle>
        <DialogContent>
          <Typography>Remove {deleteTarget?.full_name} and suspend their institution staff access?</Typography>
          {deleteTeacher.isError && <Alert severity="error">{errorMessage(deleteTeacher.error, 'Unable to remove faculty member.')}</Alert>}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDeleteTarget(null)} disabled={deleteTeacher.isPending}>Cancel</Button>
          <Button color="error" onClick={() => deleteTeacher.mutate()} disabled={deleteTeacher.isPending}>Delete</Button>
        </DialogActions>
      </Dialog>
      <Dialog open={Boolean(accessTarget)} onClose={() => { if (!updateAccess.isPending) setAccessTarget(null) }} fullWidth maxWidth="xs">
        <DialogTitle>Access for {accessTarget?.full_name}</DialogTitle>
        <DialogContent>
          <Stack gap={2} pt={1}>
            {updateAccess.isError && <Alert severity="error">{errorMessage(updateAccess.error, 'Unable to update staff access.')}</Alert>}
            <TextField select label="Staff role" value={role} onChange={(event) => setRole(event.target.value as StaffRole)}>
              {(Object.entries(staffRoleLabels) as [StaffRole, string][]).filter(([value]) => !isSchool || value !== 'HOD').map(([value, label]) => <MenuItem value={value} key={value}>{label}</MenuItem>)}
            </TextField>
            <TextField select label="Department" value={accessDepartment} onChange={(event) => setAccessDepartment(event.target.value)}
              required={role === 'HOD'} helperText={role === 'HOD' ? 'Department of responsibility' : undefined}>
              <MenuItem value="">Keep current department</MenuItem>
              {departments.data?.map((item) => <MenuItem key={item.id} value={item.id}>{item.name}</MenuItem>)}
            </TextField>
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setAccessTarget(null)} disabled={updateAccess.isPending}>Cancel</Button>
          <Button variant="contained" disabled={updateAccess.isPending || (role === 'HOD' && !accessDepartment)} onClick={() => updateAccess.mutate()}>Save access</Button>
        </DialogActions>
      </Dialog>
      <Dialog open={Boolean(reviewTarget)} onClose={() => { if (!reviewLeave.isPending) setReviewTarget(null) }} fullWidth maxWidth="xs">
        <DialogTitle>Review leave for {reviewTarget?.teacher_name}</DialogTitle>
        <DialogContent>
          <Stack gap={2} pt={1}>
            {reviewLeave.isError && <Alert severity="error">{errorMessage(reviewLeave.error, 'Unable to review leave.')}</Alert>}
            <TextField select label="Decision" value={decision} onChange={(event) => setDecision(event.target.value === 'REJECTED' ? 'REJECTED' : 'APPROVED')}>
              <MenuItem value="APPROVED">Approve</MenuItem><MenuItem value="REJECTED">Reject</MenuItem>
            </TextField>
            {decision === 'REJECTED' && <TextField label="Reason for rejection" multiline minRows={2} value={reason} onChange={(event) => setReason(event.target.value)} inputProps={{ maxLength: 255 }} />}
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setReviewTarget(null)} disabled={reviewLeave.isPending}>Cancel</Button>
          <Button variant="contained" disabled={reviewLeave.isPending} onClick={() => reviewLeave.mutate()}>Save decision</Button>
        </DialogActions>
      </Dialog>
    </Stack>
  )
}
