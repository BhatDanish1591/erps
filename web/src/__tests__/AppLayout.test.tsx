import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { ThemeProvider } from '@mui/material'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter, Route, Routes, useLocation } from 'react-router-dom'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { notificationsApi } from '@/api/notifications'
import { AppLayout } from '@/components/layout/AppLayout'
import { useAuthStore } from '@/store/authStore'
import { theme } from '@/theme'

function AcademicDestination() {
  return <h1>{useLocation().search === '?tab=sections' ? 'School Sections' : 'Academics'}</h1>
}

function renderLayout(mobile: boolean, withTenant = false, platform = true, type: 'COLLEGE' | 'SCHOOL' = 'COLLEGE') {
  vi.stubGlobal('matchMedia', (query: string) => ({
    matches: mobile,
    media: query,
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
  }))
  useAuthStore.setState({
    user: {
      id: 'admin',
      email: 'admin@example.com',
      full_name: 'Platform Admin',
      is_superadmin: platform,
      current_role: platform ? 'SUPER_ADMIN' : 'INSTITUTION_ADMIN',
      is_active: true,
      current_tenant_id: withTenant ? 'tenant' : null,
      permissions: [],
      institutions: withTenant ? [
        {
          tenant_id: 'other', institution_name: 'Other institution', institution_slug: 'other',
          institution_type: type === 'SCHOOL' ? 'COLLEGE' : 'SCHOOL',
          role_code: 'INSTITUTION_ADMIN', role_name: 'Administrator', status: 'ACTIVE', permissions: [],
        },
        {
          tenant_id: 'tenant', institution_name: 'Current institution', institution_slug: 'current',
          institution_type: type, role_code: 'INSTITUTION_ADMIN', role_name: 'Administrator',
          status: 'ACTIVE', permissions: [],
        },
      ] : [],
    },
    access_token: withTenant ? 'token' : null,
  })

  render(
    <QueryClientProvider client={new QueryClient()}>
      <ThemeProvider theme={theme}>
        <MemoryRouter initialEntries={[platform ? '/super-admin/announcements' : '/dashboard']} future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
          <Routes>
            <Route element={<AppLayout />}>
              <Route path="/super-admin/announcements" element={<h1>Announcement management</h1>} />
              <Route path="/super-admin/tickets" element={<h1>Ticket management</h1>} />
              <Route path="/dashboard" element={<h1>College dashboard</h1>} />
              <Route path="/students" element={<h1>Student directory</h1>} />
              <Route path="/academic" element={<AcademicDestination />} />
              <Route path="/academics/subjects" element={<h1>Subject management</h1>} />
            </Route>
          </Routes>
        </MemoryRouter>
      </ThemeProvider>
    </QueryClientProvider>,
  )
}

afterEach(() => {
  cleanup()
  useAuthStore.setState({ user: null, access_token: null })
  vi.restoreAllMocks()
  vi.unstubAllGlobals()
})

