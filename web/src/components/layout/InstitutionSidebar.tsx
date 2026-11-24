import { useState } from 'react'
import {
  Accordion, AccordionDetails, AccordionSummary, Box, Drawer, IconButton, List, ListItemButton,
  ListItemIcon, ListItemText, Typography,
} from '@mui/material'
import Close from '@mui/icons-material/Close'
import ExpandMore from '@mui/icons-material/ExpandMore'
import { alpha } from '@mui/material/styles'
import { Link, useLocation } from 'react-router-dom'
import { getSubmenuIcon, isModuleActive, isSubmenuItemActive } from './navbarModules'
import type { NavbarModule } from './navbarModules'

export const INSTITUTION_SIDEBAR_ID = 'institution-navigation'
const SIDEBAR_WIDTH = 264

export function InstitutionSidebar({ modules, permanent, open, onClose }: {
  modules: NavbarModule[]
  permanent: boolean
  open: boolean
  onClose: () => void
}) {
  const { pathname, search, key } = useLocation()
  const [selection, setSelection] = useState<{ route: string; module: string | null }>()
  const expanded = selection?.route === key
    ? selection.module
    : modules.find((module) => isModuleActive(module, pathname))?.id

  return (
    <Drawer
      variant={permanent ? 'permanent' : 'temporary'}
      open={permanent || open}
      onClose={onClose}
      ModalProps={{ keepMounted: true }}
      sx={permanent ? {
        flexShrink: 0, width: SIDEBAR_WIDTH, position: 'sticky', top: 61, alignSelf: 'flex-start',
      } : undefined}
      PaperProps={{ sx: {
        width: permanent ? SIDEBAR_WIDTH : 310,
        maxWidth: 'calc(100vw - 32px)',
        bgcolor: 'background.paper',
        ...(permanent && { position: 'relative', height: 'calc(100dvh - 61px)', borderColor: 'divider' }),
      } }}
    >
      <Box id={INSTITUTION_SIDEBAR_ID} component="nav" aria-label="Main navigation" sx={{ minHeight: 0, display: 'flex', flexDirection: 'column', height: '100%' }}>
        <Box sx={{
          position: 'sticky', top: 0, zIndex: 1, bgcolor: 'background.paper', display: 'flex',
          alignItems: 'center', justifyContent: 'space-between', py: 1.25, px: 2, borderBottom: 1, borderColor: 'divider',
        }}>
          <Typography variant="subtitle2" color="text.secondary" fontWeight={700}>Navigation</Typography>
          {!permanent && <IconButton aria-label="Close navigation" onClick={onClose}><Close /></IconButton>}
        </Box>
        <Box sx={{ px: 1.25, py: 1, flex: 1, overflowY: 'auto', overscrollBehavior: 'contain' }}>
          {modules.map((module) => {
            const active = isModuleActive(module, pathname)
            const Icon = module.icon
            return (
              <Accordion
                key={module.id}
                expanded={expanded === module.id}
                onChange={(_, next) => setSelection({ route: key, module: next ? module.id : null })}
                disableGutters
                elevation={0}
                slotProps={{ transition: { unmountOnExit: true } }}
                sx={{ '&::before': { display: 'none' }, bgcolor: 'transparent', mb: 0.35 }}
              >
                <AccordionSummary
                  id={`sidebar-${module.id}`}
                  aria-controls={`sidebar-${module.id}-items`}
                  expandIcon={<ExpandMore />}
                  sx={(theme) => ({
                    minHeight: { xs: 48, md: 44 }, borderRadius: 2,
                    color: active
                      ? theme.palette.primary[theme.palette.mode === 'dark' ? 'light' : 'dark']
                      : theme.palette.text.primary,
                    bgcolor: active ? alpha(theme.palette.primary.main, 0.10) : 'transparent',
                    '&:hover': { bgcolor: alpha(theme.palette.primary.main, active ? 0.14 : 0.06) },
                    '& .MuiAccordionSummary-content': { alignItems: 'center', gap: 1.25 },
                  })}
                >
                  <Icon fontSize="small" />
                  <Typography variant="body2" fontWeight={700}>{module.label}</Typography>
                </AccordionSummary>
                <AccordionDetails sx={{ p: 0 }}>
                  <List disablePadding sx={{ ml: 2.25, mt: 0.5, mb: 1, pl: 0.75, borderLeft: 1, borderColor: 'divider' }}>
                    {module.items.map((item) => {
                      const current = isSubmenuItemActive(module, item, pathname, search)
                      const ItemIcon = getSubmenuIcon(module, item)
                      const link = item.path ? { component: Link, to: item.path + (item.search ?? ''), onClick: onClose } : {}
                      return (
                        <ListItemButton
                          key={item.label}
                          {...link}
                          disabled={!item.path}
                          selected={current}
                          aria-current={current ? 'page' : undefined}
                          title={item.section}
                          sx={{
                            minHeight: 44, px: 1, py: 0.5, borderRadius: 1.5,
                            '&.Mui-selected': { color: 'primary.main', bgcolor: 'action.selected' },
                            '&.Mui-disabled': { opacity: 0.7 },
                          }}
                        >
                          <ListItemIcon sx={{ minWidth: 28, color: current ? 'inherit' : 'text.secondary' }}><ItemIcon sx={{ fontSize: 17 }} /></ListItemIcon>
                          <ListItemText primary={item.label} secondary={item.status} slotProps={{ primary: { fontWeight: current ? 700 : 500 }, secondary: { variant: 'caption' } }} />
                        </ListItemButton>
                      )
                    })}
                  </List>
                </AccordionDetails>
              </Accordion>
            )
          })}
        </Box>
      </Box>
    </Drawer>
  )
}
