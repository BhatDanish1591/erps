import { PageHeader } from '@/components/ui/PageHeader'
import { useState, useEffect } from 'react'
import {
  Box,
  Card,
  CardContent,
  Typography,
  Tabs,
  Tab,
  Button,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Chip,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  MenuItem,
  Grid,
  Alert,
  LinearProgress,
  Tooltip,
  IconButton,
  Divider,
} from '@mui/material'
import {
  Assessment as ResultsIcon,
  FactCheck as MarksheetIcon,
  HistoryEdu as RevisionsIcon,
  HelpOutline as ReEvalIcon,
  PictureAsPdf as PdfIcon,
  Analytics as AnalyticsIcon,
  Save as SaveIcon,
  Send as SubmitIcon,
  CheckCircle as ApproveIcon,
  Publish as PublishIcon,
  Refresh as RefreshIcon,
  FileDownload as DownloadIcon,
} from '@mui/icons-material'

import {
  resultsApi,
  StudentTermResult,
  SubjectMarksEntryItem,
  ReEvaluationRequestItem,
  ResultRevisionHistory,
  ClassPerformanceAnalytics,
} from '../../api/results'
import { examinationsApi, ExaminationItem } from '../../api/examinations'
import { academicsApi, AcademicSession, Subject } from '../../api/academics'
import { useAuthStore } from '@/store/authStore'

