import {
  Drawer,
  List,
  ListItem,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  Box,
  Typography,
  Divider,
  Avatar,
  IconButton,
} from '@mui/material'
import CloseIcon from '@mui/icons-material/Close'
import AdminPanelSettingsIcon from '@mui/icons-material/AdminPanelSettingsOutlined'
import LogoutIcon from '@mui/icons-material/LogoutOutlined'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { useAuthStore } from '@/store/authStore'
import { isNavigationItemActive } from './navigationItems'
import type { NavItem } from './navigationItems'

interface SidebarProps {
  open: boolean
  items: NavItem[]
  onClose: () => void
  permanent: boolean
}

const SIDEBAR_WIDTH = 280

export function Sidebar({ open, items, onClose, permanent }: SidebarProps) {
  const location = useLocation()
  const navigate = useNavigate()
  const user = useAuthStore((state) => state.user)
  const clearAuth = useAuthStore((state) => state.clearAuth)

  const content = (
    <Box
      id="global-admin-navigation"
      component="nav"
      aria-label="Main navigation"
      sx={{
        height: '100%',
        display: 'flex',
        flexDirection: 'column',
        bgcolor: '#0f172a',
        color: 'white',
      }}
    >
      <Box px={2.5} py={2} display="flex" alignItems="center" gap={1.5}>
        <Avatar variant="rounded" sx={{ bgcolor: 'secondary.dark', width: 36, height: 36 }}>
          <AdminPanelSettingsIcon fontSize="small" />
        </Avatar>
        <Box overflow="hidden" flex={1}>
          <Typography variant="subtitle2" fontWeight={700} color="white" lineHeight={1.2} noWrap>
            EduSaaS CRM
          </Typography>
          <Typography variant="caption" sx={{ color: '#94a3b8', fontSize: '0.7rem' }} noWrap display="block">
            Global Admin
          </Typography>
        </Box>
        {!permanent && <IconButton aria-label="Close navigation" onClick={onClose} size="small" sx={{ color: 'inherit' }}>
          <CloseIcon fontSize="small" />
        </IconButton>}
      </Box>

      <Divider sx={{ borderColor: '#1e293b' }} />

      <List sx={{ flex: 1, px: 1.5, py: 1.5, overflowY: 'auto' }}>
        {items.map((item) => {
          const isActive = isNavigationItemActive(item.path, location.pathname)
          return (
            <ListItem key={item.path} disablePadding sx={{ mb: 0.5 }}>
              <ListItemButton
                component={Link}
                to={item.path}
                selected={isActive}
                aria-current={isActive ? 'page' : undefined}
                onClick={onClose}
                sx={{
                  borderRadius: 2,
                  color: isActive ? 'white' : '#94a3b8',
                  '&:hover': { bgcolor: '#1e293b', color: 'white' },
                  '&.Mui-selected': {
                    bgcolor: 'secondary.dark',
                    '&:hover': { bgcolor: 'secondary.dark' },
                  },
                }}
              >
                <ListItemIcon sx={{ color: 'inherit', minWidth: 36 }}>
                  {item.icon}
                </ListItemIcon>
                <ListItemText
                  primary={item.label}
                  primaryTypographyProps={{ fontSize: '0.875rem', fontWeight: 500 }}
                />
              </ListItemButton>
            </ListItem>
          )
        })}
      </List>

      <Divider sx={{ borderColor: '#1e293b' }} />

      <Box px={2} py={2}>
        <Box display="flex" alignItems="center" gap={1.5}>
          <Avatar sx={{ width: 32, height: 32, bgcolor: 'primary.main', fontSize: '0.875rem' }}>
            {user?.full_name?.charAt(0) ?? 'U'}
          </Avatar>
          <Box overflow="hidden" flex={1}>
            <Typography variant="body2" fontWeight={600} color="white" noWrap lineHeight={1.3}>
              {user?.full_name ?? 'Guest'}
            </Typography>
            <Typography variant="caption" sx={{ color: '#94a3b8' }} noWrap display="block">
              Global Admin
            </Typography>
          </Box>
          <IconButton title="Sign out" aria-label="Sign out" sx={{ color: 'inherit' }} onClick={() => {
            clearAuth()
            navigate('/login', { replace: true })
          }}>
            <LogoutIcon fontSize="small" />
          </IconButton>
        </Box>
      </Box>
    </Box>
  )

  return (
    <Drawer
      variant={permanent ? 'permanent' : 'temporary'}
      open={permanent || open}
      onClose={onClose}
      ModalProps={{ keepMounted: true }}
      sx={{
        ...(permanent && { width: SIDEBAR_WIDTH, flexShrink: 0 }),
        '& .MuiDrawer-paper': {
          width: SIDEBAR_WIDTH,
          maxWidth: 'calc(100vw - 40px)',
          boxSizing: 'border-box',
          border: 'none',
          overflow: 'hidden',
          bgcolor: '#0f172a',
        },
      }}
    >
      {content}
    </Drawer>
  )
}
