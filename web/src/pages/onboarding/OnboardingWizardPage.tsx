import { useState } from 'react'
import {
  Box,
  Card,
  CardContent,
  Typography,
  Stepper,
  Step,
  StepLabel,
  Button,
  TextField,
  Grid,
  CircularProgress,
  Alert,
  Paper,
  Switch,
  FormControlLabel,
  IconButton,
  Chip,
  Container,
} from '@mui/material'
import AddIcon from '@mui/icons-material/Add'
import DeleteOutlineIcon from '@mui/icons-material/DeleteOutline'
import DownloadIcon from '@mui/icons-material/Download'
import UploadFileIcon from '@mui/icons-material/UploadFile'
import CheckCircleIcon from '@mui/icons-material/CheckCircle'
import RocketLaunchIcon from '@mui/icons-material/RocketLaunch'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { institutionsApi } from '@/api/institutions'

const STEPS = [
  'Profile & Branding',
  'Academic Session',
  'Classes / Departments',
  'Subjects & Courses',
  'Teacher Invitations',
  'Student Import',
  'Notifications',
  'Launch Portal',
]

export default function OnboardingWizardPage() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [activeStep, setActiveStep] = useState(0)

  // Step 0: Profile
  const [logoUrl, setLogoUrl] = useState('')
  const [phone, setPhone] = useState('')
  const [address, setAddress] = useState('')
  const [timezone, setTimezone] = useState('Asia/Kolkata')
  const [currency, setCurrency] = useState('INR')

  // Step 1: Academic Session
  const [sessionName, setSessionName] = useState('Academic Year 2026-2027')
  const [sessionCode, setSessionCode] = useState('AY-2026-27')
  const [startDate, setStartDate] = useState('2026-06-01')
  const [endDate, setEndDate] = useState('2027-05-31')

  // Step 2: Structure (Classes or Departments)
  const [structureItems, setStructureItems] = useState([
    { name: 'Class 9', code: 'CLS-9', sub_items: 'A, B' },
    { name: 'Class 10', code: 'CLS-10', sub_items: 'A, B, C' },
    { name: 'Class 11', code: 'CLS-11', sub_items: 'Science, Commerce' },
    { name: 'Class 12', code: 'CLS-12', sub_items: 'Science, Commerce' },
  ])

  // Step 3: Subjects
  const [subjects, setSubjects] = useState([
    { name: 'Mathematics', code: 'MATH-101', subject_type: 'THEORY' },
    { name: 'Physics & Chemistry', code: 'SCI-101', subject_type: 'THEORY' },
    { name: 'Computer Science Lab', code: 'CS-LAB-01', subject_type: 'PRACTICAL' },
    { name: 'English Literature', code: 'ENG-101', subject_type: 'THEORY' },
  ])

  // Step 4: Teachers
  const [teachers, setTeachers] = useState([
    { email: '', full_name: '', designation: 'Senior Faculty' },
  ])

  // Step 5: Student Import
  const [csvFile, setCsvFile] = useState<File | null>(null)
  const [importResult, setImportResult] = useState<{ imported_count: number; total_rows: number } | null>(null)
  const [uploading, setUploading] = useState(false)

  // Step 6: Notifications
  const [emailNotif, setEmailNotif] = useState(true)
  const [smsNotif, setSmsNotif] = useState(false)
  const [whatsappNotif, setWhatsappNotif] = useState(false)

  const [stepError, setStepError] = useState<string | null>(null)
  const [stepLoading, setStepLoading] = useState(false)

  // Load institution onboarding status
  const { data: statusData } = useQuery({
    queryKey: ['onboardingStatus'],
    queryFn: institutionsApi.getOnboardingStatus,
  })

  const isCollege = statusData?.institution_type === 'COLLEGE'

  const handleNext = async () => {
    setStepError(null)
    setStepLoading(true)

    try {
      if (activeStep === 0) {
        await institutionsApi.updateProfile({ logo_url: logoUrl, phone, address, timezone, currency })
      } else if (activeStep === 1) {
        await institutionsApi.setupAcademicSession({
          name: sessionName,
          code: sessionCode,
          start_date: startDate,
          end_date: endDate,
        })
      } else if (activeStep === 2) {
        const payload = structureItems.map((item) => ({
          name: item.name,
          code: item.code,
          sub_items: item.sub_items.split(',').map((s) => s.trim()).filter(Boolean),
        }))
        await institutionsApi.setupStructure({ items: payload })
      } else if (activeStep === 3) {
        await institutionsApi.setupSubjects({ subjects })
      } else if (activeStep === 4) {
        const validTeachers = teachers.filter((t) => t.email && t.full_name)
        if (validTeachers.length > 0) {
          await institutionsApi.inviteTeachers({ teachers: validTeachers })
        }
      } else if (activeStep === 5) {
        // Optional student import
        if (csvFile && !importResult) {
          const res = await institutionsApi.importStudents(csvFile)
          setImportResult(res)
        }
      } else if (activeStep === 6) {
        await institutionsApi.setupNotifications({
          email_notifications: emailNotif,
          sms_notifications: smsNotif,
          whatsapp_notifications: whatsappNotif,
        })
      } else if (activeStep === 7) {
        await institutionsApi.completeOnboarding()
        queryClient.invalidateQueries({ queryKey: ['onboardingStatus'] })
        navigate('/dashboard')
        return
      }

      setActiveStep((prev) => prev + 1)
    } catch (err: unknown) {
      const errorObj = err as { response?: { data?: { error?: { message?: string } } } }
      setStepError(errorObj.response?.data?.error?.message || 'Failed to save step configuration.')
    } finally {
      setStepLoading(false)
    }
  }

  const handleBack = () => {
    setStepError(null)
    setActiveStep((prev) => Math.max(0, prev - 1))
  }

  const handleFileUpload = async (file: File) => {
    setCsvFile(file)
    setUploading(true)
    setStepError(null)
    try {
      const res = await institutionsApi.importStudents(file)
      setImportResult(res)
    } catch (err: unknown) {
      const errorObj = err as { response?: { data?: { error?: { message?: string } } } }
      setStepError(errorObj.response?.data?.error?.message || 'Failed to parse student CSV.')
    } finally {
      setUploading(false)
    }
  }

  return (
    <Container maxWidth="lg" sx={{ py: 6 }}>
      <Box mb={4} textAlign="center">
        <Typography variant="h3" fontWeight={800} gutterBottom>
          Institution Onboarding Wizard
        </Typography>
        <Typography variant="body1" color="text.secondary">
          Configure your campus structure, academic years, teachers, and student rosters
        </Typography>
      </Box>

      {/* Stepper Progress */}
      <Card sx={{ mb: 4, p: 3, borderRadius: 2 }}>
        <Stepper activeStep={activeStep} alternativeLabel>
          {STEPS.map((label) => (
            <Step key={label}>
              <StepLabel>{label}</StepLabel>
            </Step>
          ))}
        </Stepper>
      </Card>

      {/* Wizard Step Card */}
      <Card sx={{ borderRadius: 3, boxShadow: '0 4px 20px rgba(0,0,0,0.06)' }}>
        <CardContent sx={{ p: 4 }}>
          {stepError && (
            <Alert severity="error" sx={{ mb: 3 }}>
              {stepError}
            </Alert>
          )}

          {/* STEP 0: Profile */}
          {activeStep === 0 && (
            <Box>
              <Typography variant="h5" fontWeight={700} mb={1}>
                Institution Profile & Branding
              </Typography>
              <Typography variant="body2" color="text.secondary" mb={3}>
                Set your campus logo, physical location, and localized financial preferences.
              </Typography>

              <Grid container spacing={3}>
                <Grid item xs={12} sm={8}>
                  <TextField
                    label="Institution Logo URL"
                    placeholder="https://example.com/logo.png"
                    value={logoUrl}
                    onChange={(e) => setLogoUrl(e.target.value)}
                    fullWidth
                    size="small"
                    helperText="Provide a public PNG or SVG image URL"
                  />
                </Grid>
                <Grid item xs={12} sm={4}>
                  <TextField
                    label="Official Phone"
                    placeholder="+91 98765 43210"
                    value={phone}
                    onChange={(e) => setPhone(e.target.value)}
                    fullWidth
                    size="small"
                  />
                </Grid>
                <Grid item xs={12}>
                  <TextField
                    label="Campus Address"
                    value={address}
                    onChange={(e) => setAddress(e.target.value)}
                    fullWidth
                    size="small"
                  />
                </Grid>
                <Grid item xs={12} sm={6}>
                  <TextField
                    label="System Timezone"
                    value={timezone}
                    onChange={(e) => setTimezone(e.target.value)}
                    fullWidth
                    size="small"
                  />
                </Grid>
                <Grid item xs={12} sm={6}>
                  <TextField
                    label="Base Currency"
                    value={currency}
                    onChange={(e) => setCurrency(e.target.value)}
                    fullWidth
                    size="small"
                  />
                </Grid>
              </Grid>
            </Box>
          )}

          {/* STEP 1: Academic Session */}
          {activeStep === 1 && (
            <Box>
              <Typography variant="h5" fontWeight={700} mb={1}>
                Academic Session Setup
              </Typography>
              <Typography variant="body2" color="text.secondary" mb={3}>
                Configure your current academic calendar year or semester term.
              </Typography>

              <Grid container spacing={3}>
                <Grid item xs={12} sm={8}>
                  <TextField
                    label="Session Name"
                    value={sessionName}
                    onChange={(e) => setSessionName(e.target.value)}
                    fullWidth
                    required
                    size="small"
                  />
                </Grid>
                <Grid item xs={12} sm={4}>
                  <TextField
                    label="Session Identifier Code"
                    value={sessionCode}
                    onChange={(e) => setSessionCode(e.target.value)}
                    fullWidth
                    required
                    size="small"
                  />
                </Grid>
                <Grid item xs={12} sm={6}>
                  <TextField
                    label="Term Start Date"
                    type="date"
                    value={startDate}
                    onChange={(e) => setStartDate(e.target.value)}
                    fullWidth
                    required
                    size="small"
                    InputLabelProps={{ shrink: true }}
                  />
                </Grid>
                <Grid item xs={12} sm={6}>
                  <TextField
                    label="Term End Date"
                    type="date"
                    value={endDate}
                    onChange={(e) => setEndDate(e.target.value)}
                    fullWidth
                    required
                    size="small"
                    InputLabelProps={{ shrink: true }}
                  />
                </Grid>
              </Grid>
            </Box>
          )}

          {/* STEP 2: Classes / Departments Structure */}
          {activeStep === 2 && (
            <Box>
              <Box display="flex" justifyContent="space-between" alignItems="center" mb={1}>
                <Typography variant="h5" fontWeight={700}>
                  {isCollege ? 'Departments & Degree Programs' : 'Classes & Sections'}
                </Typography>
                <Button
                  startIcon={<AddIcon />}
                  size="small"
                  variant="outlined"
                  onClick={() =>
                    setStructureItems([
                      ...structureItems,
                      { name: `New ${isCollege ? 'Department' : 'Class'}`, code: `NEW-${structureItems.length + 1}`, sub_items: 'A' },
                    ])
                  }
                >
                  Add Row
                </Button>
              </Box>
              <Typography variant="body2" color="text.secondary" mb={3}>
                {isCollege
                  ? 'Define academic departments and associated degree programs.'
                  : 'Define grades/classes and sections (comma-separated).'}
              </Typography>

              <Box display="flex" flexDirection="column" gap={2}>
                {structureItems.map((item, idx) => (
                  <Paper key={idx} variant="outlined" sx={{ p: 2, borderRadius: 2 }}>
                    <Grid container spacing={2} alignItems="center">
                      <Grid item xs={12} sm={4}>
                        <TextField
                          label={isCollege ? 'Department Name' : 'Class / Grade Name'}
                          size="small"
                          fullWidth
                          value={item.name}
                          onChange={(e) => {
                            const copy = [...structureItems]
                            copy[idx].name = e.target.value
                            setStructureItems(copy)
                          }}
                        />
                      </Grid>
                      <Grid item xs={12} sm={3}>
                        <TextField
                          label="Code"
                          size="small"
                          fullWidth
                          value={item.code}
                          onChange={(e) => {
                            const copy = [...structureItems]
                            copy[idx].code = e.target.value
                            setStructureItems(copy)
                          }}
                        />
                      </Grid>
                      <Grid item xs={12} sm={4}>
                        <TextField
                          label={isCollege ? 'Courses (comma-separated)' : 'Sections (comma-separated)'}
                          size="small"
                          fullWidth
                          value={item.sub_items}
                          onChange={(e) => {
                            const copy = [...structureItems]
                            copy[idx].sub_items = e.target.value
                            setStructureItems(copy)
                          }}
                        />
                      </Grid>
                      <Grid item xs={12} sm={1} textAlign="right">
                        <IconButton
                          size="small"
                          color="error"
                          onClick={() => setStructureItems(structureItems.filter((_, i) => i !== idx))}
                          disabled={structureItems.length <= 1}
                        >
                          <DeleteOutlineIcon fontSize="small" />
                        </IconButton>
                      </Grid>
                    </Grid>
                  </Paper>
                ))}
              </Box>
            </Box>
          )}

          {/* STEP 3: Subjects */}
          {activeStep === 3 && (
            <Box>
              <Box display="flex" justifyContent="space-between" alignItems="center" mb={1}>
                <Typography variant="h5" fontWeight={700}>
                  Subjects & Academic Modules
                </Typography>
                <Button
                  startIcon={<AddIcon />}
                  size="small"
                  variant="outlined"
                  onClick={() =>
                    setSubjects([
                      ...subjects,
                      { name: 'New Subject', code: `SUB-${subjects.length + 1}`, subject_type: 'THEORY' },
                    ])
                  }
                >
                  Add Subject
                </Button>
              </Box>
              <Typography variant="body2" color="text.secondary" mb={3}>
                Define the core curriculum subjects and practical modules taught at your institution.
              </Typography>

              <Box display="flex" flexDirection="column" gap={2}>
                {subjects.map((sub, idx) => (
                  <Paper key={idx} variant="outlined" sx={{ p: 2, borderRadius: 2 }}>
                    <Grid container spacing={2} alignItems="center">
                      <Grid item xs={12} sm={5}>
                        <TextField
                          label="Subject Name"
                          size="small"
                          fullWidth
                          value={sub.name}
                          onChange={(e) => {
                            const copy = [...subjects]
                            copy[idx].name = e.target.value
                            setSubjects(copy)
                          }}
                        />
                      </Grid>
                      <Grid item xs={12} sm={3}>
                        <TextField
                          label="Subject Code"
                          size="small"
                          fullWidth
                          value={sub.code}
                          onChange={(e) => {
                            const copy = [...subjects]
                            copy[idx].code = e.target.value
                            setSubjects(copy)
                          }}
                        />
                      </Grid>
                      <Grid item xs={12} sm={3}>
                        <TextField
                          select
                          label="Type"
                          size="small"
                          fullWidth
                          SelectProps={{ native: true }}
                          value={sub.subject_type}
                          onChange={(e) => {
                            const copy = [...subjects]
                            copy[idx].subject_type = e.target.value
                            setSubjects(copy)
                          }}
                        >
                          <option value="THEORY">Theory</option>
                          <option value="PRACTICAL">Practical / Lab</option>
                          <option value="ELECTIVE">Elective</option>
                        </TextField>
                      </Grid>
                      <Grid item xs={12} sm={1} textAlign="right">
                        <IconButton
                          size="small"
                          color="error"
                          onClick={() => setSubjects(subjects.filter((_, i) => i !== idx))}
                          disabled={subjects.length <= 1}
                        >
                          <DeleteOutlineIcon fontSize="small" />
                        </IconButton>
                      </Grid>
                    </Grid>
                  </Paper>
                ))}
              </Box>
            </Box>
          )}

          {/* STEP 4: Teachers */}
          {activeStep === 4 && (
            <Box>
              <Box display="flex" justifyContent="space-between" alignItems="center" mb={1}>
                <Typography variant="h5" fontWeight={700}>
                  Teacher & Faculty Invitations
                </Typography>
                <Button
                  startIcon={<AddIcon />}
                  size="small"
                  variant="outlined"
                  onClick={() =>
                    setTeachers([...teachers, { email: '', full_name: '', designation: 'Faculty' }])
                  }
                >
                  Add Teacher
                </Button>
              </Box>
              <Typography variant="body2" color="text.secondary" mb={3}>
                Invite your initial faculty members. Secure onboarding links will be emailed to each recipient.
              </Typography>

              <Box display="flex" flexDirection="column" gap={2}>
                {teachers.map((t, idx) => (
                  <Paper key={idx} variant="outlined" sx={{ p: 2, borderRadius: 2 }}>
                    <Grid container spacing={2} alignItems="center">
                      <Grid item xs={12} sm={4}>
                        <TextField
                          label="Full Name"
                          size="small"
                          fullWidth
                          value={t.full_name}
                          onChange={(e) => {
                            const copy = [...teachers]
                            copy[idx].full_name = e.target.value
                            setTeachers(copy)
                          }}
                        />
                      </Grid>
                      <Grid item xs={12} sm={4}>
                        <TextField
                          label="Email Address"
                          type="email"
                          size="small"
                          fullWidth
                          value={t.email}
                          onChange={(e) => {
                            const copy = [...teachers]
                            copy[idx].email = e.target.value
                            setTeachers(copy)
                          }}
                        />
                      </Grid>
                      <Grid item xs={12} sm={3}>
                        <TextField
                          label="Designation"
                          size="small"
                          fullWidth
                          value={t.designation}
                          onChange={(e) => {
                            const copy = [...teachers]
                            copy[idx].designation = e.target.value
                            setTeachers(copy)
                          }}
                        />
                      </Grid>
                      <Grid item xs={12} sm={1} textAlign="right">
                        <IconButton
                          size="small"
                          color="error"
                          onClick={() => setTeachers(teachers.filter((_, i) => i !== idx))}
                          disabled={teachers.length <= 1}
                        >
                          <DeleteOutlineIcon fontSize="small" />
                        </IconButton>
                      </Grid>
                    </Grid>
                  </Paper>
                ))}
              </Box>
            </Box>
          )}

          {/* STEP 5: Student Import */}
          {activeStep === 5 && (
            <Box>
              <Typography variant="h5" fontWeight={700} mb={1}>
                Student Roster Import
              </Typography>
              <Typography variant="body2" color="text.secondary" mb={3}>
                Quickly populate student records using our standardized CSV or Excel spreadsheet template.
              </Typography>

              <Grid container spacing={3}>
                <Grid item xs={12} md={6}>
                  <Paper variant="outlined" sx={{ p: 3, textAlign: 'center', borderRadius: 2 }}>
                    <DownloadIcon sx={{ fontSize: 48, color: 'primary.main', mb: 1 }} />
                    <Typography variant="subtitle1" fontWeight={700} gutterBottom>
                      Download Import Template
                    </Typography>
                    <Typography variant="caption" color="text.secondary" display="block" mb={2}>
                      Pre-formatted CSV template including sample admission numbers, names, and contact fields.
                    </Typography>
                    <Button
                      variant="outlined"
                      startIcon={<DownloadIcon />}
                      onClick={() => institutionsApi.downloadTemplate('students')}
                    >
                      Download CSV Template
                    </Button>
                  </Paper>
                </Grid>

                <Grid item xs={12} md={6}>
                  <Paper
                    variant="outlined"
                    sx={{
                      p: 3,
                      textAlign: 'center',
                      borderRadius: 2,
                      borderStyle: 'dashed',
                      bgcolor: '#f8fafc',
                    }}
                  >
                    <UploadFileIcon sx={{ fontSize: 48, color: 'text.secondary', mb: 1 }} />
                    <Typography variant="subtitle1" fontWeight={700} gutterBottom>
                      Upload Completed CSV File
                    </Typography>
                    <Typography variant="caption" color="text.secondary" display="block" mb={2}>
                      Select your populated student roster CSV file to parse and enroll.
                    </Typography>
                    <input
                      type="file"
                      accept=".csv"
                      id="student-csv-upload"
                      style={{ display: 'none' }}
                      onChange={(e) => {
                        const file = e.target.files?.[0]
                        if (file) handleFileUpload(file)
                      }}
                    />
                    <label htmlFor="student-csv-upload">
                      <Button variant="contained" component="span" disabled={uploading}>
                        {uploading ? <CircularProgress size={20} /> : 'Select CSV File'}
                      </Button>
                    </label>
                  </Paper>
                </Grid>

                {importResult && (
                  <Grid item xs={12}>
                    <Alert severity="success">
                      Successfully imported <strong>{importResult.imported_count}</strong> students from file.
                    </Alert>
                  </Grid>
                )}
              </Grid>
            </Box>
          )}

          {/* STEP 6: Notification Configuration */}
          {activeStep === 6 && (
            <Box>
              <Typography variant="h5" fontWeight={700} mb={1}>
                Notification Preferences
              </Typography>
              <Typography variant="body2" color="text.secondary" mb={3}>
                Configure automated communications dispatched to students and parents.
              </Typography>

              <Box display="flex" flexDirection="column" gap={2} maxWidth={600}>
                <Paper variant="outlined" sx={{ p: 2, borderRadius: 2 }}>
                  <FormControlLabel
                    control={
                      <Switch
                        checked={emailNotif}
                        onChange={(e) => setEmailNotif(e.target.checked)}
                        color="primary"
                      />
                    }
                    label="Email Notifications (Transactional alerts, fee receipts, reports)"
                  />
                </Paper>
                <Paper variant="outlined" sx={{ p: 2, borderRadius: 2 }}>
                  <FormControlLabel
                    control={
                      <Switch
                        checked={smsNotif}
                        onChange={(e) => setSmsNotif(e.target.checked)}
                        color="primary"
                      />
                    }
                    label="SMS Alerts (Urgent campus notices, attendance absence alerts)"
                  />
                </Paper>
                <Paper variant="outlined" sx={{ p: 2, borderRadius: 2 }}>
                  <FormControlLabel
                    control={
                      <Switch
                        checked={whatsappNotif}
                        onChange={(e) => setWhatsappNotif(e.target.checked)}
                        color="success"
                      />
                    }
                    label="WhatsApp Messaging (Meta WhatsApp Cloud API integration)"
                  />
                </Paper>
              </Box>
            </Box>
          )}

          {/* STEP 7: Launch & Summary */}
          {activeStep === 7 && (
            <Box textAlign="center" py={2}>
              <RocketLaunchIcon color="primary" sx={{ fontSize: 64, mb: 2 }} />
              <Typography variant="h4" fontWeight={800} gutterBottom>
                Ready to Launch Your Campus Portal!
              </Typography>
              <Typography variant="body1" color="text.secondary" mb={4}>
                Your academic structure, curriculum, and faculty accounts have been initialized. Click below to complete onboarding and enter the administration dashboard.
              </Typography>

              <Box display="flex" gap={2} justifyContent="center" mb={4}>
                <Chip icon={<CheckCircleIcon />} label="Academic Session Active" color="success" />
                <Chip icon={<CheckCircleIcon />} label="Curriculum Configured" color="success" />
                <Chip icon={<CheckCircleIcon />} label="Staff Initialized" color="success" />
              </Box>
            </Box>
          )}

          {/* Wizard Controls */}
          <Box display="flex" justifyContent="space-between" mt={4} pt={2} borderTop="1px solid #e2e8f0">
            <Button disabled={activeStep === 0 || stepLoading} onClick={handleBack}>
              Back
            </Button>
            <Button
              variant="contained"
              size="large"
              onClick={handleNext}
              disabled={stepLoading}
              sx={{ px: 4 }}
            >
              {stepLoading ? (
                <CircularProgress size={24} color="inherit" />
              ) : activeStep === STEPS.length - 1 ? (
                'Launch Campus Portal'
              ) : (
                'Save & Continue'
              )}
            </Button>
          </Box>
        </CardContent>
      </Card>
    </Container>
  )
}
