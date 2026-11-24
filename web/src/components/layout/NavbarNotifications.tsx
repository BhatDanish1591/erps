import { useState } from 'react'
import { Alert, Badge, Box, IconButton, ListItemText, Menu, MenuItem, Tooltip, Typography } from '@mui/material'
import NotificationsNone from '@mui/icons-material/NotificationsNone'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { notificationsApi } from '@/api/notifications'
import { useAuthStore } from '@/store/authStore'

const UNREAD_LIMIT = 50

export function NavbarNotifications({ hubPath }: { hubPath?: string }) {
  const user = useAuthStore((state) => state.user)
  const token = useAuthStore((state) => state.access_token)
  const queryClient = useQueryClient()
  const [anchor, setAnchor] = useState<HTMLElement | null>(null)
  const canLoad = Boolean(user?.current_tenant_id && token)
  const queryKey = ['navbar-unread', user?.id, user?.current_tenant_id]
  const unread = useQuery({
    queryKey,
    queryFn: () => notificationsApi.listInApp(true),
    enabled: canLoad,
    staleTime: 30_000,
    refetchInterval: 60_000,
    retry: false,
  })
  const markRead = useMutation({
    mutationFn: notificationsApi.markAsRead,
    onSuccess: () => queryClient.invalidateQueries({ queryKey }),
  })
  const count = canLoad ? unread.data?.length ?? 0 : 0
  const countLabel = count >= UNREAD_LIMIT ? `${UNREAD_LIMIT} or more` : count
  const label = count ? `Notifications, ${countLabel} unread` : 'Notifications'

  return (
    <>
      <Tooltip title={label}>
        <IconButton
          id="navbar-notifications-button"
          aria-label={label}
          aria-haspopup="menu"
          aria-expanded={Boolean(anchor)}
          aria-controls={anchor ? 'navbar-notifications-menu' : undefined}
          onClick={(event) => {
            markRead.reset()
            setAnchor(event.currentTarget)
            if (canLoad) void unread.refetch()
          }}
          size="small"
          sx={{ width: 40, height: 40 }}
        >
          <Badge color="error" badgeContent={count >= UNREAD_LIMIT ? `${UNREAD_LIMIT}+` : count}>
            <NotificationsNone fontSize="small" />
          </Badge>
        </IconButton>
      </Tooltip>
      <Menu
        anchorEl={anchor}
        open={Boolean(anchor)}
        onClose={() => setAnchor(null)}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}
        transformOrigin={{ vertical: 'top', horizontal: 'right' }}
        MenuListProps={{ id: 'navbar-notifications-menu', 'aria-labelledby': 'navbar-notifications-button' }}
        PaperProps={{ sx: { mt: 1, width: 320, maxWidth: 'calc(100vw - 24px)', maxHeight: 'min(420px, 75dvh)' } }}
      >
        {!canLoad && <MenuItem disabled>Select an institution to see unread notifications</MenuItem>}
        {canLoad && unread.isPending && <MenuItem disabled>Loading notifications…</MenuItem>}
        {canLoad && unread.isError && <MenuItem onClick={() => void unread.refetch()}>Couldn’t load notifications. Retry</MenuItem>}
        {canLoad && unread.isSuccess && !count && <MenuItem disabled>No unread notifications</MenuItem>}
        {markRead.isError && <Box role="none" px={1.5} py={0.5}><Alert severity="error">Couldn’t mark the notification as read.</Alert></Box>}
        {canLoad && unread.data?.map((notification) => (
          <MenuItem
            key={notification.id}
            aria-label={`${notification.title}, mark as read`}
            disabled={markRead.isPending}
            onClick={() => markRead.mutate(notification.id)}
            sx={{ whiteSpace: 'normal', borderBottom: '1px solid', borderColor: 'divider' }}
          >
            <ListItemText
              primary={<Typography variant="body2" fontWeight={700}>{notification.title}</Typography>}
              secondary={notification.message}
            />
          </MenuItem>
        ))}
        {hubPath && <MenuItem component={Link} to={hubPath} onClick={() => setAnchor(null)}>Open notifications</MenuItem>}
      </Menu>
    </>
  )
}
