import { useState } from 'react'
import {
  Box,
  Card,
  CardContent,
  Typography,
  TextField,
  MenuItem,
  Button,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Chip,
  TablePagination,
  IconButton,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Drawer,
  Divider,
  CircularProgress,
} from '@mui/material'
import SearchIcon from '@mui/icons-material/Search'
import VisibilityIcon from '@mui/icons-material/Visibility'
import CheckCircleOutlineIcon from '@mui/icons-material/CheckCircleOutline'
import HighlightOffIcon from '@mui/icons-material/HighlightOff'
import PauseCircleOutlineIcon from '@mui/icons-material/PauseCircleOutline'
import PlayCircleOutlineIcon from '@mui/icons-material/PlayCircleOutline'
import CloseIcon from '@mui/icons-material/Close'
import AddIcon from '@mui/icons-material/Add'
import InstitutionRegistrationPage from '@/pages/onboarding/InstitutionRegistrationPage'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { superAdminApi, InstitutionItem } from '@/api/superAdmin'

export default function InstitutionsPage() {
  const queryClient = useQueryClient()
  const [addOpen, setAddOpen] = useState(false)
  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState('ALL')
  const [typeFilter, setTypeFilter] = useState('ALL')
  const [page, setPage] = useState(0)
  const [rowsPerPage, setRowsPerPage] = useState(10)

  // Drawer / Detail state
  const [selectedInstId, setSelectedInstId] = useState<string | null>(null)
  const [detailOpen, setDetailOpen] = useState(false)

  // Action Dialog state
  const [dialogAction, setDialogAction] = useState<{
    open: boolean
    inst: InstitutionItem | null
    newStatus: string
    reason: string
  }>({ open: false, inst: null, newStatus: '', reason: '' })

  // Query institutions
  const { data, isLoading, refetch } = useQuery({
    queryKey: ['superAdminInstitutions', search, statusFilter, typeFilter, page, rowsPerPage],
    queryFn: () =>
      superAdminApi.listInstitutions({
        search: search || undefined,
        status: statusFilter === 'ALL' ? undefined : statusFilter,
        institution_type: typeFilter === 'ALL' ? undefined : typeFilter,
        page: page + 1,
        size: rowsPerPage,
      }),
  })

  // Query selected institution detail
  const { data: detailData, isLoading: detailLoading } = useQuery({
    queryKey: ['institutionDetail', selectedInstId],
    queryFn: () => superAdminApi.getInstitutionDetail(selectedInstId!),
    enabled: !!selectedInstId && detailOpen,
  })

  // Query institution users
  const { data: usersData, isLoading: usersLoading } = useQuery({
    queryKey: ['institutionUsers', selectedInstId],
    queryFn: () => superAdminApi.listInstitutionUsers(selectedInstId!),
    enabled: !!selectedInstId && detailOpen,
  })

  // Status mutation
  const statusMutation = useMutation({
    mutationFn: ({ id, status, reason }: { id: string; status: string; reason?: string }) =>
      superAdminApi.updateInstitutionStatus(id, status, reason),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['superAdminInstitutions'] })
      queryClient.invalidateQueries({ queryKey: ['superAdminStats'] })
      queryClient.invalidateQueries({ queryKey: ['institutionDetail', selectedInstId] })
      setDialogAction({ open: false, inst: null, newStatus: '', reason: '' })
    },
  })

  const handleOpenAction = (inst: InstitutionItem, newStatus: string) => {
    setDialogAction({ open: true, inst, newStatus, reason: '' })
  }

  const handleConfirmAction = () => {
    if (!dialogAction.inst) return
    statusMutation.mutate({
      id: dialogAction.inst.id,
      status: dialogAction.newStatus,
      reason: dialogAction.reason,
    })
  }

  const handleViewDetail = (id: string) => {
    setSelectedInstId(id)
    setDetailOpen(true)
  }

  return (
    <Box>
      <Box mb={3} display="flex" justifyContent="space-between" alignItems="center" flexWrap="wrap" gap={2}>
        <Box>
          <Typography variant="h4" fontWeight={700}>
            Institution Management
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Manage onboarding, status lifecycle, and configurations for all schools and colleges
          </Typography>
        </Box>
        <Button onClick={() => setAddOpen(true)} variant="contained" startIcon={<AddIcon />} aria-haspopup="dialog">
          Add Institution
        </Button>
      </Box>

      <Dialog open={addOpen} onClose={() => setAddOpen(false)} aria-labelledby="add-institution-title" maxWidth="md" fullWidth>
        <DialogTitle id="add-institution-title">Add Institution</DialogTitle>
        <DialogContent dividers>
          {addOpen && <InstitutionRegistrationPage onClose={() => setAddOpen(false)} />}
        </DialogContent>
      </Dialog>

      {/* Filter and Search Bar */}
      <Card sx={{ mb: 3 }}>
        <CardContent>
          <Box display="flex" gap={2} flexWrap="wrap">
            <TextField
              size="small"
              placeholder="Search by name, slug, email..."
              value={search}
              onChange={(e) => {
                setSearch(e.target.value)
                setPage(0)
              }}
              sx={{ minWidth: 260, flex: 1 }}
              InputProps={{
                startAdornment: <SearchIcon fontSize="small" sx={{ mr: 1, color: 'text.secondary' }} />,
              }}
            />
            <TextField
              size="small"
              select
              label="Status"
              value={statusFilter}
              onChange={(e) => {
                setStatusFilter(e.target.value)
                setPage(0)
              }}
              sx={{ minWidth: 150 }}
            >
              <MenuItem value="ALL">All Statuses</MenuItem>
              <MenuItem value="PENDING">Pending</MenuItem>
              <MenuItem value="ACTIVE">Active</MenuItem>
              <MenuItem value="SUSPENDED">Suspended</MenuItem>
              <MenuItem value="REJECTED">Rejected</MenuItem>
              <MenuItem value="TRIAL">Trial</MenuItem>
            </TextField>
            <TextField
              size="small"
              select
              label="Type"
              value={typeFilter}
              onChange={(e) => {
                setTypeFilter(e.target.value)
                setPage(0)
              }}
              sx={{ minWidth: 150 }}
            >
              <MenuItem value="ALL">All Types</MenuItem>
              <MenuItem value="SCHOOL">School</MenuItem>
              <MenuItem value="COLLEGE">College</MenuItem>
            </TextField>
            <Button variant="outlined" onClick={() => refetch()}>
              Apply
            </Button>
          </Box>
        </CardContent>
      </Card>

      {/* Data Table */}
      <Card>
        <TableContainer component={Paper} elevation={0} sx={{ overflowX: 'auto', width: '100%' }}>
          <Table sx={{ minWidth: 700 }}>
            <TableHead sx={{ bgcolor: 'grey.50' }}>
              <TableRow>
                <TableCell>Institution Name</TableCell>
                <TableCell>Slug / Subdomain</TableCell>
                <TableCell>Type</TableCell>
                <TableCell>Status</TableCell>
                <TableCell>Location</TableCell>
                <TableCell>Created Date</TableCell>
                <TableCell align="right">Actions</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {isLoading ? (
                <TableRow>
                  <TableCell colSpan={7} align="center" sx={{ py: 4 }}>
                    <CircularProgress size={30} />
                  </TableCell>
                </TableRow>
              ) : data?.items.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={7} align="center" sx={{ py: 4 }}>
                    <Typography color="text.secondary">No institutions match the filter criteria.</Typography>
                  </TableCell>
                </TableRow>
              ) : (
                data?.items.map((inst) => (
                  <TableRow key={inst.id} hover>
                    <TableCell>
                      <Typography variant="body2" fontWeight={600}>
                        {inst.name}
                      </Typography>
                      <Typography variant="caption" color="text.secondary">
                        {inst.email || 'No email provided'}
                      </Typography>
                    </TableCell>
                    <TableCell>
                      <code>{inst.slug}</code>
                    </TableCell>
                    <TableCell>
                      <Chip label={inst.institution_type} size="small" variant="outlined" />
                    </TableCell>
                    <TableCell>
                      <Chip
                        label={inst.status}
                        size="small"
                        color={
                          inst.status === 'ACTIVE'
                            ? 'success'
                            : inst.status === 'PENDING'
                            ? 'warning'
                            : inst.status === 'SUSPENDED'
                            ? 'error'
                            : 'default'
                        }
                      />
                    </TableCell>
                    <TableCell>
                      <Typography variant="body2">
                        {[inst.city, inst.state, inst.country].filter(Boolean).join(', ') || '—'}
                      </Typography>
                    </TableCell>
                    <TableCell>
                      <Typography variant="caption" color="text.secondary">
                        {new Date(inst.created_at).toLocaleDateString()}
                      </Typography>
                    </TableCell>
                    <TableCell align="right">
                      <IconButton size="small" title="View details" onClick={() => handleViewDetail(inst.id)}>
                        <VisibilityIcon fontSize="small" />
                      </IconButton>

                      {inst.status === 'PENDING' && (
                        <>
                          <IconButton
                            size="small"
                            color="success"
                            title="Approve Institution"
                            onClick={() => handleOpenAction(inst, 'ACTIVE')}
                          >
                            <CheckCircleOutlineIcon fontSize="small" />
                          </IconButton>
                          <IconButton
                            size="small"
                            color="error"
                            title="Reject Institution"
                            onClick={() => handleOpenAction(inst, 'REJECTED')}
                          >
                            <HighlightOffIcon fontSize="small" />
                          </IconButton>
                        </>
                      )}

                      {inst.status === 'ACTIVE' && (
                        <IconButton
                          size="small"
                          color="warning"
                          title="Suspend Institution"
                          onClick={() => handleOpenAction(inst, 'SUSPENDED')}
                        >
                          <PauseCircleOutlineIcon fontSize="small" />
                        </IconButton>
                      )}

                      {inst.status === 'SUSPENDED' && (
                        <IconButton
                          size="small"
                          color="success"
                          title="Reactivate Institution"
                          onClick={() => handleOpenAction(inst, 'ACTIVE')}
                        >
                          <PlayCircleOutlineIcon fontSize="small" />
                        </IconButton>
                      )}
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
          rowsPerPageOptions={[5, 10, 25, 50]}
        />
      </Card>

      {/* Action Confirmation Dialog */}
      <Dialog open={dialogAction.open} onClose={() => setDialogAction({ ...dialogAction, open: false })} maxWidth="sm" fullWidth>
        <DialogTitle>
          {dialogAction.newStatus === 'ACTIVE'
            ? 'Approve / Reactivate Institution'
            : dialogAction.newStatus === 'SUSPENDED'
            ? 'Suspend Institution'
            : 'Reject Institution Application'}
        </DialogTitle>
        <DialogContent>
          <Typography variant="body2" mb={2}>
            Are you sure you want to change the status of <strong>{dialogAction.inst?.name}</strong> to{' '}
            <strong>{dialogAction.newStatus}</strong>?
          </Typography>
          <TextField
            fullWidth
            label="Reason / Notes for Audit Trail"
            multiline
            rows={3}
            size="small"
            value={dialogAction.reason}
            onChange={(e) => setDialogAction({ ...dialogAction, reason: e.target.value })}
            placeholder="e.g. Verification complete / Non-payment / Policy violation"
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDialogAction({ ...dialogAction, open: false })}>Cancel</Button>
          <Button
            variant="contained"
            color={
              dialogAction.newStatus === 'ACTIVE'
                ? 'success'
                : dialogAction.newStatus === 'SUSPENDED'
                ? 'warning'
                : 'error'
            }
            onClick={handleConfirmAction}
            disabled={statusMutation.isPending}
          >
            {statusMutation.isPending ? <CircularProgress size={20} /> : 'Confirm Update'}
          </Button>
        </DialogActions>
      </Dialog>

      {/* Institution Detail Drawer */}
      <Drawer anchor="right" open={detailOpen} onClose={() => setDetailOpen(false)}>
        <Box sx={{ width: { xs: 320, sm: 540 }, p: 3 }}>
          <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
            <Typography variant="h6" fontWeight={700}>
              Institution Profile
            </Typography>
            <IconButton onClick={() => setDetailOpen(false)}>
              <CloseIcon />
            </IconButton>
          </Box>

          <Divider sx={{ mb: 2 }} />

          {detailLoading || !detailData ? (
            <Box display="flex" justifyContent="center" py={5}>
              <CircularProgress />
            </Box>
          ) : (
            <Box>
              <Typography variant="h5" fontWeight={700} gutterBottom>
                {detailData.name}
              </Typography>
              <Box display="flex" gap={1} mb={2}>
                <Chip label={detailData.institution_type} size="small" />
                <Chip
                  label={detailData.status}
                  size="small"
                  color={detailData.status === 'ACTIVE' ? 'success' : 'warning'}
                />
                <Chip label={`Plan: ${detailData.current_plan || 'Starter'}`} size="small" variant="outlined" />
              </Box>

              <Typography variant="subtitle2" color="text.secondary" gutterBottom>
                Slug / Subdomain: <code>{detailData.slug}.edusaas.com</code>
              </Typography>
              <Typography variant="body2" gutterBottom>
                Email: {detailData.email || '—'}
              </Typography>
              <Typography variant="body2" gutterBottom>
                Phone: {detailData.phone || '—'}
              </Typography>
              <Typography variant="body2" gutterBottom>
                Location: {[detailData.address, detailData.city, detailData.state, detailData.country].filter(Boolean).join(', ') || '—'}
              </Typography>
              <Typography variant="body2" gutterBottom>
                Timezone: {detailData.timezone} · Currency: {detailData.currency}
              </Typography>
              <Typography variant="body2" gutterBottom>
                Registered: {new Date(detailData.created_at).toLocaleString()}
              </Typography>

              <Divider sx={{ my: 3 }} />

              <Typography variant="h6" fontWeight={600} mb={1}>
                Enrolled Users ({detailData.total_users})
              </Typography>

              {usersLoading ? (
                <CircularProgress size={24} />
              ) : (
                <TableContainer component={Paper} elevation={0} variant="outlined" sx={{ overflowX: 'auto', width: '100%' }}>
                  <Table size="small" sx={{ minWidth: 500 }}>
                    <TableHead sx={{ bgcolor: 'grey.50' }}>
                      <TableRow>
                        <TableCell>Name</TableCell>
                        <TableCell>Email</TableCell>
                        <TableCell>Role</TableCell>
                        <TableCell>Status</TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {usersData?.items.map((u) => (
                        <TableRow key={u.membership_id}>
                          <TableCell>{u.full_name}</TableCell>
                          <TableCell>{u.email}</TableCell>
                          <TableCell>
                            <Chip label={u.role_name} size="small" variant="outlined" />
                          </TableCell>
                          <TableCell>
                            <Chip label={u.status} size="small" color={u.status === 'ACTIVE' ? 'success' : 'default'} />
                          </TableCell>
                        </TableRow>
                      ))}
                      {usersData?.items.length === 0 && (
                        <TableRow>
                          <TableCell colSpan={4} align="center">
                            No users registered under this institution.
                          </TableCell>
                        </TableRow>
                      )}
                    </TableBody>
                  </Table>
                </TableContainer>
              )}
            </Box>
          )}
        </Box>
      </Drawer>
    </Box>
  )
}
