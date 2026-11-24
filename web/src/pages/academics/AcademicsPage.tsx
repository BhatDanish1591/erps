import { useState, useEffect, useMemo } from 'react'
import { useLocation } from 'react-router-dom'
import {
  Box,
  Card,
  Typography,
  Button,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Chip,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  MenuItem,
  Grid,
  CircularProgress,
  Alert,
  IconButton,
  InputAdornment,
  Select,
  FormControl,
  Snackbar,
} from '@mui/material'
import {
  Add as AddIcon,
  Search as SearchIcon,
  EditOutlined as EditIcon,
  DeleteOutline as DeleteIcon,
  AccountBalance as BuildingIcon,
  MenuBook as CoursesIcon,
  Layers as SemestersIcon,
  CalendarMonth as SessionsIcon,
  Class as ClassIcon,
  MeetingRoom as SectionIcon,
  Code as CodeIcon,
  Settings as SettingsIcon,
  Bolt as BoltIcon,
  Engineering as EngineeringIcon,
  Science as ScienceIcon,
  BarChart as AnalyticsIcon,
  Biotech as BiotechIcon,
  AutoStories as HumanitiesIcon,
  NavigateBefore as PrevIcon,
  NavigateNext as NextIcon,
} from '@mui/icons-material'
import {
  academicsApi,
  AcademicSession,
  Department,
  Course,
  CollegeSemester,
  SchoolClass,
  Section,
} from '../../api/academics'
import { useAuthStore } from '@/store/authStore'

