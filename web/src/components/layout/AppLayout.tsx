import { useEffect, useMemo, useState } from 'react'
import { Box, IconButton, useMediaQuery, useTheme } from '@mui/material'
import MenuIcon from '@mui/icons-material/Menu'
import { Navigate, Outlet, matchPath, useLocation } from 'react-router-dom'
import { useAuthStore } from '@/store/authStore'
import { TopNav } from './TopNav'
import { Sidebar } from './Sidebar'
import { InstitutionSidebar } from './InstitutionSidebar'
import { getNavigationItems } from './navigationItems'
import { getNavbarModules } from './navbarModules'

export function AppLayout() {
  const { pathname } = useLocation()
  const user = useAuthStore((state) => state.user)
  const theme = useTheme()
  const compact = useMediaQuery(theme.breakpoints.down('md'))
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const platform = Boolean(user?.is_superadmin)
  const modules = useMemo(() => platform ? [] : getNavbarModules(user), [platform, user])
  useEffect(() => {
    if (!compact) setSidebarOpen(false)
  }, [compact])
  const institution = user?.institutions.find((membership) => membership.tenant_id === user.current_tenant_id)
  if (!platform && institution?.institution_type === 'SCHOOL' && matchPath('/hostel/*', pathname)) {
    return <Navigate to="/unauthorized" replace />
  }
  if (!user?.is_superadmin && (user?.current_role === 'PRINCIPAL' || user?.current_role === 'HOD')) {
    const paths = ['/', '/dashboard', '/teachers', '/teachers/:teacherId', '/teacher/dashboard', '/academic', '/academics']
    if (!paths.some((path) => matchPath({ path, end: true }, pathname))) {
      return <Navigate to="/unauthorized" replace />
    }
  }

  return (
    <Box minHeight="100vh" bgcolor="background.default">
      <Box component="a" href="#main-content" sx={{
        position: 'fixed', top: 8, left: 8, zIndex: (theme) => theme.zIndex.tooltip,
        transform: 'translateY(-200%)', '&:focus': { transform: 'none' },
        bgcolor: 'background.paper', color: 'primary.main', px: 2, py: 1, borderRadius: 1,
      }}>
        Skip to content
      </Box>
      {!platform && <TopNav modules={modules} compact={compact} sidebarOpen={sidebarOpen} onOpenSidebar={() => setSidebarOpen(true)} />}
      <Box sx={{ display: 'flex' }}>
        {platform ? (
          <Sidebar
            permanent={!compact}
            open={sidebarOpen}
            items={getNavigationItems(user)}
            onClose={() => setSidebarOpen(false)}
          />
        ) : (
          <InstitutionSidebar modules={modules} permanent={!compact} open={sidebarOpen} onClose={() => setSidebarOpen(false)} />
        )}
        <Box sx={{ flex: 1, minWidth: 0 }}>
          {platform && compact && (
            <IconButton
              aria-label="Open navigation"
              aria-expanded={sidebarOpen}
              aria-controls={sidebarOpen ? 'global-admin-navigation' : undefined}
              onClick={() => setSidebarOpen(true)}
              sx={{ m: 1.5, border: 1, borderColor: 'divider', borderRadius: 2, bgcolor: 'background.paper' }}
            >
              <MenuIcon />
            </IconButton>
          )}
          <Box
            component="main"
            id="main-content"
            tabIndex={-1}
            sx={{
              px: { xs: 2, sm: 3, lg: 4 },
              py: { xs: 2, md: 3 },
              mx: 'auto',
              width: '100%',
              maxWidth: 1664,
              minWidth: 0,
              overflowX: 'clip',
              '&:focus': { outline: 'none' },
            }}
          >
            <Outlet />
          </Box>
        </Box>
      </Box>
    </Box>
  )
}
