import React, { useEffect, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import {
  Box,
  Typography,
  Button,
  TextField,
  MenuItem,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Avatar,
  Chip,
  Pagination,
  Grid,
  Card,
  CardContent,
  CircularProgress,
  Alert,
  IconButton,
  Tooltip,
} from '@mui/material'
import SearchIcon from '@mui/icons-material/Search'
import RestartAltIcon from '@mui/icons-material/RestartAlt'
import VisibilityOutlinedIcon from '@mui/icons-material/VisibilityOutlined'
import EditOutlinedIcon from '@mui/icons-material/EditOutlined'
import BadgeOutlinedIcon from '@mui/icons-material/BadgeOutlined'
import PersonOffOutlinedIcon from '@mui/icons-material/PersonOffOutlined'
import { openPrintableStudentCard, studentPhotoSrc, StudentItem, studentsApi } from '../../api/students'
import type { StudentListParams } from '../../api/students'
import { Department, Course, SchoolClass, Section, academicsApi } from '../../api/academics'
import { AddEditStudentModal } from './AddEditStudentModal'
import { BulkImportStudentsModal } from './BulkImportStudentsModal'
import { useAuthStore } from '@/store/authStore'

export const StudentsListPage: React.FC = () => {
  const navigate = useNavigate()
  const [searchParams, setSearchParams] = useSearchParams()
  const canManage = useAuthStore((state) => Boolean(state.user?.is_superadmin || state.user?.current_role === 'INSTITUTION_ADMIN'))
  const canAdmit = useAuthStore((state) => Boolean(state.user?.is_superadmin || ['INSTITUTION_ADMIN', 'PRINCIPAL', 'HOD'].includes(state.user?.current_role || '')))
  const user = useAuthStore((state) => state.user)
  const tenantId = user?.current_tenant_id
  const isSchool = user?.institutions.some((institution) =>
    institution.tenant_id === tenantId && institution.institution_type === 'SCHOOL'
  )

  // State
  const [page, setPage] = useState(1)
  const [error, setError] = useState<string | null>(null)

  // Filters
  const [search, setSearch] = useState('')
  const [appliedFilters, setAppliedFilters] = useState<StudentListParams | null>(null)
  const [exporting, setExporting] = useState(false)
  const [classFilter, setClassFilter] = useState('ALL')
  const [sectionFilter, setSectionFilter] = useState('ALL')
  const [classes, setClasses] = useState<SchoolClass[]>([])
  const [sections, setSections] = useState<Section[]>([])
  const [departmentFilter, setDepartmentFilter] = useState('ALL')
  const [courseFilter, setCourseFilter] = useState('ALL')
  const [semesterFilter, setSemesterFilter] = useState('ALL')
  const [statusFilter, setStatusFilter] = useState('ACTIVE')

  // Academic metadata
  const [departments, setDepartments] = useState<Department[]>([])
  const [courses, setCourses] = useState<Course[]>([])

  // Modals
  const [addModalOpen, setAddModalOpen] = useState(false)
  const [editingStudent, setEditingStudent] = useState<StudentItem | null>(null)
  const [importModalOpen, setImportModalOpen] = useState(false)

  useEffect(() => {
    if (!canAdmit || searchParams.get('action') !== 'admit') return
    setEditingStudent(null)
    setAddModalOpen(true)
    const next = new URLSearchParams(searchParams)
    next.delete('action')
    setSearchParams(next, { replace: true })
  }, [canAdmit, searchParams, setSearchParams])

  // Load Departments and Courses
  useEffect(() => {
    let active = true
    const loadAcademicMetadata = async () => {
      try {
        if (isSchool) {
          const [classRes, sectionRes] = await Promise.all([academicsApi.getClasses(), academicsApi.getSections()])
          if (active) {
            setClasses(classRes.data ?? [])
            setSections(sectionRes.data ?? [])
          }
          return
        }
        const [deptRes, courseRes] = await Promise.all([
          academicsApi.getDepartments().catch(() => ({ data: [] })),
          academicsApi.getCourses().catch(() => ({ data: [] })),
        ])
        const deptList = (deptRes as any)?.data ?? deptRes ?? []
        const courseList = (courseRes as any)?.data ?? courseRes ?? []
        if (!active) return
        setDepartments(Array.isArray(deptList) ? deptList : [])
        setCourses(Array.isArray(courseList) ? courseList : [])
      } catch (e) {
        console.error('Failed to load department/course metadata', e)
      }
    }
    void loadAcademicMetadata()
    return () => { active = false }
  }, [isSchool, tenantId])

  const results = useQuery({
    queryKey: ['student-search', user?.id, user?.current_tenant_id, user?.current_role, appliedFilters, page],
    queryFn: () => studentsApi.listStudents({ ...appliedFilters, page, size: 15 }),
    enabled: appliedFilters !== null,
    staleTime: 0,
    refetchOnWindowFocus: false,
    refetchOnReconnect: false,
  })
  const students = results.data?.items ?? []
  const total = results.data?.total ?? 0
  const pages = results.data?.pages ?? 0
  const fetchStudents = async () => {
    if (appliedFilters) await results.refetch()
  }
  const draftFilters: StudentListParams = {
    search: search.trim() || undefined,
    ...(isSchool ? {
      class_id: classFilter === 'ALL' ? undefined : classFilter,
      section_id: sectionFilter === 'ALL' ? undefined : sectionFilter,
    } : {
      department_id: departmentFilter === 'ALL' ? undefined : departmentFilter,
      course_id: courseFilter === 'ALL' ? undefined : courseFilter,
      semester: semesterFilter === 'ALL' ? undefined : Number(semesterFilter),
    }),
    status: statusFilter === 'ALL' ? undefined : statusFilter,
  }
  const filtersChanged = JSON.stringify(appliedFilters) !== JSON.stringify(draftFilters)

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    if (!filtersChanged && page === 1) {
      void fetchStudents()
    } else {
      setAppliedFilters(draftFilters)
      setPage(1)
    }
  }

  const handleResetFilters = () => {
    setSearch('')
    setAppliedFilters(null)
    setClassFilter('ALL')
    setSectionFilter('ALL')
    setDepartmentFilter('ALL')
    setCourseFilter('ALL')
    setSemesterFilter('ALL')
    setStatusFilter('ACTIVE')
    setPage(1)
    setError(null)
  }

  const availableCourses = departmentFilter !== 'ALL'
    ? courses.filter((c) => c.department_id === departmentFilter)
    : courses
  const selectedCourse = availableCourses.find((course) => course.id === courseFilter)
  const semesterCount = Math.min(selectedCourse?.duration_semesters || 16, 16)

  const handleExportCsv = async () => {
    if (!appliedFilters) return
    setExporting(true)
    try {
      const file = await studentsApi.exportCsv(appliedFilters)
      const url = URL.createObjectURL(file)
      const link = document.createElement('a')
      link.href = url
      link.download = 'students.csv'
      link.click()
      window.setTimeout(() => URL.revokeObjectURL(url), 1000)
    } catch {
      setError('Unable to export these student records.')
    } finally {
      setExporting(false)
    }
  }

  const handleDeactivate = async (student: StudentItem) => {
    const confirmed = window.confirm(
      `Are you sure you want to deactivate ${student.full_name}?`
    )
    if (!confirmed) return

    try {
      await studentsApi.deactivateStudent(student.id)
      await fetchStudents()
    } catch (err: any) {
      setError(err?.response?.data?.error?.message || err?.message || 'Failed to deactivate student')
    }
  }

  return (
    <Box>
      {/* Top Header */}
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3, flexWrap: 'wrap', gap: 2 }}>
        <Box>
          <Typography variant="h4" sx={{ fontWeight: 800 }}>
            Student Management
          </Typography>
          <Typography variant="body2" color="text.secondary">
            {canManage ? 'Manage admissions, profiles, academic placements, promotions, and ID cards.' : 'View students in your assigned classes and courses.'}
          </Typography>
        </Box>
        <Box sx={{ display: 'flex', gap: 1.5, flexWrap: 'wrap' }}>
          <Button variant="outlined" onClick={handleExportCsv} disabled={exporting || !appliedFilters}>
            {exporting ? 'Exporting…' : 'Export CSV'}
          </Button>
          {canManage && <>
          <Button variant="outlined" onClick={() => setImportModalOpen(true)}>
            Bulk Import
          </Button>
          <Button variant="outlined" color="secondary" onClick={() => navigate('/students/promote')}>
            Promote Cohort
          </Button>
          </>}
          {canAdmit &&
          <Button
            variant="contained"
            color="primary"
            onClick={() => {
              setEditingStudent(null)
              setAddModalOpen(true)
            }}
          >
            + Admit Student
          </Button>
          }
        </Box>
      </Box>

      {/* KPI Cards */}
      {results.data && <Grid container spacing={2.5} sx={{ mb: 3 }}>
        <Grid item xs={12} sm={6} md={3}>
          <Card sx={{ borderRadius: 2 }}>
            <CardContent>
              <Typography color="text.secondary" variant="body2">
                Matching Students
              </Typography>
              <Typography variant="h4" sx={{ fontWeight: 800, mt: 0.5 }}>
                {total}
              </Typography>
              <Typography variant="caption" color="success.main">
                Across all result pages
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Card sx={{ borderRadius: 2 }}>
            <CardContent>
              <Typography color="text.secondary" variant="body2">
                Active Status
              </Typography>
              <Typography variant="h4" sx={{ fontWeight: 800, mt: 0.5, color: 'success.main' }}>
                {students.filter((s) => s.status === 'ACTIVE').length}
              </Typography>
              <Typography variant="caption" color="text.secondary">
                In current view
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Card sx={{ borderRadius: 2 }}>
            <CardContent>
              <Typography color="text.secondary" variant="body2">
                Alumni / Graduated
              </Typography>
              <Typography variant="h4" sx={{ fontWeight: 800, mt: 0.5 }}>
                {students.filter((s) => s.status === 'GRADUATED').length}
              </Typography>
              <Typography variant="caption" color="text.secondary">
                Graduation completed
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Card sx={{ borderRadius: 2 }}>
            <CardContent>
              <Typography color="text.secondary" variant="body2">
                ID Cards
              </Typography>
              <Typography variant="h4" sx={{ fontWeight: 800, mt: 0.5, color: 'primary.main' }}>
                Ready
              </Typography>
              <Typography variant="caption" color="text.secondary">
                Printable format enabled
              </Typography>
            </CardContent>
          </Card>
        </Grid>
      </Grid>}

      {/* Search & College Admin Academic Filters */}
      <Paper sx={{ p: 2.5, mb: 3, borderRadius: 2 }}>
        <form onSubmit={handleSearchSubmit}>
          <Grid container spacing={2} alignItems="center">
            {isSchool ? (
              <>
                <Grid item xs={12} sm={6} md={3}>
                  <TextField label="Class" select size="small" value={classFilter} fullWidth onChange={(event) => {
                    setClassFilter(event.target.value)
                    setSectionFilter('ALL')
                  }}>
                    <MenuItem value="ALL">All classes</MenuItem>
                    {classes.map((item) => <MenuItem key={item.id} value={item.id}>{item.name}</MenuItem>)}
                  </TextField>
                </Grid>
                <Grid item xs={12} sm={6} md={3}>
                  <TextField label="Section" select size="small" value={sectionFilter} fullWidth
                    disabled={classFilter === 'ALL'} onChange={(event) => setSectionFilter(event.target.value)}>
                    <MenuItem value="ALL">All sections</MenuItem>
                    {sections.filter((item) => item.class_id === classFilter).map((item) => (
                      <MenuItem key={item.id} value={item.id}>{item.name}</MenuItem>
                    ))}
                  </TextField>
                </Grid>
              </>
            ) : (
              <>
                {/* Department Filter */}
                <Grid item xs={12} sm={6} md={2.5}>
                  <TextField
                    label="Department"
                    select
                    size="small"
                    value={departmentFilter}
                    onChange={(e) => {
                      setDepartmentFilter(e.target.value)
                      setCourseFilter('ALL')
                      setSemesterFilter('ALL')
                    }}
                    fullWidth
                  >
                    <MenuItem value="ALL">All Departments</MenuItem>
                    {departments.map((d) => (
                      <MenuItem key={d.id} value={d.id}>
                        {d.name} {d.code ? `(${d.code})` : ''}
                      </MenuItem>
                    ))}
                  </TextField>
                </Grid>

                {/* Course Filter */}
                <Grid item xs={12} sm={6} md={2.5}>
                  <TextField
                    label="Course / Program"
                    select
                    size="small"
                    value={courseFilter}
                    onChange={(e) => {
                      setCourseFilter(e.target.value)
                      setSemesterFilter('ALL')
                    }}
                    fullWidth
                  >
                    <MenuItem value="ALL">All Courses</MenuItem>
                    {availableCourses.map((c) => (
                      <MenuItem key={c.id} value={c.id}>
                        {c.name} {c.code ? `(${c.code})` : ''}
                      </MenuItem>
                    ))}
                  </TextField>
                </Grid>

                {/* Semester Filter */}
                <Grid item xs={6} sm={3} md={1.5}>
                  <TextField
                    label="Semester"
                    select
                    size="small"
                    value={semesterFilter}
                    onChange={(e) => setSemesterFilter(e.target.value)}
                    fullWidth
                  >
                    <MenuItem value="ALL">All semesters</MenuItem>
                    {Array.from({ length: semesterCount }, (_, index) => index + 1).map((sem) => (
                      <MenuItem key={sem} value={String(sem)}>
                        Semester {sem}
                      </MenuItem>
                    ))}
                  </TextField>
                </Grid>
              </>
            )}

            {/* Status Filter */}
            <Grid item xs={6} sm={3} md={2}>
              <TextField
                label="Status"
                select
                size="small"
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
                fullWidth
              >
                <MenuItem value="ALL">All Statuses</MenuItem>
                <MenuItem value="ACTIVE">Active</MenuItem>
                <MenuItem value="INACTIVE">Inactive</MenuItem>
                <MenuItem value="GRADUATED">Graduated</MenuItem>
                <MenuItem value="TRANSFERRED">Transferred</MenuItem>
                <MenuItem value="SUSPENDED">Suspended</MenuItem>
              </TextField>
            </Grid>
            <Grid item xs={12} sm={6} md={3.5}>
              <TextField
                label="Student name, admission or roll number"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                size="small"
                fullWidth
              />
            </Grid>
          </Grid>

          {/* Active Filter Badges & Reset Actions */}
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mt: 2, flexWrap: 'wrap', gap: 1 }}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, flexWrap: 'wrap' }}>
              <Typography variant="caption" color="text.secondary" fontWeight={600}>
                Selected filters
              </Typography>
              {!isSchool && departmentFilter !== 'ALL' && (
                <Chip
                  size="small"
                  label={`Dept: ${departments.find((d) => d.id === departmentFilter)?.code || 'Selected'}`}
                  onDelete={() => {
                    setDepartmentFilter('ALL')
                    setCourseFilter('ALL')
                    setSemesterFilter('ALL')
                  }}
                  color="primary"
                  variant="outlined"
                />
              )}
              {!isSchool && courseFilter !== 'ALL' && (
                <Chip
                  size="small"
                  label={`Course: ${availableCourses.find((c) => c.id === courseFilter)?.code || 'Selected'}`}
                  onDelete={() => {
                    setCourseFilter('ALL')
                    setSemesterFilter('ALL')
                  }}
                  color="primary"
                  variant="outlined"
                />
              )}
              {!isSchool && semesterFilter !== 'ALL' && (
                <Chip
                  size="small"
                  label={`Sem: ${semesterFilter}`}
                  onDelete={() => setSemesterFilter('ALL')}
                  color="primary"
                  variant="outlined"
                />
              )}
              {search.trim() && (
                <Chip
                  size="small"
                  label={`Search: "${search.trim()}"`}
                  onDelete={() => setSearch('')}
                  color="secondary"
                  variant="outlined"
                />
              )}
              {statusFilter !== 'ALL' && (
                <Chip
                  size="small"
                  label={`Status: ${statusFilter}`}
                  onDelete={() => setStatusFilter('ALL')}
                  variant="outlined"
                />
              )}
            </Box>

            <Box sx={{ display: 'flex', gap: 1 }}>
              {(appliedFilters || departmentFilter !== 'ALL' || courseFilter !== 'ALL' || semesterFilter !== 'ALL' || search.trim() || statusFilter !== 'ACTIVE') && (
                <Button
                  size="small"
                  variant="text"
                  color="inherit"
                  startIcon={<RestartAltIcon />}
                  onClick={handleResetFilters}
                >
                  Reset
                </Button>
              )}
              <Button type="submit" variant="contained" size="small" startIcon={<SearchIcon />}>
                Search
              </Button>
            </Box>
          </Box>
          {appliedFilters && filtersChanged && (
            <Typography variant="body2" color="text.secondary" role="status" sx={{ mt: 1.5 }}>
              Click Search to apply your filter changes.
            </Typography>
          )}
        </form>
      </Paper>

      {error && (
        <Alert severity="error" sx={{ mb: 2.5 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      {/* Students Data Table */}
      <Paper sx={{ borderRadius: 2, overflow: 'hidden' }}>
        {!appliedFilters ? (
          <Typography color="text.secondary" textAlign="center" sx={{ p: 4 }}>
            Select your filters and click Search to see students.
          </Typography>
        ) : results.isError ? (
          <Alert severity="error" sx={{ m: 2 }} action={<Button onClick={() => void fetchStudents()}>Retry</Button>}>
            {results.error.message || 'Failed to fetch student records.'}
          </Alert>
        ) : results.isFetching ? (
          <Box sx={{ p: 4, display: 'flex', justifyContent: 'center' }}>
            <CircularProgress />
          </Box>
        ) : (
          <TableContainer sx={{ overflowX: 'auto', width: '100%' }}>
            <Table sx={{ minWidth: 800 }}>
              <TableHead>
                <TableRow>
                  <TableCell>Admission No</TableCell>
                  <TableCell>Student</TableCell>
                  {!isSchool && <TableCell>Department</TableCell>}
                  <TableCell>{isSchool ? 'Class' : 'Course'}</TableCell>
                  <TableCell>{isSchool ? 'Section' : 'Semester'}</TableCell>
                  <TableCell>Roll No</TableCell>
                  <TableCell>Contact</TableCell>
                  <TableCell>Status</TableCell>
                  <TableCell align="right">Actions</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {students.map((student) => (
                  <TableRow key={student.id} hover>
                    <TableCell sx={{ fontWeight: 700, color: 'primary.main' }}>
                      {student.admission_number}
                    </TableCell>
                    <TableCell>
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
                        <Avatar
                          src={studentPhotoSrc(student.photo_url)}
                          sx={{ width: 36, height: 36, bgcolor: 'primary.light', fontSize: 14 }}
                        >
                          {student.full_name.charAt(0)}
                        </Avatar>
                        <Box>
                          <Typography
                            variant="body2"
                            sx={{
                              fontWeight: 700,
                              cursor: 'pointer',
                              '&:hover': { textDecoration: 'underline' },
                            }}
                            onClick={() => navigate(`/students/${student.id}`)}
                          >
                            {student.full_name}
                          </Typography>
                          <Typography variant="caption" color="text.secondary">
                            {student.email || '—'}
                          </Typography>
                        </Box>
                      </Box>
                    </TableCell>
                    {!isSchool && <TableCell>
                      <Typography variant="body2" fontWeight={600} color="text.primary">
                        {student.department_name || '—'}
                      </Typography>
                    </TableCell>}
                    <TableCell>
                      <Typography variant="body2" fontWeight={600}>
                        {(isSchool ? student.class_name : student.course_name) || '—'}
                      </Typography>
                    </TableCell>
                    <TableCell>
                      <Box sx={{ display: 'flex', gap: 0.5, flexWrap: 'wrap' }}>
                        {!isSchool && student.semester ? (
                          <Chip
                            label={`Sem ${student.semester}`}
                            size="small"
                            color="primary"
                            variant="outlined"
                            sx={{ fontWeight: 600 }}
                          />
                        ) : null}
                        {isSchool && student.section_name ? (
                          <Chip
                            label={`Sec ${student.section_name}`}
                            size="small"
                            variant="outlined"
                            sx={{ fontWeight: 600 }}
                          />
                        ) : null}
                        {(isSchool ? !student.section_name : !student.semester) && '—'}
                      </Box>
                    </TableCell>
                    <TableCell>{student.roll_number || '—'}</TableCell>
                    <TableCell>
                      <Typography variant="body2">{student.phone || student.parent_phone || '—'}</Typography>
                    </TableCell>
                    <TableCell>
                      <Chip
                        label={student.status}
                        size="small"
                        color={
                          student.status === 'ACTIVE'
                            ? 'success'
                            : student.status === 'GRADUATED'
                            ? 'info'
                            : 'default'
                        }
                        sx={{ fontWeight: 600 }}
                      />
                    </TableCell>
                    <TableCell align="right">
                      <Box sx={{ display: 'flex', justifyContent: 'flex-end', gap: 1 }}>
                        <Tooltip title="View profile">
                          <IconButton size="small" aria-label={`View profile for ${student.full_name}`}
                            onClick={() => navigate(`/students/${student.id}`)}
                            sx={{ width: 32, height: 32, borderRadius: '8px', border: '1px solid #e2e8f0', color: '#334155' }}>
                            <VisibilityOutlinedIcon sx={{ fontSize: 16 }} />
                          </IconButton>
                        </Tooltip>
                        {canManage && <Tooltip title="Edit">
                          <IconButton size="small" aria-label={`Edit ${student.full_name}`} onClick={() => {
                            setEditingStudent(student)
                            setAddModalOpen(true)
                          }} sx={{ width: 32, height: 32, borderRadius: '8px', border: '1px solid #e2e8f0', color: '#334155' }}>
                            <EditOutlinedIcon sx={{ fontSize: 16 }} />
                          </IconButton>
                        </Tooltip>}
                        <Tooltip title="ID card">
                          <IconButton size="small" aria-label={`Open ID card for ${student.full_name}`}
                            onClick={() => void openPrintableStudentCard(student.id).catch((error: Error) => setError(error.message))}
                            sx={{ width: 32, height: 32, borderRadius: '8px', border: '1px solid #e2e8f0', color: '#334155' }}>
                            <BadgeOutlinedIcon sx={{ fontSize: 16 }} />
                          </IconButton>
                        </Tooltip>
                        {canManage && student.status === 'ACTIVE' && (
                          <Tooltip title="Deactivate">
                            <IconButton size="small" aria-label={`Deactivate ${student.full_name}`}
                              onClick={() => handleDeactivate(student)}
                              sx={{ width: 32, height: 32, borderRadius: '8px', border: '1px solid #fee2e2', color: '#ef4444', bgcolor: '#fff5f5' }}>
                              <PersonOffOutlinedIcon sx={{ fontSize: 16 }} />
                            </IconButton>
                          </Tooltip>
                        )}
                      </Box>
                    </TableCell>
                  </TableRow>
                ))}

                {students.length === 0 && (
                  <TableRow>
                    <TableCell colSpan={isSchool ? 8 : 9} sx={{ textAlign: 'center', py: 5 }}>
                      <Typography variant="body1" color="text.secondary">
                        No students found matching your criteria.
                      </Typography>
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </TableContainer>
        )}

        {/* Pagination */}
        {pages > 1 && <Box sx={{ p: 2, display: 'flex', justifyContent: 'flex-end' }}>
          <Pagination
            count={pages}
            page={page}
            onChange={(_, val) => setPage(val)}
            color="primary"
          />
        </Box>}
      </Paper>

      {/* Add / Edit Modal */}
      <AddEditStudentModal
        open={addModalOpen}
        onClose={() => {
          setAddModalOpen(false)
          setEditingStudent(null)
        }}
        onSuccess={fetchStudents}
        student={editingStudent}
      />

      {/* Bulk Import Modal */}
      <BulkImportStudentsModal
        open={importModalOpen}
        onClose={() => setImportModalOpen(false)}
        onSuccess={fetchStudents}
      />
    </Box>
  )
}
