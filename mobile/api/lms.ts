import { apiClient } from './client'

export interface MobileStudyMaterial {
  id: string
  title: string
  description?: string
  chapter?: string
  material_type: string
  category: string
  external_url?: string
  download_url?: string
  preview_url?: string
  file_name?: string
  file_size_bytes?: number
  version: number
  download_count: number
  view_count: number
  subject_name?: string
  subject_code?: string
  academic_session_name?: string
  created_at: string
}

export interface MobileAssignment {
  id: string
  title: string
  description: string
  due_datetime: string
  allow_late_submission: boolean
  late_penalty_percent: number
  total_marks: number
  passing_marks: number
  status: string
  instructions_file_name?: string
  instructions_download_url?: string
  subject_name?: string
  subject_code?: string
  submissions_count: number
  evaluated_count: number
}

export interface MobileAssignmentSubmission {
  id: string
  assignment_id: string
  student_id: string
  submission_text?: string
  attachment_file_name?: string
  attachment_download_url?: string
  submitted_at: string
  is_late: boolean
  marks_obtained?: number
  grade?: string
  teacher_feedback?: string
  status: string
}

export const mobileLmsApi = {
  listMaterials: async (params?: { category?: string; subject_id?: string; search?: string }): Promise<MobileStudyMaterial[]> => {
    const res = await apiClient.get('/materials', { params })
    return res.data.data
  },

  getMaterialDetails: async (materialId: string): Promise<MobileStudyMaterial> => {
    const res = await apiClient.get(`/materials/${materialId}`)
    return res.data.data
  },

  listAssignments: async (params?: { status?: string }): Promise<MobileAssignment[]> => {
    const res = await apiClient.get('/assignments', { params })
    return res.data.data
  },

  getAssignmentDetails: async (assignmentId: string): Promise<MobileAssignment> => {
    const res = await apiClient.get(`/assignments/${assignmentId}`)
    return res.data.data
  },

  getMySubmission: async (assignmentId: string): Promise<MobileAssignmentSubmission | null> => {
    const res = await apiClient.get(`/assignments/${assignmentId}/my-submission`)
    return res.data.data
  },
}
