import React, { useEffect, useState } from 'react'
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  TextField,
  MenuItem,
  Grid,
  Tabs,
  Tab,
  Box,
  Typography,
  Alert,
  CircularProgress,
  Avatar,
} from '@mui/material'
import AddAPhotoOutlined from '@mui/icons-material/AddAPhotoOutlined'
import { StudentCreatePayload, StudentItem, studentPhotoSrc, studentsApi } from '../../api/students'
import { Department, Course, SchoolClass, Section, academicsApi } from '../../api/academics'

import { useAuthStore } from '@/store/authStore'

interface AddEditStudentModalProps {
  open: boolean
  onClose: () => void
  onSuccess: () => void
  student?: StudentItem | null
}

export const AddEditStudentModal: React.FC<AddEditStudentModalProps> = ({
  open,
  onClose,
  onSuccess,
  student,
}) => {
  const [tabIndex, setTabIndex] = useState(0)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [photo, setPhoto] = useState<File | null>(null)
  const [photoPreview, setPhotoPreview] = useState<string | null>(null)
  const [uploadedPhoto, setUploadedPhoto] = useState<string | null>(null)
  const [departments, setDepartments] = useState<Department[]>([])
  const [courses, setCourses] = useState<Course[]>([])

  const [classes, setClasses] = useState<SchoolClass[]>([])
  const [sections, setSections] = useState<Section[]>([])
  const user = useAuthStore((state) => state.user)
  const tenantId = user?.current_tenant_id
  const isSchool = user?.institutions.some((institution) =>
    institution.tenant_id === tenantId && institution.institution_type === 'SCHOOL'
  )

  useEffect(() => {
    if (!open) return
    let active = true
    if (isSchool) {
      Promise.all([academicsApi.getClasses(), academicsApi.getSections()])
        .then(([classRes, sectionRes]) => {
          if (!active) return
          setClasses(classRes.data ?? [])
          setSections(sectionRes.data ?? [])
        })
        .catch(() => { if (active) setError('Unable to load classes and sections.') })
    } else {
      Promise.all([academicsApi.getDepartments(), academicsApi.getCourses()])
        .then(([departmentRes, courseRes]) => {
          if (!active) return
          setDepartments(departmentRes.data ?? [])
          setCourses(courseRes.data ?? [])
        })
        .catch(() => { if (active) setError('Unable to load departments and courses.') })
    }
    return () => { active = false }
  }, [open, isSchool, tenantId])

  const [formData, setFormData] = useState<StudentCreatePayload>({
    full_name: '',
    email: '',
    phone: '',
    admission_number: '',
    roll_number: '',
    admission_date: new Date().toISOString().split('T')[0],
    gender: 'MALE',
    date_of_birth: '',
    blood_group: '',

    // Academic
    semester: 1,
    batch_year: new Date().getFullYear(),

    // Address
    address_line1: '',
    address_line2: '',
    city: '',
    state: '',
    postal_code: '',
    country: 'India',

    // Parent details
    father_name: '',
    father_phone: '',
    father_occupation: '',
    mother_name: '',
    mother_phone: '',
    mother_occupation: '',
    guardian_name: '',
    guardian_phone: '',
    guardian_relation: 'GUARDIAN',
    emergency_contact_name: '',
    emergency_contact_phone: '',

    // Previous history
    previous_school_name: '',
    previous_grade: '',
    transfer_certificate_number: '',
  })

  useEffect(() => {
    setPhoto(null)
    setPhotoPreview(null)
    setUploadedPhoto(null)
    if (student) {
      setFormData({
        full_name: student.full_name || '',
        email: student.email || '',
        phone: student.phone || '',
        admission_number: student.admission_number || '',
        roll_number: student.roll_number || '',
        admission_date: student.admission_date || '',
        gender: student.gender || 'MALE',
        date_of_birth: student.date_of_birth || '',
        blood_group: student.blood_group || '',

        class_id: student.class_id || undefined,
        section_id: student.section_id || undefined,
        department_id: student.department_id || undefined,
        course_id: student.course_id || undefined,
        semester: student.semester || 1,
        batch_year: student.batch_year || new Date().getFullYear(),

        address_line1: student.address_line1 || '',
        address_line2: student.address_line2 || '',
        city: student.city || '',
        state: student.state || '',
        postal_code: student.postal_code || '',
        country: student.country || 'India',

        father_name: student.father_name || '',
        father_phone: student.father_phone || '',
        father_occupation: student.father_occupation || '',
        mother_name: student.mother_name || '',
        mother_phone: student.mother_phone || '',
        mother_occupation: student.mother_occupation || '',
        guardian_name: student.guardian_name || '',
        guardian_phone: student.guardian_phone || '',
        guardian_relation: student.guardian_relation || 'GUARDIAN',
        emergency_contact_name: student.emergency_contact_name || '',
        emergency_contact_phone: student.emergency_contact_phone || '',

        previous_school_name: student.previous_school_name || '',
        previous_grade: student.previous_grade || '',
        transfer_certificate_number: student.transfer_certificate_number || '',
      })
    } else {
      setFormData({
        full_name: '',
        email: '',
        phone: '',
        admission_number: '',
        roll_number: '',
        admission_date: new Date().toISOString().split('T')[0],
        gender: 'MALE',
        date_of_birth: '',
        blood_group: '',
        semester: 1,
        batch_year: new Date().getFullYear(),
        address_line1: '',
        address_line2: '',
        city: '',
        state: '',
        postal_code: '',
        country: 'India',
        father_name: '',
        father_phone: '',
        father_occupation: '',
        mother_name: '',
        mother_phone: '',
        mother_occupation: '',
        guardian_name: '',
        guardian_phone: '',
        guardian_relation: 'GUARDIAN',
        emergency_contact_name: '',
        emergency_contact_phone: '',
        previous_school_name: '',
        previous_grade: '',
        transfer_certificate_number: '',
      })
    }
    setTabIndex(0)
    setError(null)
  }, [student, open])

  useEffect(() => {
    if (!photo) return
    const url = URL.createObjectURL(photo)
    setPhotoPreview(url)
    return () => URL.revokeObjectURL(url)
  }, [photo])

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target
    setFormData((prev) => ({ ...prev, [name]: value }))
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!formData.full_name.trim()) {
      setError('Student full name is required.')
      setTabIndex(0)
      return
    }

    try {
      setSubmitting(true)
      setError(null)

      let photoKey = uploadedPhoto
      if (photo && !photoKey) {
        photoKey = await studentsApi.uploadPhoto(photo)
        setUploadedPhoto(photoKey)
      }
      const details = photoKey ? { ...formData, photo_url: photoKey } : formData
      const validDetails = {
        ...details,
        email: details.email || undefined,
        date_of_birth: details.date_of_birth || undefined,
        admission_date: details.admission_date || undefined,
      }
      const payload = isSchool
        ? { ...validDetails, department_id: undefined, course_id: undefined, semester: undefined, batch_year: undefined }
        : { ...validDetails, class_id: undefined }
      if (student) {
        await studentsApi.updateStudent(student.id, payload)
      } else {
        await studentsApi.createStudent(payload)
      }

      onSuccess()
      onClose()
    } catch (err: any) {
      setError(err?.message || 'Failed to save student details.')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <Dialog open={open} onClose={onClose} maxWidth="md" fullWidth>
      <form onSubmit={handleSubmit}>
        <DialogTitle sx={{ fontWeight: 700, pb: 1 }}>
          {student ? `Edit Student: ${student.full_name}` : 'New Student Admission'}
          <Typography variant="body2" color="text.secondary">
            {student
              ? `Admission No: ${student.admission_number}`
              : 'Fill in student biodata, academic placement, parent details, and previous history.'}
          </Typography>
        </DialogTitle>

        <Box sx={{ borderBottom: 1, borderColor: 'divider', px: 3 }}>
          <Tabs value={tabIndex} onChange={(_, val) => setTabIndex(val)} variant="scrollable" scrollButtons="auto">
            <Tab label="1. Basic Info" />
            <Tab label="2. Academic Placement" />
            <Tab label="3. Address & Location" />
            <Tab label="4. Parents & Guardians" />
            <Tab label="5. Previous School" />
          </Tabs>
        </Box>

        <DialogContent sx={{ minHeight: 380, pt: 2.5 }}>
          {error && (
            <Alert severity="error" sx={{ mb: 2.5 }} onClose={() => setError(null)}>
              {error}
            </Alert>
          )}

          {/* TAB 0: Basic Info */}
          {tabIndex === 0 && (
            <Grid container spacing={2}>
              <Grid item xs={12}>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                  <Avatar src={photoPreview || studentPhotoSrc(student?.photo_url)} sx={{ width: 72, height: 72 }} />
                  <Box>
                    <Button component="label" variant="outlined" startIcon={<AddAPhotoOutlined />}>
                      {photo ? 'Change photo' : 'Upload student photo'}
                      <input type="file" accept="image/jpeg,image/png" hidden onChange={(event) => {
                        const selected = event.target.files?.[0]
                        event.target.value = ''
                        if (!selected) return
                        if (!['image/jpeg', 'image/png'].includes(selected.type) || selected.size > 5 * 1024 * 1024) {
                          setError('Select a JPEG or PNG image up to 5 MB.')
                          return
                        }
                        setError(null)
                        setPhoto(selected)
                        setUploadedPhoto(null)
                      }} />
                    </Button>
                    <Typography variant="caption" display="block" color="text.secondary">JPEG or PNG, up to 5 MB</Typography>
                  </Box>
                </Box>
              </Grid>
              <Grid item xs={12} sm={8}>
                <TextField
                  label="Full Name *"
                  name="full_name"
                  value={formData.full_name}
                  onChange={handleChange}
                  fullWidth
                  required
                />
              </Grid>
              <Grid item xs={12} sm={4}>
                <TextField
                  label="Gender"
                  name="gender"
                  value={formData.gender}
                  onChange={handleChange}
                  select
                  fullWidth
                >
                  <MenuItem value="MALE">Male</MenuItem>
                  <MenuItem value="FEMALE">Female</MenuItem>
                  <MenuItem value="OTHER">Other</MenuItem>
                </TextField>
              </Grid>
              <Grid item xs={12} sm={6}>
                <TextField
                  label="Email Address"
                  name="email"
                  type="email"
                  value={formData.email || ''}
                  onChange={handleChange}
                  helperText="Leave blank to auto-generate institution internal email"
                  fullWidth
                />
              </Grid>
              <Grid item xs={12} sm={6}>
                <TextField
                  label="Contact Phone"
                  name="phone"
                  value={formData.phone || ''}
                  onChange={handleChange}
                  fullWidth
                />
              </Grid>
              <Grid item xs={12} sm={4}>
                <TextField
                  label="Admission Number"
                  name="admission_number"
                  value={formData.admission_number || ''}
                  onChange={handleChange}
                  helperText={student ? 'Cannot be changed' : 'Leave blank for sequential auto-generation'}
                  disabled={Boolean(student)}
                  fullWidth
                />
              </Grid>
              <Grid item xs={12} sm={4}>
                <TextField
                  label="Roll Number"
                  name="roll_number"
                  value={formData.roll_number || ''}
                  onChange={handleChange}
                  fullWidth
                />
              </Grid>
              <Grid item xs={12} sm={4}>
                <TextField
                  label="Date of Birth"
                  name="date_of_birth"
                  type="date"
                  value={formData.date_of_birth || ''}
                  onChange={handleChange}
                  InputLabelProps={{ shrink: true }}
                  fullWidth
                />
              </Grid>
              <Grid item xs={12} sm={6}>
                <TextField
                  label="Admission Date"
                  name="admission_date"
                  type="date"
                  value={formData.admission_date || ''}
                  onChange={handleChange}
                  InputLabelProps={{ shrink: true }}
                  fullWidth
                />
              </Grid>
              <Grid item xs={12} sm={6}>
                <TextField
                  label="Blood Group"
                  name="blood_group"
                  value={formData.blood_group || ''}
                  onChange={handleChange}
                  select
                  fullWidth
                >
                  <MenuItem value="">Not Specified</MenuItem>
                  <MenuItem value="A+">A+</MenuItem>
                  <MenuItem value="A-">A-</MenuItem>
                  <MenuItem value="B+">B+</MenuItem>
                  <MenuItem value="B-">B-</MenuItem>
                  <MenuItem value="O+">O+</MenuItem>
                  <MenuItem value="O-">O-</MenuItem>
                  <MenuItem value="AB+">AB+</MenuItem>
                  <MenuItem value="AB-">AB-</MenuItem>
                </TextField>
              </Grid>
            </Grid>
          )}

          {/* TAB 1: Academic Placement */}
          {tabIndex === 1 && (isSchool ? (
            <Grid container spacing={2}>
              <Grid item xs={12} sm={6}>
                <TextField label="Class" select fullWidth value={formData.class_id ?? ''} onChange={(event) => {
                  setFormData((previous) => ({ ...previous, class_id: event.target.value || undefined, section_id: undefined }))
                }}>
                  <MenuItem value="">Select class</MenuItem>
                  {classes.map((item) => <MenuItem key={item.id} value={item.id}>{item.name}</MenuItem>)}
                </TextField>
              </Grid>
              <Grid item xs={12} sm={6}>
                <TextField label="Section" select fullWidth value={formData.section_id ?? ''} disabled={!formData.class_id}
                  onChange={(event) => setFormData((previous) => ({ ...previous, section_id: event.target.value || undefined }))}>
                  <MenuItem value="">Select section</MenuItem>
                  {sections.filter((item) => item.class_id === formData.class_id).map((item) => (
                    <MenuItem key={item.id} value={item.id}>{item.name}</MenuItem>
                  ))}
                </TextField>
              </Grid>
            </Grid>
          ) : (
            <Grid container spacing={2}>
              <Grid item xs={12}>
                <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
                  Configure college department, program, course, and semester placement.
                </Typography>
              </Grid>

              <Grid item xs={12} sm={6}>
                <TextField
                  label="Department"
                  name="department_id"
                  select
                  value={formData.department_id || ''}
                  onChange={(e) => {
                    const deptId = e.target.value
                    setFormData((prev) => ({
                      ...prev,
                      department_id: deptId || undefined,
                      course_id: undefined,
                    }))
                  }}
                  fullWidth
                >
                  <MenuItem value="">None / General</MenuItem>
                  {departments.map((d) => (
                    <MenuItem key={d.id} value={d.id}>
                      {d.name} {d.code ? `(${d.code})` : ''}
                    </MenuItem>
                  ))}
                </TextField>
              </Grid>

              <Grid item xs={12} sm={6}>
                <TextField
                  label="Course / Program"
                  name="course_id"
                  select
                  value={formData.course_id || ''}
                  onChange={(e) => {
                    setFormData((prev) => ({
                      ...prev,
                      course_id: e.target.value || undefined,
                    }))
                  }}
                  fullWidth
                >
                  <MenuItem value="">None / General</MenuItem>
                  {(formData.department_id
                    ? courses.filter((c) => c.department_id === formData.department_id)
                    : courses
                  ).map((c) => (
                    <MenuItem key={c.id} value={c.id}>
                      {c.name} {c.code ? `(${c.code})` : ''}
                    </MenuItem>
                  ))}
                </TextField>
              </Grid>

              <Grid item xs={12} sm={6}>
                <TextField
                  label="Semester"
                  name="semester"
                  select
                  value={formData.semester || 1}
                  onChange={handleChange}
                  helperText="Current semester term"
                  fullWidth
                >
                  {[1, 2, 3, 4, 5, 6, 7, 8].map((sem) => (
                    <MenuItem key={sem} value={sem}>
                      Semester {sem}
                    </MenuItem>
                  ))}
                </TextField>
              </Grid>

              <Grid item xs={12} sm={6}>
                <TextField
                  label="Batch Year"
                  name="batch_year"
                  type="number"
                  value={formData.batch_year || new Date().getFullYear()}
                  onChange={handleChange}
                  InputProps={{ inputProps: { min: 1990, max: 2100 } }}
                  fullWidth
                />
              </Grid>
            </Grid>
          ))}

          {/* TAB 2: Address & Location */}
          {tabIndex === 2 && (
            <Grid container spacing={2}>
              <Grid item xs={12}>
                <TextField
                  label="Address Line 1"
                  name="address_line1"
                  value={formData.address_line1 || ''}
                  onChange={handleChange}
                  fullWidth
                />
              </Grid>
              <Grid item xs={12}>
                <TextField
                  label="Address Line 2"
                  name="address_line2"
                  value={formData.address_line2 || ''}
                  onChange={handleChange}
                  fullWidth
                />
              </Grid>
              <Grid item xs={12} sm={4}>
                <TextField
                  label="City"
                  name="city"
                  value={formData.city || ''}
                  onChange={handleChange}
                  fullWidth
                />
              </Grid>
              <Grid item xs={12} sm={4}>
                <TextField
                  label="State / Province"
                  name="state"
                  value={formData.state || ''}
                  onChange={handleChange}
                  fullWidth
                />
              </Grid>
              <Grid item xs={12} sm={4}>
                <TextField
                  label="Postal / ZIP Code"
                  name="postal_code"
                  value={formData.postal_code || ''}
                  onChange={handleChange}
                  fullWidth
                />
              </Grid>
              <Grid item xs={12} sm={6}>
                <TextField
                  label="Country"
                  name="country"
                  value={formData.country || 'India'}
                  onChange={handleChange}
                  fullWidth
                />
              </Grid>
            </Grid>
          )}

          {/* TAB 3: Parents & Guardians */}
          {tabIndex === 3 && (
            <Grid container spacing={2}>
              <Grid item xs={12} sm={6}>
                <TextField
                  label="Father Name"
                  name="father_name"
                  value={formData.father_name || ''}
                  onChange={handleChange}
                  fullWidth
                />
              </Grid>
              <Grid item xs={12} sm={6}>
                <TextField
                  label="Father Contact Phone"
                  name="father_phone"
                  value={formData.father_phone || ''}
                  onChange={handleChange}
                  fullWidth
                />
              </Grid>
              <Grid item xs={12} sm={6}>
                <TextField
                  label="Mother Name"
                  name="mother_name"
                  value={formData.mother_name || ''}
                  onChange={handleChange}
                  fullWidth
                />
              </Grid>
              <Grid item xs={12} sm={6}>
                <TextField
                  label="Mother Contact Phone"
                  name="mother_phone"
                  value={formData.mother_phone || ''}
                  onChange={handleChange}
                  fullWidth
                />
              </Grid>
              <Grid item xs={12} sm={6}>
                <TextField
                  label="Guardian Name"
                  name="guardian_name"
                  value={formData.guardian_name || ''}
                  onChange={handleChange}
                  fullWidth
                />
              </Grid>
              <Grid item xs={12} sm={6}>
                <TextField
                  label="Guardian Phone"
                  name="guardian_phone"
                  value={formData.guardian_phone || ''}
                  onChange={handleChange}
                  fullWidth
                />
              </Grid>
              <Grid item xs={12} sm={6}>
                <TextField
                  label="Emergency Contact Name"
                  name="emergency_contact_name"
                  value={formData.emergency_contact_name || ''}
                  onChange={handleChange}
                  fullWidth
                />
              </Grid>
              <Grid item xs={12} sm={6}>
                <TextField
                  label="Emergency Contact Phone"
                  name="emergency_contact_phone"
                  value={formData.emergency_contact_phone || ''}
                  onChange={handleChange}
                  fullWidth
                />
              </Grid>
            </Grid>
          )}

          {/* TAB 4: Previous School */}
          {tabIndex === 4 && (
            <Grid container spacing={2}>
              <Grid item xs={12}>
                <TextField
                  label="Previous School / College Name"
                  name="previous_school_name"
                  value={formData.previous_school_name || ''}
                  onChange={handleChange}
                  fullWidth
                />
              </Grid>
              <Grid item xs={12} sm={6}>
                <TextField
                  label="Previous Grade / Percentage / CGPA"
                  name="previous_grade"
                  value={formData.previous_grade || ''}
                  onChange={handleChange}
                  fullWidth
                />
              </Grid>
              <Grid item xs={12} sm={6}>
                <TextField
                  label="Transfer Certificate (TC) Number"
                  name="transfer_certificate_number"
                  value={formData.transfer_certificate_number || ''}
                  onChange={handleChange}
                  fullWidth
                />
              </Grid>
            </Grid>
          )}
        </DialogContent>

        <DialogActions sx={{ px: 3, pb: 2.5, pt: 1.5, justifyContent: 'space-between' }}>
          <Box>
            {tabIndex > 0 && (
              <Button onClick={() => setTabIndex((prev) => prev - 1)} disabled={submitting}>
                Back
              </Button>
            )}
            {tabIndex < 4 && (
              <Button onClick={() => setTabIndex((prev) => prev + 1)} sx={{ ml: 1 }}>
                Next
              </Button>
            )}
          </Box>
          <Box>
            <Button onClick={onClose} disabled={submitting} sx={{ mr: 1 }}>
              Cancel
            </Button>
            <Button
              type="submit"
              variant="contained"
              disabled={submitting}
              startIcon={submitting ? <CircularProgress size={16} color="inherit" /> : null}
            >
              {submitting ? 'Saving...' : student ? 'Update Student' : 'Admit Student'}
            </Button>
          </Box>
        </DialogActions>
      </form>
    </Dialog>
  )
}
