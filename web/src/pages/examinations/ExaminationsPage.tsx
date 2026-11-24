import { PageHeader } from '@/components/ui/PageHeader'
import { useState, useEffect, useRef } from 'react'
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
  Radio,
  RadioGroup,
  FormControlLabel,
  FormControl,
  FormLabel,
  LinearProgress,
  Tooltip,
} from '@mui/material'
import {
  Quiz as ExamIcon,
  LibraryBooks as QuestionBankIcon,
  Timer as TimerIcon,
  Grading as GradingIcon,
  BarChart as AnalyticsIcon,
  Add as AddIcon,
  PlayArrow as StartIcon,
  Refresh as RefreshIcon,
} from '@mui/icons-material'

import {
  examinationsApi,
  ExaminationItem,
  QuestionBankItem,
  StudentActiveAttemptResponse,
  AttemptEvaluationDetailResponse,
  ExaminationAnalytics,
} from '../../api/examinations'
import { academicsApi, AcademicSession, CollegeSemester, Course, SchoolClass, Subject } from '../../api/academics'

import { useAuthStore } from '@/store/authStore'

export default function ExaminationsPage() {
  const isCollege = useAuthStore(({ user }) => user?.institutions.some(
    (institution) => institution.tenant_id === user.current_tenant_id && institution.institution_type === 'COLLEGE',
  ) ?? false)
  const [courses, setCourses] = useState<Course[]>([])
  const [semesters, setSemesters] = useState<CollegeSemester[]>([])

  const [activeTab, setActiveTab] = useState(0)
  const [loading, setLoading] = useState(false)
  const [alert, setAlert] = useState<{ type: 'success' | 'error' | 'info'; message: string } | null>(null)

  // Academic dropdown filters
  const [sessions, setSessions] = useState<AcademicSession[]>([])
  const [classes, setClasses] = useState<SchoolClass[]>([])
  const [subjects, setSubjects] = useState<Subject[]>([])

  // Examinations List
  const [examinations, setExaminations] = useState<ExaminationItem[]>([])
  const [selectedSessionId, setSelectedSessionId] = useState('')

  // Create Exam Dialog
  const [openCreateExam, setOpenCreateExam] = useState(false)
  const [examForm, setExamForm] = useState({
    title: '',
    code: '',
    exam_type: 'UNIT_TEST',
    mode: 'ONLINE',
    academic_session_id: '',
    subject_id: '',
    class_id: '',
    course_id: '',
    semester_id: '',
    start_datetime: '',
    end_datetime: '',
    total_marks: 50,
    passing_marks: 20,
    duration_minutes: 60,
    shuffle_questions: false,
    shuffle_options: false,
    instructions: '',
  })

  // Question Bank
  const [questions, setQuestions] = useState<QuestionBankItem[]>([])
  const [openCreateQuestion, setOpenCreateQuestion] = useState(false)
  const [questionForm, setQuestionForm] = useState({
    subject_id: '',
    category: 'Physics',
    difficulty: 'MEDIUM',
    question_type: 'MCQ',
    question_text: '',
    option_a: '',
    option_b: '',
    option_c: '',
    option_d: '',
    correct_answer: 'opt_a',
    explanation: '',
    default_marks: 2,
    default_negative_marks: 0.5,
  })

  // Online Exam Room (Live taking simulator)
  const [activeExamSession, setActiveExamSession] = useState<StudentActiveAttemptResponse | null>(null)
  const [currentQuestionIdx, setCurrentQuestionIdx] = useState(0)
  const [studentAnswers, setStudentAnswers] = useState<Record<string, any>>({})
  const [remainingTime, setRemainingTime] = useState(0)
  const [lastAutosaved, setLastAutosaved] = useState<string | null>(null)
  const [examResultSummary, setExamResultSummary] = useState<any | null>(null)
  const timerRef = useRef<any>(null)

  // Grading / Evaluation
  const [selectedExamForEval, setSelectedExamForEval] = useState<string>('')
  const [attemptsList, setAttemptsList] = useState<any[]>([])
  const [evaluationDetail, setEvaluationDetail] = useState<AttemptEvaluationDetailResponse | null>(null)
  const [evalMarks, setEvalMarks] = useState<Record<string, number>>({})
  const [evalFeedback, setEvalFeedback] = useState<Record<string, string>>({})

  // Analytics
  const [selectedExamForAnalytics, setSelectedExamForAnalytics] = useState<string>('')
  const [analyticsData, setAnalyticsData] = useState<ExaminationAnalytics | null>(null)

  // Load Initial Academic Metadata
  useEffect(() => {
    loadAcademics()
  }, [])

  useEffect(() => {
    if (activeTab === 0) loadExaminations()
    if (activeTab === 1) loadQuestionBank()
  }, [activeTab, selectedSessionId])

  // Countdown Timer Effect
  useEffect(() => {
    if (activeExamSession && remainingTime > 0) {
      timerRef.current = setInterval(() => {
        setRemainingTime((prev) => {
          if (prev <= 1) {
            clearInterval(timerRef.current!)
            handleAutoSubmitOnExpiry()
            return 0
          }
          return prev - 1
        })
      }, 1000)
    }
    return () => {
      if (timerRef.current) clearInterval(timerRef.current)
    }
  }, [activeExamSession, remainingTime])

  const loadAcademics = async () => {
    try {
      const [sessionsResponse, classesResponse, coursesResponse, subjectsResponse] = await Promise.all([
        academicsApi.getSessions(), isCollege ? undefined : academicsApi.getClasses(),
        isCollege ? academicsApi.getCourses() : undefined, academicsApi.getSubjects(),
      ])
      const sessionList: AcademicSession[] = sessionsResponse.data ?? []
      setSessions(sessionList)
      setSelectedSessionId((current) => current || sessionList.find((item) => item.is_current)?.id || sessionList[0]?.id || '')
      setClasses(classesResponse?.data ?? [])
      setCourses(coursesResponse?.data ?? [])
      setSubjects(subjectsResponse.data ?? [])
    } catch (err: any) {
      setAlert({ type: 'error', message: 'Unable to load academic sessions and cohorts.' })
    }
  }

  useEffect(() => {
    if (!examForm.course_id || !isCollege) return
    let active = true
    academicsApi.getSemesters(examForm.course_id).then((response) => {
      if (active) setSemesters(response.data ?? [])
    }).catch(() => {
      if (active) setAlert({ type: 'error', message: 'Unable to load semesters for this course.' })
    })
    return () => { active = false }
  }, [examForm.course_id, isCollege])

  const loadExaminations = async () => {
    setLoading(true)
    try {
      const res = await examinationsApi.listExaminations({
        academic_session_id: selectedSessionId || undefined,
      })
      if (res && res.data) {
        setExaminations(res.data)
      }
    } catch (err: any) {
      setAlert({ type: 'error', message: err.response?.data?.error?.message || 'Failed to load examinations' })
    } finally {
      setLoading(false)
    }
  }

  const loadQuestionBank = async () => {
    setLoading(true)
    try {
      const res = await examinationsApi.listQuestions()
      if (res && res.data) {
        setQuestions(res.data)
      }
    } catch (err: any) {
      setAlert({ type: 'error', message: err.response?.data?.error?.message || 'Failed to load question bank' })
    } finally {
      setLoading(false)
    }
  }

  // ─────────────────────────────────────────────────────────────────────────
  // Exam CRUD Handlers
  // ─────────────────────────────────────────────────────────────────────────
  const handleCreateExam = async () => {
    const academicSessionId = examForm.academic_session_id || selectedSessionId
    const scheduled = Boolean(examForm.start_datetime || examForm.end_datetime)
    if (!academicSessionId || (scheduled && (!examForm.start_datetime || !examForm.end_datetime || examForm.start_datetime >= examForm.end_datetime))) {
      setAlert({ type: 'error', message: 'Select a session and enter a valid start and end time when scheduling.' })
      return
    }
    try {
      await examinationsApi.createExamination({
        ...examForm, academic_session_id: academicSessionId,
        subject_id: examForm.subject_id || undefined,
        class_id: !isCollege && examForm.class_id ? examForm.class_id : undefined,
        course_id: isCollege && examForm.course_id ? examForm.course_id : undefined,
        semester_id: isCollege && examForm.semester_id ? examForm.semester_id : undefined,
        start_datetime: scheduled ? new Date(examForm.start_datetime).toISOString() : undefined,
        end_datetime: scheduled ? new Date(examForm.end_datetime).toISOString() : undefined,
        status: scheduled ? 'SCHEDULED' : 'DRAFT',
      })
      setAlert({ type: 'success', message: 'Examination created successfully!' })
      setOpenCreateExam(false)
      loadExaminations()
    } catch (err: any) {
      setAlert({ type: 'error', message: err.response?.data?.error?.message || 'Failed to create examination' })
    }
  }

  const handleTogglePublish = async (exam: ExaminationItem) => {
    try {
      await examinationsApi.updateExamination(exam.id, { is_published: !exam.is_published })
      setAlert({
        type: 'success',
        message: !exam.is_published ? 'Examination published to students!' : 'Examination un-published.',
      })
      loadExaminations()
    } catch (err: any) {
      setAlert({ type: 'error', message: err.response?.data?.error?.message || 'Failed to update publish state' })
    }
  }

  const handleToggleResultsPublish = async (exam: ExaminationItem) => {
    try {
      await examinationsApi.updateExamination(exam.id, { is_results_published: !exam.is_results_published })
      setAlert({
        type: 'success',
        message: !exam.is_results_published ? 'Results released to students!' : 'Results hidden from students.',
      })
      loadExaminations()
    } catch (err: any) {
      setAlert({ type: 'error', message: err.response?.data?.error?.message || 'Failed to update results status' })
    }
  }

  // ─────────────────────────────────────────────────────────────────────────
  // Question Bank Handlers
  // ─────────────────────────────────────────────────────────────────────────
  const handleCreateQuestion = async () => {
    try {
      let optionsPayload: any = null
      if (questionForm.question_type === 'MCQ') {
        optionsPayload = [
          { id: 'opt_a', text: questionForm.option_a },
          { id: 'opt_b', text: questionForm.option_b },
          { id: 'opt_c', text: questionForm.option_c },
          { id: 'opt_d', text: questionForm.option_d },
        ]
      } else if (questionForm.question_type === 'TRUE_FALSE') {
        optionsPayload = [
          { id: 'true', text: 'True' },
          { id: 'false', text: 'False' },
        ]
      }

      await examinationsApi.createQuestion({
        subject_id: questionForm.subject_id || undefined,
        category: questionForm.category,
        difficulty: questionForm.difficulty as any,
        question_type: questionForm.question_type as any,
        question_text: questionForm.question_text,
        options: optionsPayload,
        correct_answer: questionForm.correct_answer,
        explanation: questionForm.explanation,
        default_marks: questionForm.default_marks,
        default_negative_marks: questionForm.default_negative_marks,
      })
      setAlert({ type: 'success', message: 'Question saved to bank successfully!' })
      setOpenCreateQuestion(false)
      loadQuestionBank()
    } catch (err: any) {
      setAlert({ type: 'error', message: err.response?.data?.error?.message || 'Failed to save question' })
    }
  }

  // ─────────────────────────────────────────────────────────────────────────
  // Online Exam Room Handlers
  // ─────────────────────────────────────────────────────────────────────────
  const handleLaunchExamRoom = async (examId: string) => {
    setLoading(true)
    try {
      const activeAttempt = await examinationsApi.startOrResumeExam(examId)
      setActiveExamSession(activeAttempt)
      setRemainingTime(activeAttempt.remaining_seconds)
      setStudentAnswers(activeAttempt.saved_answers || {})
      setCurrentQuestionIdx(0)
      setActiveTab(2) // switch to exam room tab
      setAlert({ type: 'info', message: `Exam room active: ${activeAttempt.exam_title}` })
    } catch (err: any) {
      setAlert({ type: 'error', message: err.response?.data?.error?.message || 'Failed to launch examination' })
    } finally {
      setLoading(false)
    }
  }

  const handleSelectAnswer = (qId: string, value: any) => {
    const updated = { ...studentAnswers, [qId]: value }
    setStudentAnswers(updated)
    // Trigger background autosave
    if (activeExamSession) {
      examinationsApi
        .autosaveExamAnswers(activeExamSession.attempt_id, [{ question_id: qId, student_answer: value }])
        .then(() => setLastAutosaved(new Date().toLocaleTimeString()))
        .catch((e) => console.error('Autosave error', e))
    }
  }

  const handleSubmitExam = async () => {
    if (!activeExamSession) return
    setLoading(true)
    try {
      const answersList = Object.entries(studentAnswers).map(([qId, val]) => ({
        question_id: qId,
        student_answer: val,
      }))
      const subRes = await examinationsApi.submitExamAttempt(activeExamSession.attempt_id, {
        submission_hash: 'web-attempt-' + Date.now(),
        final_answers: answersList,
      })
      setExamResultSummary(subRes)
      setActiveExamSession(null)
      setAlert({ type: 'success', message: subRes.message })
    } catch (err: any) {
      setAlert({ type: 'error', message: err.response?.data?.error?.message || 'Submission failed' })
    } finally {
      setLoading(false)
    }
  }

  const handleAutoSubmitOnExpiry = () => {
    if (activeExamSession) {
      handleSubmitExam()
    }
  }

  // ─────────────────────────────────────────────────────────────────────────
  // Teacher Grading Handlers
  // ─────────────────────────────────────────────────────────────────────────
  const handleSelectExamForGrading = async (examId: string) => {
    setSelectedExamForEval(examId)
    setEvaluationDetail(null)
    try {
      const res = await examinationsApi.listExamAttempts(examId)
      if (res && res.data) {
        setAttemptsList(res.data)
      }
    } catch (err: any) {
      setAlert({ type: 'error', message: err.response?.data?.error?.message || 'Failed to load attempts' })
    }
  }

  const handleOpenEvaluationDetail = async (attemptId: string) => {
    try {
      const detail = await examinationsApi.getAttemptForEvaluation(attemptId)
      setEvaluationDetail(detail)
      const initialMarks: Record<string, number> = {}
      const initialFb: Record<string, string> = {}
      detail.answers.forEach((ans) => {
        initialMarks[ans.id] = ans.marks_awarded !== null ? Number(ans.marks_awarded) : 0
        initialFb[ans.id] = ans.teacher_feedback || ''
      })
      setEvalMarks(initialMarks)
      setEvalFeedback(initialFb)
    } catch (err: any) {
      setAlert({ type: 'error', message: err.response?.data?.error?.message || 'Failed to load evaluation detail' })
    }
  }

  const handleSubmitEvaluation = async () => {
    if (!evaluationDetail) return
    setLoading(true)
    try {
      const evaluations = Object.keys(evalMarks).map((ansId) => ({
        answer_id: ansId,
        marks_awarded: evalMarks[ansId] || 0,
        teacher_feedback: evalFeedback[ansId] || '',
      }))
      const updated = await examinationsApi.evaluateAttempt(evaluationDetail.attempt_id, { evaluations })
      setEvaluationDetail(updated)
      setAlert({ type: 'success', message: `Evaluation saved! Total score: ${updated.total_score}` })
      handleSelectExamForGrading(selectedExamForEval)
    } catch (err: any) {
      setAlert({ type: 'error', message: err.response?.data?.error?.message || 'Failed to save evaluation' })
    } finally {
      setLoading(false)
    }
  }

  // ─────────────────────────────────────────────────────────────────────────
  // Analytics Handlers
  // ─────────────────────────────────────────────────────────────────────────
  const handleLoadAnalytics = async (examId: string) => {
    setSelectedExamForAnalytics(examId)
    setLoading(true)
    try {
      const res = await examinationsApi.getExamAnalytics(examId)
      setAnalyticsData(res)
    } catch (err: any) {
      setAlert({ type: 'error', message: err.response?.data?.error?.message || 'Failed to load analytics' })
    } finally {
      setLoading(false)
    }
  }

  const formatTimer = (seconds: number) => {
    const mins = Math.floor(seconds / 60)
    const secs = seconds % 60
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`
  }

  return (
    <Box sx={{ maxWidth: 1400, margin: '0 auto' }}>
      {/* Header */}
      <Box sx={{ mb: 3 }}>
        <PageHeader
          title="Examinations"
          description="Schedule exams, manage the question bank, and review attempts."
          icon={<ExamIcon />}
        >
          <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
            <Button variant="outlined" startIcon={<RefreshIcon />} onClick={loadExaminations}>
              Refresh
            </Button>
            <Button variant="contained" startIcon={<AddIcon />} onClick={() => setOpenCreateExam(true)}>
              Schedule Examination
            </Button>
          </Box>
        </PageHeader>
      </Box>

      {alert && (
        <Alert severity={alert.type} sx={{ mb: 3 }} onClose={() => setAlert(null)}>
          {alert.message}
        </Alert>
      )}

      {loading && <LinearProgress sx={{ mb: 2 }} />}

      {/* Tabs */}
      <Card sx={{ mb: 3 }}>
        <Tabs value={activeTab} onChange={(_, v) => setActiveTab(v)} variant="scrollable" scrollButtons="auto">
          <Tab icon={<ExamIcon />} label="Examinations & Schedules" />
          <Tab icon={<QuestionBankIcon />} label="Question Bank" />
          <Tab icon={<TimerIcon />} label="Live Exam Room" />
          <Tab icon={<GradingIcon />} label="Teacher Evaluation" />
          <Tab icon={<AnalyticsIcon />} label="Performance Reports" />
        </Tabs>
      </Card>

      {/* TAB 0: EXAMINATIONS & SCHEDULES */}
      {activeTab === 0 && (
        <Box>
          <Box sx={{ mb: 2, display: 'flex', gap: 2, alignItems: 'center' }}>
            <TextField
              select
              size="small"
              label="Academic Session"
              value={selectedSessionId}
              onChange={(e) => setSelectedSessionId(e.target.value)}
              sx={{ minWidth: 220 }}
            >
              {sessions.map((s) => (
                <MenuItem key={s.id} value={s.id}>
                  {s.name} {s.is_current ? '(Active)' : ''}
                </MenuItem>
              ))}
            </TextField>
          </Box>

          <TableContainer component={Paper} sx={{ overflowX: 'auto', width: '100%' }}>
            <Table sx={{ minWidth: 750 }}>
              <TableHead>
                <TableRow sx={{ backgroundColor: 'grey.100' }}>
                  <TableCell><strong>Title & Code</strong></TableCell>
                  <TableCell><strong>Type / Mode</strong></TableCell>
                  <TableCell><strong>Class & Subject</strong></TableCell>
                  <TableCell><strong>Marks (Pass / Total)</strong></TableCell>
                  <TableCell><strong>Duration</strong></TableCell>
                  <TableCell><strong>Status</strong></TableCell>
                  <TableCell><strong>Published</strong></TableCell>
                  <TableCell align="right"><strong>Actions</strong></TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {examinations.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={8} align="center" sx={{ py: 4 }}>
                      <Typography color="text.secondary">No examinations found for this session.</Typography>
                    </TableCell>
                  </TableRow>
                ) : (
                  examinations.map((exam) => (
                    <TableRow key={exam.id} hover>
                      <TableCell>
                        <Typography fontWeight="bold">{exam.title}</Typography>
                        <Typography variant="caption" color="text.secondary">
                          {exam.code || 'NO-CODE'} • {exam.questions_count} questions
                        </Typography>
                      </TableCell>
                      <TableCell>
                        <Chip label={exam.exam_type} size="small" sx={{ mr: 0.5 }} />
                        <Chip label={exam.mode} size="small" variant="outlined" color="primary" />
                      </TableCell>
                      <TableCell>
                        <Typography variant="body2">{exam.class_name || 'All Classes'}</Typography>
                        <Typography variant="caption" color="text.secondary">{exam.subject_name || 'General'}</Typography>
                      </TableCell>
                      <TableCell>
                        <Typography variant="body2" fontWeight="bold">
                          {exam.passing_marks} / {exam.total_marks}
                        </Typography>
                      </TableCell>
                      <TableCell>{exam.duration_minutes} mins</TableCell>
                      <TableCell>
                        <Chip
                          label={exam.status}
                          size="small"
                          color={exam.status === 'SCHEDULED' || exam.status === 'ONGOING' ? 'success' : 'default'}
                        />
                      </TableCell>
                      <TableCell>
                        <Tooltip title={exam.is_published ? 'Click to unpublish' : 'Click to publish'}>
                          <Chip
                            label={exam.is_published ? 'Published' : 'Draft'}
                            size="small"
                            color={exam.is_published ? 'primary' : 'default'}
                            onClick={() => handleTogglePublish(exam)}
                            sx={{ cursor: 'pointer' }}
                          />
                        </Tooltip>
                        <Tooltip title={exam.is_results_published ? 'Results released' : 'Results hidden'}>
                          <Chip
                            label={exam.is_results_published ? 'Results Out' : 'Results Hidden'}
                            size="small"
                            variant="outlined"
                            color={exam.is_results_published ? 'success' : 'default'}
                            onClick={() => handleToggleResultsPublish(exam)}
                            sx={{ cursor: 'pointer', ml: 0.5 }}
                          />
                        </Tooltip>
                      </TableCell>
                      <TableCell align="right">
                        <Button
                          size="small"
                          variant="contained"
                          color="success"
                          startIcon={<StartIcon />}
                          onClick={() => handleLaunchExamRoom(exam.id)}
                          sx={{ mr: 1 }}
                        >
                          Test Take
                        </Button>
                        <Button
                          size="small"
                          variant="outlined"
                          onClick={() => {
                            setActiveTab(3)
                            handleSelectExamForGrading(exam.id)
                          }}
                          sx={{ mr: 1 }}
                        >
                          Grade ({exam.attempts_count})
                        </Button>
                        <Button
                          size="small"
                          variant="text"
                          onClick={() => {
                            setActiveTab(4)
                            handleLoadAnalytics(exam.id)
                          }}
                        >
                          Analytics
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

      {/* TAB 1: QUESTION BANK */}
      {activeTab === 1 && (
        <Box>
          <Box sx={{ mb: 2, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <Typography variant="h6" fontWeight="bold">
              Centralized Question Repository ({questions.length} items)
            </Typography>
            <Button variant="contained" startIcon={<AddIcon />} onClick={() => setOpenCreateQuestion(true)}>
              New Question
            </Button>
          </Box>

          <Grid container spacing={2}>
            {questions.map((q) => (
              <Grid item xs={12} md={6} key={q.id}>
                <Card variant="outlined">
                  <CardContent>
                    <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                      <Chip label={q.category} size="small" color="primary" variant="outlined" />
                      <Box>
                        <Chip label={q.question_type} size="small" sx={{ mr: 0.5 }} />
                        <Chip
                          label={q.difficulty}
                          size="small"
                          color={q.difficulty === 'EASY' ? 'success' : q.difficulty === 'HARD' ? 'error' : 'warning'}
                        />
                      </Box>
                    </Box>
                    <Typography fontWeight="bold" sx={{ mb: 1 }}>
                      {q.question_text}
                    </Typography>
                    {q.options && Array.isArray(q.options) && (
                      <Box sx={{ pl: 2, mb: 1 }}>
                        {q.options.map((opt: any) => (
                          <Typography
                            key={opt.id}
                            variant="body2"
                            color={opt.id === q.correct_answer ? 'success.main' : 'text.secondary'}
                            fontWeight={opt.id === q.correct_answer ? 'bold' : 'normal'}
                          >
                            • {opt.text} {opt.id === q.correct_answer && '✓ (Correct)'}
                          </Typography>
                        ))}
                      </Box>
                    )}
                    <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mt: 2 }}>
                      <Typography variant="caption" color="text.secondary">
                        Marks: +{q.default_marks} / -{q.default_negative_marks}
                      </Typography>
                      {q.explanation && (
                        <Typography variant="caption" color="text.secondary" sx={{ fontStyle: 'italic' }}>
                          Exp: {q.explanation.slice(0, 45)}...
                        </Typography>
                      )}
                    </Box>
                  </CardContent>
                </Card>
              </Grid>
            ))}
          </Grid>
        </Box>
      )}

      {/* TAB 2: LIVE ONLINE EXAM ROOM */}
      {activeTab === 2 && (
        <Box>
          {!activeExamSession ? (
            <Card sx={{ p: 4, textAlign: 'center' }}>
              <ExamIcon sx={{ fontSize: 60, color: 'text.secondary', mb: 2 }} />
              <Typography variant="h6">No Active Exam Session Running</Typography>
              <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                Go to "Examinations & Schedules" and click "Test Take" on any published exam to launch the interactive exam room.
              </Typography>
              {examResultSummary && (
                <Alert severity="success" sx={{ maxWidth: 500, margin: '0 auto', textAlign: 'left' }}>
                  <Typography fontWeight="bold">{examResultSummary.message}</Typography>
                  {examResultSummary.instant_score !== null && (
                    <Typography variant="body2">Instant Score: {examResultSummary.instant_score}</Typography>
                  )}
                  <Typography variant="caption">Submitted at: {examResultSummary.submitted_at}</Typography>
                </Alert>
              )}
            </Card>
          ) : (
            <Box>
              {/* Exam Room Header & Countdown Timer */}
              <Card sx={{ mb: 3, p: 2, display: 'flex', justifyContent: 'space-between', alignItems: 'center', backgroundColor: 'grey.900', color: 'white' }}>
                <Box>
                  <Typography variant="h6" fontWeight="bold">
                    {activeExamSession.exam_title}
                  </Typography>
                  <Typography variant="caption" color="grey.400">
                    Question {currentQuestionIdx + 1} of {activeExamSession.questions.length} • {lastAutosaved ? `Autosaved at ${lastAutosaved}` : 'Autosave active'}
                  </Typography>
                </Box>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, backgroundColor: remainingTime < 300 ? 'error.dark' : 'primary.dark', px: 2, py: 1, borderRadius: 2 }}>
                    <TimerIcon />
                    <Typography variant="h6" fontWeight="bold">
                      {formatTimer(remainingTime)}
                    </Typography>
                  </Box>
                  <Button variant="contained" color="error" onClick={handleSubmitExam}>
                    Submit Exam
                  </Button>
                </Box>
              </Card>

              {/* Question Navigation Palette */}
              <Card sx={{ mb: 3, p: 2 }}>
                <Typography variant="caption" fontWeight="bold" sx={{ mb: 1, display: 'block' }}>
                  QUESTION PALETTE
                </Typography>
                <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
                  {activeExamSession.questions.map((q, idx) => {
                    const isAnswered = studentAnswers[q.id] !== undefined && studentAnswers[q.id] !== ''
                    const isCurrent = idx === currentQuestionIdx
                    return (
                      <Button
                        key={q.id}
                        size="small"
                        variant={isCurrent ? 'contained' : isAnswered ? 'outlined' : 'text'}
                        color={isAnswered ? 'success' : 'inherit'}
                        onClick={() => setCurrentQuestionIdx(idx)}
                        sx={{ minWidth: 40, height: 40, borderRadius: 1 }}
                      >
                        {idx + 1}
                      </Button>
                    )
                  })}
                </Box>
              </Card>

              {/* Current Question View */}
              {activeExamSession.questions[currentQuestionIdx] && (
                <Card sx={{ p: 3 }}>
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 2 }}>
                    <Chip label={`Question ${currentQuestionIdx + 1}`} color="primary" />
                    <Typography variant="body2" color="text.secondary">
                      +{activeExamSession.questions[currentQuestionIdx].marks} marks / -{activeExamSession.questions[currentQuestionIdx].negative_marks} neg
                    </Typography>
                  </Box>

                  <Typography variant="h6" sx={{ mb: 3 }}>
                    {activeExamSession.questions[currentQuestionIdx].question_text}
                  </Typography>

                  {/* Options render based on question type */}
                  {activeExamSession.questions[currentQuestionIdx].options ? (
                    <FormControl component="fieldset">
                      <FormLabel component="legend">Choose Option:</FormLabel>
                      <RadioGroup
                        value={studentAnswers[activeExamSession.questions[currentQuestionIdx].id] || ''}
                        onChange={(e) => handleSelectAnswer(activeExamSession.questions[currentQuestionIdx].id, e.target.value)}
                      >
                        {activeExamSession.questions[currentQuestionIdx].options.map((opt: any) => (
                          <FormControlLabel
                            key={opt.id}
                            value={opt.id}
                            control={<Radio />}
                            label={opt.text}
                            sx={{ mb: 1, p: 1, border: '1px solid #e0e0e0', borderRadius: 1, width: '100%' }}
                          />
                        ))}
                      </RadioGroup>
                    </FormControl>
                  ) : (
                    <TextField
                      fullWidth
                      multiline
                      rows={4}
                      placeholder="Type your answer here..."
                      value={studentAnswers[activeExamSession.questions[currentQuestionIdx].id] || ''}
                      onChange={(e) => handleSelectAnswer(activeExamSession.questions[currentQuestionIdx].id, e.target.value)}
                    />
                  )}

                  {/* Bottom Navigation */}
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', mt: 4 }}>
                    <Button
                      variant="outlined"
                      disabled={currentQuestionIdx === 0}
                      onClick={() => setCurrentQuestionIdx((p) => p - 1)}
                    >
                      Previous
                    </Button>
                    <Button
                      variant="contained"
                      disabled={currentQuestionIdx === activeExamSession.questions.length - 1}
                      onClick={() => setCurrentQuestionIdx((p) => p + 1)}
                    >
                      Next Question
                    </Button>
                  </Box>
                </Card>
              )}
            </Box>
          )}
        </Box>
      )}

      {/* TAB 3: TEACHER EVALUATION */}
      {activeTab === 3 && (
        <Box>
          <Box sx={{ mb: 2, display: 'flex', gap: 2 }}>
            <TextField
              select
              size="small"
              label="Select Examination"
              value={selectedExamForEval}
              onChange={(e) => handleSelectExamForGrading(e.target.value)}
              sx={{ minWidth: 300 }}
            >
              {examinations.map((e) => (
                <MenuItem key={e.id} value={e.id}>
                  {e.title}
                </MenuItem>
              ))}
            </TextField>
          </Box>

          <Grid container spacing={3}>
            {/* Attempts Roster */}
            <Grid item xs={12} md={4}>
              <Card>
                <CardContent>
                  <Typography variant="h6" fontWeight="bold" sx={{ mb: 2 }}>
                    Student Attempts
                  </Typography>
                  {attemptsList.length === 0 ? (
                    <Typography color="text.secondary">No student attempts recorded.</Typography>
                  ) : (
                    attemptsList.map((att) => (
                      <Paper
                        key={att.attempt_id}
                        sx={{
                          p: 1.5,
                          mb: 1,
                          cursor: 'pointer',
                          backgroundColor: evaluationDetail?.attempt_id === att.attempt_id ? 'primary.light' : 'background.paper',
                        }}
                        onClick={() => handleOpenEvaluationDetail(att.attempt_id)}
                      >
                        <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                          <Typography fontWeight="bold">{att.student_name}</Typography>
                          <Chip label={att.status} size="small" color={att.status === 'EVALUATED' ? 'success' : 'warning'} />
                        </Box>
                        <Typography variant="caption" color="text.secondary">
                          Adm: {att.admission_number} • Score: {att.total_score !== null ? att.total_score : 'Pending'}
                        </Typography>
                      </Paper>
                    ))
                  )}
                </CardContent>
              </Card>
            </Grid>

            {/* Evaluation Scoring Pane */}
            <Grid item xs={12} md={8}>
              {!evaluationDetail ? (
                <Card sx={{ p: 4, textAlign: 'center' }}>
                  <Typography color="text.secondary">Select an attempt from the left to view answers and grade.</Typography>
                </Card>
              ) : (
                <Card>
                  <CardContent>
                    <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
                      <Box>
                        <Typography variant="h6" fontWeight="bold">
                          Evaluating: {evaluationDetail.student_name}
                        </Typography>
                        <Typography variant="caption" color="text.secondary">
                          Admission: {evaluationDetail.admission_number} • Status: {evaluationDetail.status}
                        </Typography>
                      </Box>
                      <Button variant="contained" color="success" onClick={handleSubmitEvaluation}>
                        Save All Evaluations
                      </Button>
                    </Box>

                    {evaluationDetail.answers.map((ans, idx) => (
                      <Paper key={ans.id} variant="outlined" sx={{ p: 2, mb: 2 }}>
                        <Typography fontWeight="bold" sx={{ mb: 1 }}>
                          Q{idx + 1}: {ans.question_text}
                        </Typography>
                        <Typography variant="body2" sx={{ mb: 1, p: 1, backgroundColor: 'grey.50', borderRadius: 1 }}>
                          <strong>Student Answer:</strong> {JSON.stringify(ans.student_answer) || 'No Answer'}
                        </Typography>
                        {ans.correct_answer && (
                          <Typography variant="caption" color="success.main" sx={{ display: 'block', mb: 1 }}>
                            Correct Reference: {JSON.stringify(ans.correct_answer)}
                          </Typography>
                        )}
                        <Grid container spacing={2} sx={{ mt: 1 }}>
                          <Grid item xs={4}>
                            <TextField
                              size="small"
                              type="number"
                              label={`Marks (Max ${ans.max_marks})`}
                              value={evalMarks[ans.id] !== undefined ? evalMarks[ans.id] : ''}
                              onChange={(e) => setEvalMarks({ ...evalMarks, [ans.id]: Number(e.target.value) })}
                              fullWidth
                            />
                          </Grid>
                          <Grid item xs={8}>
                            <TextField
                              size="small"
                              label="Teacher Feedback / Remarks"
                              value={evalFeedback[ans.id] || ''}
                              onChange={(e) => setEvalFeedback({ ...evalFeedback, [ans.id]: e.target.value })}
                              fullWidth
                            />
                          </Grid>
                        </Grid>
                      </Paper>
                    ))}
                  </CardContent>
                </Card>
              )}
            </Grid>
          </Grid>
        </Box>
      )}

      {/* TAB 4: PERFORMANCE REPORTS & ANALYTICS */}
      {activeTab === 4 && (
        <Box>
          <Box sx={{ mb: 2, display: 'flex', gap: 2 }}>
            <TextField
              select
              size="small"
              label="Select Examination"
              value={selectedExamForAnalytics}
              onChange={(e) => handleLoadAnalytics(e.target.value)}
              sx={{ minWidth: 300 }}
            >
              {examinations.map((e) => (
                <MenuItem key={e.id} value={e.id}>
                  {e.title}
                </MenuItem>
              ))}
            </TextField>
          </Box>

          {!analyticsData ? (
            <Card sx={{ p: 4, textAlign: 'center' }}>
              <AnalyticsIcon sx={{ fontSize: 60, color: 'text.secondary', mb: 2 }} />
              <Typography color="text.secondary">Select an examination above to view analytics and metrics.</Typography>
            </Card>
          ) : (
            <Box>
              {/* Metric Cards */}
              <Grid container spacing={2} sx={{ mb: 3 }}>
                <Grid item xs={6} md={2.4}>
                  <Card>
                    <CardContent sx={{ textAlign: 'center' }}>
                      <Typography variant="h5" fontWeight="bold">
                        {analyticsData.total_attempts}
                      </Typography>
                      <Typography variant="caption" color="text.secondary">
                        Total Attempts
                      </Typography>
                    </CardContent>
                  </Card>
                </Grid>
                <Grid item xs={6} md={2.4}>
                  <Card>
                    <CardContent sx={{ textAlign: 'center' }}>
                      <Typography variant="h5" fontWeight="bold" color="primary.main">
                        {analyticsData.average_score}
                      </Typography>
                      <Typography variant="caption" color="text.secondary">
                        Average Score
                      </Typography>
                    </CardContent>
                  </Card>
                </Grid>
                <Grid item xs={6} md={2.4}>
                  <Card>
                    <CardContent sx={{ textAlign: 'center' }}>
                      <Typography variant="h5" fontWeight="bold" color="success.main">
                        {analyticsData.highest_score}
                      </Typography>
                      <Typography variant="caption" color="text.secondary">
                        Highest Score
                      </Typography>
                    </CardContent>
                  </Card>
                </Grid>
                <Grid item xs={6} md={2.4}>
                  <Card>
                    <CardContent sx={{ textAlign: 'center' }}>
                      <Typography variant="h5" fontWeight="bold" color="error.main">
                        {analyticsData.lowest_score}
                      </Typography>
                      <Typography variant="caption" color="text.secondary">
                        Lowest Score
                      </Typography>
                    </CardContent>
                  </Card>
                </Grid>
                <Grid item xs={6} md={2.4}>
                  <Card>
                    <CardContent sx={{ textAlign: 'center' }}>
                      <Typography variant="h5" fontWeight="bold" color="info.main">
                        {analyticsData.pass_percentage}%
                      </Typography>
                      <Typography variant="caption" color="text.secondary">
                        Pass Percentage
                      </Typography>
                    </CardContent>
                  </Card>
                </Grid>
              </Grid>

              {/* Grade Distribution */}
              <Card sx={{ mb: 3, p: 2 }}>
                <Typography variant="h6" fontWeight="bold" sx={{ mb: 2 }}>
                  Grade Distribution
                </Typography>
                <Grid container spacing={2}>
                  {Object.entries(analyticsData.grade_distribution).map(([grade, count]) => (
                    <Grid item xs={2.4} key={grade}>
                      <Paper variant="outlined" sx={{ p: 2, textAlign: 'center' }}>
                        <Typography variant="h6" fontWeight="bold">
                          {grade}
                        </Typography>
                        <Typography variant="body2" color="text.secondary">
                          {count} students
                        </Typography>
                      </Paper>
                    </Grid>
                  ))}
                </Grid>
              </Card>

              {/* Question Success Rates */}
              <Card>
                <CardContent>
                  <Typography variant="h6" fontWeight="bold" sx={{ mb: 2 }}>
                    Per-Question Success Rate
                  </Typography>
                  <TableContainer sx={{ overflowX: 'auto', width: '100%' }}>
                    <Table size="small" sx={{ minWidth: 600 }}>
                      <TableHead>
                        <TableRow>
                          <TableCell><strong>#</strong></TableCell>
                          <TableCell><strong>Question Preview</strong></TableCell>
                          <TableCell><strong>Type</strong></TableCell>
                          <TableCell><strong>Max Marks</strong></TableCell>
                          <TableCell><strong>Attempts</strong></TableCell>
                          <TableCell><strong>Correct</strong></TableCell>
                          <TableCell><strong>Success Rate</strong></TableCell>
                        </TableRow>
                      </TableHead>
                      <TableBody>
                        {analyticsData.question_analytics.map((qa) => (
                          <TableRow key={qa.question_id}>
                            <TableCell>{qa.order_index + 1}</TableCell>
                            <TableCell>{qa.question_text}</TableCell>
                            <TableCell>{qa.question_type}</TableCell>
                            <TableCell>{qa.max_marks}</TableCell>
                            <TableCell>{qa.total_attempts}</TableCell>
                            <TableCell>{qa.correct_count}</TableCell>
                            <TableCell>
                              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                                <LinearProgress
                                  variant="determinate"
                                  value={qa.success_rate}
                                  sx={{ flexGrow: 1, height: 8, borderRadius: 1 }}
                                  color={qa.success_rate > 70 ? 'success' : qa.success_rate > 40 ? 'warning' : 'error'}
                                />
                                <Typography variant="caption">{qa.success_rate}%</Typography>
                              </Box>
                            </TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </TableContainer>
                </CardContent>
              </Card>
            </Box>
          )}
        </Box>
      )}

      {/* CREATE EXAM DIALOG */}
      <Dialog open={openCreateExam} onClose={() => setOpenCreateExam(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Schedule Examination</DialogTitle>
        <DialogContent dividers>
          <Grid container spacing={2}>
            <Grid item xs={12}>
              <TextField
                fullWidth
                size="small"
                label="Examination Title"
                value={examForm.title}
                onChange={(e) => setExamForm({ ...examForm, title: e.target.value })}
              />
            </Grid>
            <Grid item xs={6}>
              <TextField
                fullWidth
                size="small"
                label="Exam Code"
                value={examForm.code}
                onChange={(e) => setExamForm({ ...examForm, code: e.target.value })}
              />
            </Grid>
            <Grid item xs={6}>
              <TextField
                select
                fullWidth
                size="small"
                label="Exam Type"
                value={examForm.exam_type}
                onChange={(e) => setExamForm({ ...examForm, exam_type: e.target.value })}
              >
                <MenuItem value="DAILY_TEST">Daily Test</MenuItem>
                <MenuItem value="WEEKLY_TEST">Weekly Test</MenuItem>
                <MenuItem value="MONTHLY_TEST">Monthly Test</MenuItem>
                <MenuItem value="UNIT_TEST">Unit Test</MenuItem>
                <MenuItem value="MID_TERM">Mid Term Exam</MenuItem>
                <MenuItem value="FINAL_EXAM">Final Exam</MenuItem>
                <MenuItem value="PRACTICAL">Practical Exam</MenuItem>
                <MenuItem value="MOCK_TEST">Mock Test</MenuItem>
              </TextField>
            </Grid>
            {isCollege ? (
              <>
                <Grid item xs={12} sm={6}>
                  <TextField select fullWidth size="small" label="Course" value={examForm.course_id} onChange={(event) => {
                    setSemesters([])
                    setExamForm({ ...examForm, course_id: event.target.value, semester_id: '' })
                  }}>
                    <MenuItem value="">All courses</MenuItem>
                    {courses.map((course) => <MenuItem key={course.id} value={course.id}>{course.name}</MenuItem>)}
                  </TextField>
                </Grid>
                <Grid item xs={12} sm={6}>
                  <TextField select fullWidth size="small" label="Semester" value={examForm.semester_id}
                    disabled={!examForm.course_id} onChange={(event) => setExamForm({ ...examForm, semester_id: event.target.value })}>
                    <MenuItem value="">All semesters</MenuItem>
                    {semesters.map((semester) => <MenuItem key={semester.id} value={semester.id}>{semester.name}</MenuItem>)}
                  </TextField>
                </Grid>
              </>
            ) : (
            <Grid item xs={6}>
              <TextField
                select
                fullWidth
                size="small"
                label="Class"
                value={examForm.class_id}
                onChange={(e) => setExamForm({ ...examForm, class_id: e.target.value })}
              >
                <MenuItem value="">All classes</MenuItem>
                {classes.map((c) => (
                  <MenuItem key={c.id} value={c.id}>
                    {c.name}
                  </MenuItem>
                ))}
              </TextField>
            </Grid>
            )}
            <Grid item xs={12} sm={6}>
              <TextField select fullWidth size="small" label="Mode" value={examForm.mode}
                onChange={(event) => setExamForm({ ...examForm, mode: event.target.value })}>
                <MenuItem value="ONLINE">Online</MenuItem><MenuItem value="OFFLINE">In person</MenuItem>
              </TextField>
            </Grid>
            <Grid item xs={12} sm={6}>
              <TextField fullWidth size="small" type="datetime-local" label="Starts" value={examForm.start_datetime}
                slotProps={{ inputLabel: { shrink: true } }} onChange={(event) => setExamForm({ ...examForm, start_datetime: event.target.value })} />
            </Grid>
            <Grid item xs={12} sm={6}>
              <TextField fullWidth size="small" type="datetime-local" label="Ends" value={examForm.end_datetime}
                slotProps={{ inputLabel: { shrink: true } }} onChange={(event) => setExamForm({ ...examForm, end_datetime: event.target.value })} />
            </Grid>
            <Grid item xs={6}>
              <TextField
                select
                fullWidth
                size="small"
                label="Subject"
                value={examForm.subject_id}
                onChange={(e) => setExamForm({ ...examForm, subject_id: e.target.value })}
              >
                {subjects.map((s) => (
                  <MenuItem key={s.id} value={s.id}>
                    {s.name}
                  </MenuItem>
                ))}
              </TextField>
            </Grid>
            <Grid item xs={4}>
              <TextField
                fullWidth
                size="small"
                type="number"
                label="Total Marks"
                value={examForm.total_marks}
                onChange={(e) => setExamForm({ ...examForm, total_marks: Number(e.target.value) })}
              />
            </Grid>
            <Grid item xs={4}>
              <TextField
                fullWidth
                size="small"
                type="number"
                label="Passing Marks"
                value={examForm.passing_marks}
                onChange={(e) => setExamForm({ ...examForm, passing_marks: Number(e.target.value) })}
              />
            </Grid>
            <Grid item xs={4}>
              <TextField
                fullWidth
                size="small"
                type="number"
                label="Duration (mins)"
                value={examForm.duration_minutes}
                onChange={(e) => setExamForm({ ...examForm, duration_minutes: Number(e.target.value) })}
              />
            </Grid>
          </Grid>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setOpenCreateExam(false)}>Cancel</Button>
          <Button variant="contained" onClick={handleCreateExam}>
            Create
          </Button>
        </DialogActions>
      </Dialog>

      {/* CREATE QUESTION DIALOG */}
      <Dialog open={openCreateQuestion} onClose={() => setOpenCreateQuestion(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Add Question to Bank</DialogTitle>
        <DialogContent dividers>
          <Grid container spacing={2}>
            <Grid item xs={6}>
              <TextField
                fullWidth
                size="small"
                label="Category / Topic"
                value={questionForm.category}
                onChange={(e) => setQuestionForm({ ...questionForm, category: e.target.value })}
              />
            </Grid>
            <Grid item xs={3}>
              <TextField
                select
                fullWidth
                size="small"
                label="Difficulty"
                value={questionForm.difficulty}
                onChange={(e) => setQuestionForm({ ...questionForm, difficulty: e.target.value })}
              >
                <MenuItem value="EASY">Easy</MenuItem>
                <MenuItem value="MEDIUM">Medium</MenuItem>
                <MenuItem value="HARD">Hard</MenuItem>
              </TextField>
            </Grid>
            <Grid item xs={3}>
              <TextField
                select
                fullWidth
                size="small"
                label="Question Type"
                value={questionForm.question_type}
                onChange={(e) => setQuestionForm({ ...questionForm, question_type: e.target.value })}
              >
                <MenuItem value="MCQ">MCQ</MenuItem>
                <MenuItem value="TRUE_FALSE">True / False</MenuItem>
                <MenuItem value="SHORT_ANSWER">Short Answer</MenuItem>
                <MenuItem value="LONG_ANSWER">Long Answer</MenuItem>
                <MenuItem value="NUMERICAL">Numerical</MenuItem>
              </TextField>
            </Grid>
            <Grid item xs={12}>
              <TextField
                fullWidth
                multiline
                rows={2}
                size="small"
                label="Question Text"
                value={questionForm.question_text}
                onChange={(e) => setQuestionForm({ ...questionForm, question_text: e.target.value })}
              />
            </Grid>
            {questionForm.question_type === 'MCQ' && (
              <>
                <Grid item xs={6}>
                  <TextField
                    fullWidth
                    size="small"
                    label="Option A"
                    value={questionForm.option_a}
                    onChange={(e) => setQuestionForm({ ...questionForm, option_a: e.target.value })}
                  />
                </Grid>
                <Grid item xs={6}>
                  <TextField
                    fullWidth
                    size="small"
                    label="Option B"
                    value={questionForm.option_b}
                    onChange={(e) => setQuestionForm({ ...questionForm, option_b: e.target.value })}
                  />
                </Grid>
                <Grid item xs={6}>
                  <TextField
                    fullWidth
                    size="small"
                    label="Option C"
                    value={questionForm.option_c}
                    onChange={(e) => setQuestionForm({ ...questionForm, option_c: e.target.value })}
                  />
                </Grid>
                <Grid item xs={6}>
                  <TextField
                    fullWidth
                    size="small"
                    label="Option D"
                    value={questionForm.option_d}
                    onChange={(e) => setQuestionForm({ ...questionForm, option_d: e.target.value })}
                  />
                </Grid>
                <Grid item xs={12}>
                  <TextField
                    select
                    fullWidth
                    size="small"
                    label="Correct Option"
                    value={questionForm.correct_answer}
                    onChange={(e) => setQuestionForm({ ...questionForm, correct_answer: e.target.value })}
                  >
                    <MenuItem value="opt_a">Option A</MenuItem>
                    <MenuItem value="opt_b">Option B</MenuItem>
                    <MenuItem value="opt_c">Option C</MenuItem>
                    <MenuItem value="opt_d">Option D</MenuItem>
                  </TextField>
                </Grid>
              </>
            )}
            <Grid item xs={6}>
              <TextField
                fullWidth
                size="small"
                type="number"
                label="Marks"
                value={questionForm.default_marks}
                onChange={(e) => setQuestionForm({ ...questionForm, default_marks: Number(e.target.value) })}
              />
            </Grid>
            <Grid item xs={6}>
              <TextField
                fullWidth
                size="small"
                type="number"
                label="Negative Penalty"
                value={questionForm.default_negative_marks}
                onChange={(e) => setQuestionForm({ ...questionForm, default_negative_marks: Number(e.target.value) })}
              />
            </Grid>
            <Grid item xs={12}>
              <TextField
                fullWidth
                size="small"
                label="Explanation / Rationale"
                value={questionForm.explanation}
                onChange={(e) => setQuestionForm({ ...questionForm, explanation: e.target.value })}
              />
            </Grid>
          </Grid>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setOpenCreateQuestion(false)}>Cancel</Button>
          <Button variant="contained" onClick={handleCreateQuestion}>
            Save Question
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  )
}