export default function ResultsManagementPage() {
  const canApprove = useAuthStore(({ user }) => Boolean(user?.is_superadmin || user?.current_role === 'INSTITUTION_ADMIN'))
  const [activeTab, setActiveTab] = useState(0)
  const [loading, setLoading] = useState(false)
  const [alert, setAlert] = useState<{ type: 'success' | 'error' | 'info'; message: string } | null>(null)

  // Filters & State
  const [sessions, setSessions] = useState<AcademicSession[]>([])
  const [subjects, setSubjects] = useState<Subject[]>([])
  const [selectedSubjectId, setSelectedSubjectId] = useState('')
  const [examinations, setExaminations] = useState<ExaminationItem[]>([])
  const [selectedExamId, setSelectedExamId] = useState('')
  const selectedExam = examinations.find((exam) => exam.id === selectedExamId)
  const selectedSessionId = selectedExam?.academic_session_id ?? ''
  const selectedSubject = selectedExam?.subject_id ?? selectedSubjectId

  // Tab 0: Marks Entry State
  const [marksEntries, setMarksEntries] = useState<SubjectMarksEntryItem[]>([])

  // Tab 1: Marksheet & Workflow State
  const [termResults, setTermResults] = useState<StudentTermResult[]>([])
  const [workflowDialog, setWorkflowDialog] = useState<{ open: boolean; action: string; title: string }>({
    open: false,
    action: '',
    title: '',
  })
  const [workflowComment, setWorkflowComment] = useState('')

  // Tab 2: Revision History State
  const [revisions, setRevisions] = useState<ResultRevisionHistory[]>([])
  const [revisionDialog, setRevisionDialog] = useState(false)
  const [targetResultId, setTargetResultId] = useState('')
  const [revisedTheory, setRevisedTheory] = useState<number>(0)
  const [revisedPractical, setRevisedPractical] = useState<number>(0)
  const [revisedInternal, setRevisedInternal] = useState<number>(0)
  const [revisionReason, setRevisionReason] = useState('')

  // Tab 3: Re-Evaluation State
  const [reevaluations, setReevaluations] = useState<ReEvaluationRequestItem[]>([])
  const [reEvalDialog, setReEvalDialog] = useState(false)
  const [selectedReEval, setSelectedReEval] = useState<ReEvaluationRequestItem | null>(null)
  const [reEvalStatus, setReEvalStatus] = useState<'APPROVED_UPDATED' | 'REJECTED'>('APPROVED_UPDATED')
  const [reEvalRemarks, setReEvalRemarks] = useState('')
  const [reEvalTheory, setReEvalTheory] = useState<number>(0)

  // Tab 4: Student Report Card State
  const [selectedStudentId, setSelectedStudentId] = useState('')
  const [activeReportCard, setActiveReportCard] = useState<StudentTermResult | null>(null)

  // Tab 5: Analytics State
  const [analytics, setAnalytics] = useState<ClassPerformanceAnalytics | null>(null)

  // Load Initial Academic Meta
  useEffect(() => {
    loadAcademicMeta()
  }, [])

  const loadAcademicMeta = async () => {
    try {
      const [sessRes, subRes, exRes] = await Promise.all([
        academicsApi.getSessions(), academicsApi.getSubjects(), examinationsApi.listExaminations(),
      ])
      setSessions(sessRes.data ?? [])
      setSubjects(subRes.data ?? [])
      setSelectedSubjectId((current) => current || subRes.data?.[0]?.id || '')
      setExaminations(exRes.data ?? [])
      setSelectedExamId((current) => current || exRes.data?.[0]?.id || '')
    } catch (err: any) {
      setAlert({ type: 'error', message: 'Failed to load initial academic settings.' })
    }
  }

  // Load Data When Exam or Tab Changes
  useEffect(() => {
    if (!selectedExamId) return
    let active = true
    if (activeTab === 0) {
      void loadStudentsForMarksEntry(() => active)
    } else if (activeTab === 1) {
      loadExamResults()
    } else if (activeTab === 3) {
      loadReevaluations()
    } else if (activeTab === 5) {
      loadAnalytics()
    }
    return () => { active = false }
  }, [selectedExamId, selectedSubject, activeTab])

  // Tab 0: Load Student Roster for Marks Entry
  const loadStudentsForMarksEntry = async (isActive: () => boolean) => {
    if (!selectedExamId || !selectedSubject) return
    try {
      setLoading(true)
      setMarksEntries([])
      const roster = await resultsApi.getMarksRoster(selectedExamId, selectedSubject)
      if (!isActive()) return
      const initialEntries: SubjectMarksEntryItem[] = roster.map((student) => ({
        theory_marks: 0,
        theory_max_marks: 70,
        practical_marks: 0,
        practical_max_marks: 20,
        internal_marks: 0,
        internal_max_marks: 10,
        assignment_marks: 0,
        assignment_max_marks: 0,
        credits: 3.0,
        ...student,
      }))
      setMarksEntries(initialEntries)
    } catch (err: any) {
      if (isActive()) setAlert({ type: 'error', message: err.response?.data?.error?.message || 'Failed to load student roster.' })
    } finally {
      if (isActive()) setLoading(false)
    }
  }

  const handleMarksChange = (
    index: number,
    field: keyof SubjectMarksEntryItem,
    val: number | string
  ) => {
    const updated = [...marksEntries]
    updated[index] = { ...updated[index], [field]: val }
    setMarksEntries(updated)
  }

  const handleSaveMarks = async () => {
    if (!selectedExamId || !selectedSessionId || !selectedSubject) {
      setAlert({ type: 'error', message: 'Please select Examination, Session, and Subject.' })
      return
    }
    try {
      setLoading(true)
      await resultsApi.bulkEnterMarks({
        exam_id: selectedExamId,
        academic_session_id: selectedSessionId,
        subject_id: selectedSubject,
        entries: marksEntries,
      })
      setAlert({ type: 'success', message: 'Subject marks recorded successfully!' })
    } catch (err: any) {
      setAlert({ type: 'error', message: err.response?.data?.error?.message || 'Failed to save marks.' })
    } finally {
      setLoading(false)
    }
  }

  // Tab 1: Marksheet & Workflow
  const loadExamResults = async () => {
    if (!selectedExamId) return
    try {
      setLoading(true)
      const res = await resultsApi.listExamResults(selectedExamId)
      setTermResults(res)
    } catch (err: any) {
      setAlert({ type: 'error', message: 'Failed to load class marksheet.' })
    } finally {
      setLoading(false)
    }
  }

  const triggerWorkflowAction = async () => {
    if (!selectedExamId || !workflowDialog.action || (!canApprove && workflowDialog.action !== 'SUBMIT_FOR_REVIEW')) return
    try {
      setLoading(true)
      await resultsApi.processApprovalWorkflow({
        exam_id: selectedExamId,
        action: workflowDialog.action as any,
        comments: workflowComment,
      })
      setAlert({ type: 'success', message: `Status updated successfully: ${workflowDialog.action}` })
      setWorkflowDialog({ open: false, action: '', title: '' })
      setWorkflowComment('')
      loadExamResults()
    } catch (err: any) {
      setAlert({ type: 'error', message: err.response?.data?.error?.message || 'Workflow transition failed.' })
    } finally {
      setLoading(false)
    }
  }

  // Tab 2: Revision Dialog
  const handleOpenRevision = (
    subjectResultId: string,
    curTheory = 0,
    curPractical = 0,
    curInternal = 0
  ) => {
    setTargetResultId(subjectResultId)
    setRevisedTheory(curTheory)
    setRevisedPractical(curPractical)
    setRevisedInternal(curInternal)
    setRevisionReason('')
    setRevisionDialog(true)
  }

  const handleSaveRevision = async () => {
    if (!targetResultId || !revisionReason.trim()) {
      setAlert({ type: 'error', message: 'Mandatory revision reason must be provided.' })
      return
    }
    try {
      setLoading(true)
      await resultsApi.reviseMarks({
        subject_result_id: targetResultId,
        theory_marks: revisedTheory,
        practical_marks: revisedPractical,
        internal_marks: revisedInternal,
        revision_reason: revisionReason,
      })
      setAlert({ type: 'success', message: 'Marks revised and revision ledger updated.' })
      setRevisionDialog(false)
      loadExamResults()
      const revs = await resultsApi.getRevisionHistory(targetResultId)
      setRevisions(revs)
    } catch (err: any) {
      setAlert({ type: 'error', message: err.response?.data?.error?.message || 'Failed to revise marks.' })
    } finally {
      setLoading(false)
    }
  }

  // Tab 3: Re-Evaluations
  const loadReevaluations = async () => {
    try {
      setLoading(true)
      const res = await resultsApi.listReevaluations()
      setReevaluations(res)
    } catch (err: any) {
      setAlert({ type: 'error', message: 'Failed to load re-evaluation appeals.' })
    } finally {
      setLoading(false)
    }
  }

  const handleResolveReEval = async () => {
    if (!selectedReEval || !reEvalRemarks.trim()) {
      setAlert({ type: 'error', message: 'Reviewer remarks are required.' })
      return
    }
    try {
      setLoading(true)
      await resultsApi.resolveReevaluation(selectedReEval.id, {
        status: reEvalStatus,
        reviewer_remarks: reEvalRemarks,
        updated_theory_marks: reEvalStatus === 'APPROVED_UPDATED' ? reEvalTheory : undefined,
      })
      setAlert({ type: 'success', message: 'Re-evaluation resolved successfully.' })
      setReEvalDialog(false)
      loadReevaluations()
    } catch (err: any) {
      setAlert({ type: 'error', message: err.response?.data?.error?.message || 'Failed to resolve appeal.' })
    } finally {
      setLoading(false)
    }
  }

  // Tab 4: Report Card & PDF
  const loadStudentReportCard = async (studentId: string) => {
    if (!selectedExamId || !studentId) return
    try {
      setLoading(true)
      setSelectedStudentId(studentId)
      const card = await resultsApi.getStudentReportCard(selectedExamId, studentId)
      setActiveReportCard(card)
    } catch (err: any) {
      setAlert({ type: 'error', message: err.response?.data?.error?.message || 'Failed to load report card.' })
    } finally {
      setLoading(false)
    }
  }

  const handleDownloadPdf = async (studentId?: string) => {
    const sId = studentId || selectedStudentId
    if (!selectedExamId || !sId) return
    try {
      setLoading(true)
      const blob = await resultsApi.downloadReportCardPdf(selectedExamId, sId)
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `Report-Card-${sId}.pdf`
      document.body.appendChild(a)
      a.click()
      window.URL.revokeObjectURL(url)
      document.body.removeChild(a)
      setAlert({ type: 'success', message: 'Official Report Card PDF downloaded!' })
    } catch (err: any) {
      setAlert({ type: 'error', message: 'Failed to download report card PDF.' })
    } finally {
      setLoading(false)
    }
  }

  // Tab 5: Analytics
  const loadAnalytics = async () => {
    if (!selectedExamId) return
    try {
      setLoading(true)
      const res = await resultsApi.getClassAnalytics(selectedExamId)
      setAnalytics(res)
    } catch (err: any) {
      setAlert({ type: 'error', message: 'Failed to load class analytics.' })
    } finally {
      setLoading(false)
    }
  }

  const getStatusChipColor = (status: string) => {
    switch (status) {
      case 'PUBLISHED':
        return 'success'
      case 'APPROVED':
        return 'primary'
      case 'IN_REVIEW':
      case 'SUBMITTED':
        return 'warning'
      case 'DRAFT':
      default:
        return 'default'
    }
  }

  return (
    <Box sx={{ maxWidth: 1440, margin: '0 auto' }}>
      {/* Page Header */}
      <Box sx={{ mb: 3 }}>
        <PageHeader
          title="Results & Report Cards"
          description="Enter marks, approve results, and publish report cards."
          icon={<ResultsIcon />}
        >
          <Button variant="outlined" startIcon={<RefreshIcon />} onClick={loadAcademicMeta}>
            Refresh
          </Button>
        </PageHeader>
      </Box>

      {/* Alert Banner */}
      {alert && (
        <Alert severity={alert.type} sx={{ mb: 2 }} onClose={() => setAlert(null)}>
          {alert.message}
        </Alert>
      )}

      {/* Global Academic Filter Strip */}
      <Card variant="outlined" sx={{ mb: 3 }}>
        <CardContent sx={{ pb: '16px !important' }}>
          <Grid container spacing={2}>
            <Grid item xs={12} sm={6} md={3}>
              <TextField
                select
                fullWidth
                size="small"
                label="Examination"
                value={selectedExamId}
                onChange={(e) => setSelectedExamId(e.target.value)}
              >
                {examinations.map((ex) => (
                  <MenuItem key={ex.id} value={ex.id}>
                    {ex.title} ({ex.exam_type})
                  </MenuItem>
                ))}
              </TextField>
            </Grid>
            <Grid item xs={12} sm={6} md={3}>
              <TextField fullWidth size="small" label="Academic Session"
                value={sessions.find((item) => item.id === selectedSessionId)?.name ?? ''}
                slotProps={{ htmlInput: { readOnly: true } }} />
            </Grid>
            <Grid item xs={12} sm={6} md={3}>
              <TextField fullWidth size="small" label="Cohort"
                value={selectedExam?.course_name ?? selectedExam?.class_name ?? 'All enrolled students'}
                slotProps={{ htmlInput: { readOnly: true } }} />
            </Grid>
            <Grid item xs={12} sm={6} md={3}>
              <TextField
                select
                fullWidth
                size="small"
                label="Subject"
                value={selectedSubject}
                disabled={Boolean(selectedExam?.subject_id)}
                onChange={(e) => setSelectedSubjectId(e.target.value)}
              >
                {subjects.map((sub) => (
                  <MenuItem key={sub.id} value={sub.id}>
                    {sub.name} ({sub.code})
                  </MenuItem>
                ))}
              </TextField>
            </Grid>
          </Grid>
        </CardContent>
      </Card>

      {loading && <LinearProgress sx={{ mb: 2 }} />}

      {/* Module Navigation Tabs */}
      <Tabs
        value={activeTab}
        onChange={(_, val) => setActiveTab(val)}
        sx={{ borderBottom: 1, borderColor: 'divider', mb: 3 }}
      >
        <Tab icon={<ResultsIcon />} iconPosition="start" label="Subject Marks Entry" />
        <Tab icon={<MarksheetIcon />} iconPosition="start" label="Marksheet & Approval Workflow" />
        <Tab icon={<RevisionsIcon />} iconPosition="start" label="Marks Revisions Audit" />
        <Tab icon={<ReEvalIcon />} iconPosition="start" label="Re-Evaluation Appeals" />
        <Tab icon={<PdfIcon />} iconPosition="start" label="Official Report Cards" />
        <Tab icon={<AnalyticsIcon />} iconPosition="start" label="Performance Analytics" />
      </Tabs>

      {/* ── TAB 0: SUBJECT MARKS ENTRY ────────────────────────────────────────── */}
      {activeTab === 0 && (
        <Card variant="outlined">
          <CardContent>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
              <Typography variant="h6" fontWeight={600}>
                Subject-Wise Marks Roster Entry
              </Typography>
              <Button
                variant="contained"
                startIcon={<SaveIcon />}
                onClick={handleSaveMarks}
                disabled={marksEntries.length === 0 || loading}
              >
                Save All Marks
              </Button>
            </Box>

            <TableContainer component={Paper} variant="outlined" sx={{ overflowX: 'auto', width: '100%' }}>
              <Table size="small" sx={{ minWidth: 600 }}>
                <TableHead sx={{ backgroundColor: 'action.hover' }}>
                  <TableRow>
                    <TableCell>#</TableCell>
                    <TableCell>Student Name</TableCell>
                    <TableCell>Admission No</TableCell>
                    <TableCell width={110}>Theory (70)</TableCell>
                    <TableCell width={110}>Practical (20)</TableCell>
                    <TableCell width={110}>Internal (10)</TableCell>
                    <TableCell width={110}>Assignment</TableCell>
                    <TableCell>Total</TableCell>
                    <TableCell>Preview %</TableCell>
                    <TableCell>Remarks</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {marksEntries.map((row, idx) => {
                    const total =
                      Number(row.theory_marks || 0) +
                      Number(row.practical_marks || 0) +
                      Number(row.internal_marks || 0) +
                      Number(row.assignment_marks || 0)
                    const max =
                      Number(row.theory_max_marks || 70) +
                      Number(row.practical_max_marks || 20) +
                      Number(row.internal_max_marks || 10) +
                      Number(row.assignment_max_marks || 0)
                    const pct = max > 0 ? ((total / max) * 100).toFixed(1) : '0.0'

                    return (
                      <TableRow key={row.student_id}>
                        <TableCell>{idx + 1}</TableCell>
                        <TableCell sx={{ fontWeight: 600 }}>{row.student_name}</TableCell>
                        <TableCell>{row.admission_number}</TableCell>
                        <TableCell>
                          <TextField
                            size="small"
                            type="number"
                            value={row.theory_marks}
                            onChange={(e) => handleMarksChange(idx, 'theory_marks', Number(e.target.value))}
                            inputProps={{ min: 0, max: row.theory_max_marks }}
                          />
                        </TableCell>
                        <TableCell>
                          <TextField
                            size="small"
                            type="number"
                            value={row.practical_marks}
                            onChange={(e) => handleMarksChange(idx, 'practical_marks', Number(e.target.value))}
                            inputProps={{ min: 0, max: row.practical_max_marks }}
                          />
                        </TableCell>
                        <TableCell>
                          <TextField
                            size="small"
                            type="number"
                            value={row.internal_marks}
                            onChange={(e) => handleMarksChange(idx, 'internal_marks', Number(e.target.value))}
                            inputProps={{ min: 0, max: row.internal_max_marks }}
                          />
                        </TableCell>
                        <TableCell>
                          <TextField
                            size="small"
                            type="number"
                            value={row.assignment_marks}
                            onChange={(e) => handleMarksChange(idx, 'assignment_marks', Number(e.target.value))}
                            inputProps={{ min: 0 }}
                          />
                        </TableCell>
                        <TableCell>
                          <Typography fontWeight={700} color="primary">
                            {total}
                          </Typography>
                        </TableCell>
                        <TableCell>
                          <Chip
                            size="small"
                            label={`${pct}%`}
                            color={Number(pct) >= 35 ? 'success' : 'error'}
                          />
                        </TableCell>
                        <TableCell>
                          <TextField
                            size="small"
                            placeholder="Optional note"
                            value={row.remarks || ''}
                            onChange={(e) => handleMarksChange(idx, 'remarks', e.target.value)}
                          />
                        </TableCell>
                      </TableRow>
                    )
                  })}
                  {marksEntries.length === 0 && (
                    <TableRow>
                      <TableCell colSpan={10} align="center" sx={{ py: 3 }}>
                        No enrolled students found for the selected academic group.
                      </TableCell>
                    </TableRow>
                  )}
                </TableBody>
              </Table>
            </TableContainer>
          </CardContent>
        </Card>
      )}

      {/* ── TAB 1: MARKSHEET & APPROVAL WORKFLOW ─────────────────────────────── */}
      {activeTab === 1 && (
        <Card variant="outlined">
          <CardContent>
            {/* Workflow Control Header */}
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
              <Box>
                <Typography variant="h6" fontWeight={600}>
                  Consolidated Class Marksheet
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Review student performance, pass/fail status, and execute multi-tier approval actions.
                </Typography>
              </Box>

              <Box sx={{ display: 'flex', gap: 1 }}>
                <Button
                  variant="outlined"
                  color="warning"
                  startIcon={<SubmitIcon />}
                  onClick={() =>
                    setWorkflowDialog({
                      open: true,
                      action: 'SUBMIT_FOR_REVIEW',
                      title: 'Submit Results for Administrative Review',
                    })
                  }
                >
                  Submit for Review
                </Button>
                <Button
                  variant="contained"
                  color="primary"
                  startIcon={<ApproveIcon />}
                  disabled={!canApprove}
                  onClick={() =>
                    setWorkflowDialog({
                      open: true,
                      action: 'APPROVE',
                      title: 'Approve Examination Results',
                    })
                  }
                >
                  Approve Results
                </Button>
                <Button
                  variant="contained"
                  color="success"
                  startIcon={<PublishIcon />}
                  disabled={!canApprove}
                  onClick={() =>
                    setWorkflowDialog({
                      open: true,
                      action: 'PUBLISH',
                      title: 'Publish Results Officially to Students & Parents',
                    })
                  }
                >
                  Publish Officially
                </Button>
              </Box>
            </Box>

            <TableContainer component={Paper} variant="outlined" sx={{ overflowX: 'auto', width: '100%' }}>
              <Table size="small" sx={{ minWidth: 600 }}>
                <TableHead sx={{ backgroundColor: 'action.hover' }}>
                  <TableRow>
                    <TableCell>Rank</TableCell>
                    <TableCell>Student</TableCell>
                    <TableCell>Admission No</TableCell>
                    <TableCell>Total Obtained</TableCell>
                    <TableCell>Max Marks</TableCell>
                    <TableCell>Percentage</TableCell>
                    <TableCell>Grade</TableCell>
                    <TableCell>CGPA</TableCell>
                    <TableCell>Attendance</TableCell>
                    <TableCell>Status</TableCell>
                    <TableCell>Approval</TableCell>
                    <TableCell align="center">Actions</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {termResults.map((t) => (
                    <TableRow key={t.id}>
                      <TableCell sx={{ fontWeight: 700 }}>#{t.rank || '-'}</TableCell>
                      <TableCell sx={{ fontWeight: 600 }}>{t.student_name}</TableCell>
                      <TableCell>{t.admission_number}</TableCell>
                      <TableCell>{t.total_obtained}</TableCell>
                      <TableCell>{t.total_max}</TableCell>
                      <TableCell>
                        <b>{t.overall_percentage}%</b>
                      </TableCell>
                      <TableCell>
                        <Chip size="small" label={t.overall_grade} color="primary" variant="outlined" />
                      </TableCell>
                      <TableCell>{t.cgpa ?? 'N/A'}</TableCell>
                      <TableCell>{t.attendance_percentage ? `${t.attendance_percentage}%` : 'N/A'}</TableCell>
                      <TableCell>
                        <Chip
                          size="small"
                          label={t.is_passed ? 'PASSED' : 'FAILED'}
                          color={t.is_passed ? 'success' : 'error'}
                        />
                      </TableCell>
                      <TableCell>
                        <Chip
                          size="small"
                          label={t.approval_status}
                          color={getStatusChipColor(t.approval_status) as any}
                        />
                      </TableCell>
                      <TableCell align="center">
                        <Box sx={{ display: 'flex', justifyContent: 'center', gap: 0.5 }}>
                          <Tooltip title="Revise Marks (Audit Logged)">
                            <IconButton
                              size="small"
                              color="secondary"
                              onClick={() => {
                                if (t.subject_results && t.subject_results.length > 0) {
                                  const firstSub = t.subject_results[0]
                                  handleOpenRevision(
                                    firstSub.id,
                                    Number(firstSub.theory_marks),
                                    Number(firstSub.practical_marks),
                                    Number(firstSub.internal_marks)
                                  )
                                }
                              }}
                            >
                              <RevisionsIcon fontSize="small" />
                            </IconButton>
                          </Tooltip>
                          <Tooltip title="Download Official PDF">
                            <IconButton
                              size="small"
                              color="primary"
                              onClick={() => handleDownloadPdf(t.student_id)}
                            >
                              <DownloadIcon fontSize="small" />
                            </IconButton>
                          </Tooltip>
                        </Box>
                      </TableCell>
                    </TableRow>
                  ))}
                  {termResults.length === 0 && (
                    <TableRow>
                      <TableCell colSpan={12} align="center" sx={{ py: 3 }}>
                        No examination results generated yet. Enter subject marks to calculate term results.
                      </TableCell>
                    </TableRow>
                  )}
                </TableBody>
              </Table>
            </TableContainer>
          </CardContent>
        </Card>
      )}

      {/* ── TAB 2: MARKS REVISION AUDIT TRAIL ─────────────────────────────────── */}
      {activeTab === 2 && (
        <Card variant="outlined">
          <CardContent>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
              <Box>
                <Typography variant="h6" fontWeight={600}>
                  Marks Revision & Immutability Audit Ledger
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Published results cannot be modified without an explicit justification recorded in the permanent audit trail.
                </Typography>
              </Box>
            </Box>

            <Alert severity="info" sx={{ mb: 2 }}>
              To revise a published score, select a student from the marksheet or submit an approved re-evaluation resolution. Every modification logs previous marks, new marks, modifier identity, and authorization stamps.
            </Alert>

            <TableContainer component={Paper} variant="outlined" sx={{ overflowX: 'auto', width: '100%' }}>
              <Table size="small" sx={{ minWidth: 600 }}>
                <TableHead sx={{ backgroundColor: 'action.hover' }}>
                  <TableRow>
                    <TableCell>Modified At</TableCell>
                    <TableCell>Modified By</TableCell>
                    <TableCell>Revision Reason</TableCell>
                    <TableCell>Previous Total</TableCell>
                    <TableCell>Revised Total</TableCell>
                    <TableCell>Previous Grade</TableCell>
                    <TableCell>Revised Grade</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {revisions.map((rev) => (
                    <TableRow key={rev.id}>
                      <TableCell>{new Date(rev.modified_at).toLocaleString()}</TableCell>
                      <TableCell sx={{ fontWeight: 600 }}>{rev.modified_by_name || 'Staff'}</TableCell>
                      <TableCell>{rev.revision_reason}</TableCell>
                      <TableCell>{rev.previous_marks?.total_marks || '-'}</TableCell>
                      <TableCell sx={{ fontWeight: 700, color: 'primary.main' }}>
                        {rev.new_marks?.total_marks || '-'}
                      </TableCell>
                      <TableCell>{rev.previous_marks?.grade || '-'}</TableCell>
                      <TableCell sx={{ fontWeight: 700 }}>{rev.new_marks?.grade || '-'}</TableCell>
                    </TableRow>
                  ))}
                  {revisions.length === 0 && (
                    <TableRow>
                      <TableCell colSpan={7} align="center" sx={{ py: 3 }}>
                        No marks revisions logged. All examination scores remain in their pristine original entry state.
                      </TableCell>
                    </TableRow>
                  )}
                </TableBody>
              </Table>
            </TableContainer>
          </CardContent>
        </Card>
      )}

      {/* ── TAB 3: RE-EVALUATION APPEALS ───────────────────────────────────────── */}
      {activeTab === 3 && (
        <Card variant="outlined">
          <CardContent>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
              <Box>
                <Typography variant="h6" fontWeight={600}>
                  Student Re-Evaluation Appeals
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Review student/parent re-checking requests, re-score assessment components, and update records.
                </Typography>
              </Box>
            </Box>

            <TableContainer component={Paper} variant="outlined" sx={{ overflowX: 'auto', width: '100%' }}>
              <Table size="small" sx={{ minWidth: 600 }}>
                <TableHead sx={{ backgroundColor: 'action.hover' }}>
                  <TableRow>
                    <TableCell>Date</TableCell>
                    <TableCell>Student</TableCell>
                    <TableCell>Subject</TableCell>
                    <TableCell>Student Reason</TableCell>
                    <TableCell>Status</TableCell>
                    <TableCell>Reviewer Remarks</TableCell>
                    <TableCell align="center">Actions</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {reevaluations.map((r) => (
                    <TableRow key={r.id}>
                      <TableCell>{new Date(r.created_at).toLocaleDateString()}</TableCell>
                      <TableCell sx={{ fontWeight: 600 }}>{r.student_name}</TableCell>
                      <TableCell>{r.subject_name}</TableCell>
                      <TableCell>{r.reason}</TableCell>
                      <TableCell>
                        <Chip
                          size="small"
                          label={r.status}
                          color={
                            r.status === 'APPROVED_UPDATED'
                              ? 'success'
                              : r.status === 'REJECTED'
                              ? 'error'
                              : 'warning'
                          }
                        />
                      </TableCell>
                      <TableCell>{r.reviewer_remarks || '-'}</TableCell>
                      <TableCell align="center">
                        {r.status === 'PENDING' && (
                          <Button
                            size="small"
                            variant="outlined"
                            onClick={() => {
                              setSelectedReEval(r)
                              setReEvalRemarks('')
                              setReEvalTheory(0)
                              setReEvalDialog(true)
                            }}
                          >
                            Resolve Appeal
                          </Button>
                        )}
                      </TableCell>
                    </TableRow>
                  ))}
                  {reevaluations.length === 0 && (
                    <TableRow>
                      <TableCell colSpan={7} align="center" sx={{ py: 3 }}>
                        No pending re-evaluation appeals submitted.
                      </TableCell>
                    </TableRow>
                  )}
                </TableBody>
              </Table>
            </TableContainer>
          </CardContent>
        </Card>
      )}

      {/* ── TAB 4: OFFICIAL REPORT CARD VIEWER ─────────────────────────────────── */}
      {activeTab === 4 && (
        <Card variant="outlined">
          <CardContent>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
              <Box sx={{ width: 350 }}>
                <TextField
                  select
                  fullWidth
                  size="small"
                  label="Select Student to Preview Report Card"
                  value={selectedStudentId}
                  onChange={(e) => loadStudentReportCard(e.target.value)}
                >
                  {termResults.map((t) => (
                    <MenuItem key={t.student_id} value={t.student_id}>
                      {t.student_name} ({t.admission_number})
                    </MenuItem>
                  ))}
                </TextField>
              </Box>

              {activeReportCard && (
                <Button
                  variant="contained"
                  color="primary"
                  startIcon={<DownloadIcon />}
                  onClick={() => handleDownloadPdf()}
                >
                  Download Official PDF
                </Button>
              )}
            </Box>

            {activeReportCard ? (
              <Box
                sx={{
                  border: '2px solid #1e3a8a',
                  borderRadius: 2,
                  p: 4,
                  backgroundColor: '#ffffff',
                }}
              >
                {/* School Header */}
                <Box sx={{ textAlign: 'center', mb: 3 }}>
                  <Typography variant="h5" fontWeight={700} color="#1e3a8a">
                    ST. XAVIER'S MODEL ACADEMY
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Affiliated to Central Board of Secondary Education • Institutional Report Card
                  </Typography>
                  <Divider sx={{ my: 1.5, borderColor: '#1e3a8a', borderWidth: 1 }} />
                  <Typography variant="subtitle1" fontWeight={700}>
                    ACADEMIC EVALUATION & ACHIEVEMENT REPORT
                  </Typography>
                </Box>

                {/* Student Info Box */}
                <Grid container spacing={2} sx={{ mb: 3, p: 2, bgcolor: '#f8fafc', borderRadius: 1 }}>
                  <Grid item xs={6} sm={3}>
                    <Typography variant="caption" color="text.secondary">
                      Student Name:
                    </Typography>
                    <Typography fontWeight={600}>{activeReportCard.student_name}</Typography>
                  </Grid>
                  <Grid item xs={6} sm={3}>
                    <Typography variant="caption" color="text.secondary">
                      Admission Number:
                    </Typography>
                    <Typography fontWeight={600}>{activeReportCard.admission_number}</Typography>
                  </Grid>
                  <Grid item xs={6} sm={3}>
                    <Typography variant="caption" color="text.secondary">
                      Examination:
                    </Typography>
                    <Typography fontWeight={600}>{activeReportCard.exam_title}</Typography>
                  </Grid>
                  <Grid item xs={6} sm={3}>
                    <Typography variant="caption" color="text.secondary">
                      Academic Session:
                    </Typography>
                    <Typography fontWeight={600}>{activeReportCard.academic_session_name || '2026-2027'}</Typography>
                  </Grid>
                </Grid>

                {/* Subject-Wise Assessment Table */}
                <TableContainer component={Paper} variant="outlined" sx={{ mb: 3, overflowX: 'auto', width: '100%' }}>
                  <Table size="small" sx={{ minWidth: 600 }}>
                    <TableHead sx={{ backgroundColor: '#1e3a8a' }}>
                      <TableRow>
                        <TableCell sx={{ color: 'white', fontWeight: 600 }}>Subject</TableCell>
                        <TableCell sx={{ color: 'white', fontWeight: 600 }} align="center">Theory</TableCell>
                        <TableCell sx={{ color: 'white', fontWeight: 600 }} align="center">Practical</TableCell>
                        <TableCell sx={{ color: 'white', fontWeight: 600 }} align="center">Internal</TableCell>
                        <TableCell sx={{ color: 'white', fontWeight: 600 }} align="center">Total</TableCell>
                        <TableCell sx={{ color: 'white', fontWeight: 600 }} align="center">Max</TableCell>
                        <TableCell sx={{ color: 'white', fontWeight: 600 }} align="center">Percentage</TableCell>
                        <TableCell sx={{ color: 'white', fontWeight: 600 }} align="center">Grade</TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {(activeReportCard.subject_results || []).map((sub) => (
                        <TableRow key={sub.id}>
                          <TableCell sx={{ fontWeight: 600 }}>{sub.subject_name}</TableCell>
                          <TableCell align="center">{sub.theory_marks}</TableCell>
                          <TableCell align="center">{sub.practical_marks}</TableCell>
                          <TableCell align="center">{sub.internal_marks}</TableCell>
                          <TableCell align="center" sx={{ fontWeight: 700 }}>
                            {sub.total_marks}
                          </TableCell>
                          <TableCell align="center">{sub.max_marks}</TableCell>
                          <TableCell align="center">{sub.percentage}%</TableCell>
                          <TableCell align="center">
                            <Chip size="small" label={sub.grade || '-'} color="primary" />
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </TableContainer>

                {/* Summary & Attendance Panel */}
                <Grid container spacing={2} sx={{ mb: 4, p: 2, border: '1px solid #cbd5e1', borderRadius: 1 }}>
                  <Grid item xs={12} sm={3}>
                    <Typography variant="caption" color="text.secondary">
                      Total Obtained:
                    </Typography>
                    <Typography variant="h6" fontWeight={700} color="primary">
                      {activeReportCard.total_obtained} / {activeReportCard.total_max}
                    </Typography>
                  </Grid>
                  <Grid item xs={12} sm={3}>
                    <Typography variant="caption" color="text.secondary">
                      Overall Percentage:
                    </Typography>
                    <Typography variant="h6" fontWeight={700}>
                      {activeReportCard.overall_percentage}%
                    </Typography>
                  </Grid>
                  <Grid item xs={12} sm={3}>
                    <Typography variant="caption" color="text.secondary">
                      Overall Grade:
                    </Typography>
                    <Typography variant="h6" fontWeight={700}>
                      {activeReportCard.overall_grade}
                    </Typography>
                  </Grid>
                  <Grid item xs={12} sm={3}>
                    <Typography variant="caption" color="text.secondary">
                      Result Status:
                    </Typography>
                    <Typography
                      variant="h6"
                      fontWeight={700}
                      color={activeReportCard.is_passed ? 'success.main' : 'error.main'}
                    >
                      {activeReportCard.is_passed ? 'PASSED' : 'FAILED'}
                    </Typography>
                  </Grid>
                </Grid>

                {/* Signature Strip */}
                <Box sx={{ display: 'flex', justifyContent: 'space-between', mt: 6, pt: 3, borderTop: '1px dashed #cbd5e1' }}>
                  <Box sx={{ textAlign: 'center' }}>
                    <Typography variant="body2">___________________________</Typography>
                    <Typography variant="caption" fontWeight={600}>Class Teacher</Typography>
                  </Box>
                  <Box sx={{ textAlign: 'center' }}>
                    <Typography variant="body2">___________________________</Typography>
                    <Typography variant="caption" fontWeight={600}>Exam Controller</Typography>
                  </Box>
                  <Box sx={{ textAlign: 'center' }}>
                    <Typography variant="body2">___________________________</Typography>
                    <Typography variant="caption" fontWeight={600}>Principal / Director</Typography>
                  </Box>
                </Box>
              </Box>
            ) : (
              <Box sx={{ textAlign: 'center', py: 6 }}>
                <PdfIcon sx={{ fontSize: 60, color: 'text.disabled', mb: 1 }} />
                <Typography color="text.secondary">
                  Please select an enrolled student above to render the official report card preview.
                </Typography>
              </Box>
            )}
          </CardContent>
        </Card>
      )}

      {/* ── TAB 5: CLASS PERFORMANCE ANALYTICS ────────────────────────────────── */}
      {activeTab === 5 && (
        <Box>
          {analytics ? (
            <Grid container spacing={3}>
              {/* KPI Cards */}
              <Grid item xs={12} sm={6} md={3}>
                <Card variant="outlined">
                  <CardContent sx={{ textAlign: 'center' }}>
                    <Typography variant="caption" color="text.secondary">
                      Total Appeared
                    </Typography>
                    <Typography variant="h4" fontWeight={700}>
                      {analytics.total_students}
                    </Typography>
                  </CardContent>
                </Card>
              </Grid>
              <Grid item xs={12} sm={6} md={3}>
                <Card variant="outlined">
                  <CardContent sx={{ textAlign: 'center' }}>
                    <Typography variant="caption" color="text.secondary">
                      Pass Percentage
                    </Typography>
                    <Typography variant="h4" fontWeight={700} color="success.main">
                      {analytics.pass_percentage}%
                    </Typography>
                  </CardContent>
                </Card>
              </Grid>
              <Grid item xs={12} sm={6} md={3}>
                <Card variant="outlined">
                  <CardContent sx={{ textAlign: 'center' }}>
                    <Typography variant="caption" color="text.secondary">
                      Class Average Score
                    </Typography>
                    <Typography variant="h4" fontWeight={700} color="primary.main">
                      {analytics.class_average_percentage}%
                    </Typography>
                  </CardContent>
                </Card>
              </Grid>
              <Grid item xs={12} sm={6} md={3}>
                <Card variant="outlined">
                  <CardContent sx={{ textAlign: 'center' }}>
                    <Typography variant="caption" color="text.secondary">
                      Score Range (High - Low)
                    </Typography>
                    <Typography variant="h4" fontWeight={700}>
                      {analytics.highest_percentage}% - {analytics.lowest_percentage}%
                    </Typography>
                  </CardContent>
                </Card>
              </Grid>

              {/* Subject Breakdown Table */}
              <Grid item xs={12}>
                <Card variant="outlined">
                  <CardContent>
                    <Typography variant="h6" fontWeight={600} sx={{ mb: 2 }}>
                      Subject-Wise Performance Metrics
                    </Typography>
                    <TableContainer component={Paper} variant="outlined" sx={{ overflowX: 'auto', width: '100%' }}>
                      <Table size="small" sx={{ minWidth: 600 }}>
                        <TableHead sx={{ backgroundColor: 'action.hover' }}>
                          <TableRow>
                            <TableCell>Subject</TableCell>
                            <TableCell>Code</TableCell>
                            <TableCell align="center">Average Marks</TableCell>
                            <TableCell align="center">Highest Marks</TableCell>
                            <TableCell align="center">Lowest Marks</TableCell>
                            <TableCell align="center">Pass Percentage</TableCell>
                          </TableRow>
                        </TableHead>
                        <TableBody>
                          {analytics.subject_analytics.map((sub) => (
                            <TableRow key={sub.subject_id}>
                              <TableCell sx={{ fontWeight: 600 }}>{sub.subject_name}</TableCell>
                              <TableCell>{sub.subject_code}</TableCell>
                              <TableCell align="center">{sub.average_marks}</TableCell>
                              <TableCell align="center">{sub.highest_marks}</TableCell>
                              <TableCell align="center">{sub.lowest_marks}</TableCell>
                              <TableCell align="center">
                                <Chip
                                  size="small"
                                  label={`${sub.pass_percentage}%`}
                                  color={sub.pass_percentage >= 50 ? 'success' : 'error'}
                                />
                              </TableCell>
                            </TableRow>
                          ))}
                        </TableBody>
                      </Table>
                    </TableContainer>
                  </CardContent>
                </Card>
              </Grid>
            </Grid>
          ) : (
            <Box sx={{ textAlign: 'center', py: 6 }}>
              <Typography color="text.secondary">No analytics available for this examination.</Typography>
            </Box>
          )}
        </Box>
      )}

      {/* Workflow Confirmation Dialog */}
      <Dialog open={workflowDialog.open} onClose={() => setWorkflowDialog({ open: false, action: '', title: '' })}>
        <DialogTitle>{workflowDialog.title}</DialogTitle>
        <DialogContent>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            Confirm this workflow action for examination results. Authorized state transition will be applied across all students in this session.
          </Typography>
          <TextField
            fullWidth
            label="Comments / Directives (Optional)"
            multiline
            rows={3}
            value={workflowComment}
            onChange={(e) => setWorkflowComment(e.target.value)}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setWorkflowDialog({ open: false, action: '', title: '' })}>Cancel</Button>
          <Button variant="contained" onClick={triggerWorkflowAction} disabled={loading}>
            Confirm Action
          </Button>
        </DialogActions>
      </Dialog>

      {/* Marks Revision Dialog */}
      <Dialog open={revisionDialog} onClose={() => setRevisionDialog(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Revise Marks (Audit Logged)</DialogTitle>
        <DialogContent>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            Provide the corrected marks along with a mandatory audit justification reason.
          </Typography>
          <Grid container spacing={2}>
            <Grid item xs={4}>
              <TextField
                fullWidth
                size="small"
                type="number"
                label="Theory Marks"
                value={revisedTheory}
                onChange={(e) => setRevisedTheory(Number(e.target.value))}
              />
            </Grid>
            <Grid item xs={4}>
              <TextField
                fullWidth
                size="small"
                type="number"
                label="Practical Marks"
                value={revisedPractical}
                onChange={(e) => setRevisedPractical(Number(e.target.value))}
              />
            </Grid>
            <Grid item xs={4}>
              <TextField
                fullWidth
                size="small"
                type="number"
                label="Internal Marks"
                value={revisedInternal}
                onChange={(e) => setRevisedInternal(Number(e.target.value))}
              />
            </Grid>
            <Grid item xs={12}>
              <TextField
                fullWidth
                required
                multiline
                rows={3}
                label="Mandatory Revision Reason"
                placeholder="e.g. Scrutiny re-check revealed missing marks in Section B totaling"
                value={revisionReason}
                onChange={(e) => setRevisionReason(e.target.value)}
              />
            </Grid>
          </Grid>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setRevisionDialog(false)}>Cancel</Button>
          <Button variant="contained" onClick={handleSaveRevision} disabled={loading}>
            Save & Record Audit Log
          </Button>
        </DialogActions>
      </Dialog>

      {/* Resolve Re-Evaluation Dialog */}
      <Dialog open={reEvalDialog} onClose={() => setReEvalDialog(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Resolve Student Re-Evaluation Appeal</DialogTitle>
        <DialogContent>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            Student: <b>{selectedReEval?.student_name}</b> | Subject: <b>{selectedReEval?.subject_name}</b>
          </Typography>
          <TextField
            select
            fullWidth
            size="small"
            label="Resolution Action"
            value={reEvalStatus}
            onChange={(e) => setReEvalStatus(e.target.value as any)}
            sx={{ mb: 2 }}
          >
            <MenuItem value="APPROVED_UPDATED">Approve Appeal & Update Marks</MenuItem>
            <MenuItem value="REJECTED">Reject Appeal (No Change)</MenuItem>
          </TextField>

          {reEvalStatus === 'APPROVED_UPDATED' && (
            <TextField
              fullWidth
              size="small"
              type="number"
              label="Updated Theory Marks"
              value={reEvalTheory}
              onChange={(e) => setReEvalTheory(Number(e.target.value))}
              sx={{ mb: 2 }}
            />
          )}

          <TextField
            fullWidth
            required
            multiline
            rows={3}
            label="Reviewer Remarks / Verification Findings"
            value={reEvalRemarks}
            onChange={(e) => setReEvalRemarks(e.target.value)}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setReEvalDialog(false)}>Cancel</Button>
          <Button variant="contained" onClick={handleResolveReEval} disabled={loading}>
            Submit Resolution
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  )
}
