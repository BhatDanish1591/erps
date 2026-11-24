import apiClient from './client'

export interface StudyMaterialVersion {
  id: string
  material_id: string
  version_number: number
  file_name?: string
  file_size_bytes?: number
  mime_type?: string
  change_summary?: string
  uploader_name?: string
  created_at: string
}

export interface StudyMaterial {
  id: string
  tenant_id: string
  academic_session_id: string
  academic_session_name?: string
  subject_id?: string
  subject_name?: string
  subject_code?: string
  class_id?: string
  class_name?: string
  section_id?: string
  section_name?: string
  department_id?: string
  course_id?: string
  semester_id?: string
  batch_id?: string
  title: string
  description?: string
  chapter?: string
  material_type: string // PDF, WORD, POWERPOINT, IMAGE, VIDEO_LINK, RECORDED_LECTURE, REFERENCE_MATERIAL, PREVIOUS_PAPER, OTHER
  category: string // LECTURE_NOTE, SYLLABUS, PAST_PAPER, READING, REFERENCE, LAB_MANUAL, GENERAL
  external_url?: string
  tags: string[]
  is_published: boolean
  file_key?: string
  file_name?: string
  file_size_bytes?: number
  mime_type?: string
  download_url?: string
  preview_url?: string
  version: number
  download_count: number
  view_count: number
  uploaded_by: string
  uploader_name?: string
  created_at: string
  updated_at: string
  versions?: StudyMaterialVersion[]
}

export interface Assignment {
  id: string
  tenant_id: string
  academic_session_id: string
  academic_session_name?: string
  subject_id?: string
  subject_name?: string
  subject_code?: string
  class_id?: string
  class_name?: string
  section_id?: string
  section_name?: string
  course_id?: string
  semester_id?: string
  title: string
  description: string
  due_datetime: string
  allow_late_submission: boolean
  late_penalty_percent: number
  total_marks: number
  passing_marks: number
  status: string // DRAFT, PUBLISHED, CLOSED, ARCHIVED
  instructions_file_key?: string
  instructions_file_name?: string
  instructions_file_size?: number
  instructions_download_url?: string
  created_by: string
  creator_name?: string
  submissions_count: number
  evaluated_count: number
  pending_count: number
  created_at: string
  updated_at: string
}

export interface AssignmentSubmission {
  id: string
  tenant_id: string
  assignment_id: string
  student_id: string
  student_name: string
  admission_number: string
  roll_number?: string
  submission_text?: string
  attachment_file_key?: string
  attachment_file_name?: string
  attachment_file_size?: number
  attachment_download_url?: string
  submitted_at: string
  is_late: boolean
  marks_obtained?: number
  grade?: string
  teacher_feedback?: string
  evaluated_by?: string
  evaluator_name?: string
  evaluated_at?: string
  status: string // SUBMITTED, EVALUATED, RESUBMISSION_REQUESTED
}

export interface AssignmentReport {
  assignment_id: string
  assignment_title: string
  total_assigned: number
  total_submitted: number
  total_evaluated: number
  total_pending: number
  submission_rate_percent: number
  average_score: number
  highest_score: number
  lowest_score: number
  pass_percentage: number
}

export interface StudyMaterialQueryParams {
  academic_session_id?: string
  subject_id?: string
  class_id?: string
  section_id?: string
  category?: string
  material_type?: string
  search?: string
  is_published?: boolean
  page?: number
  size?: number
}

export interface AssignmentQueryParams {
  academic_session_id?: string
  subject_id?: string
  class_id?: string
  section_id?: string
  status?: string
  search?: string
  page?: number
  size?: number
}

export const lmsApi = {
  // Study Materials
  listMaterials: async (params?: StudyMaterialQueryParams) => {
    const res = await apiClient.get('/materials', { params })
    return res.data
  },

  getMaterial: async (materialId: string) => {
    const res = await apiClient.get(`/materials/${materialId}`)
    return res.data
  },

  createMaterialJson: async (data: Partial<StudyMaterial>) => {
    const res = await apiClient.post('/materials', data)
    return res.data
  },

  uploadMaterialFile: async (formData: FormData) => {
    const res = await apiClient.post('/materials/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    return res.data
  },

  uploadMaterialVersion: async (materialId: string, formData: FormData) => {
    const res = await apiClient.post(`/materials/${materialId}/versions`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    return res.data
  },

  updateMaterial: async (materialId: string, data: Partial<StudyMaterial>) => {
    const res = await apiClient.put(`/materials/${materialId}`, data)
    return res.data
  },

  deleteMaterial: async (materialId: string) => {
    const res = await apiClient.delete(`/materials/${materialId}`)
    return res.data
  },

  getDownloadUrl: async (materialId: string) => {
    const res = await apiClient.get(`/materials/${materialId}/download?redirect=false`)
    return res.data
  },

  // Assignments
  listAssignments: async (params?: AssignmentQueryParams) => {
    const res = await apiClient.get('/assignments', { params })
    return res.data
  },

  getAssignment: async (assignmentId: string) => {
    const res = await apiClient.get(`/assignments/${assignmentId}`)
    return res.data
  },

  createAssignmentJson: async (data: Partial<Assignment>) => {
    const res = await apiClient.post('/assignments', data)
    return res.data
  },

  createAssignmentWithFile: async (formData: FormData) => {
    const res = await apiClient.post('/assignments/with-file', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    return res.data
  },

  updateAssignment: async (assignmentId: string, data: Partial<Assignment>) => {
    const res = await apiClient.put(`/assignments/${assignmentId}`, data)
    return res.data
  },

  submitAssignment: async (assignmentId: string, formData: FormData) => {
    const res = await apiClient.post(`/assignments/${assignmentId}/submit`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    return res.data
  },

  getMySubmission: async (assignmentId: string, studentId?: string) => {
    const res = await apiClient.get(`/assignments/${assignmentId}/my-submission`, {
      params: studentId ? { student_id: studentId } : undefined,
    })
    return res.data
  },

  listSubmissions: async (assignmentId: string, status?: string) => {
    const res = await apiClient.get(`/assignments/${assignmentId}/submissions`, {
      params: status ? { status } : undefined,
    })
    return res.data
  },

  evaluateSubmission: async (
    submissionId: string,
    data: { marks_obtained: number; grade?: string; teacher_feedback?: string; status?: string }
  ) => {
    const res = await apiClient.post(`/assignments/submissions/${submissionId}/evaluate`, data)
    return res.data
  },

  getAssignmentReport: async (assignmentId: string) => {
    const res = await apiClient.get(`/assignments/${assignmentId}/report`)
    return res.data
  },
}
