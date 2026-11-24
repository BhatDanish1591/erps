import { useState } from 'react'
import {
  AppBar, Avatar, Box, Button, Dialog, DialogActions, DialogContent, DialogTitle, Divider,
  IconButton, ListItemIcon, ListItemText, Menu, MenuItem, Toolbar, Tooltip, Typography,
} from '@mui/material'
import MenuIcon from '@mui/icons-material/Menu'
import Logout from '@mui/icons-material/Logout'
import School from '@mui/icons-material/SchoolOutlined'
import Search from '@mui/icons-material/Search'
import Person from '@mui/icons-material/PersonOutline'
import Settings from '@mui/icons-material/SettingsOutlined'
import AdminPanelSettings from '@mui/icons-material/AdminPanelSettingsOutlined'
import { alpha } from '@mui/material/styles'
import { Link, useNavigate } from 'react-router-dom'
import { useAuthStore } from '@/store/authStore'
import { staffRoleLabels } from '@/api/teachers'
import { INSTITUTION_SIDEBAR_ID } from './InstitutionSidebar'
import { NavbarNotifications } from './NavbarNotifications'
import { NavbarSearch } from './NavbarSearch'
import type { NavbarModule } from './navbarModules'

export function TopNav({ modules, compact, sidebarOpen, onOpenSidebar }: {
  modules: NavbarModule[]
  compact: boolean
  sidebarOpen: boolean
  onOpenSidebar: () => void
}) {
  const user = useAuthStore((state) => state.user)
  const clearAuth = useAuthStore((state) => state.clearAuth)
  const navigate = useNavigate()
  const [searchOpen, setSearchOpen] = useState(false)
  const [profileOpen, setProfileOpen] = useState(false)
  const [accountAnchor, setAccountAnchor] = useState<HTMLElement | null>(null)
  const closeAccount = () => setAccountAnchor(null)

  const homePath = user?.is_superadmin ? '/super-admin' : '/dashboard'
  const institution = user?.institutions.find((item) => item.tenant_id === user.current_tenant_id)
  const currentRole = user?.current_role
  const role = user?.is_superadmin ? 'Global Admin'
    : currentRole === 'HOD' || currentRole === 'PRINCIPAL' || currentRole === 'TEACHER' ? staffRoleLabels[currentRole]
    : currentRole === 'INSTITUTION_ADMIN' ? (institution?.institution_type === 'COLLEGE' ? 'College Admin' : 'Institution Admin')
    : currentRole?.replaceAll('_', ' ') ?? 'User'
  const manager = currentRole === 'HOD' || currentRole === 'PRINCIPAL'
  const settingsPath = user?.is_superadmin
    ? '/super-admin/settings'
    : user?.current_tenant_id && !manager ? '/notifications' : undefined
  const settingsLink = settingsPath ? { component: Link, to: settingsPath, onClick: closeAccount } : {}

  return (
    <AppBar
      position="sticky"
      color="inherit"
      elevation={0}
      sx={(theme) => ({
        borderBottom: 1, borderColor: 'divider', bgcolor: 'background.paper', color: 'text.primary',
        boxShadow: `0 4px 18px ${alpha(theme.palette.common.black, 0.06)}`,
        ...(user?.is_superadmin && {
          backgroundImage: `linear-gradient(105deg, ${alpha(theme.palette.secondary.main, 0.10)}, transparent 68%)`,
        }),
      })}
    >
      <Toolbar
        variant="dense"
        disableGutters
        sx={{ minHeight: 60, px: { xs: 1.25, sm: 2 }, gap: { xs: 0.5, md: 1.5 } }}
      >
        <Box sx={{ display: 'flex', alignItems: 'center', minWidth: 0, gap: 0.5, flex: 1 }}>
          {compact && (
            <IconButton
              aria-label="Open navigation"
              aria-expanded={sidebarOpen}
              aria-controls={sidebarOpen ? INSTITUTION_SIDEBAR_ID : undefined}
              onClick={onOpenSidebar}
              sx={{ flexShrink: 0, width: 42, height: 42 }}
            >
              <MenuIcon fontSize="small" />
            </IconButton>
          )}
          <Box
            component={Link}
            to={homePath}
            aria-label="EduSaaS CRM home"
            sx={{ display: 'flex', alignItems: 'center', gap: 0.9, color: 'text.primary', textDecoration: 'none', minWidth: 0 }}
          >
            <Avatar variant="rounded" sx={{ width: 36, height: 36, flexShrink: 0, bgcolor: user?.is_superadmin ? 'secondary.main' : 'primary.main', color: 'primary.contrastText' }}>
              {user?.is_superadmin ? <AdminPanelSettings fontSize="small" /> : <School fontSize="small" />}
            </Avatar>
            <Box minWidth={0}>
              <Typography variant="subtitle2" component="span" noWrap display="block" fontWeight={800}>
                EduSaaS CRM
              </Typography>
              {(user?.is_superadmin || institution) && (
                <Typography variant="caption" color="text.secondary" noWrap display="block" sx={{ maxWidth: 125 }}>
                  {user?.is_superadmin ? 'Global Admin' : institution?.institution_name}
                </Typography>
              )}
            </Box>
          </Box>
        </Box>

        <Box sx={{ display: 'flex', alignItems: 'center', gap: { xs: 0.15, sm: 0.75 }, flexShrink: 0, pl: { md: 1.25 }, borderLeft: { md: 1 }, borderColor: 'divider' }}>
          <Tooltip title="Search ERP">
            <IconButton aria-label="Search ERP" onClick={() => setSearchOpen(true)} size="small" sx={{ width: 40, height: 40 }}>
              <Search fontSize="small" />
            </IconButton>
          </Tooltip>
          {(!user?.is_superadmin || user.current_tenant_id) && <NavbarNotifications hubPath={manager || user?.is_superadmin ? undefined : '/notifications'} />}
          <Tooltip title="Account menu">
            <IconButton
              id="navbar-account-button"
              aria-label="Account menu"
              aria-haspopup="menu"
              aria-expanded={Boolean(accountAnchor)}
              aria-controls={accountAnchor ? 'navbar-account-menu' : undefined}
              onClick={(event) => setAccountAnchor(event.currentTarget)}
              size="small"
              sx={{ width: 40, height: 40 }}
            >
              <Avatar sx={{ width: 32, height: 32, bgcolor: 'action.selected', color: 'text.primary', fontSize: '0.875rem', fontWeight: 700 }}>
                {user?.full_name.charAt(0) || 'U'}
              </Avatar>
            </IconButton>
          </Tooltip>
        </Box>
      </Toolbar>

      {searchOpen && <NavbarSearch modules={modules} onClose={() => setSearchOpen(false)} />}
      <Menu
        anchorEl={accountAnchor}
        open={Boolean(accountAnchor)}
        onClose={closeAccount}
        transformOrigin={{ horizontal: 'right', vertical: 'top' }}
        anchorOrigin={{ horizontal: 'right', vertical: 'bottom' }}
        MenuListProps={{ id: 'navbar-account-menu', 'aria-labelledby': 'navbar-account-button' }}
        PaperProps={{ sx: { mt: 1, minWidth: 220, maxWidth: 'calc(100vw - 24px)' } }}
      >
        <Box role="none" px={2} py={1}>
          <Typography variant="body2" fontWeight={700}>{user?.full_name ?? 'Guest'}</Typography>
          <Typography variant="caption" color="text.secondary">{role}</Typography>
        </Box>
        <Divider />
        <MenuItem onClick={() => { closeAccount(); setProfileOpen(true) }}>
          <ListItemIcon><Person fontSize="small" /></ListItemIcon>
          My Profile
        </MenuItem>
        <MenuItem {...settingsLink} disabled={!settingsPath}>
          <ListItemIcon><Settings fontSize="small" /></ListItemIcon>
          <ListItemText
            primary="Settings"
            secondary={user?.is_superadmin ? undefined : settingsPath ? 'My Notification Preferences tab' : 'Unavailable for this account'}
          />
        </MenuItem>
        {user && user.institutions.length > 1 && (
          <MenuItem component={Link} to="/select-institution" onClick={closeAccount}>
            <ListItemIcon><School fontSize="small" /></ListItemIcon>
            Switch Institution
          </MenuItem>
        )}
        <Divider />
        <MenuItem onClick={() => { closeAccount(); clearAuth(); navigate('/login') }} sx={{ color: 'error.main' }}>
          <ListItemIcon sx={{ color: 'inherit' }}><Logout fontSize="small" /></ListItemIcon>
          Logout
        </MenuItem>
      </Menu>
      <Dialog open={profileOpen} onClose={() => setProfileOpen(false)} aria-labelledby="navbar-profile-title" fullWidth maxWidth="xs">
        <DialogTitle id="navbar-profile-title">My Profile</DialogTitle>
        <DialogContent>
          <Typography variant="subtitle1" fontWeight={700}>{user?.full_name}</Typography>
          <Typography color="text.secondary">{user?.email}</Typography>
          <Typography color="text.secondary">{role}</Typography>
          {institution && <Typography color="text.secondary">{institution.institution_name}</Typography>}
        </DialogContent>
        <DialogActions><Button onClick={() => setProfileOpen(false)}>Close</Button></DialogActions>
      </Dialog>
    </AppBar>
  )
}
