import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, expect, it, vi } from 'vitest'
import { academicsApi } from '@/api/academics'
import { studentsApi } from '@/api/students'
import { StudentsListPage } from '@/pages/students/StudentsListPage'
import { useAuthStore } from '@/store/authStore'

vi.mock('@/pages/students/AddEditStudentModal', () => ({ AddEditStudentModal: ({ open }: { open: boolean }) => open ? <div role="dialog">New Student Admission</div> : null }))
vi.mock('@/pages/students/BulkImportStudentsModal', () => ({ BulkImportStudentsModal: () => null }))

afterEach(() => {
  cleanup()
  useAuthStore.setState({ user: null })
  vi.restoreAllMocks()
})

it('opens the admission form from the Admissions navigation link', async () => {
  useAuthStore.setState({ user: {
    id: 'admin', email: 'admin@example.com', full_name: 'Admin', is_superadmin: false,
    is_active: true, current_tenant_id: 'college', current_role: 'INSTITUTION_ADMIN', permissions: [],
    institutions: [{ tenant_id: 'college', institution_name: 'College', institution_slug: 'college',
      institution_type: 'COLLEGE', role_code: 'INSTITUTION_ADMIN', role_name: 'Administrator', status: 'ACTIVE', permissions: [] }],
  } })
  vi.spyOn(academicsApi, 'getDepartments').mockResolvedValue({ data: [] })
  vi.spyOn(academicsApi, 'getCourses').mockResolvedValue({ data: [] })
  render(<QueryClientProvider client={new QueryClient()}><MemoryRouter initialEntries={['/students?action=admit']}><StudentsListPage /></MemoryRouter></QueryClientProvider>)
  expect(await screen.findByRole('dialog')).toHaveTextContent('New Student Admission')
})

it('submits class and section filters for a school tenant', async () => {
  useAuthStore.setState({ user: {
    id: 'school-admin', email: 'admin@example.com', full_name: 'School Admin', is_superadmin: false,
    is_active: true, current_tenant_id: 'school', current_role: 'INSTITUTION_ADMIN', permissions: [],
    institutions: [{
      tenant_id: 'school', institution_name: 'Example School', institution_slug: 'example-school',
      institution_type: 'SCHOOL', role_code: 'INSTITUTION_ADMIN', role_name: 'Administrator',
      status: 'ACTIVE', permissions: [],
    }],
  } })
  vi.spyOn(academicsApi, 'getClasses').mockResolvedValue({ data: [{ id: 'grade-8', name: 'Grade 8' }] })
  vi.spyOn(academicsApi, 'getSections').mockResolvedValue({ data: [{ id: 'section-a', name: 'Section A', class_id: 'grade-8' }] })
  const search = vi.spyOn(studentsApi, 'listStudents').mockResolvedValue({ items: [], page: 1, size: 15, total: 0, pages: 0 })
  render(
    <QueryClientProvider client={new QueryClient()}>
      <MemoryRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}><StudentsListPage /></MemoryRouter>
    </QueryClientProvider>,
  )
  expect(screen.queryByRole('combobox', { name: 'Department' })).toBeNull()
  await openSelect('Class')
  fireEvent.click(await screen.findByRole('option', { name: 'Grade 8' }))
  await openSelect('Section')
  fireEvent.click(await screen.findByRole('option', { name: 'Section A' }))
  expect(search).not.toHaveBeenCalled()
  fireEvent.click(screen.getByRole('button', { name: 'Search' }))
  await waitFor(() => expect(search).toHaveBeenCalledWith({
    search: undefined, class_id: 'grade-8', section_id: 'section-a', status: 'ACTIVE', page: 1, size: 15,
  }))
})

async function openSelect(name: string) {
  const input = await screen.findByRole('combobox', { name })
  vi.spyOn(input, 'getBoundingClientRect').mockReturnValue(new DOMRect(20, 40, 160, 40))
  fireEvent.mouseDown(input)
  await screen.findByRole('listbox')
}

it('loads student results only after submitting the selected academic filters', async () => {
  vi.spyOn(academicsApi, 'getDepartments').mockResolvedValue({
    data: [{ id: 'science', name: 'Science' }, { id: 'arts', name: 'Arts' }],
  })
  vi.spyOn(academicsApi, 'getCourses').mockResolvedValue({
    data: [
      { id: 'biology', name: 'Biology', department_id: 'science', duration_semesters: 4 },
      { id: 'history', name: 'History', department_id: 'arts', duration_semesters: 8 },
    ],
  })
  const listStudents = vi.spyOn(studentsApi, 'listStudents').mockResolvedValue({
    items: [{
      id: 'student', tenant_id: 'college', user_id: 'user', full_name: 'Maya Sharma',
      admission_number: 'ADM-01', status: 'ACTIVE', created_at: '2026-01-01', updated_at: '2026-01-01',
    }],
    page: 1, size: 15, total: 1, pages: 1,
  })

  render(
    <QueryClientProvider client={new QueryClient()}>
      <MemoryRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
        <StudentsListPage />
      </MemoryRouter>
    </QueryClientProvider>,
  )

  expect(screen.getByText(/click search to see students/i)).toBeTruthy()
  await openSelect('Department')
  fireEvent.click(await screen.findByRole('option', { name: 'Science' }))
  await openSelect('Course / Program')
  expect(screen.queryByRole('option', { name: 'History' })).toBeNull()
  fireEvent.click(await screen.findByRole('option', { name: 'Biology' }))
  await openSelect('Semester')
  expect(screen.queryByRole('option', { name: 'Semester 5' })).toBeNull()
  fireEvent.click(screen.getByRole('option', { name: 'Semester 2' }))
  fireEvent.change(await screen.findByRole('textbox', { name: 'Student name, admission or roll number' }), {
    target: { value: ' Maya ' },
  })
  expect(listStudents).not.toHaveBeenCalled()

  fireEvent.click(screen.getByRole('button', { name: 'Search' }))
  expect(await screen.findByText('Maya Sharma')).toBeTruthy()
  expect(listStudents).toHaveBeenCalledWith({
    department_id: 'science', course_id: 'biology', semester: 2, search: 'Maya', status: 'ACTIVE',
    page: 1, size: 15,
  })

  await openSelect('Department')
  fireEvent.click(screen.getByRole('option', { name: 'Arts' }))
  expect((await screen.findByRole('combobox', { name: 'Course / Program' })).textContent).toBe('All Courses')
  expect(screen.getByRole('combobox', { name: 'Semester' }).textContent).toBe('All semesters')
  expect(screen.getByText('Maya Sharma')).toBeTruthy()
  expect(listStudents).toHaveBeenCalledTimes(1)

  fireEvent.click(screen.getByRole('button', { name: 'Reset' }))
  expect(screen.getByText(/click search to see students/i)).toBeTruthy()
  expect(listStudents).toHaveBeenCalledTimes(1)
})
