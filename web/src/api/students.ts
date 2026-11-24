import client from './client'

export function studentPhotoSrc(url?: string | null): string | undefined {
  if (!url) return undefined
  if (url.startsWith('/api/v1/')) {
    const base = client.defaults.baseURL || '/api/v1'
    return `${base.replace(/\/api\/v1\/?$/, '')}${url}`
  }
  return url
}

export async function openPrintableStudentCard(id: string): Promise<void> {
  const preview = window.open('', '_blank')
  if (!preview) throw new Error('Allow pop-ups to open the ID card.')
  preview.opener = null
  try {
    const result = await client.get<Blob>(`/students/${id}/id-card/html`, { responseType: 'blob' })
    const html = await result.data.text()
    const apiOrigin = new URL(client.defaults.baseURL || '/api/v1', window.location.href).origin
    const document = html.replace('<head>', `<head><base href="${apiOrigin}/">`)
    const url = URL.createObjectURL(new Blob([document], { type: 'text/html' }))
    preview.location.replace(url)
    window.setTimeout(() => URL.revokeObjectURL(url), 60_000)
  } catch {
    preview.close()
    throw new Error('Unable to open the ID card.')
  }
}

export interface StudentItem {
  id: string
  tenant_id: string
  user_id: string
  full_name: string
  email?: string | null
  phone?: string | null
  admission_number: string
  roll_number?: string | null
  admission_date?: string | null
  status: 'ACTIVE' | 'INACTIVE' | 'GRADUATED' | 'TRANSFERRED' | 'SUSPENDED'
  gender?: string | null
  date_of_birth?: string | null
  blood_group?: string | null

  // Academic Structure
  academic_session_id?: string | null
  academic_session_name?: string | null
  class_id?: string | null
  class_name?: string | null
  section_id?: string | null
  section_name?: string | null
  department_id?: string | null
  department_name?: string | null
  course_id?: string | null
  course_name?: string | null
  semester?: number | null
  batch_year?: number | null

  // Address
  address_line1?: string | null
  address_line2?: string | null
  city?: string | null
  state?: string | null
  postal_code?: string | null
  country?: string

  // Parents
  parent_name?: string | null
  parent_phone?: string | null
  parent_email?: string | null
  father_name?: string | null
  father_phone?: string | null
  father_occupation?: string | null
  mother_name?: string | null
  mother_phone?: string | null
  mother_occupation?: string | null
  guardian_name?: string | null
  guardian_phone?: string | null
  guardian_relation?: string | null
  emergency_contact_name?: string | null
  emergency_contact_phone?: string | null

  // Previous Academic History
  previous_school_name?: string | null
  previous_grade?: string | null
  transfer_certificate_number?: string | null

  photo_url?: string | null
  custom_fields?: Record<string, any>
  created_at: string
  updated_at: string
}

export interface StudentListParams {
  search?: string
  class_id?: string
  section_id?: string
  department_id?: string
  course_id?: string
  semester?: number
  status?: string
  page?: number
  size?: number
}

export interface StudentListResponse {
  items: StudentItem[]
  total: number
  page: number
  size: number
  pages: number
}

export interface StudentCreatePayload {
  full_name: string
  email?: string
  phone?: string
  admission_number?: string
  roll_number?: string
  admission_date?: string
  academic_session_id?: string
  class_id?: string
  section_id?: string
  department_id?: string
  course_id?: string
  semester?: number
  batch_year?: number
  gender?: string
  date_of_birth?: string
  blood_group?: string

  address_line1?: string
  address_line2?: string
  city?: string
  state?: string
  postal_code?: string
  country?: string

  parent_name?: string
  parent_phone?: string
  parent_email?: string
  father_name?: string
  father_phone?: string
  father_occupation?: string
  mother_name?: string
  mother_phone?: string
  mother_occupation?: string
  guardian_name?: string
  guardian_phone?: string
  guardian_relation?: string
  emergency_contact_name?: string
  emergency_contact_phone?: string

  previous_school_name?: string
  previous_grade?: string
  transfer_certificate_number?: string
  photo_url?: string
}

export interface StudentPromotionPayload {
  target_academic_session_id: string
  target_class_id?: string
  target_section_id?: string
  target_course_id?: string
  target_semester?: number
  student_ids: string[]
  action: 'PROMOTE' | 'GRADUATE' | 'TRANSFER' | 'REPEAT'
  remarks?: string
}

export interface StudentIDCard {
  student_id: string
  full_name: string
  admission_number: string
  roll_number?: string
  photo_url?: string
  institution_name: string
  institution_logo_url?: string
  institution_address?: string
  class_or_course: string
  section_or_semester: string
  academic_session?: string
  blood_group?: string
  emergency_contact?: string
  barcode_data: string
  valid_until?: string
}

export interface StudentDocumentItem {
  id: string
  student_id: string
  document_type: string
  document_name: string
  file_url: string
  file_size_bytes?: number
  mime_type?: string
  created_at: string
}

export interface BulkImportResult {
  total_processed: number
  successful: number
  failed: number
  errors: Array<{ row: number; name?: string; error: string }>
}

export const studentsApi = {
  listStudents: async (params?: StudentListParams): Promise<StudentListResponse> => {
    const res = await client.get('/students', { params })
    return res.data.data
  },

  getStudent: async (id: string): Promise<StudentItem> => {
    const res = await client.get(`/students/${id}`)
    return res.data.data
  },

  createStudent: async (payload: StudentCreatePayload): Promise<StudentItem> => {
    const res = await client.post('/students', payload)
    return res.data.data
  },

  uploadPhoto: async (file: File): Promise<string> => {
    const body = new FormData()
    body.append('file', file)
    const response = await client.post('/students/photo', body, { headers: { 'Content-Type': 'multipart/form-data' } })
    return response.data.data.photo_key
  },

  updateStudent: async (id: string, payload: Partial<StudentCreatePayload>): Promise<StudentItem> => {
    const res = await client.put(`/students/${id}`, payload)
    return res.data.data
  },

  deactivateStudent: async (id: string): Promise<void> => {
    await client.delete(`/students/${id}`)
  },

  promoteStudents: async (payload: StudentPromotionPayload): Promise<any> => {
    const res = await client.post('/students/promote', payload)
    return res.data.data
  },

  getStudentIdCard: async (id: string): Promise<StudentIDCard> => {
    const res = await client.get(`/students/${id}/id-card`)
    return res.data.data
  },

  uploadDocument: async (
    id: string,
    payload: { document_type: string; document_name: string; file_url: string; file_size_bytes?: number; mime_type?: string }
  ): Promise<StudentDocumentItem> => {
    const res = await client.post(`/students/${id}/documents`, payload)
    return res.data.data
  },

  bulkImport: async (file: File): Promise<BulkImportResult> => {
    const formData = new FormData()
    formData.append('file', file)
    const res = await client.post('/students/import', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    })
    return res.data.data
  },

  exportCsv: async (params?: {
    search?: string
    department_id?: string
    course_id?: string
    semester?: number
    class_id?: string
    section_id?: string
    status?: string
  }): Promise<Blob> => {
    const result = await client.get<Blob>('/students/export', { params, responseType: 'blob' })
    return result.data
  },
}
