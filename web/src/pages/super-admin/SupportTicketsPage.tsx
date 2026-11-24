import { useState } from 'react'
import {
  Box,
  Card,
  Typography,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Chip,
  IconButton,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  TextField,
  MenuItem,
  CircularProgress,
  Divider,
  FormControlLabel,
  Switch,
} from '@mui/material'
import QuestionAnswerIcon from '@mui/icons-material/QuestionAnswer'
import SendIcon from '@mui/icons-material/Send'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { superAdminApi, SupportTicketItem } from '@/api/superAdmin'

export default function SupportTicketsPage() {
  const queryClient = useQueryClient()
  const [statusFilter, setStatusFilter] = useState('ALL')
  const [activeTicket, setActiveTicket] = useState<SupportTicketItem | null>(null)
  const [replyMessage, setReplyMessage] = useState('')
  const [isInternal, setIsInternal] = useState(false)

  const { data: tickets, isLoading } = useQuery({
    queryKey: ['superAdminTickets', statusFilter],
    queryFn: () => superAdminApi.listTickets(statusFilter === 'ALL' ? undefined : statusFilter),
  })

  const replyMutation = useMutation({
    mutationFn: ({ id, message, isInternal }: { id: string; message: string; isInternal: boolean }) =>
      superAdminApi.replyTicket(id, message, isInternal),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['superAdminTickets'] })
      setReplyMessage('')
      setActiveTicket(null)
    },
  })

  const statusMutation = useMutation({
    mutationFn: ({ id, status }: { id: string; status: string }) =>
      superAdminApi.updateTicketStatus(id, status),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['superAdminTickets'] })
      setActiveTicket(null)
    },
  })

  const handleSendReply = () => {
    if (!activeTicket || !replyMessage.trim()) return
    replyMutation.mutate({ id: activeTicket.id, message: replyMessage, isInternal })
  }

  return (
    <Box>
      <Box mb={4} display="flex" justifyContent="space-between" alignItems="center">
        <Box>
          <Typography variant="h4" fontWeight={700}>
            Support & Inquiry Desk
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Resolve incoming support requests, technical issues, and billing questions from tenant administrators
          </Typography>
        </Box>
        <TextField
          select
          size="small"
          label="Filter Status"
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          sx={{ minWidth: 160 }}
        >
          <MenuItem value="ALL">All Tickets</MenuItem>
          <MenuItem value="OPEN">Open</MenuItem>
          <MenuItem value="IN_PROGRESS">In Progress</MenuItem>
          <MenuItem value="RESOLVED">Resolved</MenuItem>
          <MenuItem value="CLOSED">Closed</MenuItem>
        </TextField>
      </Box>

      <Card>
        <TableContainer component={Paper} elevation={0} sx={{ overflowX: 'auto', width: '100%' }}>
          <Table sx={{ minWidth: 650 }}>
            <TableHead sx={{ bgcolor: 'grey.50' }}>
              <TableRow>
                <TableCell>Ticket ID</TableCell>
                <TableCell>Institution / Requester</TableCell>
                <TableCell>Subject</TableCell>
                <TableCell>Category</TableCell>
                <TableCell>Priority</TableCell>
                <TableCell>Status</TableCell>
                <TableCell>Created</TableCell>
                <TableCell align="right">Action</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {isLoading ? (
                <TableRow>
                  <TableCell colSpan={8} align="center" sx={{ py: 4 }}>
                    <CircularProgress size={28} />
                  </TableCell>
                </TableRow>
              ) : tickets?.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={8} align="center" sx={{ py: 4 }}>
                    <Typography color="text.secondary">No support tickets match the selected status.</Typography>
                  </TableCell>
                </TableRow>
              ) : (
                tickets?.map((t) => (
                  <TableRow key={t.id} hover>
                    <TableCell>
                      <code>{t.ticket_number}</code>
                    </TableCell>
                    <TableCell>
                      <Typography variant="body2" fontWeight={600}>
                        {t.tenant_name || 'Platform User'}
                      </Typography>
                      <Typography variant="caption" color="text.secondary">
                        {t.user_name} ({t.user_email})
                      </Typography>
                    </TableCell>
                    <TableCell>
                      <Typography variant="body2" fontWeight={500}>
                        {t.subject}
                      </Typography>
                    </TableCell>
                    <TableCell>
                      <Chip label={t.category} size="small" variant="outlined" />
                    </TableCell>
                    <TableCell>
                      <Chip
                        label={t.priority}
                        size="small"
                        color={
                          t.priority === 'URGENT'
                            ? 'error'
                            : t.priority === 'HIGH'
                            ? 'warning'
                            : 'default'
                        }
                      />
                    </TableCell>
                    <TableCell>
                      <Chip
                        label={t.status}
                        size="small"
                        color={
                          t.status === 'OPEN'
                            ? 'error'
                            : t.status === 'IN_PROGRESS'
                            ? 'info'
                            : t.status === 'RESOLVED'
                            ? 'success'
                            : 'default'
                        }
                      />
                    </TableCell>
                    <TableCell>
                      <Typography variant="caption" color="text.secondary">
                        {new Date(t.created_at).toLocaleDateString()}
                      </Typography>
                    </TableCell>
                    <TableCell align="right">
                      <IconButton size="small" color="primary" onClick={() => setActiveTicket(t)}>
                        <QuestionAnswerIcon fontSize="small" />
                      </IconButton>
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </TableContainer>
      </Card>

      {/* Ticket Conversation & Status Dialog */}
      <Dialog open={!!activeTicket} onClose={() => setActiveTicket(null)} maxWidth="md" fullWidth>
        <DialogTitle>
          <Box display="flex" justifyContent="space-between" alignItems="center">
            <Box>
              <Typography variant="h6" fontWeight={700}>
                {activeTicket?.subject}
              </Typography>
              <Typography variant="caption" color="text.secondary">
                {activeTicket?.ticket_number} · From: {activeTicket?.user_name} ({activeTicket?.tenant_name})
              </Typography>
            </Box>
            <Box display="flex" gap={1}>
              <Button
                size="small"
                variant="outlined"
                color="info"
                onClick={() => activeTicket && statusMutation.mutate({ id: activeTicket.id, status: 'IN_PROGRESS' })}
              >
                Mark In Progress
              </Button>
              <Button
                size="small"
                variant="contained"
                color="success"
                onClick={() => activeTicket && statusMutation.mutate({ id: activeTicket.id, status: 'RESOLVED' })}
              >
                Resolve Ticket
              </Button>
            </Box>
          </Box>
        </DialogTitle>
        <DialogContent dividers>
          <Box mb={3} p={2} bgcolor="#f8fafc" borderRadius={2}>
            <Typography variant="caption" fontWeight={600} color="text.secondary" display="block" mb={0.5}>
              ORIGINAL INQUIRY DESCRIPTION:
            </Typography>
            <Typography variant="body2">{activeTicket?.description}</Typography>
          </Box>

          <Typography variant="subtitle2" fontWeight={600} mb={1.5}>
            Response Thread ({activeTicket?.replies?.length || 0})
          </Typography>

          <Box display="flex" flexDirection="column" gap={1.5} mb={3}>
            {activeTicket?.replies?.map((rep) => (
              <Paper
                key={rep.id}
                variant="outlined"
                sx={{
                  p: 2,
                  bgcolor: rep.is_internal ? '#fef3c7' : 'white',
                  borderColor: rep.is_internal ? '#fde68a' : '#e2e8f0',
                }}
              >
                <Box display="flex" justifyContent="space-between" alignItems="center" mb={0.5}>
                  <Box display="flex" alignItems="center" gap={1}>
                    <Typography variant="body2" fontWeight={600}>
                      {rep.user_name}
                    </Typography>
                    {rep.is_internal && <Chip label="Internal Note" size="small" color="warning" />}
                  </Box>
                  <Typography variant="caption" color="text.secondary">
                    {new Date(rep.created_at).toLocaleString()}
                  </Typography>
                </Box>
                <Typography variant="body2">{rep.message}</Typography>
              </Paper>
            ))}
            {(!activeTicket?.replies || activeTicket.replies.length === 0) && (
              <Typography variant="body2" color="text.secondary">
                No replies posted yet. Compose a reply below.
              </Typography>
            )}
          </Box>

          <Divider sx={{ my: 2 }} />

          <Typography variant="subtitle2" fontWeight={600} mb={1}>
            Post Staff Reply or Internal Note
          </Typography>
          <TextField
            multiline
            rows={3}
            fullWidth
            placeholder="Type your response to the institution administrator..."
            value={replyMessage}
            onChange={(e) => setReplyMessage(e.target.value)}
          />
          <FormControlLabel
            control={
              <Switch
                checked={isInternal}
                onChange={(e) => setIsInternal(e.target.checked)}
                color="warning"
              />
            }
            label="Internal Staff Note (Hidden from tenant user)"
            sx={{ mt: 1 }}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setActiveTicket(null)}>Close</Button>
          <Button
            variant="contained"
            endIcon={<SendIcon />}
            onClick={handleSendReply}
            disabled={!replyMessage.trim() || replyMutation.isPending}
          >
            {replyMutation.isPending ? <CircularProgress size={20} /> : 'Send Reply'}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  )
}
