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
  TablePagination,
  CircularProgress,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  IconButton,
} from '@mui/material'
import CodeIcon from '@mui/icons-material/Code'
import SecurityIcon from '@mui/icons-material/Security'
import { useQuery } from '@tanstack/react-query'
import { superAdminApi, AuditLogItem } from '@/api/superAdmin'

export default function AuditLogsPage() {
  const [page, setPage] = useState(0)
  const [rowsPerPage, setRowsPerPage] = useState(15)
  const [activeChanges, setActiveChanges] = useState<AuditLogItem | null>(null)

  const { data, isLoading } = useQuery({
    queryKey: ['superAdminAuditLogs', page, rowsPerPage],
    queryFn: () => superAdminApi.listAuditLogs({ page: page + 1, size: rowsPerPage }),
  })

  return (
    <Box>
      <Box mb={4} display="flex" justifyContent="space-between" alignItems="center">
        <Box>
          <Box display="flex" alignItems="center" gap={1.5} mb={0.5}>
            <SecurityIcon color="primary" sx={{ fontSize: 32 }} />
            <Typography variant="h4" fontWeight={700}>
              Platform Audit Trail
            </Typography>
          </Box>
          <Typography variant="body2" color="text.secondary">
            Immutable security ledger tracking administrative actions, status mutations, and platform configuration changes
          </Typography>
        </Box>
      </Box>

      <Card>
        <TableContainer component={Paper} elevation={0} sx={{ overflowX: 'auto', width: '100%' }}>
          <Table size="small" sx={{ minWidth: 650 }}>
            <TableHead sx={{ bgcolor: 'grey.50' }}>
              <TableRow>
                <TableCell>Timestamp</TableCell>
                <TableCell>Actor</TableCell>
                <TableCell>Action</TableCell>
                <TableCell>Entity Type</TableCell>
                <TableCell>Entity ID</TableCell>
                <TableCell>IP Address</TableCell>
                <TableCell align="right">Payload</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {isLoading ? (
                <TableRow>
                  <TableCell colSpan={7} align="center" sx={{ py: 4 }}>
                    <CircularProgress size={28} />
                  </TableCell>
                </TableRow>
              ) : data?.items.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={7} align="center" sx={{ py: 4 }}>
                    <Typography color="text.secondary">No audit logs recorded yet.</Typography>
                  </TableCell>
                </TableRow>
              ) : (
                data?.items.map((log) => (
                  <TableRow key={log.id} hover>
                    <TableCell>
                      <Typography variant="caption" color="text.secondary" noWrap>
                        {new Date(log.created_at).toLocaleString()}
                      </Typography>
                    </TableCell>
                    <TableCell>
                      <Typography variant="body2" fontWeight={600}>
                        {log.actor_email}
                      </Typography>
                    </TableCell>
                    <TableCell>
                      <Chip
                        label={log.action}
                        size="small"
                        color={
                          log.action.includes('SUSPEND') || log.action.includes('DELETE')
                            ? 'error'
                            : log.action.includes('ACTIVE') || log.action.includes('CREATE')
                            ? 'success'
                            : 'info'
                        }
                      />
                    </TableCell>
                    <TableCell>
                      <code>{log.entity_type}</code>
                    </TableCell>
                    <TableCell>
                      <Typography variant="caption">{log.entity_id || '—'}</Typography>
                    </TableCell>
                    <TableCell>
                      <Typography variant="caption" color="text.secondary">
                        {log.ip_address || 'Internal / CLI'}
                      </Typography>
                    </TableCell>
                    <TableCell align="right">
                      <IconButton size="small" onClick={() => setActiveChanges(log)}>
                        <CodeIcon fontSize="small" />
                      </IconButton>
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </TableContainer>

        <TablePagination
          component="div"
          count={data?.total || 0}
          page={page}
          onPageChange={(_, newPage) => setPage(newPage)}
          rowsPerPage={rowsPerPage}
          onRowsPerPageChange={(e) => {
            setRowsPerPage(parseInt(e.target.value, 10))
            setPage(0)
          }}
          rowsPerPageOptions={[10, 15, 25, 50]}
        />
      </Card>

      {/* JSON Changes Dialog */}
      <Dialog open={!!activeChanges} onClose={() => setActiveChanges(null)} maxWidth="sm" fullWidth>
        <DialogTitle>Audit Mutation Payload: {activeChanges?.action}</DialogTitle>
        <DialogContent>
          <Box
            component="pre"
            sx={{
              p: 2,
              bgcolor: '#0f172a',
              color: '#38bdf8',
              borderRadius: 2,
              overflow: 'auto',
              fontSize: '0.825rem',
            }}
          >
            {JSON.stringify(activeChanges?.changes, null, 2)}
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setActiveChanges(null)}>Close</Button>
        </DialogActions>
      </Dialog>
    </Box>
  )
}
