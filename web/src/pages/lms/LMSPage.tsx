import { PageHeader } from '@/components/ui/PageHeader'
import React, { useState, useEffect } from 'react'
import { useSearchParams } from 'react-router-dom'
import {
  Box,
  Typography,
  Card,
  CardContent,
  CardActions,
  Grid,
  Button,
  TextField,
  MenuItem,
  Chip,
  Tabs,
  Tab,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  IconButton,
  Tooltip,
  Alert,
  CircularProgress,
  Divider,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  LinearProgress,
  Stack,
  Switch,
  FormControlLabel,
} from '@mui/material'
import {
  MenuBook,
  Assignment as AssignmentIcon,
  CloudUpload,
  Download,
  Visibility,
  History,
  Delete,
  Edit,
  Warning,
  Assessment,
  Add,
  AttachFile,
  School,
  PlayCircleFilled,
  Description,
  PictureAsPdf,
  Refresh,
} from '@mui/icons-material'
import { lmsApi, StudyMaterial, Assignment, AssignmentSubmission, AssignmentReport } from '../../api/lms'
import { academicsApi } from '../../api/academics'

export default function LMSPage() {
  const [params] = useSearchParams()
  const requestedTab = params.get('tab')
  const [activeTab, setActiveTab] = useState(requestedTab === 'assignments' ? 2 : 0)
  useEffect(() => { if (requestedTab === 'assignments') setActiveTab(2) }, [requestedTab])
  const [loading, setLoading] = useState(false)
  const [alertInfo, setAlertInfo] = useState<{ type: 'success' | 'error' | 'info'; message: string } | null>(null)

  // Academic dropdown data
  const [sessions, setSessions] = useState<any[]>([])
  const [subjects, setSubjects] = useState<any[]>([])
  const [classes, setClasses] = useState<any[]>([])

  // Study Materials State
  const [materials, setMaterials] = useState<StudyMaterial[]>([])
  const [searchQuery, setSearchQuery] = useState('')
  const [categoryFilter, setCategoryFilter] = useState('ALL')
  const [subjectFilter, setSubjectFilter] = useState('ALL')
  const [selectedMaterial, setSelectedMaterial] = useState<StudyMaterial | null>(null)
  const [versionModalOpen, setVersionModalOpen] = useState(false)
  const [uploadVersionFile, setUploadVersionFile] = useState<File | null>(null)
  const [versionSummary, setVersionSummary] = useState('')

  // Upload Material Form State
  const [materialTitle, setMaterialTitle] = useState('')
  const [materialDescription, setMaterialDescription] = useState('')
  const [materialChapter, setMaterialChapter] = useState('')
  const [materialType, setMaterialType] = useState('PDF')
  const [materialCategory, setMaterialCategory] = useState('LECTURE_NOTE')
  const [materialSessionId, setMaterialSessionId] = useState('')
  const [materialSubjectId, setMaterialSubjectId] = useState('')
  const [materialClassId, setMaterialClassId] = useState('')
  const [materialFile, setMaterialFile] = useState<File | null>(null)
  const [materialExternalUrl, setMaterialExternalUrl] = useState('')
  const [materialTags, setMaterialTags] = useState('')
  const [materialIsPublished, setMaterialIsPublished] = useState(true)

  // Assignments State
  const [assignments, setAssignments] = useState<Assignment[]>([])
  const [selectedAssignment, setSelectedAssignment] = useState<Assignment | null>(null)
  const [assignmentSubmissions, setAssignmentSubmissions] = useState<AssignmentSubmission[]>([])
  const [assignmentReport, setAssignmentReport] = useState<AssignmentReport | null>(null)
  const [reportModalOpen, setReportModalOpen] = useState(false)

  // Create Assignment State
  const [createAssignOpen, setCreateAssignOpen] = useState(false)
  const [assignTitle, setAssignTitle] = useState('')
  const [assignDescription, setAssignDescription] = useState('')
  const [assignDueDate, setAssignDueDate] = useState('')
  const [assignTotalMarks, setAssignTotalMarks] = useState('100')
  const [assignPassMarks, setAssignPassMarks] = useState('40')
  const [assignPenalty, setAssignPenalty] = useState('10')
  const [assignAllowLate, setAssignAllowLate] = useState(true)
  const [assignSessionId, setAssignSessionId] = useState('')
  const [assignSubjectId, setAssignSubjectId] = useState('')
  const [assignClassId, setAssignClassId] = useState('')
  const [assignInstructionsFile, setAssignInstructionsFile] = useState<File | null>(null)

  // Student Submission State
  const [submitModalOpen, setSubmitModalOpen] = useState(false)
  const [submissionText, setSubmissionText] = useState('')
  const [submissionFile, setSubmissionFile] = useState<File | null>(null)

  // Teacher Evaluation Modal State
  const [evalModalOpen, setEvalModalOpen] = useState(false)
  const [evaluatingSub, setEvaluatingSub] = useState<AssignmentSubmission | null>(null)
  const [evalMarks, setEvalMarks] = useState('')
  const [evalGrade, setEvalGrade] = useState('A')
  const [evalFeedback, setEvalFeedback] = useState('')

  // Preview Dialog State
  const [previewModalOpen, setPreviewModalOpen] = useState(false)
  const [previewUrl, setPreviewUrl] = useState<string | null>(null)
  const [previewTitle, setPreviewTitle] = useState('')

  useEffect(() => {
    loadAcademicLookups()
    loadMaterials()
    loadAssignments()
  }, [])

  const loadAcademicLookups = async () => {
    try {
      const sessRes = await academicsApi.getSessions()
      const sessList = sessRes.data || []
      setSessions(sessList)
      if (sessList.length > 0) {
        setMaterialSessionId(sessList[0].id)
        setAssignSessionId(sessList[0].id)
      }

      const subjRes = await academicsApi.getSubjects()
      setSubjects(subjRes.data || [])

      const classRes = await academicsApi.getClasses()
      setClasses(classRes.data || [])
    } catch (err) {
      console.error('Failed to load academic lookup metadata', err)
    }
  }

  const loadMaterials = async () => {
    setLoading(true)
    try {
      const res = await lmsApi.listMaterials({
        search: searchQuery || undefined,
        category: categoryFilter !== 'ALL' ? categoryFilter : undefined,
        subject_id: subjectFilter !== 'ALL' ? subjectFilter : undefined,
      })
      setMaterials(res.data || [])
    } catch (err: any) {
      setAlertInfo({ type: 'error', message: err.response?.data?.error?.message || 'Failed to load materials.' })
    } finally {
      setLoading(false)
    }
  }

  const loadAssignments = async () => {
    try {
      const res = await lmsApi.listAssignments()
      setAssignments(res.data || [])
    } catch (err: any) {
      console.error('Failed to load assignments', err)
    }
  }

  // Handle Material Upload
  const handleUploadMaterial = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!materialTitle || !materialSessionId) {
      setAlertInfo({ type: 'error', message: 'Please provide Title and Academic Session.' })
      return
    }

    try {
      setLoading(true)
      if (materialFile) {
        const formData = new FormData()
        formData.append('file', materialFile)
        formData.append('title', materialTitle)
        formData.append('academic_session_id', materialSessionId)
        formData.append('description', materialDescription)
        formData.append('chapter', materialChapter)
        formData.append('material_type', materialType)
        formData.append('category', materialCategory)
        if (materialSubjectId) formData.append('subject_id', materialSubjectId)
        if (materialClassId) formData.append('class_id', materialClassId)
        if (materialExternalUrl) formData.append('external_url', materialExternalUrl)
        if (materialTags) formData.append('tags_json', JSON.stringify(materialTags.split(',').map((t) => t.trim())))
        formData.append('is_published', materialIsPublished.toString())

        await lmsApi.uploadMaterialFile(formData)
      } else {
        await lmsApi.createMaterialJson({
          title: materialTitle,
          academic_session_id: materialSessionId,
          description: materialDescription,
          chapter: materialChapter,
          material_type: materialType,
          category: materialCategory,
          subject_id: materialSubjectId || undefined,
          class_id: materialClassId || undefined,
          external_url: materialExternalUrl || undefined,
          tags: materialTags ? materialTags.split(',').map((t) => t.trim()) : [],
          is_published: materialIsPublished,
        })
      }

      setAlertInfo({ type: 'success', message: 'Study material uploaded and published successfully!' })
      // Reset form
      setMaterialTitle('')
      setMaterialDescription('')
      setMaterialChapter('')
      setMaterialFile(null)
      setMaterialExternalUrl('')
      setMaterialTags('')
      setActiveTab(0)
      loadMaterials()
    } catch (err: any) {
      setAlertInfo({ type: 'error', message: err.response?.data?.error?.message || 'Failed to upload material.' })
    } finally {
      setLoading(false)
    }
  }

  // Handle Version Upload
  const handleUploadNewVersion = async () => {
    if (!selectedMaterial || !uploadVersionFile) return
    try {
      setLoading(true)
      const formData = new FormData()
      formData.append('file', uploadVersionFile)
      formData.append('change_summary', versionSummary || 'Updated version')
      const res = await lmsApi.uploadMaterialVersion(selectedMaterial.id, formData)
      setSelectedMaterial(res.data)
      setVersionModalOpen(false)
      setUploadVersionFile(null)
      setVersionSummary('')
      setAlertInfo({ type: 'success', message: 'New version uploaded successfully!' })
      loadMaterials()
    } catch (err: any) {
      setAlertInfo({ type: 'error', message: err.response?.data?.error?.message || 'Failed to upload new version.' })
    } finally {
      setLoading(false)
    }
  }

  // Delete Material
  const handleDeleteMaterial = async (id: string) => {
    if (!window.confirm('Are you sure you want to delete this study material?')) return
    try {
      await lmsApi.deleteMaterial(id)
      setAlertInfo({ type: 'success', message: 'Material deleted successfully.' })
      loadMaterials()
    } catch (err: any) {
      setAlertInfo({ type: 'error', message: err.response?.data?.error?.message || 'Failed to delete material.' })
    }
  }

  // Handle Create Assignment
  const handleCreateAssignment = async () => {
    if (!assignTitle || !assignDueDate || !assignSessionId) {
      setAlertInfo({ type: 'error', message: 'Please fill in Title, Academic Session, and Due Date.' })
      return
    }

    try {
      setLoading(true)
      if (assignInstructionsFile) {
        const formData = new FormData()
        formData.append('title', assignTitle)
        formData.append('description', assignDescription)
        formData.append('academic_session_id', assignSessionId)
        formData.append('due_datetime', assignDueDate)
        formData.append('total_marks', assignTotalMarks)
        formData.append('passing_marks', assignPassMarks)
        formData.append('late_penalty_percent', assignPenalty)
        formData.append('allow_late_submission', assignAllowLate.toString())
        formData.append('status_val', 'PUBLISHED')
        if (assignSubjectId) formData.append('subject_id', assignSubjectId)
        if (assignClassId) formData.append('class_id', assignClassId)
        formData.append('instructions_file', assignInstructionsFile)

        await lmsApi.createAssignmentWithFile(formData)
      } else {
        await lmsApi.createAssignmentJson({
          title: assignTitle,
          description: assignDescription,
          academic_session_id: assignSessionId,
          due_datetime: assignDueDate,
          total_marks: parseFloat(assignTotalMarks),
          passing_marks: parseFloat(assignPassMarks),
          late_penalty_percent: parseFloat(assignPenalty),
          allow_late_submission: assignAllowLate,
          subject_id: assignSubjectId || undefined,
          class_id: assignClassId || undefined,
          status: 'PUBLISHED',
        })
      }

      setAlertInfo({ type: 'success', message: 'Assignment published successfully!' })
      setCreateAssignOpen(false)
      loadAssignments()
    } catch (err: any) {
      setAlertInfo({ type: 'error', message: err.response?.data?.error?.message || 'Failed to create assignment.' })
    } finally {
      setLoading(false)
    }
  }

  // Load Submissions for selected assignment
  const handleViewSubmissions = async (assignment: Assignment) => {
    setSelectedAssignment(assignment)
    try {
      setLoading(true)
      const res = await lmsApi.listSubmissions(assignment.id)
      setAssignmentSubmissions(res.data || [])
      setActiveTab(3) // Switch to grading view
    } catch (err: any) {
      setAlertInfo({ type: 'error', message: err.response?.data?.error?.message || 'Failed to load submissions.' })
    } finally {
      setLoading(false)
    }
  }

  // Load Assignment Report
  const handleViewReport = async (assignment: Assignment) => {
    try {
      setLoading(true)
      const res = await lmsApi.getAssignmentReport(assignment.id)
      setAssignmentReport(res.data)
      setReportModalOpen(true)
    } catch (err: any) {
      setAlertInfo({ type: 'error', message: err.response?.data?.error?.message || 'Failed to load report.' })
    } finally {
      setLoading(false)
    }
  }

  // Submit Assignment (Student)
  const handleSubmitAssignment = async () => {
    if (!selectedAssignment) return
    try {
      setLoading(true)
      const formData = new FormData()
      if (submissionText) formData.append('submission_text', submissionText)
      if (submissionFile) formData.append('file', submissionFile)

      await lmsApi.submitAssignment(selectedAssignment.id, formData)
      setAlertInfo({ type: 'success', message: 'Assignment submitted successfully!' })
      setSubmitModalOpen(false)
      setSubmissionText('')
      setSubmissionFile(null)
      loadAssignments()
    } catch (err: any) {
      setAlertInfo({ type: 'error', message: err.response?.data?.error?.message || 'Submission failed.' })
    } finally {
      setLoading(false)
    }
  }

  // Evaluate Submission (Teacher)
  const handleEvaluate = async () => {
    if (!evaluatingSub) return
    try {
      setLoading(true)
      await lmsApi.evaluateSubmission(evaluatingSub.id, {
        marks_obtained: parseFloat(evalMarks),
        grade: evalGrade,
        teacher_feedback: evalFeedback,
        status: 'EVALUATED',
      })
      setAlertInfo({ type: 'success', message: 'Evaluation and grade saved successfully!' })
      setEvalModalOpen(false)
      if (selectedAssignment) {
        const res = await lmsApi.listSubmissions(selectedAssignment.id)
        setAssignmentSubmissions(res.data || [])
      }
    } catch (err: any) {
      setAlertInfo({ type: 'error', message: err.response?.data?.error?.message || 'Evaluation failed.' })
    } finally {
      setLoading(false)
    }
  }

  const getFormatIcon = (type: string) => {
    switch (type) {
      case 'PDF':
        return <PictureAsPdf sx={{ color: '#E53935' }} />
      case 'VIDEO_LINK':
      case 'RECORDED_LECTURE':
        return <PlayCircleFilled sx={{ color: '#1E88E5' }} />
      case 'POWERPOINT':
        return <Description sx={{ color: '#D84315' }} />
      case 'WORD':
        return <Description sx={{ color: '#1565C0' }} />
      default:
        return <Description sx={{ color: '#546E7A' }} />
    }
  }

  return (
    <Box sx={{ maxWidth: 1400, mx: 'auto' }}>
      {/* Header */}
      <Box sx={{ mb: 3 }}>
        <PageHeader
          title="Learning Management"
          description="Share study materials, manage assignments, and grade submissions."
          icon={<MenuBook />}
        >
          <Stack direction="row" spacing={1.5} flexWrap="wrap">
            <Button
              variant="outlined"
              startIcon={<Refresh />}
              onClick={() => {
                loadMaterials()
                loadAssignments()
              }}
            >
              Refresh
            </Button>
            <Button
              variant="contained"
              startIcon={<Add />}
              onClick={() => setCreateAssignOpen(true)}
            >
              Create Assignment
            </Button>
          </Stack>
        </PageHeader>
      </Box>

      {/* Global Alerts */}
      {alertInfo && (
        <Alert severity={alertInfo.type} onClose={() => setAlertInfo(null)} sx={{ mb: 3 }}>
          {alertInfo.message}
        </Alert>
      )}

      {/* Main Tabs */}
      <Box sx={{ borderBottom: 1, borderColor: 'divider', mb: 3 }}>
        <Tabs value={activeTab} onChange={(_, val) => setActiveTab(val)}>
          <Tab icon={<MenuBook />} iconPosition="start" label="Materials Library" />
          <Tab icon={<CloudUpload />} iconPosition="start" label="Upload Material" />
          <Tab icon={<AssignmentIcon />} iconPosition="start" label="Assignments Board" />
          {selectedAssignment && <Tab icon={<Assessment />} iconPosition="start" label={`Submissions (${selectedAssignment.title})`} />}
        </Tabs>
      </Box>

      {/* ───────────────────────────────────────────────────────────────────────── */}
      {/* TAB 0: Materials Library */}
      {/* ───────────────────────────────────────────────────────────────────────── */}
      {activeTab === 0 && (
        <Box>
          {/* Filters Bar */}
          <Card sx={{ mb: 3, p: 2 }}>
            <Grid container spacing={2} alignItems="center">
              <Grid item xs={12} sm={4}>
                <TextField
                  fullWidth
                  size="small"
                  label="Search Materials"
                  placeholder="Search by title, chapter or topic..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && loadMaterials()}
                />
              </Grid>
              <Grid item xs={12} sm={3}>
                <TextField
                  fullWidth
                  size="small"
                  select
                  label="Category"
                  value={categoryFilter}
                  onChange={(e) => setCategoryFilter(e.target.value)}
                >
                  <MenuItem value="ALL">All Categories</MenuItem>
                  <MenuItem value="LECTURE_NOTE">Lecture Notes</MenuItem>
                  <MenuItem value="SYLLABUS">Syllabus</MenuItem>
                  <MenuItem value="PAST_PAPER">Past Question Papers</MenuItem>
                  <MenuItem value="READING">Reading Materials</MenuItem>
                  <MenuItem value="REFERENCE">Reference Books</MenuItem>
                  <MenuItem value="LAB_MANUAL">Lab Manuals</MenuItem>
                  <MenuItem value="GENERAL">General</MenuItem>
                </TextField>
              </Grid>
              <Grid item xs={12} sm={3}>
                <TextField
                  fullWidth
                  size="small"
                  select
                  label="Subject"
                  value={subjectFilter}
                  onChange={(e) => setSubjectFilter(e.target.value)}
                >
                  <MenuItem value="ALL">All Subjects</MenuItem>
                  {subjects.map((s) => (
                    <MenuItem key={s.id} value={s.id}>
                      {s.name} ({s.code})
                    </MenuItem>
                  ))}
                </TextField>
              </Grid>
              <Grid item xs={12} sm={2}>
                <Button fullWidth variant="contained" onClick={loadMaterials}>
                  Apply Filter
                </Button>
              </Grid>
            </Grid>
          </Card>

          {loading ? (
            <Box sx={{ display: 'flex', justifyContent: 'center', p: 5 }}>
              <CircularProgress />
            </Box>
          ) : materials.length === 0 ? (
            <Card sx={{ p: 5, textAlign: 'center' }}>
              <MenuBook sx={{ fontSize: 60, color: 'text.disabled', mb: 2 }} />
              <Typography variant="h6">No Study Materials Found</Typography>
              <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                Upload PDF notes, lecture slides, video links or previous question papers to get started.
              </Typography>
              <Button variant="contained" startIcon={<CloudUpload />} onClick={() => setActiveTab(1)}>
                Upload First Material
              </Button>
            </Card>
          ) : (
            <Grid container spacing={3}>
              {materials.map((m) => (
                <Grid item xs={12} sm={6} md={4} key={m.id}>
                  <Card sx={{ height: '100%', display: 'flex', flexDirection: 'column', position: 'relative' }}>
                    <CardContent sx={{ flexGrow: 1 }}>
                      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 1.5 }}>
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                          {getFormatIcon(m.material_type)}
                          <Chip size="small" label={m.category} color="primary" variant="outlined" />
                        </Box>
                        <Chip
                          size="small"
                          label={`v${m.version}`}
                          sx={{ fontWeight: 600, cursor: 'pointer' }}
                          onClick={() => {
                            setSelectedMaterial(m)
                            setVersionModalOpen(true)
                          }}
                        />
                      </Box>

                      <Typography variant="h6" sx={{ fontWeight: 600, mb: 1, fontSize: '1.05rem' }}>
                        {m.title}
                      </Typography>

                      {m.chapter && (
                        <Typography variant="caption" sx={{ display: 'block', color: 'primary.dark', fontWeight: 600, mb: 1 }}>
                          {m.chapter}
                        </Typography>
                      )}

                      {m.description && (
                        <Typography variant="body2" color="text.secondary" sx={{ mb: 1.5, maxHeight: 40, overflow: 'hidden' }}>
                          {m.description}
                        </Typography>
                      )}

                      {m.subject_name && (
                        <Chip
                          size="small"
                          icon={<School sx={{ fontSize: 16 }} />}
                          label={`${m.subject_name} (${m.subject_code || ''})`}
                          sx={{ mb: 1 }}
                        />
                      )}

                      <Box sx={{ display: 'flex', gap: 2, mt: 1 }}>
                        <Typography variant="caption" color="text.secondary" sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                          <Visibility sx={{ fontSize: 14 }} /> {m.view_count} Views
                        </Typography>
                        <Typography variant="caption" color="text.secondary" sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                          <Download sx={{ fontSize: 14 }} /> {m.download_count} Downloads
                        </Typography>
                      </Box>
                    </CardContent>

                    <Divider />
                    <CardActions sx={{ justifyContent: 'space-between', px: 2 }}>
                      <Box>
                        {m.download_url && (
                          <Tooltip title="Preview / Open">
                            <IconButton
                              size="small"
                              color="primary"
                              onClick={() => {
                                setPreviewUrl(m.preview_url || m.download_url || null)
                                setPreviewTitle(m.title)
                                setPreviewModalOpen(true)
                              }}
                            >
                              <Visibility />
                            </IconButton>
                          </Tooltip>
                        )}
                        {m.download_url && (
                          <Tooltip title="Download File">
                            <IconButton
                              size="small"
                              color="primary"
                              component="a"
                              href={m.download_url}
                              target="_blank"
                              rel="noreferrer"
                            >
                              <Download />
                            </IconButton>
                          </Tooltip>
                        )}
                        <Tooltip title="Version History">
                          <IconButton
                            size="small"
                            onClick={() => {
                              setSelectedMaterial(m)
                              setVersionModalOpen(true)
                            }}
                          >
                            <History />
                          </IconButton>
                        </Tooltip>
                      </Box>
                      <IconButton size="small" color="error" onClick={() => handleDeleteMaterial(m.id)}>
                        <Delete />
                      </IconButton>
                    </CardActions>
                  </Card>
                </Grid>
              ))}
            </Grid>
          )}
        </Box>
      )}

      {/* ───────────────────────────────────────────────────────────────────────── */}
      {/* TAB 1: Upload Material */}
      {/* ───────────────────────────────────────────────────────────────────────── */}
      {activeTab === 1 && (
        <Card sx={{ p: 4, maxWidth: 800, mx: 'auto' }}>
          <Typography variant="h5" sx={{ fontWeight: 600, mb: 1 }}>
            Upload New Study Material
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
            Upload syllabus, lecture presentations, notes, PDF papers or external links partitioned securely per tenant.
          </Typography>

          <form onSubmit={handleUploadMaterial}>
            <Grid container spacing={2.5}>
              <Grid item xs={12}>
                <TextField
                  fullWidth
                  required
                  label="Material Title"
                  placeholder="e.g. Chapter 4 - Electrochemistry Comprehensive Notes"
                  value={materialTitle}
                  onChange={(e) => setMaterialTitle(e.target.value)}
                />
              </Grid>

              <Grid item xs={12} sm={6}>
                <TextField
                  fullWidth
                  select
                  required
                  label="Academic Session"
                  value={materialSessionId}
                  onChange={(e) => setMaterialSessionId(e.target.value)}
                >
                  {sessions.map((s) => (
                    <MenuItem key={s.id} value={s.id}>
                      {s.name}
                    </MenuItem>
                  ))}
                </TextField>
              </Grid>

              <Grid item xs={12} sm={6}>
                <TextField
                  fullWidth
                  select
                  label="Subject"
                  value={materialSubjectId}
                  onChange={(e) => setMaterialSubjectId(e.target.value)}
                >
                  <MenuItem value="">None / General</MenuItem>
                  {subjects.map((s) => (
                    <MenuItem key={s.id} value={s.id}>
                      {s.name} ({s.code})
                    </MenuItem>
                  ))}
                </TextField>
              </Grid>

              <Grid item xs={12} sm={6}>
                <TextField
                  fullWidth
                  select
                  label="Category"
                  value={materialCategory}
                  onChange={(e) => setMaterialCategory(e.target.value)}
                >
                  <MenuItem value="LECTURE_NOTE">Lecture Notes</MenuItem>
                  <MenuItem value="SYLLABUS">Syllabus</MenuItem>
                  <MenuItem value="PAST_PAPER">Previous Question Paper</MenuItem>
                  <MenuItem value="READING">Reading Material</MenuItem>
                  <MenuItem value="REFERENCE">Reference Material</MenuItem>
                  <MenuItem value="LAB_MANUAL">Lab Manual</MenuItem>
                  <MenuItem value="GENERAL">General</MenuItem>
                </TextField>
              </Grid>

              <Grid item xs={12} sm={6}>
                <TextField
                  fullWidth
                  select
                  label="Material Format"
                  value={materialType}
                  onChange={(e) => setMaterialType(e.target.value)}
                >
                  <MenuItem value="PDF">PDF Document</MenuItem>
                  <MenuItem value="WORD">Microsoft Word (.doc, .docx)</MenuItem>
                  <MenuItem value="POWERPOINT">PowerPoint Presentation (.ppt, .pptx)</MenuItem>
                  <MenuItem value="IMAGE">Image File (.png, .jpg)</MenuItem>
                  <MenuItem value="VIDEO_LINK">Video Link (YouTube / Vimeo / Cloud)</MenuItem>
                  <MenuItem value="RECORDED_LECTURE">Recorded Lecture Video</MenuItem>
                  <MenuItem value="OTHER">Other Attachment</MenuItem>
                </TextField>
              </Grid>

              <Grid item xs={12} sm={6}>
                <TextField
                  fullWidth
                  label="Chapter / Module"
                  placeholder="e.g. Chapter 3: Chemical Bonding"
                  value={materialChapter}
                  onChange={(e) => setMaterialChapter(e.target.value)}
                />
              </Grid>

              <Grid item xs={12} sm={6}>
                <TextField
                  fullWidth
                  select
                  label="Class (Optional)"
                  value={materialClassId}
                  onChange={(e) => setMaterialClassId(e.target.value)}
                >
                  <MenuItem value="">None / All Classes</MenuItem>
                  {classes.map((c) => (
                    <MenuItem key={c.id} value={c.id}>
                      {c.name}
                    </MenuItem>
                  ))}
                </TextField>
              </Grid>

              {materialType === 'VIDEO_LINK' ? (
                <Grid item xs={12}>
                  <TextField
                    fullWidth
                    label="Video / External URL"
                    placeholder="https://..."
                    value={materialExternalUrl}
                    onChange={(e) => setMaterialExternalUrl(e.target.value)}
                  />
                </Grid>
              ) : (
                <Grid item xs={12}>
                  <Box
                    sx={{
                      border: '2px dashed',
                      borderColor: 'primary.light',
                      p: 3,
                      borderRadius: 2,
                      textAlign: 'center',
                      bgcolor: 'action.hover',
                    }}
                  >
                    <CloudUpload sx={{ fontSize: 40, color: 'primary.main', mb: 1 }} />
                    <Typography variant="body1" sx={{ fontWeight: 600 }}>
                      {materialFile ? materialFile.name : 'Select or drop a file to upload (Max 50MB)'}
                    </Typography>
                    <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 2 }}>
                      Supported formats: PDF, DOCX, PPTX, XLSX, Images, MP4, ZIP
                    </Typography>
                    <Button variant="outlined" component="label" startIcon={<AttachFile />}>
                      Browse File
                      <input
                        type="file"
                        hidden
                        onChange={(e) => {
                          if (e.target.files && e.target.files[0]) {
                            setMaterialFile(e.target.files[0])
                          }
                        }}
                      />
                    </Button>
                  </Box>
                </Grid>
              )}

              <Grid item xs={12}>
                <TextField
                  fullWidth
                  multiline
                  rows={3}
                  label="Description / Instructions"
                  placeholder="Provide context, references or reading guidance for students..."
                  value={materialDescription}
                  onChange={(e) => setMaterialDescription(e.target.value)}
                />
              </Grid>

              <Grid item xs={12}>
                <TextField
                  fullWidth
                  label="Tags (Comma-separated)"
                  placeholder="chemistry, organic, revision, 2026"
                  value={materialTags}
                  onChange={(e) => setMaterialTags(e.target.value)}
                />
              </Grid>

              <Grid item xs={12}>
                <FormControlLabel
                  control={
                    <Switch
                      checked={materialIsPublished}
                      onChange={(e) => setMaterialIsPublished(e.target.checked)}
                      color="primary"
                    />
                  }
                  label="Publish immediately to enrolled students"
                />
              </Grid>

              <Grid item xs={12}>
                <Button fullWidth type="submit" variant="contained" size="large" disabled={loading} startIcon={<CloudUpload />}>
                  {loading ? 'Uploading & Processing...' : 'Upload & Publish Material'}
                </Button>
              </Grid>
            </Grid>
          </form>
        </Card>
      )}

      {/* ───────────────────────────────────────────────────────────────────────── */}
      {/* TAB 2: Assignments Board */}
      {/* ───────────────────────────────────────────────────────────────────────── */}
      {activeTab === 2 && (
        <Box>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
            <Typography variant="h6" sx={{ fontWeight: 600 }}>
              Course Assignments & Homework Tasks
            </Typography>
            <Button variant="contained" startIcon={<Add />} onClick={() => setCreateAssignOpen(true)}>
              New Assignment
            </Button>
          </Box>

          <Grid container spacing={3}>
            {assignments.map((a) => {
              const isPast = new Date(a.due_datetime) < new Date()
              return (
                <Grid item xs={12} md={6} key={a.id}>
                  <Card sx={{ p: 2.5, height: '100%', display: 'flex', flexDirection: 'column' }}>
                    <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 1 }}>
                      <Chip
                        label={isPast ? 'Past Deadline' : 'Active'}
                        color={isPast ? 'default' : 'success'}
                        size="small"
                        sx={{ fontWeight: 600 }}
                      />
                      <Typography variant="caption" sx={{ fontWeight: 600, color: 'text.secondary' }}>
                        Due: {new Date(a.due_datetime).toLocaleString()}
                      </Typography>
                    </Box>

                    <Typography variant="h6" sx={{ fontWeight: 700, mb: 1 }}>
                      {a.title}
                    </Typography>

                    <Typography variant="body2" color="text.secondary" sx={{ mb: 2, flexGrow: 1 }}>
                      {a.description}
                    </Typography>

                    <Stack direction="row" spacing={1} sx={{ mb: 2, flexWrap: 'wrap', gap: 0.5 }}>
                      <Chip size="small" icon={<School />} label={a.subject_name || 'Subject'} />
                      <Chip size="small" label={`Total Marks: ${a.total_marks}`} />
                      <Chip size="small" label={`Pass: ${a.passing_marks}`} />
                      {a.late_penalty_percent > 0 && (
                        <Chip
                          size="small"
                          color="warning"
                          icon={<Warning />}
                          label={`-${a.late_penalty_percent}% Late Penalty`}
                        />
                      )}
                    </Stack>

                    <Divider sx={{ my: 1.5 }} />

                    <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <Typography variant="caption" color="text.secondary">
                        <strong>{a.submissions_count}</strong> Submitted &bull; <strong>{a.evaluated_count}</strong> Evaluated
                      </Typography>
                      <Stack direction="row" spacing={1}>
                        <Button
                          size="small"
                          variant="outlined"
                          startIcon={<Assessment />}
                          onClick={() => handleViewReport(a)}
                        >
                          Report
                        </Button>
                        <Button
                          size="small"
                          variant="contained"
                          onClick={() => handleViewSubmissions(a)}
                        >
                          View Submissions
                        </Button>
                        <Button
                          size="small"
                          color="secondary"
                          variant="outlined"
                          onClick={() => {
                            setSelectedAssignment(a)
                            setSubmitModalOpen(true)
                          }}
                        >
                          Submit Work
                        </Button>
                      </Stack>
                    </Box>
                  </Card>
                </Grid>
              )
            })}
          </Grid>
        </Box>
      )}

      {/* ───────────────────────────────────────────────────────────────────────── */}
      {/* TAB 3: Submissions & Grading Table */}
      {/* ───────────────────────────────────────────────────────────────────────── */}
      {activeTab === 3 && selectedAssignment && (
        <Box>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
            <Box>
              <Typography variant="h5" sx={{ fontWeight: 700 }}>
                Submissions: {selectedAssignment.title}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Max Marks: {selectedAssignment.total_marks} &bull; Passing: {selectedAssignment.passing_marks} &bull; Late Penalty: {selectedAssignment.late_penalty_percent}%
              </Typography>
            </Box>
            <Button variant="outlined" onClick={() => setActiveTab(2)}>
              Back to Board
            </Button>
          </Box>

          <TableContainer component={Paper} sx={{ overflowX: 'auto', width: '100%' }}>
            <Table sx={{ minWidth: 650 }}>
              <TableHead sx={{ bgcolor: 'action.hover' }}>
                <TableRow>
                  <TableCell sx={{ fontWeight: 600 }}>Student Name</TableCell>
                  <TableCell sx={{ fontWeight: 600 }}>Admission No.</TableCell>
                  <TableCell sx={{ fontWeight: 600 }}>Submitted At</TableCell>
                  <TableCell sx={{ fontWeight: 600 }}>Status</TableCell>
                  <TableCell sx={{ fontWeight: 600 }}>Attachment</TableCell>
                  <TableCell sx={{ fontWeight: 600 }}>Marks</TableCell>
                  <TableCell sx={{ fontWeight: 600 }}>Grade</TableCell>
                  <TableCell sx={{ fontWeight: 600 }}>Feedback</TableCell>
                  <TableCell sx={{ fontWeight: 600 }} align="right">Actions</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {assignmentSubmissions.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={9} align="center" sx={{ py: 4 }}>
                      No submissions recorded yet for this assignment.
                    </TableCell>
                  </TableRow>
                ) : (
                  assignmentSubmissions.map((sub) => (
                    <TableRow key={sub.id}>
                      <TableCell sx={{ fontWeight: 600 }}>{sub.student_name}</TableCell>
                      <TableCell>{sub.admission_number}</TableCell>
                      <TableCell>
                        {new Date(sub.submitted_at).toLocaleString()}
                        {sub.is_late && <Chip size="small" color="error" label="LATE" sx={{ ml: 1 }} />}
                      </TableCell>
                      <TableCell>
                        <Chip
                          size="small"
                          label={sub.status}
                          color={sub.status === 'EVALUATED' ? 'success' : 'warning'}
                        />
                      </TableCell>
                      <TableCell>
                        {sub.attachment_download_url ? (
                          <Button
                            size="small"
                            startIcon={<Download />}
                            component="a"
                            href={sub.attachment_download_url}
                            target="_blank"
                          >
                            {sub.attachment_file_name || 'Download'}
                          </Button>
                        ) : (
                          'Text only'
                        )}
                      </TableCell>
                      <TableCell sx={{ fontWeight: 700 }}>
                        {sub.marks_obtained !== null && sub.marks_obtained !== undefined ? sub.marks_obtained : '-'}
                      </TableCell>
                      <TableCell>
                        {sub.grade ? <Chip size="small" label={sub.grade} color="primary" /> : '-'}
                      </TableCell>
                      <TableCell sx={{ maxWidth: 200, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                        {sub.teacher_feedback || '-'}
                      </TableCell>
                      <TableCell align="right">
                        <Button
                          size="small"
                          variant="contained"
                          startIcon={<Edit />}
                          onClick={() => {
                            setEvaluatingSub(sub)
                            setEvalMarks(sub.marks_obtained ? sub.marks_obtained.toString() : '')
                            setEvalGrade(sub.grade || 'A')
                            setEvalFeedback(sub.teacher_feedback || '')
                            setEvalModalOpen(true)
                          }}
                        >
                          Grade
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          </TableContainer>
        </Box>
      )}

      {/* ───────────────────────────────────────────────────────────────────────── */}
      {/* DIALOG: Create Assignment */}
      {/* ───────────────────────────────────────────────────────────────────────── */}
      <Dialog open={createAssignOpen} onClose={() => setCreateAssignOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle sx={{ fontWeight: 700 }}>Create New Assignment</DialogTitle>
        <DialogContent dividers>
          <Stack spacing={2.5}>
            <TextField
              fullWidth
              required
              label="Assignment Title"
              placeholder="e.g. Laboratory Report - Acid-Base Titration"
              value={assignTitle}
              onChange={(e) => setAssignTitle(e.target.value)}
            />
            <TextField
              fullWidth
              multiline
              rows={3}
              label="Description & Instructions"
              value={assignDescription}
              onChange={(e) => setAssignDescription(e.target.value)}
            />
            <Grid container spacing={2}>
              <Grid item xs={6}>
                <TextField
                  fullWidth
                  select
                  label="Subject"
                  value={assignSubjectId}
                  onChange={(e) => setAssignSubjectId(e.target.value)}
                >
                  <MenuItem value="">None / General</MenuItem>
                  {subjects.map((s) => (
                    <MenuItem key={s.id} value={s.id}>
                      {s.name} ({s.code})
                    </MenuItem>
                  ))}
                </TextField>
              </Grid>
              <Grid item xs={6}>
                <TextField
                  fullWidth
                  select
                  label="Class (Optional)"
                  value={assignClassId}
                  onChange={(e) => setAssignClassId(e.target.value)}
                >
                  <MenuItem value="">None / All Classes</MenuItem>
                  {classes.map((c) => (
                    <MenuItem key={c.id} value={c.id}>
                      {c.name}
                    </MenuItem>
                  ))}
                </TextField>
              </Grid>
            </Grid>
            <TextField
              fullWidth
              required
              type="datetime-local"
              label="Submission Due Date"
              InputLabelProps={{ shrink: true }}
              value={assignDueDate}
              onChange={(e) => setAssignDueDate(e.target.value)}
            />
            <Grid container spacing={2}>
              <Grid item xs={6}>
                <TextField
                  fullWidth
                  type="number"
                  label="Total Marks"
                  value={assignTotalMarks}
                  onChange={(e) => setAssignTotalMarks(e.target.value)}
                />
              </Grid>
              <Grid item xs={6}>
                <TextField
                  fullWidth
                  type="number"
                  label="Passing Marks"
                  value={assignPassMarks}
                  onChange={(e) => setAssignPassMarks(e.target.value)}
                />
              </Grid>
            </Grid>
            <Grid container spacing={2}>
              <Grid item xs={6}>
                <TextField
                  fullWidth
                  type="number"
                  label="Late Penalty (%)"
                  value={assignPenalty}
                  onChange={(e) => setAssignPenalty(e.target.value)}
                />
              </Grid>
              <Grid item xs={6}>
                <FormControlLabel
                  control={
                    <Switch
                      checked={assignAllowLate}
                      onChange={(e) => setAssignAllowLate(e.target.checked)}
                    />
                  }
                  label="Allow Late Submissions"
                  sx={{ mt: 1 }}
                />
              </Grid>
            </Grid>

            <Box>
              <Typography variant="caption" sx={{ fontWeight: 600, display: 'block', mb: 1 }}>
                Optional Instructions Attachment (PDF, DOCX, PPT)
              </Typography>
              <Button variant="outlined" component="label" startIcon={<AttachFile />}>
                {assignInstructionsFile ? assignInstructionsFile.name : 'Upload Instructions Document'}
                <input
                  type="file"
                  hidden
                  onChange={(e) => {
                    if (e.target.files && e.target.files[0]) {
                      setAssignInstructionsFile(e.target.files[0])
                    }
                  }}
                />
              </Button>
            </Box>
          </Stack>
        </DialogContent>
        <DialogActions sx={{ p: 2 }}>
          <Button onClick={() => setCreateAssignOpen(false)}>Cancel</Button>
          <Button variant="contained" onClick={handleCreateAssignment} disabled={loading}>
            Publish Assignment
          </Button>
        </DialogActions>
      </Dialog>

      {/* ───────────────────────────────────────────────────────────────────────── */}
      {/* DIALOG: Submit Assignment Work */}
      {/* ───────────────────────────────────────────────────────────────────────── */}
      <Dialog open={submitModalOpen} onClose={() => setSubmitModalOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle sx={{ fontWeight: 700 }}>
          Submit Work: {selectedAssignment?.title}
        </DialogTitle>
        <DialogContent dividers>
          <Stack spacing={2.5}>
            <Alert severity="info">
              Due Date: {selectedAssignment && new Date(selectedAssignment.due_datetime).toLocaleString()}. Late submissions will incur a {selectedAssignment?.late_penalty_percent}% penalty deduction.
            </Alert>
            <TextField
              fullWidth
              multiline
              rows={4}
              label="Submission Notes / Answers"
              placeholder="Type your answer, observations, or lab summary here..."
              value={submissionText}
              onChange={(e) => setSubmissionText(e.target.value)}
            />
            <Box>
              <Typography variant="body2" sx={{ fontWeight: 600, mb: 1 }}>
                Attach Completed Document / Lab File (PDF, Word, Excel, ZIP)
              </Typography>
              <Button variant="outlined" component="label" startIcon={<CloudUpload />}>
                {submissionFile ? submissionFile.name : 'Select File To Submit'}
                <input
                  type="file"
                  hidden
                  onChange={(e) => {
                    if (e.target.files && e.target.files[0]) {
                      setSubmissionFile(e.target.files[0])
                    }
                  }}
                />
              </Button>
            </Box>
          </Stack>
        </DialogContent>
        <DialogActions sx={{ p: 2 }}>
          <Button onClick={() => setSubmitModalOpen(false)}>Cancel</Button>
          <Button variant="contained" onClick={handleSubmitAssignment} disabled={loading}>
            Submit Assignment
          </Button>
        </DialogActions>
      </Dialog>

      {/* ───────────────────────────────────────────────────────────────────────── */}
      {/* DIALOG: Teacher Evaluation */}
      {/* ───────────────────────────────────────────────────────────────────────── */}
      <Dialog open={evalModalOpen} onClose={() => setEvalModalOpen(false)} maxWidth="xs" fullWidth>
        <DialogTitle sx={{ fontWeight: 700 }}>
          Evaluate: {evaluatingSub?.student_name}
        </DialogTitle>
        <DialogContent dividers>
          <Stack spacing={2.5}>
            {evaluatingSub?.is_late && (
              <Alert severity="warning">
                This submission was received past the deadline. Configured late penalty will be applied automatically to the awarded score.
              </Alert>
            )}
            <TextField
              fullWidth
              type="number"
              label="Marks Obtained"
              value={evalMarks}
              onChange={(e) => setEvalMarks(e.target.value)}
            />
            <TextField
              fullWidth
              select
              label="Letter Grade"
              value={evalGrade}
              onChange={(e) => setEvalGrade(e.target.value)}
            >
              {['A+', 'A', 'B+', 'B', 'C+', 'C', 'D', 'F'].map((g) => (
                <MenuItem key={g} value={g}>
                  {g}
                </MenuItem>
              ))}
            </TextField>
            <TextField
              fullWidth
              multiline
              rows={3}
              label="Teacher Feedback"
              placeholder="Detailed constructive feedback for the student..."
              value={evalFeedback}
              onChange={(e) => setEvalFeedback(e.target.value)}
            />
          </Stack>
        </DialogContent>
        <DialogActions sx={{ p: 2 }}>
          <Button onClick={() => setEvalModalOpen(false)}>Cancel</Button>
          <Button variant="contained" onClick={handleEvaluate} disabled={loading}>
            Save Evaluation
          </Button>
        </DialogActions>
      </Dialog>

      {/* ───────────────────────────────────────────────────────────────────────── */}
      {/* DIALOG: Version History */}
      {/* ───────────────────────────────────────────────────────────────────────── */}
      <Dialog open={versionModalOpen} onClose={() => setVersionModalOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle sx={{ fontWeight: 700 }}>
          Version History & Updates
        </DialogTitle>
        <DialogContent dividers>
          <Stack spacing={2}>
            <Box sx={{ p: 2, bgcolor: 'action.hover', borderRadius: 2 }}>
              <Typography variant="subtitle2" sx={{ fontWeight: 600, mb: 1 }}>
                Upload New Revised Version
              </Typography>
              <Stack direction="row" spacing={1.5} alignItems="center">
                <Button variant="outlined" size="small" component="label" startIcon={<AttachFile />}>
                  {uploadVersionFile ? uploadVersionFile.name : 'Select File'}
                  <input
                    type="file"
                    hidden
                    onChange={(e) => {
                      if (e.target.files && e.target.files[0]) {
                        setUploadVersionFile(e.target.files[0])
                      }
                    }}
                  />
                </Button>
                <TextField
                  size="small"
                  fullWidth
                  placeholder="Change notes (e.g. Added 2026 practice questions)"
                  value={versionSummary}
                  onChange={(e) => setVersionSummary(e.target.value)}
                />
                <Button variant="contained" size="small" onClick={handleUploadNewVersion} disabled={!uploadVersionFile}>
                  Upload
                </Button>
              </Stack>
            </Box>

            <Typography variant="subtitle2" sx={{ fontWeight: 600, mt: 2 }}>
              Previous Revisions
            </Typography>
            {selectedMaterial?.versions?.map((v) => (
              <Box key={v.id} sx={{ p: 1.5, border: '1px solid', borderColor: 'divider', borderRadius: 1 }}>
                <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                  <Typography variant="body2" sx={{ fontWeight: 600 }}>
                    Version {v.version_number}: {v.file_name}
                  </Typography>
                  <Typography variant="caption" color="text.secondary">
                    {new Date(v.created_at).toLocaleDateString()}
                  </Typography>
                </Box>
                <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mt: 0.5 }}>
                  {v.change_summary || 'No change description provided'}
                </Typography>
              </Box>
            ))}
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setVersionModalOpen(false)}>Close</Button>
        </DialogActions>
      </Dialog>

      {/* ───────────────────────────────────────────────────────────────────────── */}
      {/* DIALOG: Assignment Report & Analytics */}
      {/* ───────────────────────────────────────────────────────────────────────── */}
      <Dialog open={reportModalOpen} onClose={() => setReportModalOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle sx={{ fontWeight: 700 }}>
          Assignment Performance Analytics
        </DialogTitle>
        <DialogContent dividers>
          {assignmentReport && (
            <Stack spacing={2.5}>
              <Typography variant="h6" sx={{ fontWeight: 600 }}>
                {assignmentReport.assignment_title}
              </Typography>
              <Grid container spacing={2}>
                <Grid item xs={6}>
                  <Card sx={{ p: 2, textAlign: 'center', bgcolor: 'primary.50' }}>
                    <Typography variant="h4" color="primary.main" sx={{ fontWeight: 700 }}>
                      {assignmentReport.submission_rate_percent}%
                    </Typography>
                    <Typography variant="caption" color="text.secondary">
                      Submission Completion Rate
                    </Typography>
                  </Card>
                </Grid>
                <Grid item xs={6}>
                  <Card sx={{ p: 2, textAlign: 'center', bgcolor: 'success.50' }}>
                    <Typography variant="h4" color="success.main" sx={{ fontWeight: 700 }}>
                      {assignmentReport.pass_percentage}%
                    </Typography>
                    <Typography variant="caption" color="text.secondary">
                      Pass Percentage
                    </Typography>
                  </Card>
                </Grid>
              </Grid>

              <Box sx={{ display: 'flex', justifyContent: 'space-between', px: 1 }}>
                <Typography variant="body2">Average Score: <strong>{assignmentReport.average_score}</strong></Typography>
                <Typography variant="body2">Highest Score: <strong>{assignmentReport.highest_score}</strong></Typography>
                <Typography variant="body2">Lowest Score: <strong>{assignmentReport.lowest_score}</strong></Typography>
              </Box>

              <Box>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 0.5 }}>
                  <Typography variant="caption">Submitted vs Assigned ({assignmentReport.total_submitted} / {assignmentReport.total_assigned})</Typography>
                  <Typography variant="caption">{assignmentReport.submission_rate_percent}%</Typography>
                </Box>
                <LinearProgress variant="determinate" value={Math.min(100, assignmentReport.submission_rate_percent)} />
              </Box>

              <Box>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 0.5 }}>
                  <Typography variant="caption">Evaluated vs Submitted ({assignmentReport.total_evaluated} / {assignmentReport.total_submitted})</Typography>
                  <Typography variant="caption">
                    {assignmentReport.total_submitted > 0 ? Math.round((assignmentReport.total_evaluated / assignmentReport.total_submitted) * 100) : 0}%
                  </Typography>
                </Box>
                <LinearProgress
                  variant="determinate"
                  color="secondary"
                  value={assignmentReport.total_submitted > 0 ? (assignmentReport.total_evaluated / assignmentReport.total_submitted) * 100 : 0}
                />
              </Box>
            </Stack>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setReportModalOpen(false)}>Close</Button>
        </DialogActions>
      </Dialog>

      {/* ───────────────────────────────────────────────────────────────────────── */}
      {/* DIALOG: Document Preview */}
      {/* ───────────────────────────────────────────────────────────────────────── */}
      <Dialog open={previewModalOpen} onClose={() => setPreviewModalOpen(false)} maxWidth="md" fullWidth>
        <DialogTitle sx={{ fontWeight: 700 }}>
          Preview: {previewTitle}
        </DialogTitle>
        <DialogContent dividers sx={{ height: 500, p: 0 }}>
          {previewUrl && (
            <iframe
              src={previewUrl}
              title={previewTitle}
              width="100%"
              height="100%"
              style={{ border: 'none' }}
            />
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setPreviewModalOpen(false)}>Close</Button>
          {previewUrl && (
            <Button variant="contained" component="a" href={previewUrl} target="_blank">
              Open In New Tab
            </Button>
          )}
        </DialogActions>
      </Dialog>
    </Box>
  )
}
