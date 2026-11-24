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
import DirectionsBusIcon from '@mui/icons-material/DirectionsBus'
import AltRouteIcon from '@mui/icons-material/AltRoute'
import PersonPinIcon from '@mui/icons-material/PersonPin'
import MyLocationIcon from '@mui/icons-material/MyLocation'
import BuildIcon from '@mui/icons-material/Build'
import AddIcon from '@mui/icons-material/Add'

import {
  transportApi,
  TransportVehicle,
  TransportDriver,
  TransportRoute,
  StudentTransportAllocation,
  TransportGpsLog,
} from '../../api/transport'

export default function TransportManagementPage() {
  const [tab, setTab] = useState(0)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)

  // Data
  const [vehicles, setVehicles] = useState<TransportVehicle[]>([])
  const [drivers, setDrivers] = useState<TransportDriver[]>([])
  const [routes, setRoutes] = useState<TransportRoute[]>([])
  const [allocations, setAllocations] = useState<StudentTransportAllocation[]>([])
  const [selectedLiveGps, setSelectedLiveGps] = useState<TransportGpsLog | null>(null)

  // Modals
  const [openVehicleModal, setOpenVehicleModal] = useState(false)
  const [openDriverModal, setOpenDriverModal] = useState(false)
  const [openRouteModal, setOpenRouteModal] = useState(false)
  const [openAllocModal, setOpenAllocModal] = useState(false)
  const [openGpsModal, setOpenGpsModal] = useState(false)

  // Forms
  const [vehForm, setVehForm] = useState({
    registration_number: '',
    vehicle_model: '',
    seating_capacity: 35,
    fuel_type: 'DIESEL',
    insurance_number: '',
  })
  const [drvForm, setDrvForm] = useState({
    full_name: '',
    phone: '',
    license_number: '',
    experience_years: 5,
  })
  const [routeForm, setRouteForm] = useState({
    name: '',
    code: '',
    start_location: '',
    end_location: '',
    vehicle_id: '',
    driver_id: '',
    monthly_fare: 2000,
  })
  const [allocForm, setAllocForm] = useState({
    student_id: '',
    route_id: '',
    stop_id: '',
    pickup_drop_type: 'BOTH' as 'PICKUP_ONLY' | 'DROP_ONLY' | 'BOTH',
    monthly_fee: 2000,
    start_date: new Date().toISOString().split('T')[0],
  })

  const loadAll = async () => {
    try {
      const [vData, dData, rData, aData] = await Promise.all([
        transportApi.listVehicles().catch(() => []),
        transportApi.listDrivers().catch(() => []),
        transportApi.listRoutes().catch(() => []),
        transportApi.listAllocations().catch(() => []),
      ])
      setVehicles(vData)
      setDrivers(dData)
      setRoutes(rData)
      setAllocations(aData)
    } catch (err: any) {
      setError(err?.message || 'Failed to load transport data')
    }
  }

  useEffect(() => {
    loadAll()
  }, [])

  const handleCreateVehicle = async () => {
    try {
      await transportApi.createVehicle(vehForm)
      setSuccess('Vehicle registered successfully')
      setOpenVehicleModal(false)
      loadAll()
    } catch (err: any) {
      setError(err?.response?.data?.error?.message || 'Failed to register vehicle')
    }
  }

  const handleCreateDriver = async () => {
    try {
      await transportApi.createDriver(drvForm)
      setSuccess('Driver registered successfully')
      setOpenDriverModal(false)
      loadAll()
    } catch (err: any) {
      setError(err?.response?.data?.error?.message || 'Failed to register driver')
    }
  }

  const handleCreateRoute = async () => {
    try {
      await transportApi.createRoute({
        ...routeForm,
        vehicle_id: routeForm.vehicle_id || undefined,
        driver_id: routeForm.driver_id || undefined,
        monthly_fare: Number(routeForm.monthly_fare),
      })
      setSuccess('Route configured successfully')
      setOpenRouteModal(false)
      loadAll()
    } catch (err: any) {
      setError(err?.response?.data?.error?.message || 'Failed to create route')
    }
  }

  const handleAllocate = async () => {
    try {
      await transportApi.allocateStudent(allocForm)
      setSuccess('Student transport allocated successfully')
      setOpenAllocModal(false)
      loadAll()
    } catch (err: any) {
      setError(err?.response?.data?.error?.message || 'Failed to allocate student')
    }
  }

  const handleViewGps = async (vehicleId: string) => {
    try {
      const loc = await transportApi.getLiveLocation(vehicleId)
      setSelectedLiveGps(loc)
      setOpenGpsModal(true)
    } catch (err) {
      setError('Unable to fetch live vehicle telemetry')
    }
  }

  return (
    <Box sx={{ maxWidth: 1400, mx: 'auto' }}>
      {/* Header */}
      <Box sx={{ mb: 3 }}>
        <PageHeader
          title="Transport"
          description="Manage vehicles, drivers, routes, and student transport allocations."
          icon={<DirectionsBusIcon />}
        >
          <Box sx={{ display: 'flex', gap: 1.5 }}>
            <Button variant="outlined" startIcon={<AddIcon />} onClick={() => setOpenDriverModal(true)}>
              Add Driver
            </Button>
            <Button variant="outlined" startIcon={<AddIcon />} onClick={() => setOpenVehicleModal(true)}>
              Add Vehicle
            </Button>
            <Button variant="contained" startIcon={<AltRouteIcon />} onClick={() => setOpenRouteModal(true)}>
              Create Route
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
              <Typography variant="body2" color="text.secondary">Fleet Vehicles</Typography>
              <Typography variant="h4" fontWeight="bold">{vehicles.length}</Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={3}>
          <Card>
            <CardContent>
              <Typography variant="body2" color="text.secondary">Active Routes</Typography>
              <Typography variant="h4" fontWeight="bold">{routes.length}</Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={3}>
          <Card>
            <CardContent>
              <Typography variant="body2" color="text.secondary">Registered Drivers</Typography>
              <Typography variant="h4" fontWeight="bold">{drivers.length}</Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={3}>
          <Card>
            <CardContent>
              <Typography variant="body2" color="primary.main">Students Allocated</Typography>
              <Typography variant="h4" fontWeight="bold" color="primary.main">
                {allocations.length}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Tabs */}
      <Tabs value={tab} onChange={(_, val) => setTab(val)} sx={{ borderBottom: 1, borderColor: 'divider', mb: 3 }}>
        <Tab icon={<AltRouteIcon />} iconPosition="start" label="Routes & Bus Stops" />
        <Tab icon={<PersonPinIcon />} iconPosition="start" label="Student Route Allocations" />
        <Tab icon={<DirectionsBusIcon />} iconPosition="start" label="Fleet Vehicles & Telemetry" />
        <Tab icon={<BuildIcon />} iconPosition="start" label="Drivers & Maintenance" />
      </Tabs>

      {/* Tab 0: Routes */}
      {tab === 0 && (
        <TableContainer component={Paper} sx={{ overflowX: 'auto', width: '100%' }}>
          <Table sx={{ minWidth: 600 }}>
            <TableHead>
              <TableRow sx={{ backgroundColor: 'action.hover' }}>
                <TableCell>Route Name</TableCell>
                <TableCell>Code</TableCell>
                <TableCell>Origin → Destination</TableCell>
                <TableCell>Assigned Vehicle</TableCell>
                <TableCell>Driver</TableCell>
                <TableCell>Monthly Fare</TableCell>
                <TableCell>Stops Count</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {routes.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={7} align="center" sx={{ py: 3, color: 'text.secondary' }}>
                    No routes configured yet. Click "Create Route" above.
                  </TableCell>
                </TableRow>
              ) : (
                routes.map((r) => (
                  <TableRow key={r.id} hover>
                    <TableCell sx={{ fontWeight: 'medium' }}>{r.name}</TableCell>
                    <TableCell>
                      <code>{r.code}</code>
                    </TableCell>
                    <TableCell>
                      {r.start_location} → {r.end_location}
                    </TableCell>
                    <TableCell>{r.vehicle_registration || 'Unassigned'}</TableCell>
                    <TableCell>{r.driver_name || 'Unassigned'}</TableCell>
                    <TableCell>₹{r.monthly_fare}</TableCell>
                    <TableCell>
                      <Chip size="small" label={`${r.stops?.length || 0} stops`} />
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </TableContainer>
      )}

      {/* Tab 1: Allocations */}
      {tab === 1 && (
        <Box>
          <Box sx={{ display: 'flex', justifyContent: 'flex-end', mb: 2 }}>
            <Button variant="contained" startIcon={<AddIcon />} onClick={() => setOpenAllocModal(true)}>
              Allocate Student
            </Button>
          </Box>
          <TableContainer component={Paper} sx={{ overflowX: 'auto', width: '100%' }}>
            <Table sx={{ minWidth: 600 }}>
              <TableHead>
                <TableRow sx={{ backgroundColor: 'action.hover' }}>
                  <TableCell>Student Name</TableCell>
                  <TableCell>Admission No</TableCell>
                  <TableCell>Route</TableCell>
                  <TableCell>Stop & Timing</TableCell>
                  <TableCell>Service Type</TableCell>
                  <TableCell>Monthly Fee</TableCell>
                  <TableCell>Status</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {allocations.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={7} align="center" sx={{ py: 3, color: 'text.secondary' }}>
                      No students allocated to transport yet.
                    </TableCell>
                  </TableRow>
                ) : (
                  allocations.map((a) => (
                    <TableRow key={a.id} hover>
                      <TableCell sx={{ fontWeight: 'medium' }}>{a.student_name || '-'}</TableCell>
                      <TableCell>{a.admission_number || '-'}</TableCell>
                      <TableCell>{a.route_name || '-'}</TableCell>
                      <TableCell>
                        {a.stop_name} ({a.pickup_time || '-'} / {a.drop_time || '-'})
                      </TableCell>
                      <TableCell>
                        <Chip size="small" label={a.pickup_drop_type} />
                      </TableCell>
                      <TableCell>₹{a.monthly_fee}</TableCell>
                      <TableCell>
                        <Chip size="small" color="success" label={a.status} />
                      </TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          </TableContainer>
        </Box>
      )}

      {/* Tab 2: Fleet Vehicles */}
      {tab === 2 && (
        <TableContainer component={Paper} sx={{ overflowX: 'auto', width: '100%' }}>
          <Table sx={{ minWidth: 600 }}>
            <TableHead>
              <TableRow sx={{ backgroundColor: 'action.hover' }}>
                <TableCell>Registration No</TableCell>
                <TableCell>Model</TableCell>
                <TableCell>Capacity</TableCell>
                <TableCell>Fuel</TableCell>
                <TableCell>Insurance Expiry</TableCell>
                <TableCell>Status</TableCell>
                <TableCell align="right">GPS Telemetry</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {vehicles.map((v) => (
                <TableRow key={v.id} hover>
                  <TableCell sx={{ fontWeight: 'medium' }}>
                    <code>{v.registration_number}</code>
                  </TableCell>
                  <TableCell>{v.vehicle_model}</TableCell>
                  <TableCell>{v.seating_capacity} seats</TableCell>
                  <TableCell>{v.fuel_type}</TableCell>
                  <TableCell>{v.insurance_expiry || 'N/A'}</TableCell>
                  <TableCell>
                    <Chip size="small" color={v.status === 'ACTIVE' ? 'success' : 'default'} label={v.status} />
                  </TableCell>
                  <TableCell align="right">
                    <Button
                      size="small"
                      startIcon={<MyLocationIcon />}
                      onClick={() => handleViewGps(v.id)}
                    >
                      Live Location
                    </Button>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      )}

      {/* Tab 3: Drivers & Maintenance */}
      {tab === 3 && (
        <TableContainer component={Paper} sx={{ overflowX: 'auto', width: '100%' }}>
          <Table sx={{ minWidth: 600 }}>
            <TableHead>
              <TableRow sx={{ backgroundColor: 'action.hover' }}>
                <TableCell>Driver Name</TableCell>
                <TableCell>Phone Number</TableCell>
                <TableCell>License No</TableCell>
                <TableCell>Experience</TableCell>
                <TableCell>Status</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {drivers.map((d) => (
                <TableRow key={d.id} hover>
                  <TableCell sx={{ fontWeight: 'medium' }}>{d.full_name}</TableCell>
                  <TableCell>{d.phone}</TableCell>
                  <TableCell>
                    <code>{d.license_number}</code>
                  </TableCell>
                  <TableCell>{d.experience_years} years</TableCell>
                  <TableCell>
                    <Chip size="small" color={d.is_active ? 'success' : 'default'} label={d.is_active ? 'Active' : 'Inactive'} />
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      )}

      {/* Dialog: Add Vehicle */}
      <Dialog open={openVehicleModal} onClose={() => setOpenVehicleModal(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Register Fleet Vehicle</DialogTitle>
        <DialogContent sx={{ display: 'flex', flexDirection: 'column', gap: 2, pt: 2 }}>
          <TextField
            label="Registration Number"
            value={vehForm.registration_number}
            onChange={(e) => setVehForm({ ...vehForm, registration_number: e.target.value.toUpperCase() })}
            placeholder="e.g. MH-12-AB-1234"
            fullWidth
            required
          />
          <TextField
            label="Vehicle Model"
            value={vehForm.vehicle_model}
            onChange={(e) => setVehForm({ ...vehForm, vehicle_model: e.target.value })}
            placeholder="e.g. Tata Starbus Ultra"
            fullWidth
            required
          />
          <TextField
            label="Seating Capacity"
            type="number"
            value={vehForm.seating_capacity}
            onChange={(e) => setVehForm({ ...vehForm, seating_capacity: Number(e.target.value) })}
            fullWidth
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setOpenVehicleModal(false)}>Cancel</Button>
          <Button variant="contained" onClick={handleCreateVehicle} disabled={!vehForm.registration_number || !vehForm.vehicle_model}>
            Save Vehicle
          </Button>
        </DialogActions>
      </Dialog>

      {/* Dialog: Add Driver */}
      <Dialog open={openDriverModal} onClose={() => setOpenDriverModal(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Register Driver</DialogTitle>
        <DialogContent sx={{ display: 'flex', flexDirection: 'column', gap: 2, pt: 2 }}>
          <TextField
            label="Full Name"
            value={drvForm.full_name}
            onChange={(e) => setDrvForm({ ...drvForm, full_name: e.target.value })}
            fullWidth
            required
          />
          <TextField
            label="Contact Phone"
            value={drvForm.phone}
            onChange={(e) => setDrvForm({ ...drvForm, phone: e.target.value })}
            fullWidth
            required
          />
          <TextField
            label="Commercial License Number"
            value={drvForm.license_number}
            onChange={(e) => setDrvForm({ ...drvForm, license_number: e.target.value })}
            fullWidth
            required
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setOpenDriverModal(false)}>Cancel</Button>
          <Button variant="contained" onClick={handleCreateDriver} disabled={!drvForm.full_name || !drvForm.license_number}>
            Save Driver
          </Button>
        </DialogActions>
      </Dialog>

      {/* Dialog: Create Route */}
      <Dialog open={openRouteModal} onClose={() => setOpenRouteModal(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Configure Bus Route</DialogTitle>
        <DialogContent sx={{ display: 'flex', flexDirection: 'column', gap: 2, pt: 2 }}>
          <TextField
            label="Route Name"
            value={routeForm.name}
            onChange={(e) => setRouteForm({ ...routeForm, name: e.target.value })}
            placeholder="e.g. South Sector Morning Express"
            fullWidth
            required
          />
          <TextField
            label="Route Code"
            value={routeForm.code}
            onChange={(e) => setRouteForm({ ...routeForm, code: e.target.value.toUpperCase() })}
            placeholder="e.g. R-101"
            fullWidth
            required
          />
          <TextField
            label="Starting Location"
            value={routeForm.start_location}
            onChange={(e) => setRouteForm({ ...routeForm, start_location: e.target.value })}
            fullWidth
            required
          />
          <TextField
            label="Destination Location"
            value={routeForm.end_location}
            onChange={(e) => setRouteForm({ ...routeForm, end_location: e.target.value })}
            fullWidth
            required
          />
          <TextField
            label="Standard Monthly Fare (₹)"
            type="number"
            value={routeForm.monthly_fare}
            onChange={(e) => setRouteForm({ ...routeForm, monthly_fare: Number(e.target.value) })}
            fullWidth
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setOpenRouteModal(false)}>Cancel</Button>
          <Button variant="contained" onClick={handleCreateRoute} disabled={!routeForm.name || !routeForm.code}>
            Save Route
          </Button>
        </DialogActions>
      </Dialog>

      {/* Dialog: Allocate Student */}
      <Dialog open={openAllocModal} onClose={() => setOpenAllocModal(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Allocate Student to Transport Route</DialogTitle>
        <DialogContent sx={{ display: 'flex', flexDirection: 'column', gap: 2, pt: 2 }}>
          <TextField
            label="Student ID (UUID)"
            value={allocForm.student_id}
            onChange={(e) => setAllocForm({ ...allocForm, student_id: e.target.value })}
            fullWidth
            required
          />
          <TextField
            select
            label="Select Route"
            value={allocForm.route_id}
            onChange={(e) => setAllocForm({ ...allocForm, route_id: e.target.value })}
            fullWidth
            required
          >
            {routes.map((r) => (
              <MenuItem key={r.id} value={r.id}>
                {r.name} ({r.code})
              </MenuItem>
            ))}
          </TextField>
          <TextField
            label="Stop ID (UUID)"
            value={allocForm.stop_id}
            onChange={(e) => setAllocForm({ ...allocForm, stop_id: e.target.value })}
            fullWidth
            required
          />
          <TextField
            label="Monthly Transport Fee (₹)"
            type="number"
            value={allocForm.monthly_fee}
            onChange={(e) => setAllocForm({ ...allocForm, monthly_fee: Number(e.target.value) })}
            fullWidth
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setOpenAllocModal(false)}>Cancel</Button>
          <Button variant="contained" onClick={handleAllocate} disabled={!allocForm.student_id || !allocForm.route_id}>
            Confirm Allocation
          </Button>
        </DialogActions>
      </Dialog>

      {/* Dialog: Live GPS */}
      <Dialog open={openGpsModal} onClose={() => setOpenGpsModal(false)} maxWidth="xs" fullWidth>
        <DialogTitle>Live Telemetry</DialogTitle>
        <DialogContent sx={{ pt: 2 }}>
          {selectedLiveGps ? (
            <Box>
              <Typography variant="body2" color="text.secondary">Latitude / Longitude</Typography>
              <Typography variant="h6" fontWeight="bold">
                {selectedLiveGps.latitude}, {selectedLiveGps.longitude}
              </Typography>
              <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>Current Speed</Typography>
              <Typography variant="h6" fontWeight="bold">
                {selectedLiveGps.speed_kmh} km/h
              </Typography>
              <Typography variant="caption" color="text.secondary" sx={{ mt: 1, display: 'block' }}>
                Last Ping: {new Date(selectedLiveGps.recorded_at).toLocaleTimeString()}
              </Typography>
            </Box>
          ) : (
            <Typography color="text.secondary">No GPS telemetry ping recorded yet for this vehicle.</Typography>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setOpenGpsModal(false)}>Close</Button>
        </DialogActions>
      </Dialog>
    </Box>
  )
}
