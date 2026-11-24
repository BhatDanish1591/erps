import type { ReactNode } from 'react'
import { Box, Typography } from '@mui/material'

interface PageHeaderProps {
  title: string
  description?: string
  icon?: ReactNode
  children?: ReactNode
}

export function PageHeader({ title, description, icon, children }: PageHeaderProps) {
  return (
    <Box component="header" sx={{
      display: 'flex',
      flexWrap: 'wrap',
      alignItems: 'center',
      justifyContent: 'space-between',
      gap: 2,
      py: 0.5,
      pb: 2.5,
      borderBottom: 1,
      borderColor: 'divider',
    }}>
      <Box sx={{ display: 'flex', alignItems: 'flex-start', gap: { xs: 1.25, sm: 1.75 }, minWidth: 0 }}>
        {icon && (
          <Box aria-hidden="true" sx={(theme) => ({
            bgcolor: theme.palette.action.selected,
            color: 'primary.main',
            borderRadius: 2,
            width: { xs: 38, sm: 44 },
            height: { xs: 38, sm: 44 },
            display: 'grid',
            placeItems: 'center',
            flexShrink: 0,
          })}>
            {icon}
          </Box>
        )}
        <Box>
          <Typography component="h1" variant="h4">{title}</Typography>
          {description && (
            <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5, maxWidth: '66ch' }}>
              {description}
            </Typography>
          )}
        </Box>
      </Box>
      {children && (
        <Box sx={{
          display: 'flex',
          flexWrap: 'wrap',
          alignItems: 'center',
          width: { xs: '100%', sm: 'auto' },
          '& > .MuiBox-root, & > .MuiStack-root': { flexWrap: 'wrap' },
        }}>
          {children}
        </Box>
      )}
    </Box>
  )
}
