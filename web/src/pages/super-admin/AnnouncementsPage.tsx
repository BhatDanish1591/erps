import { useState } from 'react'
import {
  Box,
  Card,
  CardContent,
  Typography,
  Button,
  Grid,
  Chip,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  MenuItem,
  CircularProgress,
  IconButton,
  Paper,
} from '@mui/material'
import CampaignIcon from '@mui/icons-material/Campaign'
import AddIcon from '@mui/icons-material/Add'
import DeleteOutlineIcon from '@mui/icons-material/DeleteOutline'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { superAdminApi } from '@/api/superAdmin'

export default function AnnouncementsPage() {
  const queryClient = useQueryClient()
  const [open, setOpen] = useState(false)
  const [title, setTitle] = useState('')
  const [content, setContent] = useState('')
  const [priority, setPriority] = useState('NORMAL')
  const [targetRole, setTargetRole] = useState('ALL')

  const { data: announcements, isLoading } = useQuery({
    queryKey: ['superAdminAnnouncements'],
    queryFn: superAdminApi.listAnnouncements,
  })

  const createMutation = useMutation({
    mutationFn: superAdminApi.createAnnouncement,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['superAdminAnnouncements'] })
      setOpen(false)
      setTitle('')
      setContent('')
    },
  })

  const deleteMutation = useMutation({
    mutationFn: superAdminApi.deleteAnnouncement,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['superAdminAnnouncements'] })
    },
  })

  const handlePublish = () => {
    createMutation.mutate({
      title,
      content,
      priority,
      target_role: targetRole === 'ALL' ? undefined : targetRole,
    })
  }

  return (
    <Box>
      <Box mb={4} display="flex" justifyContent="space-between" alignItems="center">
        <Box>
          <Typography variant="h4" fontWeight={700}>
            Global Announcements
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Broadcast platform updates, scheduled maintenance, and alerts to schools and colleges
          </Typography>
        </Box>
        <Button variant="contained" startIcon={<AddIcon />} onClick={() => setOpen(true)}>
          New Announcement
        </Button>
      </Box>

      {isLoading ? (
        <Box display="flex" justifyContent="center" py={5}>
          <CircularProgress />
        </Box>
      ) : (
        <Grid container spacing={2}>
          {announcements?.map((item) => (
            <Grid item xs={12} key={item.id}>
              <Paper variant="outlined" sx={{ p: 2.5, borderRadius: 2 }}>
                <Box display="flex" justifyContent="space-between" alignItems="flex-start" mb={1}>
                  <Box display="flex" alignItems="center" gap={1.5}>
                    <CampaignIcon color="primary" />
                    <Typography variant="h6" fontWeight={600}>
                      {item.title}
                    </Typography>
                    <Chip
                      label={item.priority}
                      size="small"
                      color={
                        item.priority === 'URGENT'
                          ? 'error'
                          : item.priority === 'HIGH'
                          ? 'warning'
                          : 'default'
                      }
                    />
                    <Chip
                      label={item.target_role ? `Role: ${item.target_role}` : 'Target: All Platform Users'}
                      size="small"
                      variant="outlined"
                    />
                  </Box>
                  <IconButton
                    size="small"
                    color="error"
                    onClick={() => deleteMutation.mutate(item.id)}
                    disabled={deleteMutation.isPending}
                  >
                    <DeleteOutlineIcon fontSize="small" />
                  </IconButton>
                </Box>
                <Typography variant="body1" color="text.primary" mb={1}>
                  {item.content}
                </Typography>
                <Typography variant="caption" color="text.secondary">
                  Published: {new Date(item.created_at).toLocaleString()}
                </Typography>
              </Paper>
            </Grid>
          ))}
          {announcements?.length === 0 && (
            <Grid item xs={12}>
              <Card>
                <CardContent sx={{ textAlign: 'center', py: 4 }}>
                  <Typography color="text.secondary">
                    No active platform announcements. Click "New Announcement" to publish one.
                  </Typography>
                </CardContent>
              </Card>
            </Grid>
          )}
        </Grid>
      )}

      {/* Create Announcement Dialog */}
      <Dialog open={open} onClose={() => setOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Broadcast Platform Announcement</DialogTitle>
        <DialogContent>
          <Box display="flex" flexDirection="column" gap={2} pt={1}>
            <TextField
              label="Announcement Title"
              size="small"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              fullWidth
              required
            />
            <Grid container spacing={2}>
              <Grid item xs={6}>
                <TextField
                  select
                  label="Priority Level"
                  size="small"
                  value={priority}
                  onChange={(e) => setPriority(e.target.value)}
                  fullWidth
                >
                  <MenuItem value="LOW">Low</MenuItem>
                  <MenuItem value="NORMAL">Normal</MenuItem>
                  <MenuItem value="HIGH">High</MenuItem>
                  <MenuItem value="URGENT">Urgent Alert</MenuItem>
                </TextField>
              </Grid>
              <Grid item xs={6}>
                <TextField
                  select
                  label="Target Audience"
                  size="small"
                  value={targetRole}
                  onChange={(e) => setTargetRole(e.target.value)}
                  fullWidth
                >
                  <MenuItem value="ALL">All Users</MenuItem>
                  <MenuItem value="INSTITUTION_ADMIN">Institution Admins</MenuItem>
                  <MenuItem value="TEACHER">Faculty / Teachers</MenuItem>
                  <MenuItem value="STUDENT">Students</MenuItem>
                  <MenuItem value="PARENT">Parents</MenuItem>
                </TextField>
              </Grid>
            </Grid>
            <TextField
              label="Message Body"
              multiline
              rows={4}
              value={content}
              onChange={(e) => setContent(e.target.value)}
              placeholder="Write the announcement details here..."
              fullWidth
              required
            />
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setOpen(false)}>Cancel</Button>
          <Button
            variant="contained"
            onClick={handlePublish}
            disabled={!title || !content || createMutation.isPending}
          >
            {createMutation.isPending ? <CircularProgress size={20} /> : 'Publish'}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  )
}