describe('App navigation', () => {
  it('lets college admins open Subjects and Admissions', async () => {
    renderLayout(false, true, false)
    const nav = screen.getByRole('navigation', { name: 'Main navigation' })
    fireEvent.click(within(nav).getByRole('button', { name: 'Academics' }))
    const subjects = await within(nav).findByRole('link', { name: 'Subjects' })
    expect(subjects).toHaveAttribute('href', '/academics/subjects')
    fireEvent.click(subjects)
    expect(await screen.findByRole('heading', { name: 'Subject management' })).toBeTruthy()
    fireEvent.click(within(nav).getByRole('button', { name: 'ERP' }))
    const admissions = await within(nav).findByRole('link', { name: 'Admissions' })
    expect(admissions).toHaveAttribute('href', '/students?action=admit')
    fireEvent.click(admissions)
    expect(await screen.findByRole('heading', { name: 'Student directory' })).toBeTruthy()
  })
  it('uses a permanent sidebar for Global Admin on desktop', async () => {
    renderLayout(false)
    const nav = screen.getByRole('navigation', { name: 'Main navigation' })
    expect(within(nav).getByRole('link', { name: 'Announcements' }).getAttribute('aria-current')).toBe('page')
    expect(within(nav).queryByRole('link', { name: 'Students' })).toBeNull()
    expect(screen.queryByRole('button', { name: 'Search ERP' })).toBeNull()
    expect(screen.queryByRole('button', { name: 'Open navigation' })).toBeNull()
    fireEvent.click(within(nav).getByRole('link', { name: 'Support Desk' }))
    expect(await screen.findByRole('heading', { name: 'Ticket management' })).toBeTruthy()
    expect(within(nav).getByRole('link', { name: 'Support Desk' }).getAttribute('aria-current')).toBe('page')
  })

  it('opens the mobile sidebar on demand and closes it after following a link', async () => {
    renderLayout(true)
    const openButton = screen.getByRole('button', { name: 'Open navigation' })
    expect(openButton.getAttribute('aria-expanded')).toBe('false')
    expect(screen.queryByRole('navigation', { name: 'Main navigation' })).toBeNull()

    fireEvent.click(openButton)
    const drawer = await screen.findByRole('navigation', { name: 'Main navigation' })
    expect(within(drawer).getByRole('link', { name: 'Announcements' }).getAttribute('aria-current')).toBe('page')
    fireEvent.click(within(drawer).getByRole('link', { name: 'Support Desk' }))

    await waitFor(() => expect(screen.queryByRole('navigation', { name: 'Main navigation' })).toBeNull())
    expect(screen.getByRole('heading', { name: 'Ticket management' })).toBeTruthy()
    expect(openButton.getAttribute('aria-expanded')).toBe('false')
  })

  it('shows the college modules in the sidebar and keeps search in the header', async () => {
    renderLayout(false, true, false)
    const nav = screen.getByRole('navigation', { name: 'Main navigation' })
    expect(within(nav).getByRole('button', { name: 'Academics' })).toBeTruthy()
    expect(within(nav).getByRole('button', { name: 'Hostel' })).toBeTruthy()
    expect(within(nav).queryByRole('link', { name: 'Institutions' })).toBeNull()
    expect(within(screen.getByRole('banner')).queryByRole('button', { name: 'Academics' })).toBeNull()
    fireEvent.click(screen.getByRole('button', { name: 'Search ERP' }))
    const dialog = await screen.findByRole('dialog', { name: 'Search ERP' })
    fireEvent.change(within(dialog).getByRole('combobox'), { target: { value: 'students' } })
    fireEvent.click(await within(dialog).findByRole('option', { name: 'Students' }))
    expect(await screen.findByRole('heading', { name: 'Student directory' })).toBeTruthy()
  })

  it.each([false, true])('uses the school menus from the active membership (mobile=%s)', async (mobile) => {
    renderLayout(mobile, true, false, 'SCHOOL')
    if (mobile) fireEvent.click(screen.getByRole('button', { name: 'Open navigation' }))
    const nav = await screen.findByRole('navigation', { name: 'Main navigation' })
    expect(within(nav).queryByRole('button', { name: 'Hostel' })).toBeNull()
    const academics = within(nav).getByRole('button', { name: 'Academics' })
    vi.spyOn(academics, 'getBoundingClientRect').mockReturnValue(new DOMRect(16, 22, 120, 30))
    fireEvent.click(academics)
    const role = 'link'
    expect(screen.getByRole(role, { name: /^Classes/ }).getAttribute('href')).toBe('/academic?tab=classes')
    for (const label of ['Departments', 'Courses', 'Semesters']) {
      expect(screen.queryByRole(role, { name: new RegExp(label) })).toBeNull()
    }
    fireEvent.click(screen.getByRole(role, { name: /^Sections/ }))
    expect(await screen.findByRole('heading', { name: 'School Sections' })).toBeTruthy()
    if (mobile) {
      await waitFor(() => expect(screen.getByRole('button', { name: 'Open navigation' }).getAttribute('aria-expanded')).toBe('false'))
    } else {
      expect(screen.getByRole('link', { name: /^Sections/ }).getAttribute('aria-current')).toBe('page')
    }
  })

  it('uses the existing notification API for the unread badge and mark-as-read action', async () => {
    const notice = {
      id: 'notice', tenant_id: 'tenant', user_id: 'admin', title: 'Term reminder',
      message: 'The term starts Monday.', is_read: false, event_type: 'ANNOUNCEMENT',
      created_at: '2026-01-01T00:00:00Z',
    }
    const list = vi.spyOn(notificationsApi, 'listInApp').mockResolvedValue([notice])
    const markRead = vi.spyOn(notificationsApi, 'markAsRead').mockImplementation(async () => {
      list.mockResolvedValue([])
      return { ...notice, is_read: true }
    })
    renderLayout(false, true, false)
    const bell = await screen.findByRole('button', { name: 'Notifications, 1 unread' })
    vi.spyOn(bell, 'getBoundingClientRect').mockReturnValue(new DOMRect(700, 16, 32, 32))
    fireEvent.click(bell)
    fireEvent.click(await screen.findByRole('menuitem', { name: 'Term reminder, mark as read' }))
    expect(await screen.findByRole('menuitem', { name: 'No unread notifications' })).toBeTruthy()
    expect(list).toHaveBeenCalledWith(true)
    expect(markRead).toHaveBeenCalledTimes(1)
    expect(markRead.mock.calls[0][0]).toBe('notice')
  })
})
