import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { MemoryRouter, useLocation } from 'react-router-dom'
import { afterEach, expect, it, vi } from 'vitest'
import { institutionsApi } from '@/api/institutions'
import { superAdminApi } from '@/api/superAdmin'
import InstitutionsPage from '@/pages/super-admin/InstitutionsPage'

function CurrentPath() {
  return <span data-testid="current-path">{useLocation().pathname}</span>
}

afterEach(() => {
  cleanup()
  vi.restoreAllMocks()
})

it.each([
  ['SCHOOL', /K-12 School/],
  ['COLLEGE', /College \/ University/],
])('adds a %s in a modal without leaving Institutions', async (institutionType, option) => {
  const list = vi.spyOn(superAdminApi, 'listInstitutions').mockResolvedValue({
    items: [], total: 0, page: 1, size: 10, pages: 0,
  })
  const register = vi.spyOn(institutionsApi, 'register').mockResolvedValue({
    tenant_id: 'new-tenant', slug: 'evergreen', invitation_token: 'test-token', message: 'Pending approval',
  })
  render(
    <QueryClientProvider client={new QueryClient()}>
      <MemoryRouter initialEntries={['/super-admin/institutions']} future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
        <InstitutionsPage />
        <CurrentPath />
      </MemoryRouter>
    </QueryClientProvider>,
  )

  fireEvent.click(screen.getByRole('button', { name: 'Add Institution' }))
  const dialog = within(await screen.findByRole('dialog', { name: 'Add Institution' }))
  fireEvent.click(dialog.getByRole('button', { name: option }))
  fireEvent.change(screen.getByLabelText(/Official Institution Name/), { target: { value: 'Evergreen' } })
  fireEvent.change(screen.getByLabelText(/Official Email/), { target: { value: 'office@example.com' } })
  fireEvent.change(screen.getByLabelText(/Full Name & Title/), { target: { value: 'Reva Patel' } })
  fireEvent.change(screen.getByLabelText(/Administrator Email/), { target: { value: 'admin@example.com' } })
  fireEvent.click(dialog.getByRole('button', { name: 'Add Institution' }))

  expect(await screen.findByText('Evergreen was added and is pending approval.')).toBeTruthy()
  expect(register).toHaveBeenCalledWith(expect.objectContaining({
    institution_type: institutionType, slug: 'evergreen', principal_email: 'admin@example.com',
  }))
  fireEvent.click(dialog.getByRole('button', { name: 'Done' }))
  await waitFor(() => expect(screen.queryByRole('dialog')).toBeNull())
  expect(await screen.findByRole('heading', { name: 'Institution Management' })).toBeTruthy()
  expect(screen.getByTestId('current-path').textContent).toBe('/super-admin/institutions')
  expect(list.mock.calls.length).toBeGreaterThanOrEqual(2)
})
