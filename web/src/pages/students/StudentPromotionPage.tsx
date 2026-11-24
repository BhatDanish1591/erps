import React, { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Box,
  Typography,
  Paper,
  Grid,
  TextField,
  MenuItem,
  Button,
  Checkbox,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Alert,
  CircularProgress,
  Chip,
  Card,
  CardContent,
} from '@mui/material'
import { StudentItem, studentsApi } from '../../api/students'

export const StudentPromotionPage: React.FC = () => {
  const navigate = useNavigate()

  const [students, setStudents] = useState<StudentItem[]>([])
  const [loading, setLoading] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [successMsg, setSuccessMsg] = useState<string | null>(null)

  // Promotion configuration
  const [action, setAction] = useState<'PROMOTE' | 'GRADUATE' | 'TRANSFER' | 'REPEAT'>('PROMOTE')
  const [targetSessionId, setTargetSessionId] = useState('')
  const [targetSemester, setTargetSemester] = useState<number>(2)
  const [remarks, setRemarks] = useState('')
  const [selectedStudentIds, setSelectedStudentIds] = useState<string[]>([])

  const loadStudents = async () => {
    try {
      setLoading(true)
      setError(null)
      const res = await studentsApi.listStudents({ status: 'ACTIVE', size: 100 })
      setStudents(res.items)
    } catch (err: any) {
      setError(err?.message || 'Failed to fetch student cohort')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadStudents()
  }, [])

  const handleSelectAll = (checked: boolean) => {
    if (checked) {
      setSelectedStudentIds(students.map((s) => s.id))
    } else {
      setSelectedStudentIds([])
    }
  }

  const handleSelectStudent = (id: string) => {
    setSelectedStudentIds((prev) =>
      prev.includes(id) ? prev.filter((item) => item !== id) : [...prev, id]
    )
  }

  const handlePromote = async () => {
    if (selectedStudentIds.length === 0) {
      setError('Please select at least one student to promote.')
      return
    }

    try {
      setSubmitting(true)
      setError(null)
      setSuccessMsg(null)

      // Fallback target session: use first student's session if targetSessionId is empty
      const resolvedSessionId =
        targetSessionId ||
        students[0]?.academic_session_id ||
        '00000000-0000-0000-0000-000000000000'

      const res = await studentsApi.promoteStudents({
        target_academic_session_id: resolvedSessionId,
        student_ids: selectedStudentIds,
        action,
        target_semester: targetSemester,
        remarks: remarks || `Batch ${action} processed via portal.`,
      })

      setSuccessMsg(res.message || `Successfully processed ${res.processed_students} students for ${action.toLowerCase()}.`)
      setSelectedStudentIds([])
      await loadStudents()
    } catch (err: any) {
      setError(err?.message || 'Failed to process student promotion.')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <Box>
      <Button size="small" onClick={() => navigate('/students')} sx={{ mb: 2 }}>
        ← Back to Students
      </Button>

      <Typography variant="h5" sx={{ fontWeight: 800, mb: 1 }}>
        Student Promotion & Cohort Transition
      </Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
        Promote classes to the next academic grade, graduate final year batches, or transfer students across sessions.
      </Typography>

      {error && (
        <Alert severity="error" sx={{ mb: 2.5 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      {successMsg && (
        <Alert severity="success" sx={{ mb: 2.5 }} onClose={() => setSuccessMsg(null)}>
          {successMsg}
        </Alert>
      )}

      {/* Target Placement Card */}
      <Card sx={{ mb: 3, borderRadius: 2 }}>
        <CardContent>
          <Typography variant="subtitle1" sx={{ fontWeight: 700, mb: 2 }}>
            Promotion & Transition Settings
          </Typography>
          <Grid container spacing={2}>
            <Grid item xs={12} sm={3}>
              <TextField
                label="Action Type"
                select
                fullWidth
                value={action}
                onChange={(e) => setAction(e.target.value as any)}
              >
                <MenuItem value="PROMOTE">PROMOTE (Advance to next grade)</MenuItem>
                <MenuItem value="GRADUATE">GRADUATE (Complete degree/schooling)</MenuItem>
                <MenuItem value="TRANSFER">TRANSFER (Issue transfer certificate)</MenuItem>
                <MenuItem value="REPEAT">REPEAT (Retain in grade)</MenuItem>
              </TextField>
            </Grid>

            <Grid item xs={12} sm={3}>
              <TextField
                label="Target Academic Session ID"
                fullWidth
                placeholder="Leave blank for default"
                value={targetSessionId}
                onChange={(e) => setTargetSessionId(e.target.value)}
              />
            </Grid>

            {action === 'PROMOTE' && (
              <Grid item xs={12} sm={2}>
                <TextField
                  label="Target Semester"
                  type="number"
                  fullWidth
                  value={targetSemester}
                  onChange={(e) => setTargetSemester(parseInt(e.target.value) || 1)}
                  InputProps={{ inputProps: { min: 1, max: 16 } }}
                />
              </Grid>
            )}

            <Grid item xs={12} sm={action === 'PROMOTE' ? 4 : 6}>
              <TextField
                label="Remarks / Transition Notes"
                fullWidth
                value={remarks}
                onChange={(e) => setRemarks(e.target.value)}
                placeholder="e.g. Promoted based on annual exam results"
              />
            </Grid>
          </Grid>
        </CardContent>
      </Card>

      {/* Student Selection Table */}
      <Paper sx={{ borderRadius: 2, overflow: 'hidden' }}>
        <Box sx={{ p: 2, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <Typography variant="subtitle1" sx={{ fontWeight: 700 }}>
            Active Students Eligible for Promotion ({selectedStudentIds.length} selected of {students.length})
          </Typography>
          <Button
            variant="contained"
            color="primary"
            onClick={handlePromote}
            disabled={selectedStudentIds.length === 0 || submitting}
            startIcon={submitting ? <CircularProgress size={16} color="inherit" /> : null}
          >
            {submitting ? 'Processing...' : `Execute ${action} (${selectedStudentIds.length})`}
          </Button>
        </Box>

        {loading ? (
          <Box sx={{ p: 4, display: 'flex', justifyContent: 'center' }}>
            <CircularProgress />
          </Box>
        ) : (
          <TableContainer>
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell padding="checkbox">
                    <Checkbox
                      indeterminate={
                        selectedStudentIds.length > 0 && selectedStudentIds.length < students.length
                      }
                      checked={students.length > 0 && selectedStudentIds.length === students.length}
                      onChange={(e) => handleSelectAll(e.target.checked)}
                    />
                  </TableCell>
                  <TableCell>Admission No</TableCell>
                  <TableCell>Student Name</TableCell>
                  <TableCell>Class / Course</TableCell>
                  <TableCell>Section / Sem</TableCell>
                  <TableCell>Roll No</TableCell>
                  <TableCell>Status</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {students.map((s) => {
                  const isSelected = selectedStudentIds.includes(s.id)
                  return (
                    <TableRow key={s.id} hover selected={isSelected}>
                      <TableCell padding="checkbox">
                        <Checkbox
                          checked={isSelected}
                          onChange={() => handleSelectStudent(s.id)}
                        />
                      </TableCell>
                      <TableCell sx={{ fontWeight: 700 }}>{s.admission_number}</TableCell>
                      <TableCell>{s.full_name}</TableCell>
                      <TableCell>{s.class_name || s.course_name || 'Standard'}</TableCell>
                      <TableCell>
                        {s.section_name ? `Sec ${s.section_name}` : s.semester ? `Sem ${s.semester}` : '—'}
                      </TableCell>
                      <TableCell>{s.roll_number || '—'}</TableCell>
                      <TableCell>
                        <Chip label={s.status} size="small" color="success" />
                      </TableCell>
                    </TableRow>
                  )
                })}
                {students.length === 0 && (
                  <TableRow>
                    <TableCell colSpan={7} sx={{ textAlign: 'center', py: 4 }}>
                      No active students found in this institution.
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </TableContainer>
        )}
      </Paper>
    </Box>
  )
}
