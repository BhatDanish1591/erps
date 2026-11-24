import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { afterEach, expect, it, vi } from 'vitest'
import { academicsApi } from '@/api/academics'
import { useAuthStore } from '@/store/authStore'
import SubjectsPage from '@/pages/academics/SubjectsPage'

afterEach(() => { cleanup(); vi.restoreAllMocks(); useAuthStore.setState({ user: null }) })

it('lists college subjects and opens the edit form with saved values', async () => {
  useAuthStore.setState({ user: {
    id: 'admin', email: 'admin@example.com', full_name: 'Admin', is_superadmin: false, is_active: true,
    current_tenant_id: 'college', current_role: 'INSTITUTION_ADMIN', permissions: [],
    institutions: [{ tenant_id: 'college', institution_name: 'College', institution_slug: 'college', institution_type: 'COLLEGE', role_code: 'INSTITUTION_ADMIN', role_name: 'Admin', status: 'ACTIVE', permissions: [] }],
  } })
  vi.spyOn(academicsApi, 'getSubjects').mockResolvedValue({ data: [{ id: 'subject', name: 'Algorithms', code: 'CS101', department_id: 'dept', department_name: 'Computing', subject_type: 'THEORY', credits: 3, hours_per_week: 4 }] })
  vi.spyOn(academicsApi, 'getDepartments').mockResolvedValue({ data: [{ id: 'dept', name: 'Computing' }] })
  vi.spyOn(academicsApi, 'getCourses').mockResolvedValue({ data: [] })
  vi.spyOn(academicsApi, 'getSessions').mockResolvedValue({ data: [] })
  vi.spyOn(academicsApi, 'getSubjectMappings').mockResolvedValue({ data: [] })
  const update = vi.spyOn(academicsApi, 'updateSubject').mockResolvedValue({})
  render(<QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}><SubjectsPage /></QueryClientProvider>)
  fireEvent.click(await screen.findByRole('button', { name: 'Edit Algorithms' }))
  const name = screen.getByLabelText(/Subject name/) as HTMLInputElement
  expect(name.value).toBe('Algorithms')
  fireEvent.change(name, { target: { value: 'Advanced Algorithms' } })
  fireEvent.click(screen.getByRole('button', { name: 'Save' }))
  await waitFor(() => expect(update).toHaveBeenCalledWith('subject', expect.objectContaining({ name: 'Advanced Algorithms', department_id: 'dept' })))
})
