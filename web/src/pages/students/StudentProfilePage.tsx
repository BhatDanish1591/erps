import React, { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import {
  Box,
  Typography,
  Button,
  Tabs,
  Tab,
  Paper,
  Grid,
  Chip,
  Avatar,
  Divider,
  Alert,
  CircularProgress,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  MenuItem,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
} from '@mui/material'
import {
  openPrintableStudentCard,
  StudentItem,
  StudentIDCard,
  studentsApi,
  studentPhotoSrc,
} from '../../api/students'
import { AddEditStudentModal } from './AddEditStudentModal'
import { useAuthStore } from '@/store/authStore'

export const StudentProfilePage: React.FC = () => {
  const { studentId } = useParams<{ studentId: string }>()
  const navigate = useNavigate()
  const canManage = useAuthStore((state) => Boolean(state.user?.is_superadmin || state.user?.current_role === 'INSTITUTION_ADMIN'))
  const [printError, setPrintError] = useState('')

  const [student, setStudent] = useState<StudentItem | null>(null)
  const [idCard, setIdCard] = useState<StudentIDCard | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [tabIndex, setTabIndex] = useState(0)

  // Dialog states
  const [editOpen, setEditOpen] = useState(false)
  const [docUploadOpen, setDocUploadOpen] = useState(false)
  const [docSubmitting, setDocSubmitting] = useState(false)
  const [docForm, setDocForm] = useState({
    document_type: 'BIRTH_CERTIFICATE',
    document_name: '',
    file_url: '',
  })

  const loadData = async () => {
    if (!studentId) return
    try {
      setLoading(true)
      setError(null)
      const data = await studentsApi.getStudent(studentId)
      setStudent(data)

      try {
        const card = await studentsApi.getStudentIdCard(studentId)
        setIdCard(card)
      } catch {
        // ID card data might fail if missing dependencies
      }
    } catch (err: any) {
      setError(err?.message || 'Failed to fetch student profile.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadData()
  }, [studentId])

  const handleDeactivate = async () => {
    if (!studentId || !student) return
    const confirmed = window.confirm(
      `Are you sure you want to deactivate student ${student.full_name}? They will no longer have access to portal services.`
    )
    if (!confirmed) return

    try {
      await studentsApi.deactivateStudent(studentId)
      await loadData()
    } catch (err: any) {
      alert(err?.message || 'Failed to deactivate student')
    }
  }

  const handleUploadDoc = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!studentId || !docForm.document_name.trim() || !docForm.file_url.trim()) return

    try {
      setDocSubmitting(true)
      await studentsApi.uploadDocument(studentId, {
        document_type: docForm.document_type,
        document_name: docForm.document_name.trim(),
        file_url: docForm.file_url.trim(),
      })
      setDocUploadOpen(false)
      setDocForm({ document_type: 'BIRTH_CERTIFICATE', document_name: '', file_url: '' })
      await loadData()
    } catch (err: any) {
      alert(err?.message || 'Failed to upload document')
    } finally {
      setDocSubmitting(false)
    }
  }

  const handlePrintIdCard = () => {
    if (!studentId) return
    setPrintError('')
    void openPrintableStudentCard(studentId).catch((error: Error) => setPrintError(error.message))
  }

  if (loading) {
    return (
      <Box sx={{ p: 4, display: 'flex', justifyContent: 'center' }}>
        <CircularProgress />
      </Box>
    )
  }

  if (error || !student) {
    return (
      <Box sx={{ p: 3 }}>
        <Alert severity="error">{error || 'Student not found.'}</Alert>
        <Button sx={{ mt: 2 }} onClick={() => navigate('/students')}>
          Back to Students List
        </Button>
      </Box>
    )
  }

  return (
    <Box>
      {printError && <Alert severity="error" onClose={() => setPrintError('')} sx={{ mb: 2 }}>{printError}</Alert>}
      {/* Back Button & Title */}
      <Box sx={{ mb: 2 }}>
        <Button size="small" onClick={() => navigate('/students')} sx={{ mb: 1 }}>
          ← Back to Students
        </Button>
      </Box>

      {/* Header Profile Card */}
      <Paper sx={{ p: 3, mb: 3, borderRadius: 2 }}>
        <Grid container spacing={3} alignItems="center">
          <Grid item>
            <Avatar
              src={studentPhotoSrc(student.photo_url)}
              sx={{ width: 84, height: 84, bgcolor: 'primary.main', fontSize: 32, fontWeight: 700 }}
            >
              {student.full_name.charAt(0)}
            </Avatar>
          </Grid>
          <Grid item xs>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5, flexWrap: 'wrap' }}>
              <Typography variant="h5" sx={{ fontWeight: 800 }}>
                {student.full_name}
              </Typography>
              <Chip
                label={student.status}
                color={student.status === 'ACTIVE' ? 'success' : 'default'}
                size="small"
                sx={{ fontWeight: 700 }}
              />
            </Box>
            <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
              Admission No: <strong>{student.admission_number}</strong> | Roll No:{' '}
              <strong>{student.roll_number || '—'}</strong> | Class/Course:{' '}
              <strong>{student.class_name || student.course_name || 'Standard'}</strong>
              {student.section_name && ` (Sec ${student.section_name})`}
              {student.semester && ` (Sem ${student.semester})`}
            </Typography>
            <Typography variant="caption" color="text.secondary">
              Campus Email: {student.email || '—'} | Phone: {student.phone || '—'}
            </Typography>
          </Grid>
          <Grid item>
            <Box sx={{ display: 'flex', gap: 1.5 }}>
              {canManage && <Button variant="outlined" onClick={() => setEditOpen(true)}>
                Edit Profile
              </Button>}
              <Button variant="outlined" color="primary" onClick={handlePrintIdCard}>
                Print ID Card
              </Button>
              {canManage && student.status === 'ACTIVE' && (
                <Button variant="outlined" color="error" onClick={handleDeactivate}>
                  Deactivate
                </Button>
              )}
            </Box>
          </Grid>
        </Grid>
      </Paper>

      {/* Navigation Tabs */}
      <Box sx={{ borderBottom: 1, borderColor: 'divider', mb: 3 }}>
        <Tabs value={tabIndex} onChange={(_, val) => setTabIndex(val)}>
          <Tab label="Overview & Biodata" />
          <Tab label="Parents & Guardians" />
          <Tab label="Documents" />
          <Tab label="ID Card Preview" />
        </Tabs>
      </Box>

      {/* TAB 0: Overview */}
      {tabIndex === 0 && (
        <Grid container spacing={3}>
          <Grid item xs={12} md={6}>
            <Paper sx={{ p: 2.5, borderRadius: 2 }}>
              <Typography variant="subtitle1" sx={{ fontWeight: 700, mb: 2 }}>
                Academic & Personal Information
              </Typography>
              <Grid container spacing={1.5}>
                <Grid item xs={5}><Typography color="text.secondary">Academic Session:</Typography></Grid>
                <Grid item xs={7}><Typography fontWeight={600}>{student.academic_session_name || 'Current'}</Typography></Grid>
                <Grid item xs={5}><Typography color="text.secondary">Date of Birth:</Typography></Grid>
                <Grid item xs={7}><Typography fontWeight={600}>{student.date_of_birth || '—'}</Typography></Grid>
                <Grid item xs={5}><Typography color="text.secondary">Gender:</Typography></Grid>
                <Grid item xs={7}><Typography fontWeight={600}>{student.gender || '—'}</Typography></Grid>
                <Grid item xs={5}><Typography color="text.secondary">Blood Group:</Typography></Grid>
                <Grid item xs={7}><Typography fontWeight={600}>{student.blood_group || '—'}</Typography></Grid>
                <Grid item xs={5}><Typography color="text.secondary">Admission Date:</Typography></Grid>
                <Grid item xs={7}><Typography fontWeight={600}>{student.admission_date || '—'}</Typography></Grid>
              </Grid>
            </Paper>
          </Grid>

          <Grid item xs={12} md={6}>
            <Paper sx={{ p: 2.5, borderRadius: 2 }}>
              <Typography variant="subtitle1" sx={{ fontWeight: 700, mb: 2 }}>
                Residential Address
              </Typography>
              <Grid container spacing={1.5}>
                <Grid item xs={5}><Typography color="text.secondary">Address Line 1:</Typography></Grid>
                <Grid item xs={7}><Typography fontWeight={600}>{student.address_line1 || '—'}</Typography></Grid>
                <Grid item xs={5}><Typography color="text.secondary">Address Line 2:</Typography></Grid>
                <Grid item xs={7}><Typography fontWeight={600}>{student.address_line2 || '—'}</Typography></Grid>
                <Grid item xs={5}><Typography color="text.secondary">City & State:</Typography></Grid>
                <Grid item xs={7}>
                  <Typography fontWeight={600}>
                    {student.city ? `${student.city}, ${student.state || ''}` : '—'}
                  </Typography>
                </Grid>
                <Grid item xs={5}><Typography color="text.secondary">Postal Code:</Typography></Grid>
                <Grid item xs={7}><Typography fontWeight={600}>{student.postal_code || '—'}</Typography></Grid>
                <Grid item xs={5}><Typography color="text.secondary">Country:</Typography></Grid>
                <Grid item xs={7}><Typography fontWeight={600}>{student.country || 'India'}</Typography></Grid>
              </Grid>
            </Paper>
          </Grid>

          <Grid item xs={12}>
            <Paper sx={{ p: 2.5, borderRadius: 2 }}>
              <Typography variant="subtitle1" sx={{ fontWeight: 700, mb: 2 }}>
                Previous Academic Records
              </Typography>
              <Grid container spacing={1.5}>
                <Grid item xs={12} sm={4}>
                  <Typography color="text.secondary">Previous Institution:</Typography>
                  <Typography fontWeight={600}>{student.previous_school_name || '—'}</Typography>
                </Grid>
                <Grid item xs={12} sm={4}>
                  <Typography color="text.secondary">Grade / Percentage Achieved:</Typography>
                  <Typography fontWeight={600}>{student.previous_grade || '—'}</Typography>
                </Grid>
                <Grid item xs={12} sm={4}>
                  <Typography color="text.secondary">Transfer Certificate (TC) No:</Typography>
                  <Typography fontWeight={600}>{student.transfer_certificate_number || '—'}</Typography>
                </Grid>
              </Grid>
            </Paper>
          </Grid>
        </Grid>
      )}

      {/* TAB 1: Parents & Guardians */}
      {tabIndex === 1 && (
        <Grid container spacing={3}>
          <Grid item xs={12} md={6}>
            <Paper sx={{ p: 2.5, borderRadius: 2 }}>
              <Typography variant="subtitle1" sx={{ fontWeight: 700, mb: 2 }}>
                Father's Details
              </Typography>
              <Grid container spacing={1.5}>
                <Grid item xs={5}><Typography color="text.secondary">Name:</Typography></Grid>
                <Grid item xs={7}><Typography fontWeight={600}>{student.father_name || '—'}</Typography></Grid>
                <Grid item xs={5}><Typography color="text.secondary">Phone:</Typography></Grid>
                <Grid item xs={7}><Typography fontWeight={600}>{student.father_phone || '—'}</Typography></Grid>
                <Grid item xs={5}><Typography color="text.secondary">Occupation:</Typography></Grid>
                <Grid item xs={7}><Typography fontWeight={600}>{student.father_occupation || '—'}</Typography></Grid>
              </Grid>

              <Divider sx={{ my: 2 }} />

              <Typography variant="subtitle1" sx={{ fontWeight: 700, mb: 2 }}>
                Mother's Details
              </Typography>
              <Grid container spacing={1.5}>
                <Grid item xs={5}><Typography color="text.secondary">Name:</Typography></Grid>
                <Grid item xs={7}><Typography fontWeight={600}>{student.mother_name || '—'}</Typography></Grid>
                <Grid item xs={5}><Typography color="text.secondary">Phone:</Typography></Grid>
                <Grid item xs={7}><Typography fontWeight={600}>{student.mother_phone || '—'}</Typography></Grid>
                <Grid item xs={5}><Typography color="text.secondary">Occupation:</Typography></Grid>
                <Grid item xs={7}><Typography fontWeight={600}>{student.mother_occupation || '—'}</Typography></Grid>
              </Grid>
            </Paper>
          </Grid>

          <Grid item xs={12} md={6}>
            <Paper sx={{ p: 2.5, borderRadius: 2 }}>
              <Typography variant="subtitle1" sx={{ fontWeight: 700, mb: 2 }}>
                Guardian / Emergency Contact
              </Typography>
              <Grid container spacing={1.5}>
                <Grid item xs={5}><Typography color="text.secondary">Guardian Name:</Typography></Grid>
                <Grid item xs={7}><Typography fontWeight={600}>{student.guardian_name || '—'}</Typography></Grid>
                <Grid item xs={5}><Typography color="text.secondary">Guardian Phone:</Typography></Grid>
                <Grid item xs={7}><Typography fontWeight={600}>{student.guardian_phone || '—'}</Typography></Grid>
                <Grid item xs={5}><Typography color="text.secondary">Relation:</Typography></Grid>
                <Grid item xs={7}><Typography fontWeight={600}>{student.guardian_relation || '—'}</Typography></Grid>
                <Grid item xs={5}><Typography color="text.secondary">Emergency Contact:</Typography></Grid>
                <Grid item xs={7}>
                  <Typography fontWeight={600}>
                    {student.emergency_contact_name
                      ? `${student.emergency_contact_name} (${student.emergency_contact_phone || ''})`
                      : '—'}
                  </Typography>
                </Grid>
              </Grid>
            </Paper>
          </Grid>
        </Grid>
      )}

      {/* TAB 2: Documents */}
      {tabIndex === 2 && (
        <Paper sx={{ p: 3, borderRadius: 2 }}>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
            <Typography variant="subtitle1" sx={{ fontWeight: 700 }}>
              Official Student Documents
            </Typography>
            <Button variant="contained" size="small" onClick={() => setDocUploadOpen(true)}>
              Upload Document
            </Button>
          </Box>

          <TableContainer>
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell>Document Type</TableCell>
                  <TableCell>Document Name</TableCell>
                  <TableCell>File Link</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                <TableRow>
                  <TableCell>ADMISSION_RECORD</TableCell>
                  <TableCell>Admission Acknowledgement</TableCell>
                  <TableCell>
                    <Typography variant="caption" color="primary" sx={{ cursor: 'pointer' }}>
                      Registered on {student.admission_date || 'Enrolment'}
                    </Typography>
                  </TableCell>
                </TableRow>
              </TableBody>
            </Table>
          </TableContainer>
        </Paper>
      )}

      {/* TAB 3: ID Card Preview */}
      {tabIndex === 3 && idCard && (
        <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center', py: 2 }}>
          <Box
            sx={{
              width: 320,
              bgcolor: 'background.paper',
              borderRadius: 3,
              boxShadow: 3,
              border: '1px solid',
              borderColor: 'divider',
              overflow: 'hidden',
              textAlign: 'center',
            }}
          >
            <Box sx={{ bgcolor: 'primary.main', color: 'primary.contrastText', p: 2 }}>
              <Typography variant="subtitle1" sx={{ fontWeight: 800, textTransform: 'uppercase' }}>
                {idCard.institution_name}
              </Typography>
              <Typography variant="caption">Student Identity Card</Typography>
            </Box>

            <Box sx={{ p: 2.5 }}>
              <Avatar
                src={studentPhotoSrc(idCard.photo_url)}
                sx={{ width: 80, height: 80, mx: 'auto', mb: 1.5, border: '3px solid white', boxShadow: 1 }}
              >
                {idCard.full_name.charAt(0)}
              </Avatar>

              <Typography variant="h6" sx={{ fontWeight: 800 }}>
                {idCard.full_name}
              </Typography>
              <Chip
                label={idCard.admission_number}
                size="small"
                color="primary"
                variant="outlined"
                sx={{ fontWeight: 700, my: 1 }}
              />

              <Box sx={{ textAlign: 'left', mt: 1.5, fontSize: 13 }}>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', py: 0.5 }}>
                  <Typography variant="body2" color="text.secondary">Class/Course:</Typography>
                  <Typography variant="body2" fontWeight={600}>{idCard.class_or_course}</Typography>
                </Box>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', py: 0.5 }}>
                  <Typography variant="body2" color="text.secondary">Section/Sem:</Typography>
                  <Typography variant="body2" fontWeight={600}>{idCard.section_or_semester}</Typography>
                </Box>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', py: 0.5 }}>
                  <Typography variant="body2" color="text.secondary">Roll No:</Typography>
                  <Typography variant="body2" fontWeight={600}>{idCard.roll_number || '—'}</Typography>
                </Box>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', py: 0.5 }}>
                  <Typography variant="body2" color="text.secondary">Blood Group:</Typography>
                  <Typography variant="body2" fontWeight={600}>{idCard.blood_group || '—'}</Typography>
                </Box>
              </Box>

              <Box sx={{ mt: 2, pt: 1.5, borderTop: '1px dashed', borderColor: 'divider' }}>
                <Typography variant="caption" sx={{ fontFamily: 'monospace', letterSpacing: 2 }}>
                  ||| | ||| |||| | ||
                </Typography>
                <Typography variant="caption" display="block" color="text.secondary" sx={{ mt: 0.5 }}>
                  Valid Thru: {idCard.valid_until}
                </Typography>
              </Box>
            </Box>
          </Box>

          <Button variant="contained" sx={{ mt: 3 }} onClick={handlePrintIdCard}>
            Open Printable HTML Card
          </Button>
        </Box>
      )}

      {/* Edit Student Modal */}
      <AddEditStudentModal
        open={editOpen}
        onClose={() => setEditOpen(false)}
        onSuccess={loadData}
        student={student}
      />

      {/* Document Upload Dialog */}
      <Dialog open={docUploadOpen} onClose={() => setDocUploadOpen(false)} maxWidth="sm" fullWidth>
        <form onSubmit={handleUploadDoc}>
          <DialogTitle sx={{ fontWeight: 700 }}>Upload Student Document</DialogTitle>
          <DialogContent>
            <TextField
              label="Document Type"
              select
              fullWidth
              value={docForm.document_type}
              onChange={(e) => setDocForm((prev) => ({ ...prev, document_type: e.target.value }))}
              sx={{ mt: 1, mb: 2 }}
            >
              <MenuItem value="BIRTH_CERTIFICATE">Birth Certificate</MenuItem>
              <MenuItem value="AADHAR_CARD">Aadhar Card</MenuItem>
              <MenuItem value="TRANSFER_CERTIFICATE">Transfer Certificate (TC)</MenuItem>
              <MenuItem value="PREVIOUS_MARKSHEET">Previous Marksheet</MenuItem>
              <MenuItem value="MEDICAL_RECORD">Medical Record</MenuItem>
              <MenuItem value="OTHER">Other Document</MenuItem>
            </TextField>
            <TextField
              label="Document Name"
              required
              fullWidth
              value={docForm.document_name}
              onChange={(e) => setDocForm((prev) => ({ ...prev, document_name: e.target.value }))}
              placeholder="e.g. Birth Certificate Original Copy"
              sx={{ mb: 2 }}
            />
            <TextField
              label="Document URL / Storage Key"
              required
              fullWidth
              value={docForm.file_url}
              onChange={(e) => setDocForm((prev) => ({ ...prev, file_url: e.target.value }))}
              placeholder="https://..."
            />
          </DialogContent>
          <DialogActions sx={{ px: 3, pb: 2.5 }}>
            <Button onClick={() => setDocUploadOpen(false)} disabled={docSubmitting}>
              Cancel
            </Button>
            <Button type="submit" variant="contained" disabled={docSubmitting}>
              {docSubmitting ? 'Uploading...' : 'Upload'}
            </Button>
          </DialogActions>
        </form>
      </Dialog>
    </Box>
  )
}
