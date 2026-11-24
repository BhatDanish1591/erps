import { PageHeader } from '@/components/ui/PageHeader'
import { useState, useEffect } from 'react'
import {
  Box,
  Card,
  CardContent,
  Grid,
  Typography,
  Chip,
  Button,
  Tabs,
  Tab,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  Alert,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  MenuItem,
} from '@mui/material'
import ApartmentIcon from '@mui/icons-material/Apartment'
import HotelIcon from '@mui/icons-material/Hotel'
import HowToRegIcon from '@mui/icons-material/HowToReg'
import PeopleOutlineIcon from '@mui/icons-material/PeopleOutline'
import AddIcon from '@mui/icons-material/Add'

import {
  hostelApi,
  HostelBuilding,
  HostelRoom,
  HostelRoomAllocation,
  HostelAttendance,
  HostelVisitor,
  HostelMaintenanceRequest,
} from '../../api/hostel'

export default function HostelManagementPage() {
  const [tab, setTab] = useState(0)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)

  // Data
  const [buildings, setBuildings] = useState<HostelBuilding[]>([])
  const [rooms, setRooms] = useState<HostelRoom[]>([])
  const [allocations, setAllocations] = useState<HostelRoomAllocation[]>([])
  const [attendance, setAttendance] = useState<HostelAttendance[]>([])
  const [visitors, setVisitors] = useState<HostelVisitor[]>([])
  const [maintenance, setMaintenance] = useState<HostelMaintenanceRequest[]>([])

  // Modals
  const [openBuildingModal, setOpenBuildingModal] = useState(false)
  const [openRoomModal, setOpenRoomModal] = useState(false)
  const [openAllocModal, setOpenAllocModal] = useState(false)
  const [openAttendanceModal, setOpenAttendanceModal] = useState(false)
  const [openVisitorModal, setOpenVisitorModal] = useState(false)

  // Forms
  const [bldForm, setBldForm] = useState({
    name: '',
    code: '',
    hostel_type: 'BOYS' as 'BOYS' | 'GIRLS' | 'CO_ED',
    total_floors: 3,
    warden_name: '',
    warden_phone: '',
  })
  const [roomForm, setRoomForm] = useState({
    building_id: '',
    room_number: '',
    floor: 1,
    room_type: 'DOUBLE',
    is_ac: false,
    capacity: 2,
    rent_per_term: 35000,
  })
  const [allocForm, setAllocForm] = useState({
    building_id: '',
    room_id: '',
    student_id: '',
    bed_number: 'Bed-1',
    check_in_date: new Date().toISOString().split('T')[0],
    rent_amount: 35000,
  })
  const [attForm, setAttForm] = useState({
    building_id: '',
    student_id: '',
    attendance_date: new Date().toISOString().split('T')[0],
    status: 'PRESENT',
    in_time: '21:30:00',
    remarks: '',
  })
  const [visForm, setVisForm] = useState({
    building_id: '',
    student_id: '',
    visitor_name: '',
    relation: 'PARENT',
    phone: '',
    visit_date: new Date().toISOString().split('T')[0],
    in_time: new Date().toISOString(),
    purpose: 'Visiting ward',
  })

  const loadAll = async () => {
    try {
      const [bData, rData, aData, attData, vData, mData] = await Promise.all([
        hostelApi.listBuildings().catch(() => []),
        hostelApi.listRooms().catch(() => []),
        hostelApi.listAllocations().catch(() => []),
        hostelApi.listAttendance().catch(() => []),
        hostelApi.listVisitors().catch(() => []),
        hostelApi.listMaintenance().catch(() => []),
      ])
      setBuildings(bData)
      setRooms(rData)
      setAllocations(aData)
      setAttendance(attData)
      setVisitors(vData)
      setMaintenance(mData)
    } catch (err: any) {
      setError(err?.message || 'Failed to load hostel data')
    }
  }

  useEffect(() => {
    loadAll()
  }, [])

  const handleCreateBuilding = async () => {
    try {
      await hostelApi.createBuilding(bldForm)
      setSuccess('Hostel building created successfully')
      setOpenBuildingModal(false)
      loadAll()
    } catch (err: any) {
      setError(err?.response?.data?.error?.message || 'Failed to create building')
    }
  }

  const handleCreateRoom = async () => {
    try {
      await hostelApi.createRoom({
        ...roomForm,
        capacity: Number(roomForm.capacity),
        rent_per_term: Number(roomForm.rent_per_term),
      })
      setSuccess('Room added successfully')
      setOpenRoomModal(false)
      loadAll()
    } catch (err: any) {
      setError(err?.response?.data?.error?.message || 'Failed to add room')
    }
  }

  const handleAllocate = async () => {
    try {
      await hostelApi.allocateRoom({
        ...allocForm,
        rent_amount: Number(allocForm.rent_amount),
      })
      setSuccess('Room allocated to student successfully')
      setOpenAllocModal(false)
      loadAll()
    } catch (err: any) {
      setError(err?.response?.data?.error?.message || 'Failed to allocate room')
    }
  }

  const handleAttendance = async () => {
    try {
      await hostelApi.recordAttendance(attForm)
      setSuccess('Night curfew attendance recorded')
      setOpenAttendanceModal(false)
      loadAll()
    } catch (err: any) {
      setError(err?.response?.data?.error?.message || 'Failed to record attendance')
    }
  }

  const handleVisitor = async () => {
    try {
      await hostelApi.logVisitor(visForm)
      setSuccess('Visitor logged successfully')
      setOpenVisitorModal(false)
      loadAll()
    } catch (err: any) {
      setError(err?.response?.data?.error?.message || 'Failed to log visitor')
    }
  }

  return (
    <Box sx={{ maxWidth: 1400, mx: 'auto' }}>
      {/* Header */}
      <Box sx={{ mb: 3 }}>
        <PageHeader
          title="Hostel"
          description="Manage buildings, rooms, student allocations, and visitor records."
          icon={<ApartmentIcon />}
        >
          <Box sx={{ display: 'flex', gap: 1.5 }}>
            <Button variant="outlined" startIcon={<AddIcon />} onClick={() => setOpenBuildingModal(true)}>
              Add Building
            </Button>
            <Button variant="outlined" startIcon={<AddIcon />} onClick={() => setOpenRoomModal(true)}>
              Add Room
            </Button>
            <Button variant="contained" startIcon={<HotelIcon />} onClick={() => setOpenAllocModal(true)}>
              Allocate Room
            </Button>
          </Box>
        </PageHeader>
      </Box>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}
      {success && (
        <Alert severity="success" sx={{ mb: 2 }} onClose={() => setSuccess(null)}>
          {success}
        </Alert>
      )}

      {/* KPI Cards */}
      <Grid container spacing={2} sx={{ mb: 3 }}>
        <Grid item xs={12} sm={3}>
          <Card>
            <CardContent>
              <Typography variant="body2" color="text.secondary">Hostel Buildings</Typography>
              <Typography variant="h4" fontWeight="bold">{buildings.length}</Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={3}>
          <Card>
            <CardContent>
              <Typography variant="body2" color="text.secondary">Total Rooms</Typography>
              <Typography variant="h4" fontWeight="bold">{rooms.length}</Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={3}>
          <Card>
            <CardContent>
              <Typography variant="body2" color="primary.main">Active Residents</Typography>
              <Typography variant="h4" fontWeight="bold" color="primary.main">
                {allocations.filter((a) => a.status === 'ACTIVE').length}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={3}>
          <Card>
            <CardContent>
              <Typography variant="body2" color="warning.main">Pending Maintenance</Typography>
              <Typography variant="h4" fontWeight="bold" color="warning.main">
                {maintenance.filter((m) => m.status === 'PENDING').length}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Tabs */}
      <Tabs value={tab} onChange={(_, val) => setTab(val)} sx={{ borderBottom: 1, borderColor: 'divider', mb: 3 }}>
        <Tab icon={<ApartmentIcon />} iconPosition="start" label="Buildings & Rooms" />
        <Tab icon={<HotelIcon />} iconPosition="start" label="Resident Allocations" />
        <Tab icon={<HowToRegIcon />} iconPosition="start" label="Curfew Attendance" />
        <Tab icon={<PeopleOutlineIcon />} iconPosition="start" label="Visitors & Maintenance" />
      </Tabs>

      {/* Tab 0: Buildings & Rooms */}
      {tab === 0 && (
        <TableContainer component={Paper} sx={{ overflowX: 'auto', width: '100%' }}>
          <Table sx={{ minWidth: 600 }}>
            <TableHead>
              <TableRow sx={{ backgroundColor: 'action.hover' }}>
                <TableCell>Building Name</TableCell>
                <TableCell>Type</TableCell>
                <TableCell>Room No</TableCell>
                <TableCell>Floor</TableCell>
                <TableCell>Type / AC</TableCell>
                <TableCell>Capacity</TableCell>
                <TableCell>Occupied / Available</TableCell>
                <TableCell>Rent / Term</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {rooms.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={8} align="center" sx={{ py: 3, color: 'text.secondary' }}>
                    No rooms configured yet. Add hostel buildings and rooms to begin.
                  </TableCell>
                </TableRow>
              ) : (
                rooms.map((r) => (
                  <TableRow key={r.id} hover>
                    <TableCell sx={{ fontWeight: 'medium' }}>{r.building_name || '-'}</TableCell>
                    <TableCell>
                      <Chip size="small" label={r.room_type} />
                    </TableCell>
                    <TableCell sx={{ fontWeight: 'bold' }}>Room {r.room_number}</TableCell>
                    <TableCell>Floor {r.floor}</TableCell>
                    <TableCell>{r.is_ac ? 'AC' : 'Non-AC'}</TableCell>
                    <TableCell>{r.capacity} beds</TableCell>
                    <TableCell>
                      <Chip
                        size="small"
                        color={r.occupied_beds < r.capacity ? 'success' : 'default'}
                        label={`${r.occupied_beds} occupied (${r.available_beds ?? (r.capacity - r.occupied_beds)} free)`}
                      />
                    </TableCell>
                    <TableCell>₹{r.rent_per_term}</TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </TableContainer>
      )}

      {/* Tab 1: Allocations */}
      {tab === 1 && (
        <TableContainer component={Paper} sx={{ overflowX: 'auto', width: '100%' }}>
          <Table sx={{ minWidth: 600 }}>
            <TableHead>
              <TableRow sx={{ backgroundColor: 'action.hover' }}>
                <TableCell>Student Name</TableCell>
                <TableCell>Admission No</TableCell>
                <TableCell>Building</TableCell>
                <TableCell>Room / Bed</TableCell>
                <TableCell>Check-in Date</TableCell>
                <TableCell>Rent Amount</TableCell>
                <TableCell>Status</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {allocations.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={7} align="center" sx={{ py: 3, color: 'text.secondary' }}>
                    No students currently allocated to hostel rooms.
                  </TableCell>
                </TableRow>
              ) : (
                allocations.map((a) => (
                  <TableRow key={a.id} hover>
                    <TableCell sx={{ fontWeight: 'medium' }}>{a.student_name || '-'}</TableCell>
                    <TableCell>{a.admission_number || '-'}</TableCell>
                    <TableCell>{a.building_name || '-'}</TableCell>
                    <TableCell>
                      Room {a.room_number || '-'} ({a.bed_number})
                    </TableCell>
                    <TableCell>{a.check_in_date}</TableCell>
                    <TableCell>₹{a.rent_amount}</TableCell>
                    <TableCell>
                      <Chip size="small" color={a.status === 'ACTIVE' ? 'success' : 'default'} label={a.status} />
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </TableContainer>
      )}

      {/* Tab 2: Curfew Attendance */}
      {tab === 2 && (
        <Box>
          <Box sx={{ display: 'flex', justifyContent: 'flex-end', mb: 2 }}>
            <Button variant="contained" startIcon={<AddIcon />} onClick={() => setOpenAttendanceModal(true)}>
              Mark Night Curfew Roll Call
            </Button>
          </Box>
          <TableContainer component={Paper} sx={{ overflowX: 'auto', width: '100%' }}>
            <Table sx={{ minWidth: 600 }}>
              <TableHead>
                <TableRow sx={{ backgroundColor: 'action.hover' }}>
                  <TableCell>Student Name</TableCell>
                  <TableCell>Date</TableCell>
                  <TableCell>Status</TableCell>
                  <TableCell>In-Time</TableCell>
                  <TableCell>Remarks</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {attendance.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={5} align="center" sx={{ py: 3, color: 'text.secondary' }}>
                      No night curfew attendance logs recorded yet.
                    </TableCell>
                  </TableRow>
                ) : (
                  attendance.map((att) => (
                    <TableRow key={att.id} hover>
                      <TableCell sx={{ fontWeight: 'medium' }}>{att.student_name || '-'}</TableCell>
                      <TableCell>{att.attendance_date}</TableCell>
                      <TableCell>
                        <Chip
                          size="small"
                          color={
                            att.status === 'PRESENT'
                              ? 'success'
                              : att.status === 'NIGHT_OUT'
                              ? 'warning'
                              : 'error'
                          }
                          label={att.status}
                        />
                      </TableCell>
                      <TableCell>{att.in_time || '-'}</TableCell>
                      <TableCell>{att.remarks || '-'}</TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          </TableContainer>
        </Box>
      )}

      {/* Tab 3: Visitors & Maintenance */}
      {tab === 3 && (
        <Box>
          <Box sx={{ display: 'flex', justifyContent: 'flex-end', gap: 2, mb: 2 }}>
            <Button variant="outlined" startIcon={<AddIcon />} onClick={() => setOpenVisitorModal(true)}>
              Log Visitor
            </Button>
          </Box>
          <TableContainer component={Paper} sx={{ overflowX: 'auto', width: '100%' }}>
            <Table sx={{ minWidth: 600 }}>
              <TableHead>
                <TableRow sx={{ backgroundColor: 'action.hover' }}>
                  <TableCell>Visitor Name</TableCell>
                  <TableCell>Relation</TableCell>
                  <TableCell>Resident Student</TableCell>
                  <TableCell>Contact Phone</TableCell>
                  <TableCell>Visit Date & Time</TableCell>
                  <TableCell>Purpose</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {visitors.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={6} align="center" sx={{ py: 3, color: 'text.secondary' }}>
                      No visitor records logged.
                    </TableCell>
                  </TableRow>
                ) : (
                  visitors.map((v) => (
                    <TableRow key={v.id} hover>
                      <TableCell sx={{ fontWeight: 'medium' }}>{v.visitor_name}</TableCell>
                      <TableCell>{v.relation}</TableCell>
                      <TableCell>{v.student_name || '-'}</TableCell>
                      <TableCell>{v.phone}</TableCell>
                      <TableCell>{new Date(v.in_time).toLocaleString()}</TableCell>
                      <TableCell>{v.purpose}</TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          </TableContainer>
        </Box>
      )}

      {/* Dialog: Add Building */}
      <Dialog open={openBuildingModal} onClose={() => setOpenBuildingModal(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Add Hostel Building</DialogTitle>
        <DialogContent sx={{ display: 'flex', flexDirection: 'column', gap: 2, pt: 2 }}>
          <TextField
            label="Building Name"
            value={bldForm.name}
            onChange={(e) => setBldForm({ ...bldForm, name: e.target.value })}
            placeholder="e.g. Himalaya Boys Hostel"
            fullWidth
            required
          />
          <TextField
            label="Building Code"
            value={bldForm.code}
            onChange={(e) => setBldForm({ ...bldForm, code: e.target.value.toUpperCase() })}
            placeholder="e.g. HIM-01"
            fullWidth
            required
          />
          <TextField
            select
            label="Hostel Type"
            value={bldForm.hostel_type}
            onChange={(e: any) => setBldForm({ ...bldForm, hostel_type: e.target.value })}
            fullWidth
          >
            <MenuItem value="BOYS">Boys Hostel</MenuItem>
            <MenuItem value="GIRLS">Girls Hostel</MenuItem>
            <MenuItem value="CO_ED">Co-Ed Accommodation</MenuItem>
          </TextField>
          <TextField
            label="Warden Name"
            value={bldForm.warden_name}
            onChange={(e) => setBldForm({ ...bldForm, warden_name: e.target.value })}
            fullWidth
            required
          />
          <TextField
            label="Warden Phone"
            value={bldForm.warden_phone}
            onChange={(e) => setBldForm({ ...bldForm, warden_phone: e.target.value })}
            fullWidth
            required
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setOpenBuildingModal(false)}>Cancel</Button>
          <Button variant="contained" onClick={handleCreateBuilding} disabled={!bldForm.name || !bldForm.code}>
            Save Building
          </Button>
        </DialogActions>
      </Dialog>

      {/* Dialog: Add Room */}
      <Dialog open={openRoomModal} onClose={() => setOpenRoomModal(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Add Hostel Room</DialogTitle>
        <DialogContent sx={{ display: 'flex', flexDirection: 'column', gap: 2, pt: 2 }}>
          <TextField
            select
            label="Select Building"
            value={roomForm.building_id}
            onChange={(e) => setRoomForm({ ...roomForm, building_id: e.target.value })}
            fullWidth
            required
          >
            {buildings.map((b) => (
              <MenuItem key={b.id} value={b.id}>
                {b.name}
              </MenuItem>
            ))}
          </TextField>
          <TextField
            label="Room Number"
            value={roomForm.room_number}
            onChange={(e) => setRoomForm({ ...roomForm, room_number: e.target.value })}
            placeholder="e.g. 201"
            fullWidth
            required
          />
          <TextField
            label="Floor"
            type="number"
            value={roomForm.floor}
            onChange={(e) => setRoomForm({ ...roomForm, floor: Number(e.target.value) })}
            fullWidth
          />
          <TextField
            select
            label="Room Sharing Type"
            value={roomForm.room_type}
            onChange={(e) => setRoomForm({ ...roomForm, room_type: e.target.value })}
            fullWidth
          >
            <MenuItem value="SINGLE">Single Room</MenuItem>
            <MenuItem value="DOUBLE">Double Sharing</MenuItem>
            <MenuItem value="TRIPLE">Triple Sharing</MenuItem>
            <MenuItem value="FOUR_SHARING">Four Sharing</MenuItem>
            <MenuItem value="DORMITORY">Dormitory</MenuItem>
          </TextField>
          <TextField
            label="Bed Capacity"
            type="number"
            value={roomForm.capacity}
            onChange={(e) => setRoomForm({ ...roomForm, capacity: Number(e.target.value) })}
            fullWidth
          />
          <TextField
            label="Rent Per Term (₹)"
            type="number"
            value={roomForm.rent_per_term}
            onChange={(e) => setRoomForm({ ...roomForm, rent_per_term: Number(e.target.value) })}
            fullWidth
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setOpenRoomModal(false)}>Cancel</Button>
          <Button
            variant="contained"
            onClick={handleCreateRoom}
            disabled={!roomForm.building_id || !roomForm.room_number}
          >
            Save Room
          </Button>
        </DialogActions>
      </Dialog>

      {/* Dialog: Allocate Room */}
      <Dialog open={openAllocModal} onClose={() => setOpenAllocModal(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Allocate Room to Student</DialogTitle>
        <DialogContent sx={{ display: 'flex', flexDirection: 'column', gap: 2, pt: 2 }}>
          <TextField
            select
            label="Select Building"
            value={allocForm.building_id}
            onChange={(e) => setAllocForm({ ...allocForm, building_id: e.target.value })}
            fullWidth
            required
          >
            {buildings.map((b) => (
              <MenuItem key={b.id} value={b.id}>
                {b.name}
              </MenuItem>
            ))}
          </TextField>
          <TextField
            label="Room ID (UUID)"
            value={allocForm.room_id}
            onChange={(e) => setAllocForm({ ...allocForm, room_id: e.target.value })}
            fullWidth
            required
          />
          <TextField
            label="Student ID (UUID)"
            value={allocForm.student_id}
            onChange={(e) => setAllocForm({ ...allocForm, student_id: e.target.value })}
            fullWidth
            required
          />
          <TextField
            label="Bed Number / Label"
            value={allocForm.bed_number}
            onChange={(e) => setAllocForm({ ...allocForm, bed_number: e.target.value })}
            fullWidth
          />
          <TextField
            label="Rent Amount (₹)"
            type="number"
            value={allocForm.rent_amount}
            onChange={(e) => setAllocForm({ ...allocForm, rent_amount: Number(e.target.value) })}
            fullWidth
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setOpenAllocModal(false)}>Cancel</Button>
          <Button variant="contained" onClick={handleAllocate} disabled={!allocForm.room_id || !allocForm.student_id}>
            Confirm Allocation
          </Button>
        </DialogActions>
      </Dialog>

      {/* Dialog: Curfew Attendance */}
      <Dialog open={openAttendanceModal} onClose={() => setOpenAttendanceModal(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Record Night Curfew Roll Call</DialogTitle>
        <DialogContent sx={{ display: 'flex', flexDirection: 'column', gap: 2, pt: 2 }}>
          <TextField
            select
            label="Building"
            value={attForm.building_id}
            onChange={(e) => setAttForm({ ...attForm, building_id: e.target.value })}
            fullWidth
            required
          >
            {buildings.map((b) => (
              <MenuItem key={b.id} value={b.id}>
                {b.name}
              </MenuItem>
            ))}
          </TextField>
          <TextField
            label="Student ID (UUID)"
            value={attForm.student_id}
            onChange={(e) => setAttForm({ ...attForm, student_id: e.target.value })}
            fullWidth
            required
          />
          <TextField
            select
            label="Curfew Status"
            value={attForm.status}
            onChange={(e) => setAttForm({ ...attForm, status: e.target.value })}
            fullWidth
          >
            <MenuItem value="PRESENT">Present In Hostel</MenuItem>
            <MenuItem value="NIGHT_OUT">Night Out (Authorized)</MenuItem>
            <MenuItem value="LEAVE">Official Leave</MenuItem>
            <MenuItem value="ABSENT">Unexcused Absent</MenuItem>
          </TextField>
          <TextField
            label="In-Time"
            value={attForm.in_time}
            onChange={(e) => setAttForm({ ...attForm, in_time: e.target.value })}
            placeholder="21:30:00"
            fullWidth
          />
          <TextField
            label="Remarks"
            value={attForm.remarks}
            onChange={(e) => setAttForm({ ...attForm, remarks: e.target.value })}
            fullWidth
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setOpenAttendanceModal(false)}>Cancel</Button>
          <Button variant="contained" onClick={handleAttendance} disabled={!attForm.building_id || !attForm.student_id}>
            Save Roll Call
          </Button>
        </DialogActions>
      </Dialog>

      {/* Dialog: Log Visitor */}
      <Dialog open={openVisitorModal} onClose={() => setOpenVisitorModal(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Log Hostel Visitor</DialogTitle>
        <DialogContent sx={{ display: 'flex', flexDirection: 'column', gap: 2, pt: 2 }}>
          <TextField
            select
            label="Building"
            value={visForm.building_id}
            onChange={(e) => setVisForm({ ...visForm, building_id: e.target.value })}
            fullWidth
            required
          >
            {buildings.map((b) => (
              <MenuItem key={b.id} value={b.id}>
                {b.name}
              </MenuItem>
            ))}
          </TextField>
          <TextField
            label="Resident Student ID (UUID)"
            value={visForm.student_id}
            onChange={(e) => setVisForm({ ...visForm, student_id: e.target.value })}
            fullWidth
            required
          />
          <TextField
            label="Visitor Full Name"
            value={visForm.visitor_name}
            onChange={(e) => setVisForm({ ...visForm, visitor_name: e.target.value })}
            fullWidth
            required
          />
          <TextField
            label="Relation to Student"
            value={visForm.relation}
            onChange={(e) => setVisForm({ ...visForm, relation: e.target.value })}
            placeholder="e.g. Parent, Guardian, Sibling"
            fullWidth
            required
          />
          <TextField
            label="Visitor Contact Phone"
            value={visForm.phone}
            onChange={(e) => setVisForm({ ...visForm, phone: e.target.value })}
            fullWidth
            required
          />
          <TextField
            label="Purpose of Visit"
            value={visForm.purpose}
            onChange={(e) => setVisForm({ ...visForm, purpose: e.target.value })}
            fullWidth
            required
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setOpenVisitorModal(false)}>Cancel</Button>
          <Button variant="contained" onClick={handleVisitor} disabled={!visForm.visitor_name || !visForm.phone}>
            Log Visitor
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  )
}