export default function AcademicsPage() {
  const location = useLocation()
  const user = useAuthStore((state) => state.user)
  const institutionType = user?.institutions.find((institution) => institution.tenant_id === user.current_tenant_id)?.institution_type
  const isSchool = institutionType === 'SCHOOL'
  const [selectedTab, setActiveTab] = useState('')
  const schoolTabs = ['classes', 'sections', 'sessions']
  const collegeTabs = ['departments', 'courses', 'semesters', 'sessions']
  const tabs = isSchool ? schoolTabs : collegeTabs
  const activeTab = tabs.includes(selectedTab) ? selectedTab : tabs[0]

  useEffect(() => {
    const tab = new URLSearchParams(location.search).get('tab')
    setActiveTab(tab === 'school-structure' ? 'classes' : tab ?? '')
  }, [location.key, location.search])

  const [loading, setLoading] = useState(false)
  const [searchQuery, setSearchQuery] = useState('')
  const [statusFilter, setStatusFilter] = useState('ALL')
  const [sortBy, setSortBy] = useState('NAME_ASC')
  const [currentPage, setCurrentPage] = useState(1)
  const pageSize = 8

  // Live Data states from API
  const [apiDepts, setApiDepts] = useState<Department[]>([])
  const [apiCourses, setApiCourses] = useState<Course[]>([])
  const [apiSemesters, setApiSemesters] = useState<CollegeSemester[]>([])
  const [apiClasses, setApiClasses] = useState<SchoolClass[]>([])
  const [apiSections, setApiSections] = useState<Section[]>([])
  const [apiSessions, setApiSessions] = useState<AcademicSession[]>([])

  // Modal states
  const [editingId, setEditingId] = useState<string | null>(null)
  const [deleteTarget, setDeleteTarget] = useState<{ id: string; name: string; type: string } | null>(null)
  const [saving, setSaving] = useState(false)
  const [deptModalOpen, setDeptModalOpen] = useState(false)
  const [courseModalOpen, setCourseModalOpen] = useState(false)
  const [semesterModalOpen, setSemesterModalOpen] = useState(false)
  const [classModalOpen, setClassModalOpen] = useState(false)
  const [sectionModalOpen, setSectionModalOpen] = useState(false)
  const [sessionModalOpen, setSessionModalOpen] = useState(false)

  // Form states
  const [deptForm, setDeptForm] = useState({ name: '', code: '', hod_name: '' })
  const [courseForm, setCourseForm] = useState({ name: '', code: '', department_id: '', duration_years: 4, duration_semesters: 8 })
  const [semesterForm, setSemesterForm] = useState({ course_id: '', semester_number: 1, name: '', credits_required: 24 })
  const [classForm, setClassForm] = useState({ name: '', code: '', order_index: 1, category: 'GENERAL', class_teacher_name: '' })
  const [sectionForm, setSectionForm] = useState({ name: '', class_id: '', capacity: 40, room_number: '', class_teacher_name: '' })
  const [sessionForm, setSessionForm] = useState({ name: '', code: '', start_date: '', end_date: '', is_current: false })

  const [notification, setNotification] = useState<string | null>(null)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)

  const loadData = async () => {
    try {
      setLoading(true)
      const [dRes, cRes, semRes, clsRes, secRes, sRes] = await Promise.allSettled([
        isSchool ? undefined : academicsApi.getDepartments(),
        isSchool ? undefined : academicsApi.getCourses(),
        isSchool ? undefined : academicsApi.getSemesters(),
        isSchool ? academicsApi.getClasses() : undefined,
        isSchool ? academicsApi.getSections() : undefined,
        academicsApi.getSessions(),
      ])

      if (dRes.status === 'fulfilled' && dRes.value?.data) setApiDepts(dRes.value.data)
      if (cRes.status === 'fulfilled' && cRes.value?.data) setApiCourses(cRes.value.data)
      if (semRes.status === 'fulfilled' && semRes.value?.data) setApiSemesters(semRes.value.data)
      if (clsRes.status === 'fulfilled' && clsRes.value?.data) setApiClasses(clsRes.value.data)
      if (secRes.status === 'fulfilled' && secRes.value?.data) setApiSections(secRes.value.data)
      if (sRes.status === 'fulfilled' && sRes.value?.data) setApiSessions(sRes.value.data)
      if ([dRes, cRes, semRes, clsRes, secRes, sRes].some((result) => result.status === 'rejected')) {
        setErrorMessage('Some academic records could not be loaded. Please try again.')
      }
    } catch {
      setErrorMessage('Academic records could not be loaded. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadData()
  }, [user?.current_tenant_id, isSchool])

  // Combined College Departments
  const departmentsData = useMemo(() => {
    const formattedApi = apiDepts.map((d) => ({
      id: d.id,
      name: d.name,
      code: d.code,
      hod_name: d.hod_name || 'Unassigned',
      courses_count: d.courses_count ?? 0,
      students_count: 0,
      status: 'Active',
      iconType: getIconType(d.name, d.code),
      iconColor: '#6366f1',
      iconBg: '#eef2ff',
    }))
    return formattedApi
  }, [apiDepts])

  // Combined College Courses
  const coursesData = useMemo(() => {
    const formattedApi = apiCourses.map((c) => ({
      id: c.id,
      name: c.name,
      code: c.code,
      department_name: c.department_name || 'Unassigned',
      duration_years: c.duration_years || 4,
      duration_semesters: c.duration_semesters || 8,
      students_count: 0,
      status: 'Active',
    }))
    return formattedApi
  }, [apiCourses])

  // Combined College Semesters
  const semestersData = useMemo(() => {
    if (apiSemesters.length > 0) {
      return apiSemesters.map((s) => ({
        id: s.id,
        name: s.name,
        semester_number: s.semester_number,
        course_name: s.course_name || 'Unassigned',
        credits_required: s.credits_required || 24,
        status: s.status || 'Active',
      }))
    }
    return []
  }, [apiSemesters])

  // Combined School Classes
  const classesData = useMemo(() => {
    const formattedApi = apiClasses.map((c, idx) => ({
      id: c.id,
      name: c.name,
      code: c.code,
      category: c.category || 'GENERAL',
      order_index: c.order_index || idx + 1,
      class_teacher_name: c.class_teacher_name || 'Unassigned',
      sections_count: c.sections_count ?? 0,
      students_count: 0,
      status: 'Active',
    }))
    return formattedApi
  }, [apiClasses])

  // Combined School Sections
  const sectionsData = useMemo(() => {
    const formattedApi = apiSections.map((s) => ({
      id: s.id,
      name: s.name,
      class_name: s.class_name || 'Unassigned',
      room_number: s.room_number || '?',
      class_teacher_name: s.class_teacher_name || 'Unassigned',
      capacity: s.capacity || 40,
      enrolled_count: 0,
      status: 'Active',
    }))
    return formattedApi
  }, [apiSections])

  // Sessions (used by both School and College)
  const sessionsData = useMemo(() => {
    if (apiSessions.length > 0) {
      return apiSessions
    }
    return []
  }, [apiSessions])

  // Helper to determine icon per department
  function getIconType(name: string, code: string) {
    const text = (name + ' ' + code).toLowerCase()
    if (text.includes('comput') || text.includes('cse') || text.includes('it')) return 'code'
    if (text.includes('mech')) return 'mech'
    if (text.includes('electr') || text.includes('ee')) return 'ee'
    if (text.includes('civil')) return 'civil'
    if (text.includes('electron') || text.includes('ece') || text.includes('chem')) return 'ece'
    if (text.includes('manage') || text.includes('mba') || text.includes('busin')) return 'mba'
    if (text.includes('appli') || text.includes('sci') || text.includes('bio')) return 'as'
    return 'hss'
  }

  const renderDeptIcon = (iconType: string) => {
    switch (iconType) {
      case 'code':
        return <CodeIcon sx={{ fontSize: 18, color: '#6366f1' }} />
      case 'mech':
        return <SettingsIcon sx={{ fontSize: 18, color: '#2563eb' }} />
      case 'ee':
        return <BoltIcon sx={{ fontSize: 18, color: '#d97706' }} />
      case 'civil':
        return <EngineeringIcon sx={{ fontSize: 18, color: '#ea580c' }} />
      case 'ece':
        return <ScienceIcon sx={{ fontSize: 18, color: '#db2777' }} />
      case 'mba':
        return <AnalyticsIcon sx={{ fontSize: 18, color: '#0891b2' }} />
      case 'as':
        return <BiotechIcon sx={{ fontSize: 18, color: '#7c3aed' }} />
      case 'hss':
      default:
        return <HumanitiesIcon sx={{ fontSize: 18, color: '#4f46e5' }} />
    }
  }

  // Filtered & Sorted list for active view
  const currentList = useMemo(() => {
    let list: any[] = []
    if (activeTab === 'departments') list = [...departmentsData]
    else if (activeTab === 'courses') list = [...coursesData]
    else if (activeTab === 'semesters') list = [...semestersData]
    else if (activeTab === 'classes') list = [...classesData]
    else if (activeTab === 'sections') list = [...sectionsData]
    else if (activeTab === 'sessions') list = [...sessionsData]

    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase()
      list = list.filter((item) =>
        (item.name && item.name.toLowerCase().includes(q)) ||
        (item.code && item.code.toLowerCase().includes(q)) ||
        (item.hod_name && item.hod_name.toLowerCase().includes(q)) ||
        (item.class_teacher_name && item.class_teacher_name.toLowerCase().includes(q))
      )
    }

    if (statusFilter !== 'ALL') {
      list = list.filter((item) => (item.status || 'Active').toUpperCase() === statusFilter)
    }

    if (sortBy === 'NAME_ASC') {
      list.sort((a, b) => (a.name || '').localeCompare(b.name || ''))
    } else if (sortBy === 'NAME_DESC') {
      list.sort((a, b) => (b.name || '').localeCompare(a.name || ''))
    }

    return list
  }, [activeTab, departmentsData, coursesData, semestersData, classesData, sectionsData, sessionsData, searchQuery, statusFilter, sortBy])

  const totalItems = currentList.length
  const paginatedList = useMemo(() => {
    const startIndex = (currentPage - 1) * pageSize
    return currentList.slice(startIndex, startIndex + pageSize)
  }, [currentList, currentPage])

  const totalPages = Math.ceil(totalItems / pageSize) || 1

  // Save Handlers
  const handleSaveDepartment = async () => {
    if (!deptForm.name.trim() || !deptForm.code.trim()) {
      setErrorMessage('Please provide both Department Name and Code')
      return
    }
    try {
      await (editingId ? (data: any) => academicsApi.updateDepartment(editingId, data) : academicsApi.createDepartment)({
        name: deptForm.name.trim(),
        code: deptForm.code.trim().toUpperCase(),
      })
      setNotification(`Department "${deptForm.name}" ${editingId ? 'updated' : 'created'} successfully!`)
      setDeptModalOpen(false)
      setDeptForm({ name: '', code: '', hod_name: '' })
      loadData()
    } catch (e: any) {
      setErrorMessage(e?.response?.data?.detail || e.message || 'Failed to create department')
    }
  }

  const handleSaveCourse = async () => {
    if (!courseForm.name.trim() || !courseForm.code.trim()) {
      setErrorMessage('Please provide Course Name and Code')
      return
    }
    try {
      await (editingId ? (data: any) => academicsApi.updateCourse(editingId, data) : academicsApi.createCourse)({
        name: courseForm.name.trim(),
        code: courseForm.code.trim().toUpperCase(),
        department_id: courseForm.department_id || undefined,
        duration_years: Number(courseForm.duration_years) || 4,
        duration_semesters: Number(courseForm.duration_semesters) || 8,
      })
      setNotification(`Course "${courseForm.name}" ${editingId ? 'updated' : 'created'} successfully!`)
      setCourseModalOpen(false)
      setCourseForm({ name: '', code: '', department_id: '', duration_years: 4, duration_semesters: 8 })
      loadData()
    } catch (e: any) {
      setErrorMessage(e?.response?.data?.detail || e.message || 'Failed to create course')
    }
  }

  const handleSaveSemester = async () => {
    if (!semesterForm.course_id || !semesterForm.name.trim()) {
      setErrorMessage('Please select a course and enter semester name')
      return
    }
    try {
      await (editingId ? (data: any) => academicsApi.updateSemester(editingId, { name: data.name, credits_required: data.credits_required }) : academicsApi.createSemester)({
        course_id: semesterForm.course_id,
        semester_number: Number(semesterForm.semester_number),
        name: semesterForm.name.trim(),
        credits_required: Number(semesterForm.credits_required) || 24,
      })
      setNotification(`Semester ${editingId ? 'updated' : 'created'} successfully!`)
      setSemesterModalOpen(false)
      setSemesterForm({ course_id: '', semester_number: 1, name: '', credits_required: 24 })
      loadData()
    } catch (e: any) {
      setErrorMessage(e?.response?.data?.detail || e.message || 'Failed to create semester')
    }
  }

  const handleSaveClass = async () => {
    if (!classForm.name.trim() || !classForm.code.trim()) {
      setErrorMessage('Please provide Class Name and Code')
      return
    }
    try {
      await (editingId ? (data: any) => academicsApi.updateClass(editingId, data) : academicsApi.createClass)({
        name: classForm.name.trim(),
        code: classForm.code.trim().toUpperCase(),
        order_index: Number(classForm.order_index) || 1,
        category: classForm.category || 'GENERAL',
      })
      setNotification(`Class "${classForm.name}" ${editingId ? 'updated' : 'created'} successfully!`)
      setClassModalOpen(false)
      setClassForm({ name: '', code: '', order_index: 1, category: 'GENERAL', class_teacher_name: '' })
      loadData()
    } catch (e: any) {
      setErrorMessage(e?.response?.data?.detail || e.message || 'Failed to create class')
    }
  }

  const handleSaveSection = async () => {
    if (!sectionForm.name.trim() || !sectionForm.class_id) {
      setErrorMessage('Please provide Section Name and select a Class')
      return
    }
    try {
      await (editingId ? (data: any) => academicsApi.updateSection(editingId, data) : academicsApi.createSection)({
        name: sectionForm.name.trim(),
        class_id: sectionForm.class_id,
        capacity: Number(sectionForm.capacity) || 40,
        room_number: sectionForm.room_number || undefined,
      })
      setNotification(`Section "${sectionForm.name}" ${editingId ? 'updated' : 'created'} successfully!`)
      setSectionModalOpen(false)
      setSectionForm({ name: '', class_id: '', capacity: 40, room_number: '', class_teacher_name: '' })
      loadData()
    } catch (e: any) {
      setErrorMessage(e?.response?.data?.detail || e.message || 'Failed to create section')
    }
  }

  const handleSaveSession = async () => {
    if (!sessionForm.name.trim() || !sessionForm.code.trim() || !sessionForm.start_date || !sessionForm.end_date) {
      setErrorMessage('Please fill in all session details')
      return
    }
    try {
      await (editingId ? (data: any) => academicsApi.updateSession(editingId, data) : academicsApi.createSession)(sessionForm)
      setNotification(`Academic session ${editingId ? 'updated' : 'created'} successfully!`)
      setSessionModalOpen(false)
      setSessionForm({ name: '', code: '', start_date: '', end_date: '', is_current: false })
      loadData()
    } catch (e: any) {
      setErrorMessage(e?.response?.data?.detail || e.message || 'Failed to create session')
    }
  }

  const getAddButtonTitle = () => {
    switch (activeTab) {
      case 'departments':
        return '+ Add Department'
      case 'courses':
        return '+ Add Course'
      case 'semesters':
        return '+ Add Semester'
      case 'classes':
        return '+ Add Class'
      case 'sections':
        return '+ Add Section'
      case 'sessions':
        return '+ Add Session'
      default:
        return '+ Add'
    }
  }

  const openEdit = (id: string) => {
    setErrorMessage(null)
    setEditingId(id)
    if (activeTab === 'departments') {
      const item = apiDepts.find((record) => record.id === id)
      if (item) { setDeptForm({ name: item.name, code: item.code, hod_name: '' }); setDeptModalOpen(true) }
    } else if (activeTab === 'courses') {
      const item = apiCourses.find((record) => record.id === id)
      if (item) { setCourseForm({ name: item.name, code: item.code, department_id: item.department_id || '', duration_years: item.duration_years, duration_semesters: item.duration_semesters }); setCourseModalOpen(true) }
    } else if (activeTab === 'semesters') {
      const item = apiSemesters.find((record) => record.id === id)
      if (item) { setSemesterForm({ course_id: item.course_id, semester_number: item.semester_number, name: item.name, credits_required: item.credits_required }); setSemesterModalOpen(true) }
    } else if (activeTab === 'classes') {
      const item = apiClasses.find((record) => record.id === id)
      if (item) { setClassForm({ name: item.name, code: item.code, order_index: item.order_index, category: item.category, class_teacher_name: '' }); setClassModalOpen(true) }
    } else if (activeTab === 'sections') {
      const item = apiSections.find((record) => record.id === id)
      if (item) { setSectionForm({ name: item.name, class_id: item.class_id || '', capacity: item.capacity, room_number: item.room_number || '', class_teacher_name: '' }); setSectionModalOpen(true) }
    } else {
      const item = apiSessions.find((record) => record.id === id)
      if (item) { setSessionForm({ name: item.name, code: item.code, start_date: item.start_date, end_date: item.end_date, is_current: item.is_current }); setSessionModalOpen(true) }
    }
  }

  const deleteRecord = async () => {
    if (!deleteTarget || saving) return
    const actions: Record<string, (id: string) => Promise<unknown>> = {
      departments: academicsApi.deleteDepartment, courses: academicsApi.deleteCourse,
      semesters: academicsApi.deleteSemester, classes: academicsApi.deleteClass,
      sections: academicsApi.deleteSection, sessions: academicsApi.deleteSession,
    }
    try {
      setSaving(true)
      await actions[deleteTarget.type](deleteTarget.id)
      setNotification(deleteTarget.name + ' deleted successfully.')
      setDeleteTarget(null)
      setCurrentPage(1)
      await loadData()
    } catch (error: any) {
      setErrorMessage(error?.message || 'Failed to delete academic record')
      setDeleteTarget(null)
    } finally { setSaving(false) }
  }

  const handleOpenAddModal = () => {
    setEditingId(null)
    setErrorMessage(null)
    setDeptForm({ name: '', code: '', hod_name: '' })
    setCourseForm({ name: '', code: '', department_id: '', duration_years: 4, duration_semesters: 8 })
    setSemesterForm({ course_id: '', semester_number: 1, name: '', credits_required: 24 })
    setClassForm({ name: '', code: '', order_index: 1, category: 'GENERAL', class_teacher_name: '' })
    setSectionForm({ name: '', class_id: '', capacity: 40, room_number: '', class_teacher_name: '' })
    setSessionForm({ name: '', code: '', start_date: '', end_date: '', is_current: false })
    switch (activeTab) {
      case 'departments':
        setDeptModalOpen(true)
        break
      case 'courses':
        setCourseModalOpen(true)
        break
      case 'semesters':
        setSemesterModalOpen(true)
        break
      case 'classes':
        setClassModalOpen(true)
        break
      case 'sections':
        setSectionModalOpen(true)
        break
      case 'sessions':
        setSessionModalOpen(true)
        break
    }
  }

  const activeTabMeta: Record<string, { title: string; subtitle: string }> = {
    departments: {
      title: 'Departments',
      subtitle: 'Manage all academic departments of your institution.',
    },
    courses: {
      title: 'Courses',
      subtitle: 'Configure degree programs, courses, and credit requirements.',
    },
    semesters: {
      title: 'Semesters',
      subtitle: 'Define semesters, syllabus terms, and credits per cohort.',
    },
    classes: {
      title: 'Classes',
      subtitle: 'Manage school grades, class levels, and assigned class teachers.',
    },
    sections: {
      title: 'Sections',
      subtitle: 'Configure classroom divisions, room numbers, and seating capacities.',
    },
    sessions: {
      title: 'Sessions',
      subtitle: 'Manage academic calendar sessions, school years, and terms.',
    },
  }

  const currentMeta = activeTabMeta[activeTab] || { title: 'Academics', subtitle: 'Academic structure' }

  return (
    <Box sx={{ p: { xs: 2, md: 3 }, bgcolor: '#f8fafc', minHeight: '100vh' }}>
      {/* 2. Top Header Bar with Center Pill Switcher and Action Button */}
      <Box
        sx={{
          display: 'flex',
          flexDirection: { xs: 'column', md: 'row' },
          alignItems: { xs: 'flex-start', md: 'center' },
          justifyContent: 'space-between',
          gap: 2,
          mb: 3,
        }}
      >
        {/* Left: Icon + Title & Subtitle */}
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
          <Box
            sx={{
              width: 48,
              height: 48,
              borderRadius: '12px',
              bgcolor: '#ede9fe',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: '#6366f1',
              boxShadow: '0 1px 2px rgba(99, 102, 241, 0.1)',
            }}
          >
            {institutionType === 'SCHOOL' ? <ClassIcon sx={{ fontSize: 26 }} /> : <BuildingIcon sx={{ fontSize: 26 }} />}
          </Box>
          <Box>
            <Typography variant="h5" sx={{ fontWeight: 700, color: '#0f172a', fontSize: '24px', lineHeight: 1.2 }}>
              {currentMeta.title}
            </Typography>
            <Typography variant="body2" sx={{ color: '#64748b', fontSize: '13.5px', mt: 0.3 }}>
              {currentMeta.subtitle}
            </Typography>
          </Box>
        </Box>

        {/* Center: Rounded Pill Switcher */}
        <Box
          sx={{
            display: 'inline-flex',
            alignItems: 'center',
            bgcolor: '#ffffff',
            p: 0.6,
            borderRadius: '50px',
            border: '1px solid #e2e8f0',
            boxShadow: '0 1px 3px rgba(0,0,0,0.03)',
            gap: 0.5,
            alignSelf: { xs: 'stretch', md: 'center' },
            justifyContent: 'center',
          }}
        >
          {institutionType === 'SCHOOL' ? (
            /* School Pills: Classes, Sections, Sessions */
            <>
              <Button
                onClick={() => { setActiveTab('classes'); setCurrentPage(1) }}
                startIcon={<ClassIcon sx={{ fontSize: 17 }} />}
                sx={{
                  borderRadius: '30px',
                  px: 2.2,
                  py: 0.8,
                  fontSize: '13.5px',
                  fontWeight: 600,
                  textTransform: 'none',
                  transition: 'all 0.2s',
                  bgcolor: activeTab === 'classes' ? '#4f46e5' : 'transparent',
                  color: activeTab === 'classes' ? '#ffffff' : '#64748b',
                  '&:hover': {
                    bgcolor: activeTab === 'classes' ? '#4338ca' : '#f1f5f9',
                  },
                }}
              >
                Classes
              </Button>

              <Button
                onClick={() => { setActiveTab('sections'); setCurrentPage(1) }}
                startIcon={<SectionIcon sx={{ fontSize: 17 }} />}
                sx={{
                  borderRadius: '30px',
                  px: 2.2,
                  py: 0.8,
                  fontSize: '13.5px',
                  fontWeight: 600,
                  textTransform: 'none',
                  transition: 'all 0.2s',
                  bgcolor: activeTab === 'sections' ? '#4f46e5' : 'transparent',
                  color: activeTab === 'sections' ? '#ffffff' : '#64748b',
                  '&:hover': {
                    bgcolor: activeTab === 'sections' ? '#4338ca' : '#f1f5f9',
                  },
                }}
              >
                Sections
              </Button>

              <Button
                onClick={() => { setActiveTab('sessions'); setCurrentPage(1) }}
                startIcon={<SessionsIcon sx={{ fontSize: 17 }} />}
                sx={{
                  borderRadius: '30px',
                  px: 2.2,
                  py: 0.8,
                  fontSize: '13.5px',
                  fontWeight: 600,
                  textTransform: 'none',
                  transition: 'all 0.2s',
                  bgcolor: activeTab === 'sessions' ? '#4f46e5' : 'transparent',
                  color: activeTab === 'sessions' ? '#ffffff' : '#64748b',
                  '&:hover': {
                    bgcolor: activeTab === 'sessions' ? '#4338ca' : '#f1f5f9',
                  },
                }}
              >
                Sessions
              </Button>
            </>
          ) : (
            /* College Pills: Departments, Courses, Semesters, Sessions */
            <>
              <Button
                onClick={() => { setActiveTab('departments'); setCurrentPage(1) }}
                startIcon={<BuildingIcon sx={{ fontSize: 17 }} />}
                sx={{
                  borderRadius: '30px',
                  px: 2.2,
                  py: 0.8,
                  fontSize: '13.5px',
                  fontWeight: 600,
                  textTransform: 'none',
                  transition: 'all 0.2s',
                  bgcolor: activeTab === 'departments' ? '#4f46e5' : 'transparent',
                  color: activeTab === 'departments' ? '#ffffff' : '#64748b',
                  '&:hover': {
                    bgcolor: activeTab === 'departments' ? '#4338ca' : '#f1f5f9',
                  },
                }}
              >
                Departments
              </Button>

              <Button
                onClick={() => { setActiveTab('courses'); setCurrentPage(1) }}
                startIcon={<CoursesIcon sx={{ fontSize: 17 }} />}
                sx={{
                  borderRadius: '30px',
                  px: 2.2,
                  py: 0.8,
                  fontSize: '13.5px',
                  fontWeight: 600,
                  textTransform: 'none',
                  transition: 'all 0.2s',
                  bgcolor: activeTab === 'courses' ? '#4f46e5' : 'transparent',
                  color: activeTab === 'courses' ? '#ffffff' : '#64748b',
                  '&:hover': {
                    bgcolor: activeTab === 'courses' ? '#4338ca' : '#f1f5f9',
                  },
                }}
              >
                Courses
              </Button>

              <Button
                onClick={() => { setActiveTab('semesters'); setCurrentPage(1) }}
                startIcon={<SemestersIcon sx={{ fontSize: 17 }} />}
                sx={{
                  borderRadius: '30px',
                  px: 2.2,
                  py: 0.8,
                  fontSize: '13.5px',
                  fontWeight: 600,
                  textTransform: 'none',
                  transition: 'all 0.2s',
                  bgcolor: activeTab === 'semesters' ? '#4f46e5' : 'transparent',
                  color: activeTab === 'semesters' ? '#ffffff' : '#64748b',
                  '&:hover': {
                    bgcolor: activeTab === 'semesters' ? '#4338ca' : '#f1f5f9',
                  },
                }}
              >
                Semesters
              </Button>

              <Button
                onClick={() => { setActiveTab('sessions'); setCurrentPage(1) }}
                startIcon={<SessionsIcon sx={{ fontSize: 17 }} />}
                sx={{
                  borderRadius: '30px',
                  px: 2.2,
                  py: 0.8,
                  fontSize: '13.5px',
                  fontWeight: 600,
                  textTransform: 'none',
                  transition: 'all 0.2s',
                  bgcolor: activeTab === 'sessions' ? '#4f46e5' : 'transparent',
                  color: activeTab === 'sessions' ? '#ffffff' : '#64748b',
                  '&:hover': {
                    bgcolor: activeTab === 'sessions' ? '#4338ca' : '#f1f5f9',
                  },
                }}
              >
                Sessions
              </Button>
            </>
          )}
        </Box>

        {/* Right: + Add Button */}
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <Button
            variant="contained"
            onClick={handleOpenAddModal}
            startIcon={<AddIcon />}
            sx={{
              bgcolor: '#4f46e5',
              color: '#ffffff',
              borderRadius: '10px',
              px: 2.5,
              py: 1,
              fontWeight: 600,
              fontSize: '14px',
              textTransform: 'none',
              boxShadow: '0 2px 4px rgba(79, 70, 229, 0.25)',
              '&:hover': {
                bgcolor: '#4338ca',
              },
            }}
          >
            {getAddButtonTitle()}
          </Button>
        </Box>
      </Box>

      {/* 4. White Card Table Box */}
      <Card
        elevation={0}
        sx={{
          borderRadius: '16px',
          border: '1px solid #e2e8f0',
          bgcolor: '#ffffff',
          boxShadow: '0 1px 3px rgba(0,0,0,0.03)',
          overflow: 'hidden',
        }}
      >
        {/* Table Top Toolbar */}
        <Box
          sx={{
            p: 2.5,
            display: 'flex',
            flexDirection: { xs: 'column', md: 'row' },
            alignItems: { xs: 'stretch', md: 'center' },
            justifyContent: 'space-between',
            gap: 2,
            borderBottom: '1px solid #f1f5f9',
          }}
        >
          {/* Left: Search Input */}
          <TextField
            size="small"
            placeholder={`Search ${activeTab}...`}
            value={searchQuery}
            onChange={(e) => { setSearchQuery(e.target.value); setCurrentPage(1) }}
            InputProps={{
              startAdornment: (
                <InputAdornment position="start">
                  <SearchIcon sx={{ color: '#94a3b8', fontSize: 20 }} />
                </InputAdornment>
              ),
            }}
            sx={{
              width: { xs: '100%', md: 280 },
              '& .MuiOutlinedInput-root': {
                borderRadius: '10px',
                bgcolor: '#ffffff',
                fontSize: '13.5px',
                '& fieldset': {
                  borderColor: '#e2e8f0',
                },
                '&:hover fieldset': {
                  borderColor: '#cbd5e1',
                },
                '&.Mui-focused fieldset': {
                  borderColor: '#6366f1',
                },
              },
            }}
          />

          {/* Right: Filters */}
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, flexWrap: 'wrap' }}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              <Typography sx={{ fontSize: '13.5px', color: '#64748b', fontWeight: 500 }}>
                Status
              </Typography>
              <FormControl size="small">
                <Select
                  value={statusFilter}
                  onChange={(e) => { setStatusFilter(e.target.value); setCurrentPage(1) }}
                  sx={{
                    borderRadius: '8px',
                    fontSize: '13.5px',
                    height: '38px',
                    minWidth: 120,
                    bgcolor: '#ffffff',
                    '& fieldset': { borderColor: '#e2e8f0' },
                  }}
                >
                  <MenuItem value="ALL">All Status</MenuItem>
                  <MenuItem value="ACTIVE">Active</MenuItem>
                  <MenuItem value="INACTIVE">Inactive</MenuItem>
                </Select>
              </FormControl>
            </Box>

            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              <Typography sx={{ fontSize: '13.5px', color: '#64748b', fontWeight: 500 }}>
                Sort By
              </Typography>
              <FormControl size="small">
                <Select
                  value={sortBy}
                  onChange={(e) => setSortBy(e.target.value)}
                  sx={{
                    borderRadius: '8px',
                    fontSize: '13.5px',
                    height: '38px',
                    minWidth: 140,
                    bgcolor: '#ffffff',
                    '& fieldset': { borderColor: '#e2e8f0' },
                  }}
                >
                  <MenuItem value="NAME_ASC">Name (A-Z)</MenuItem>
                  <MenuItem value="NAME_DESC">Name (Z-A)</MenuItem>
                </Select>
              </FormControl>
            </Box>
          </Box>
        </Box>

        {/* Table Content */}
        <TableContainer>
          <Table sx={{ minWidth: 800 }}>
            <TableHead>
              <TableRow sx={{ bgcolor: '#fafafa', '& th': { borderBottom: '1px solid #f1f5f9', py: 1.8 } }}>
                <TableCell sx={{ fontWeight: 600, color: '#475569', fontSize: '13px', width: 60 }}>#</TableCell>

                {/* College Headers */}
                {activeTab === 'departments' && (
                  <>
                    <TableCell sx={{ fontWeight: 600, color: '#475569', fontSize: '13px' }}>Department Name</TableCell>
                    <TableCell sx={{ fontWeight: 600, color: '#475569', fontSize: '13px' }}>Department Code</TableCell>
                    <TableCell sx={{ fontWeight: 600, color: '#475569', fontSize: '13px' }}>HOD / In-Charge</TableCell>
                    <TableCell sx={{ fontWeight: 600, color: '#475569', fontSize: '13px' }}>Courses</TableCell>
                    <TableCell sx={{ fontWeight: 600, color: '#475569', fontSize: '13px' }}>Students</TableCell>
                  </>
                )}
                {activeTab === 'courses' && (
                  <>
                    <TableCell sx={{ fontWeight: 600, color: '#475569', fontSize: '13px' }}>Course Name</TableCell>
                    <TableCell sx={{ fontWeight: 600, color: '#475569', fontSize: '13px' }}>Course Code</TableCell>
                    <TableCell sx={{ fontWeight: 600, color: '#475569', fontSize: '13px' }}>Department</TableCell>
                    <TableCell sx={{ fontWeight: 600, color: '#475569', fontSize: '13px' }}>Duration</TableCell>
                    <TableCell sx={{ fontWeight: 600, color: '#475569', fontSize: '13px' }}>Students</TableCell>
                  </>
                )}
                {activeTab === 'semesters' && (
                  <>
                    <TableCell sx={{ fontWeight: 600, color: '#475569', fontSize: '13px' }}>Semester Name</TableCell>
                    <TableCell sx={{ fontWeight: 600, color: '#475569', fontSize: '13px' }}>Semester Number</TableCell>
                    <TableCell sx={{ fontWeight: 600, color: '#475569', fontSize: '13px' }}>Course Program</TableCell>
                    <TableCell sx={{ fontWeight: 600, color: '#475569', fontSize: '13px' }}>Credits Required</TableCell>
                  </>
                )}

                {/* School Headers: Classes & Sections */}
                {activeTab === 'classes' && (
                  <>
                    <TableCell sx={{ fontWeight: 600, color: '#475569', fontSize: '13px' }}>Class / Grade Name</TableCell>
                    <TableCell sx={{ fontWeight: 600, color: '#475569', fontSize: '13px' }}>Class Code</TableCell>
                    <TableCell sx={{ fontWeight: 600, color: '#475569', fontSize: '13px' }}>Category</TableCell>
                    <TableCell sx={{ fontWeight: 600, color: '#475569', fontSize: '13px' }}>Class Teacher</TableCell>
                    <TableCell sx={{ fontWeight: 600, color: '#475569', fontSize: '13px' }}>Sections</TableCell>
                    <TableCell sx={{ fontWeight: 600, color: '#475569', fontSize: '13px' }}>Students</TableCell>
                  </>
                )}
                {activeTab === 'sections' && (
                  <>
                    <TableCell sx={{ fontWeight: 600, color: '#475569', fontSize: '13px' }}>Section Name</TableCell>
                    <TableCell sx={{ fontWeight: 600, color: '#475569', fontSize: '13px' }}>Class</TableCell>
                    <TableCell sx={{ fontWeight: 600, color: '#475569', fontSize: '13px' }}>Room Number</TableCell>
                    <TableCell sx={{ fontWeight: 600, color: '#475569', fontSize: '13px' }}>Section Teacher</TableCell>
                    <TableCell sx={{ fontWeight: 600, color: '#475569', fontSize: '13px' }}>Capacity / Enrolled</TableCell>
                  </>
                )}

                {/* Sessions Header (Common) */}
                {activeTab === 'sessions' && (
                  <>
                    <TableCell sx={{ fontWeight: 600, color: '#475569', fontSize: '13px' }}>Session Name</TableCell>
                    <TableCell sx={{ fontWeight: 600, color: '#475569', fontSize: '13px' }}>Code</TableCell>
                    <TableCell sx={{ fontWeight: 600, color: '#475569', fontSize: '13px' }}>Start Date</TableCell>
                    <TableCell sx={{ fontWeight: 600, color: '#475569', fontSize: '13px' }}>End Date</TableCell>
                    <TableCell sx={{ fontWeight: 600, color: '#475569', fontSize: '13px' }}>Current Session</TableCell>
                  </>
                )}

                <TableCell sx={{ fontWeight: 600, color: '#475569', fontSize: '13px' }}>Status</TableCell>
                <TableCell sx={{ fontWeight: 600, color: '#475569', fontSize: '13px', textAlign: 'center' }}>Actions</TableCell>
              </TableRow>
            </TableHead>

            <TableBody>
              {loading ? (
                <TableRow>
                  <TableCell colSpan={8} align="center" sx={{ py: 6 }}>
                    <CircularProgress size={32} sx={{ color: '#6366f1' }} />
                  </TableCell>
                </TableRow>
              ) : paginatedList.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={8} align="center" sx={{ py: 6, color: '#94a3b8' }}>
                    No records found matching your filters.
                  </TableCell>
                </TableRow>
              ) : (
                paginatedList.map((row, idx) => {
                  const rowNumber = (currentPage - 1) * pageSize + idx + 1
                  return (
                    <TableRow
                      key={row.id || idx}
                      hover
                      sx={{
                        '&:hover': { bgcolor: '#f8fafc' },
                        '& td': { borderBottom: '1px solid #f8fafc', py: 1.8, fontSize: '13.5px' },
                      }}
                    >
                      <TableCell sx={{ color: '#64748b', fontWeight: 600 }}>{rowNumber}</TableCell>

                      {/* College: Departments */}
                      {activeTab === 'departments' && (
                        <>
                          <TableCell>
                            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
                              <Box
                                sx={{
                                  width: 32,
                                  height: 32,
                                  borderRadius: '8px',
                                  bgcolor: row.iconBg || '#ede9fe',
                                  display: 'flex',
                                  alignItems: 'center',
                                  justifyContent: 'center',
                                }}
                              >
                                {renderDeptIcon(row.iconType)}
                              </Box>
                              <Typography sx={{ fontWeight: 700, color: '#0f172a', fontSize: '14px' }}>
                                {row.name}
                              </Typography>
                            </Box>
                          </TableCell>
                          <TableCell>
                            <Chip
                              label={row.code}
                              size="small"
                              sx={{
                                bgcolor: '#ede9fe',
                                color: '#6366f1',
                                fontWeight: 700,
                                fontSize: '12px',
                                borderRadius: '6px',
                                height: '24px',
                              }}
                            />
                          </TableCell>
                          <TableCell sx={{ color: '#334155', fontWeight: 500 }}>{row.hod_name || 'Dr. HOD'}</TableCell>
                          <TableCell sx={{ color: '#334155', fontWeight: 600 }}>{row.courses_count || 4}</TableCell>
                          <TableCell sx={{ color: '#334155', fontWeight: 600 }}>{'?'}</TableCell>
                        </>
                      )}

                      {/* College: Courses */}
                      {activeTab === 'courses' && (
                        <>
                          <TableCell sx={{ fontWeight: 700, color: '#0f172a' }}>{row.name}</TableCell>
                          <TableCell>
                            <Chip
                              label={row.code}
                              size="small"
                              sx={{
                                bgcolor: '#ede9fe',
                                color: '#6366f1',
                                fontWeight: 700,
                                fontSize: '12px',
                                borderRadius: '6px',
                                height: '24px',
                              }}
                            />
                          </TableCell>
                          <TableCell sx={{ color: '#334155' }}>{row.department_name}</TableCell>
                          <TableCell sx={{ color: '#334155' }}>{row.duration_years} Years ({row.duration_semesters} Semesters)</TableCell>
                          <TableCell sx={{ color: '#334155', fontWeight: 600 }}>{'?'}</TableCell>
                        </>
                      )}

                      {/* College: Semesters */}
                      {activeTab === 'semesters' && (
                        <>
                          <TableCell sx={{ fontWeight: 700, color: '#0f172a' }}>{row.name}</TableCell>
                          <TableCell>
                            <Chip
                              label={`Sem ${row.semester_number}`}
                              size="small"
                              sx={{
                                bgcolor: '#dbeafe',
                                color: '#1d4ed8',
                                fontWeight: 700,
                                fontSize: '12px',
                                borderRadius: '6px',
                                height: '24px',
                              }}
                            />
                          </TableCell>
                          <TableCell sx={{ color: '#334155' }}>{row.course_name}</TableCell>
                          <TableCell sx={{ color: '#334155', fontWeight: 600 }}>{row.credits_required} Credits</TableCell>
                        </>
                      )}

                      {/* School: Classes */}
                      {activeTab === 'classes' && (
                        <>
                          <TableCell>
                            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
                              <Box
                                sx={{
                                  width: 32,
                                  height: 32,
                                  borderRadius: '8px',
                                  bgcolor: '#ede9fe',
                                  display: 'flex',
                                  alignItems: 'center',
                                  justifyContent: 'center',
                                  color: '#6366f1',
                                }}
                              >
                                <ClassIcon sx={{ fontSize: 18 }} />
                              </Box>
                              <Typography sx={{ fontWeight: 700, color: '#0f172a', fontSize: '14px' }}>
                                {row.name}
                              </Typography>
                            </Box>
                          </TableCell>
                          <TableCell>
                            <Chip
                              label={row.code}
                              size="small"
                              sx={{
                                bgcolor: '#ede9fe',
                                color: '#6366f1',
                                fontWeight: 700,
                                fontSize: '12px',
                                borderRadius: '6px',
                                height: '24px',
                              }}
                            />
                          </TableCell>
                          <TableCell>
                            <Chip
                              label={row.category || 'General'}
                              size="small"
                              sx={{
                                bgcolor: '#f1f5f9',
                                color: '#475569',
                                fontWeight: 600,
                                fontSize: '11.5px',
                                borderRadius: '6px',
                              }}
                            />
                          </TableCell>
                          <TableCell sx={{ color: '#334155', fontWeight: 500 }}>{row.class_teacher_name || 'Class Teacher'}</TableCell>
                          <TableCell sx={{ color: '#334155', fontWeight: 600 }}>{row.sections_count ?? 0} Sections</TableCell>
                          <TableCell sx={{ color: '#334155', fontWeight: 600 }}>{'?'}</TableCell>
                        </>
                      )}

                      {/* School: Sections */}
                      {activeTab === 'sections' && (
                        <>
                          <TableCell>
                            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
                              <Box
                                sx={{
                                  width: 32,
                                  height: 32,
                                  borderRadius: '8px',
                                  bgcolor: '#dcfce7',
                                  display: 'flex',
                                  alignItems: 'center',
                                  justifyContent: 'center',
                                  color: '#16a34a',
                                }}
                              >
                                <SectionIcon sx={{ fontSize: 18 }} />
                              </Box>
                              <Typography sx={{ fontWeight: 700, color: '#0f172a', fontSize: '14px' }}>
                                {row.name}
                              </Typography>
                            </Box>
                          </TableCell>
                          <TableCell>
                            <Chip
                              label={row.class_name || 'Class'}
                              size="small"
                              sx={{
                                bgcolor: '#dbeafe',
                                color: '#1d4ed8',
                                fontWeight: 700,
                                fontSize: '12px',
                                borderRadius: '6px',
                                height: '24px',
                              }}
                            />
                          </TableCell>
                          <TableCell sx={{ color: '#334155' }}>{row.room_number || 'Room -'}</TableCell>
                          <TableCell sx={{ color: '#334155', fontWeight: 500 }}>{row.class_teacher_name || 'Teacher'}</TableCell>
                          <TableCell sx={{ color: '#334155', fontWeight: 600 }}>
                            {'?'} / {row.capacity || 40}
                          </TableCell>
                        </>
                      )}

                      {/* Sessions (Common) */}
                      {activeTab === 'sessions' && (
                        <>
                          <TableCell sx={{ fontWeight: 700, color: '#0f172a' }}>{row.name}</TableCell>
                          <TableCell>
                            <Chip
                              label={row.code}
                              size="small"
                              sx={{
                                bgcolor: '#ede9fe',
                                color: '#6366f1',
                                fontWeight: 700,
                                fontSize: '12px',
                                borderRadius: '6px',
                                height: '24px',
                              }}
                            />
                          </TableCell>
                          <TableCell sx={{ color: '#334155' }}>{row.start_date}</TableCell>
                          <TableCell sx={{ color: '#334155' }}>{row.end_date}</TableCell>
                          <TableCell>
                            {row.is_current ? (
                              <Chip label="Current Session" size="small" sx={{ bgcolor: '#dcfce7', color: '#15803d', fontWeight: 600 }} />
                            ) : (
                              <Typography sx={{ color: '#94a3b8', fontSize: '13px' }}>-</Typography>
                            )}
                          </TableCell>
                        </>
                      )}

                      {/* Status */}
                      <TableCell>
                        <Box
                          sx={{
                            display: 'inline-flex',
                            alignItems: 'center',
                            gap: 0.8,
                            bgcolor: '#dcfce7',
                            color: '#15803d',
                            px: 1.4,
                            py: 0.4,
                            borderRadius: '20px',
                            fontSize: '12px',
                            fontWeight: 600,
                          }}
                        >
                          <Box sx={{ width: 6, height: 6, borderRadius: '50%', bgcolor: '#15803d' }} />
                          {row.status || 'Active'}
                        </Box>
                      </TableCell>

                      {/* Actions */}
                      <TableCell align="center">
                        <Box sx={{ display: 'inline-flex', alignItems: 'center', gap: 1 }}>
                          <IconButton
                            size="small"
                            aria-label={'Edit ' + row.name}
                            onClick={() => openEdit(row.id)}
                            sx={{
                              width: 32,
                              height: 32,
                              borderRadius: '8px',
                              border: '1px solid #e2e8f0',
                              color: '#334155',
                              '&:hover': { bgcolor: '#f1f5f9', color: '#0f172a' },
                            }}
                          >
                            <EditIcon sx={{ fontSize: 16 }} />
                          </IconButton>
                          <IconButton
                            size="small"
                            aria-label={'Delete ' + row.name}
                            onClick={() => setDeleteTarget({ id: row.id, name: row.name, type: activeTab })}
                            sx={{
                              width: 32,
                              height: 32,
                              borderRadius: '8px',
                              border: '1px solid #fee2e2',
                              color: '#ef4444',
                              bgcolor: '#fff5f5',
                              '&:hover': { bgcolor: '#fee2e2' },
                            }}
                          >
                            <DeleteIcon sx={{ fontSize: 16 }} />
                          </IconButton>
                        </Box>
                      </TableCell>
                    </TableRow>
                  )
                })
              )}
            </TableBody>
          </Table>
        </TableContainer>

        {/* Table Footer with Pagination */}
        <Box
          sx={{
            p: 2.5,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            borderTop: '1px solid #f1f5f9',
            flexWrap: 'wrap',
            gap: 2,
          }}
        >
          <Typography sx={{ fontSize: '13.5px', color: '#64748b' }}>
            Showing {totalItems === 0 ? 0 : (currentPage - 1) * pageSize + 1} to{' '}
            {Math.min(currentPage * pageSize, totalItems)} of {totalItems} {activeTab}
          </Typography>

          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <IconButton
              size="small"
              disabled={currentPage <= 1}
              onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
              sx={{
                width: 32,
                height: 32,
                borderRadius: '8px',
                border: '1px solid #e2e8f0',
                '&.Mui-disabled': { opacity: 0.4 },
              }}
            >
              <PrevIcon sx={{ fontSize: 18 }} />
            </IconButton>

            {Array.from({ length: totalPages }).map((_, i) => {
              const p = i + 1
              const isActive = p === currentPage
              return (
                <Button
                  key={p}
                  size="small"
                  onClick={() => setCurrentPage(p)}
                  sx={{
                    minWidth: 32,
                    height: 32,
                    p: 0,
                    borderRadius: '8px',
                    fontWeight: 700,
                    fontSize: '13px',
                    bgcolor: isActive ? '#4f46e5' : 'transparent',
                    color: isActive ? '#ffffff' : '#64748b',
                    border: isActive ? 'none' : '1px solid #e2e8f0',
                    '&:hover': {
                      bgcolor: isActive ? '#4338ca' : '#f1f5f9',
                    },
                  }}
                >
                  {p}
                </Button>
              )
            })}

            <IconButton
              size="small"
              disabled={currentPage >= totalPages}
              onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
              sx={{
                width: 32,
                height: 32,
                borderRadius: '8px',
                border: '1px solid #e2e8f0',
                '&.Mui-disabled': { opacity: 0.4 },
              }}
            >
              <NextIcon sx={{ fontSize: 18 }} />
            </IconButton>
          </Box>
        </Box>
      </Card>

      <Dialog open={Boolean(deleteTarget)} onClose={() => { if (!saving) setDeleteTarget(null) }}>
        <DialogTitle>Delete academic record?</DialogTitle>
        <DialogContent><Typography>Delete {deleteTarget?.name}?</Typography></DialogContent>
        <DialogActions><Button disabled={saving} onClick={() => setDeleteTarget(null)}>Cancel</Button><Button color="error" disabled={saving} onClick={deleteRecord}>Delete</Button></DialogActions>
      </Dialog>

      {/* Modal: Add Department (College) */}
      <Dialog open={deptModalOpen} onClose={() => setDeptModalOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle sx={{ fontWeight: 700, color: '#0f172a' }}>{editingId ? 'Edit Department' : 'Add Department'}</DialogTitle>
        <DialogContent dividers>
          {errorMessage && <Alert severity="error" sx={{ mb: 2 }} onClose={() => setErrorMessage(null)}>{errorMessage}</Alert>}
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2.5, pt: 1 }}>
            <TextField
              label="Department Name"
              placeholder="e.g. Computer Science & Engineering"
              value={deptForm.name}
              onChange={(e) => setDeptForm({ ...deptForm, name: e.target.value })}
              fullWidth
              required
            />
            <TextField
              label="Department Code"
              placeholder="e.g. CSE"
              value={deptForm.code}
              onChange={(e) => setDeptForm({ ...deptForm, code: e.target.value })}
              fullWidth
              required
            />
          </Box>
        </DialogContent>
        <DialogActions sx={{ p: 2 }}>
          <Button onClick={() => setDeptModalOpen(false)} sx={{ textTransform: 'none', color: '#64748b' }}>
            Cancel
          </Button>
          <Button
            variant="contained"
            onClick={handleSaveDepartment}
            sx={{ bgcolor: '#4f46e5', textTransform: 'none', px: 3, '&:hover': { bgcolor: '#4338ca' } }}
          >
            {editingId ? 'Save changes' : 'Create Department'}
          </Button>
        </DialogActions>
      </Dialog>

      {/* Modal: Add Course (College) */}
      <Dialog open={courseModalOpen} onClose={() => setCourseModalOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle sx={{ fontWeight: 700, color: '#0f172a' }}>{editingId ? 'Edit Course' : 'Add Course'}</DialogTitle>
        <DialogContent dividers>
          {errorMessage && <Alert severity="error" sx={{ mb: 2 }} onClose={() => setErrorMessage(null)}>{errorMessage}</Alert>}
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2.5, pt: 1 }}>
            <TextField
              label="Course / Degree Name"
              placeholder="e.g. B.Tech in Computer Science & Engineering"
              value={courseForm.name}
              onChange={(e) => setCourseForm({ ...courseForm, name: e.target.value })}
              fullWidth
              required
            />
            <TextField
              label="Course Code"
              placeholder="e.g. BT-CSE"
              value={courseForm.code}
              onChange={(e) => setCourseForm({ ...courseForm, code: e.target.value })}
              fullWidth
              required
            />
            <FormControl fullWidth>
              <TextField
                select
                label="Department"
                value={courseForm.department_id}
                onChange={(e) => setCourseForm({ ...courseForm, department_id: e.target.value })}
              >
                <MenuItem value="">-- Select Department --</MenuItem>
                {departmentsData.map((d) => (
                  <MenuItem key={d.id} value={d.id}>
                    {d.name} ({d.code})
                  </MenuItem>
                ))}
              </TextField>
            </FormControl>
            <Grid container spacing={2}>
              <Grid item xs={6}>
                <TextField
                  label="Duration (Years)"
                  type="number"
                  value={courseForm.duration_years}
                  onChange={(e) => setCourseForm({ ...courseForm, duration_years: Number(e.target.value) })}
                  fullWidth
                />
              </Grid>
              <Grid item xs={6}>
                <TextField
                  label="Total Semesters"
                  type="number"
                  value={courseForm.duration_semesters}
                  onChange={(e) => setCourseForm({ ...courseForm, duration_semesters: Number(e.target.value) })}
                  fullWidth
                />
              </Grid>
            </Grid>
          </Box>
        </DialogContent>
        <DialogActions sx={{ p: 2 }}>
          <Button onClick={() => setCourseModalOpen(false)} sx={{ textTransform: 'none', color: '#64748b' }}>
            Cancel
          </Button>
          <Button
            variant="contained"
            onClick={handleSaveCourse}
            sx={{ bgcolor: '#4f46e5', textTransform: 'none', px: 3, '&:hover': { bgcolor: '#4338ca' } }}
          >
            {editingId ? 'Save changes' : 'Create Course'}
          </Button>
        </DialogActions>
      </Dialog>

      {/* Modal: Add Semester (College) */}
      <Dialog open={semesterModalOpen} onClose={() => setSemesterModalOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle sx={{ fontWeight: 700, color: '#0f172a' }}>{editingId ? 'Edit Semester' : 'Add Semester'}</DialogTitle>
        <DialogContent dividers>
          {errorMessage && <Alert severity="error" sx={{ mb: 2 }} onClose={() => setErrorMessage(null)}>{errorMessage}</Alert>}
          {!editingId && <Alert severity="info" sx={{ mb: 2 }}>Semesters are created automatically when you add a course. Edit an existing semester to change its details.</Alert>}
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2.5, pt: 1 }}>
            <FormControl fullWidth>
              <TextField
                select
                label="Course Program"
                disabled={Boolean(editingId)}
                value={semesterForm.course_id}
                onChange={(e) => setSemesterForm({ ...semesterForm, course_id: e.target.value })}
                required
              >
                <MenuItem value="">-- Select Course Program --</MenuItem>
                {coursesData.map((c) => (
                  <MenuItem key={c.id} value={c.id}>
                    {c.name} ({c.code})
                  </MenuItem>
                ))}
              </TextField>
            </FormControl>
            <TextField
              label="Semester Number"
              disabled={Boolean(editingId)}
              type="number"
              value={semesterForm.semester_number}
              onChange={(e) =>
                setSemesterForm({
                  ...semesterForm,
                  semester_number: Number(e.target.value),
                  name: `Semester ${e.target.value}`,
                })
              }
              fullWidth
              required
            />
            <TextField
              label="Semester Name"
              placeholder="e.g. Semester 1"
              value={semesterForm.name}
              onChange={(e) => setSemesterForm({ ...semesterForm, name: e.target.value })}
              fullWidth
              required
            />
            <TextField
              label="Credits Required"
              type="number"
              value={semesterForm.credits_required}
              onChange={(e) => setSemesterForm({ ...semesterForm, credits_required: Number(e.target.value) })}
              fullWidth
            />
          </Box>
        </DialogContent>
        <DialogActions sx={{ p: 2 }}>
          <Button onClick={() => setSemesterModalOpen(false)} sx={{ textTransform: 'none', color: '#64748b' }}>
            Cancel
          </Button>
          <Button
            variant="contained"
            onClick={handleSaveSemester}
            sx={{ bgcolor: '#4f46e5', textTransform: 'none', px: 3, '&:hover': { bgcolor: '#4338ca' } }}
          >
            {editingId ? 'Save changes' : 'Create Semester'}
          </Button>
        </DialogActions>
      </Dialog>

      {/* Modal: Add Class (School) */}
      <Dialog open={classModalOpen} onClose={() => setClassModalOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle sx={{ fontWeight: 700, color: '#0f172a' }}>{editingId ? 'Edit Class' : 'Add Class'}</DialogTitle>
        <DialogContent dividers>
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2.5, pt: 1 }}>
            <TextField
              label="Class / Grade Name"
              placeholder="e.g. Class 10"
              value={classForm.name}
              onChange={(e) => setClassForm({ ...classForm, name: e.target.value })}
              fullWidth
              required
            />
            <TextField
              label="Class Code"
              placeholder="e.g. CLS-10"
              value={classForm.code}
              onChange={(e) => setClassForm({ ...classForm, code: e.target.value })}
              fullWidth
              required
            />
            <FormControl fullWidth>
              <TextField
                select
                label="Category"
                value={classForm.category}
                onChange={(e) => setClassForm({ ...classForm, category: e.target.value })}
              >
                <MenuItem value="PRE_PRIMARY">Pre-Primary (Nursery, KG)</MenuItem>
                <MenuItem value="PRIMARY">Primary (Class 1-5)</MenuItem>
                <MenuItem value="MIDDLE">Middle School (Class 6-8)</MenuItem>
                <MenuItem value="SECONDARY">Secondary (Class 9-10)</MenuItem>
                <MenuItem value="HIGHER_SECONDARY">Higher Secondary (Class 11-12)</MenuItem>
                <MenuItem value="GENERAL">General</MenuItem>
              </TextField>
            </FormControl>
            <TextField
              label="Display Order Index"
              type="number"
              value={classForm.order_index}
              onChange={(e) => setClassForm({ ...classForm, order_index: Number(e.target.value) })}
              fullWidth
            />
          </Box>
        </DialogContent>
        <DialogActions sx={{ p: 2 }}>
          <Button onClick={() => setClassModalOpen(false)} sx={{ textTransform: 'none', color: '#64748b' }}>
            Cancel
          </Button>
          <Button
            variant="contained"
            onClick={handleSaveClass}
            sx={{ bgcolor: '#4f46e5', textTransform: 'none', px: 3, '&:hover': { bgcolor: '#4338ca' } }}
          >
            {editingId ? 'Save changes' : 'Create Class'}
          </Button>
        </DialogActions>
      </Dialog>

      {/* Modal: Add Section (School) */}
      <Dialog open={sectionModalOpen} onClose={() => setSectionModalOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle sx={{ fontWeight: 700, color: '#0f172a' }}>{editingId ? 'Edit Section' : 'Add Section'}</DialogTitle>
        <DialogContent dividers>
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2.5, pt: 1 }}>
            <FormControl fullWidth>
              <TextField
                select
                label="Assign to Class"
                value={sectionForm.class_id}
                onChange={(e) => setSectionForm({ ...sectionForm, class_id: e.target.value })}
                required
              >
                <MenuItem value="">-- Select Class --</MenuItem>
                {classesData.map((c) => (
                  <MenuItem key={c.id} value={c.id}>
                    {c.name} ({c.code})
                  </MenuItem>
                ))}
              </TextField>
            </FormControl>
            <TextField
              label="Section Name"
              placeholder="e.g. Section A"
              value={sectionForm.name}
              onChange={(e) => setSectionForm({ ...sectionForm, name: e.target.value })}
              fullWidth
              required
            />
            <TextField
              label="Room Number"
              placeholder="e.g. Room 101"
              value={sectionForm.room_number}
              onChange={(e) => setSectionForm({ ...sectionForm, room_number: e.target.value })}
              fullWidth
            />
            <TextField
              label="Max Student Capacity"
              type="number"
              value={sectionForm.capacity}
              onChange={(e) => setSectionForm({ ...sectionForm, capacity: Number(e.target.value) })}
              fullWidth
            />
          </Box>
        </DialogContent>
        <DialogActions sx={{ p: 2 }}>
          <Button onClick={() => setSectionModalOpen(false)} sx={{ textTransform: 'none', color: '#64748b' }}>
            Cancel
          </Button>
          <Button
            variant="contained"
            onClick={handleSaveSection}
            sx={{ bgcolor: '#4f46e5', textTransform: 'none', px: 3, '&:hover': { bgcolor: '#4338ca' } }}
          >
            {editingId ? 'Save changes' : 'Create Section'}
          </Button>
        </DialogActions>
      </Dialog>

      {/* Modal: Add Session (Common) */}
      <Dialog open={sessionModalOpen} onClose={() => setSessionModalOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle sx={{ fontWeight: 700, color: '#0f172a' }}>{editingId ? 'Edit Academic Session' : 'Add Academic Session'}</DialogTitle>
        <DialogContent dividers>
          {errorMessage && <Alert severity="error" sx={{ mb: 2 }} onClose={() => setErrorMessage(null)}>{errorMessage}</Alert>}
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2.5, pt: 1 }}>
            <TextField
              label="Session Name"
              placeholder="e.g. Academic Year 2026-2027"
              value={sessionForm.name}
              onChange={(e) => setSessionForm({ ...sessionForm, name: e.target.value })}
              fullWidth
              required
            />
            <TextField
              label="Session Code"
              placeholder="e.g. AY-26-27"
              value={sessionForm.code}
              onChange={(e) => setSessionForm({ ...sessionForm, code: e.target.value })}
              fullWidth
              required
            />
            <TextField
              label="Start Date"
              type="date"
              InputLabelProps={{ shrink: true }}
              value={sessionForm.start_date}
              onChange={(e) => setSessionForm({ ...sessionForm, start_date: e.target.value })}
              fullWidth
              required
            />
            <TextField
              label="End Date"
              type="date"
              InputLabelProps={{ shrink: true }}
              value={sessionForm.end_date}
              onChange={(e) => setSessionForm({ ...sessionForm, end_date: e.target.value })}
              fullWidth
              required
            />
          </Box>
        </DialogContent>
        <DialogActions sx={{ p: 2 }}>
          <Button onClick={() => setSessionModalOpen(false)} sx={{ textTransform: 'none', color: '#64748b' }}>
            Cancel
          </Button>
          <Button
            variant="contained"
            onClick={handleSaveSession}
            sx={{ bgcolor: '#4f46e5', textTransform: 'none', px: 3, '&:hover': { bgcolor: '#4338ca' } }}
          >
            {editingId ? 'Save changes' : 'Create Session'}
          </Button>
        </DialogActions>
      </Dialog>

      {/* Success / Error Feedback */}
      <Snackbar
        open={Boolean(notification)}
        autoHideDuration={4000}
        onClose={() => setNotification(null)}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}
      >
        <Alert severity="success" onClose={() => setNotification(null)} sx={{ width: '100%' }}>
          {notification}
        </Alert>
      </Snackbar>

      <Snackbar
        open={Boolean(errorMessage)}
        autoHideDuration={5000}
        onClose={() => setErrorMessage(null)}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}
      >
        <Alert severity="error" onClose={() => setErrorMessage(null)} sx={{ width: '100%' }}>
          {errorMessage}
        </Alert>
      </Snackbar>
    </Box>
  )
}
