import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { afterEach, expect, it, vi } from 'vitest'
import { MemoryRouter } from 'react-router-dom'
import { academicsApi, type Course, type Department, type SchoolClass } from '@/api/academics'
import { attendanceApi } from '@/api/attendance'
import { AttendanceCohortReport } from '@/pages/attendance/AttendanceCohortReport'
import AttendancePage from '@/pages/attendance/AttendancePage'
import { useAuthStore } from '@/store/authStore'

afterEach(() => {
  cleanup()
  useAuthStore.setState({ user: null })
  vi.restoreAllMocks()
})

it.each(['COLLEGE', 'SCHOOL'] as const)('loads the %s teacher roster only on View', async (institutionType) => {
  const college = institutionType === 'COLLEGE'
  useAuthStore.setState({ user: {
    id: 'teacher', email: 'teacher@example.com', full_name: 'Teacher', is_superadmin: false,
    is_active: true, current_tenant_id: 'tenant', current_role: 'TEACHER', permissions: [],
    institutions: [{
      tenant_id: 'tenant', institution_name: 'Example', institution_slug: 'example',
      institution_type: institutionType, role_code: 'TEACHER', role_name: 'Teacher',
      status: 'ACTIVE', permissions: [],
    }],
  } })
  vi.spyOn(academicsApi, 'getSessions').mockResolvedValue({ data: [{ id: 'session', is_current: true }] })
  vi.spyOn(academicsApi, 'getSubjects').mockResolvedValue({ data: [{ id: 'subject', name: 'Mathematics' }] })
  vi.spyOn(academicsApi, 'getClasses').mockResolvedValue({ data: [{ id: 'class', name: 'Grade 8' }] })
  vi.spyOn(academicsApi, 'getDepartments').mockResolvedValue({ data: [] })
  vi.spyOn(academicsApi, 'getCourses').mockResolvedValue({ data: [{ id: 'course', name: 'B.Tech' }] })
  vi.spyOn(academicsApi, 'getSemesters').mockResolvedValue({ data: [{ id: 'semester', name: 'Semester 4' }] })
  vi.spyOn(academicsApi, 'getSections').mockResolvedValue({ data: college
    ? [{ id: 'batch', name: 'Batch A', semester_id: 'semester' }]
    : [{ id: 'section', name: 'Section A', class_id: 'class' }] })
  const getRoster = vi.spyOn(attendanceApi, 'getRoster').mockResolvedValue({
    academic_session_id: 'session', session_date: '', session_type: 'PERIOD_WISE',
    is_submitted: false, students: [],
  })
  render(<MemoryRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}><AttendancePage /></MemoryRouter>)
  const view = screen.getByRole('button', { name: 'View' })
  expect(view).toBeDisabled()
  await waitFor(() => expect(academicsApi.getSubjects).toHaveBeenCalled())
  if (college) {
    expect(screen.queryByRole('combobox', { name: 'Section' })).toBeNull()
    await select('Course', 'B.Tech')
    await select('Semester', 'Semester 4 · Batch A')
    await select('Subject', 'Mathematics')
  } else {
    expect(screen.queryByRole('combobox', { name: 'Class' })).toBeNull()
    await select('Subject', 'Mathematics')
    await select('Section', 'Grade 8 Section A')
  }
  fireEvent.change(screen.getByRole('spinbutton', { name: 'Time (period)' }), { target: { value: '3' } })
  expect(getRoster).not.toHaveBeenCalled()
  fireEvent.click(view)
  expect(await screen.findByText('No enrolled students were found for this selection.')).toBeTruthy()
  expect(getRoster).toHaveBeenCalledWith(expect.objectContaining({
    academic_session_id: 'session', session_type: 'PERIOD_WISE', subject_id: 'subject', period_number: 3,
    ...(college ? { course_id: 'course', semester_id: 'semester', section_id: 'batch' }
      : { class_id: 'class', section_id: 'section' }),
  }))
})

async function select(label: string, option: string) {
  const field = screen.getByRole('combobox', { name: label })
  await waitFor(() => expect(field.getAttribute('aria-disabled')).not.toBe('true'))
  vi.spyOn(field, 'getBoundingClientRect').mockReturnValue(new DOMRect(10, 10, 120, 40))
  fireEvent.mouseDown(field)
  fireEvent.click(await screen.findByRole('option', { name: option }))
}

it.each([true, false])('loads the selected admin attendance report (college=%s)', async (isCollege) => {
  vi.spyOn(academicsApi, 'getSemesters').mockResolvedValue({ data: [{ id: 'semester', name: 'Semester 4' }] })
  vi.spyOn(academicsApi, 'getSections').mockResolvedValue({ data: [{ id: 'section', name: 'Section A' }] })
  const student = { id: 'student', name: 'Maya Rao', admission_number: 'A-1', total: 5, attended: 4, percentage: 80 }
  const report = vi.spyOn(attendanceApi, 'getCohortReport').mockResolvedValue({
    students: [student], overview: student,
    subjects: [{ id: 'subject', name: 'Computer Networks', classes: 5, total: 5, attended: 4, percentage: 80, students: [student] }],
  })
  render(
    <QueryClientProvider client={new QueryClient()}>
      <AttendanceCohortReport isCollege={isCollege} tenantId="tenant"
        sessions={[{ id: 'current', name: 'Current session', is_current: true, tenant_id: 'tenant', code: 'AY', start_date: '', end_date: '', status: 'ACTIVE', created_at: '' }]}
        departments={[{ id: 'department', name: 'Computing' } as Department]}
        courses={[{ id: 'course', name: 'B.Tech', department_id: 'department' } as Course]}
        classes={[{ id: 'class', name: 'Grade 8' } as SchoolClass]}
      />
    </QueryClientProvider>,
  )
  if (isCollege) {
    expect(screen.queryByRole('combobox', { name: 'Class' })).toBeNull()
    await select('Department', 'Computing')
    await select('Course', 'B.Tech')
    await screen.findByRole('combobox', { name: 'Semester' })
    await select('Semester', 'Semester 4')
  } else {
    expect(screen.queryByRole('combobox', { name: 'Department' })).toBeNull()
    await select('Class', 'Grade 8')
    await select('Section', 'Section A')
  }
  expect(report).not.toHaveBeenCalled()
  fireEvent.click(screen.getByRole('button', { name: 'View' }))
  expect(await screen.findByText('Average attendance')).toBeTruthy()
  expect(report).toHaveBeenCalledWith(isCollege
    ? { academic_session_id: 'current', department_id: 'department', course_id: 'course', semester_id: 'semester' }
    : { academic_session_id: 'current', class_id: 'class', section_id: 'section' })
  fireEvent.click(screen.getByRole('tab', { name: 'Subject-wise' }))
  fireEvent.click(screen.getByRole('button', { name: 'View students for Computer Networks' }))
  expect(within(await screen.findByRole('dialog', { name: 'Computer Networks' })).getByText('Maya Rao')).toBeTruthy()
})

it('shows enrolled college students before attendance has been recorded', async () => {
  vi.spyOn(academicsApi, 'getSemesters').mockResolvedValue({ data: [{ id: 'semester', name: 'Semester 1' }] })
  vi.spyOn(attendanceApi, 'getCohortReport').mockResolvedValue({
    students: [{ id: 'student', name: 'New Student', admission_number: 'ADM-1', total: 0, attended: 0, percentage: null }],
    overview: { total: 0, attended: 0, percentage: null }, subjects: [],
  })
  render(<QueryClientProvider client={new QueryClient()}><AttendanceCohortReport isCollege tenantId="tenant"
    sessions={[{ id: 'current', name: 'Current session', is_current: true, tenant_id: 'tenant', code: 'AY', start_date: '', end_date: '', status: 'ACTIVE', created_at: '' }]}
    departments={[{ id: 'department', name: 'Computing' } as Department]}
    courses={[{ id: 'course', name: 'B.Tech', department_id: 'department' } as Course]} classes={[]} />
  </QueryClientProvider>)
  await select('Department', 'Computing')
  await select('Course', 'B.Tech')
  await select('Semester', 'Semester 1')
  fireEvent.click(screen.getByRole('button', { name: 'View' }))
  expect(await screen.findByText('New Student')).toBeTruthy()
  expect(screen.getByText('No records')).toBeTruthy()
})
