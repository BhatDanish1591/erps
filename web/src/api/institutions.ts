import client from './client'

export interface InstitutionRegistrationPayload {
  name: string
  slug: string
  institution_type: 'SCHOOL' | 'COLLEGE'
  email: string
  phone?: string
  address?: string
  city?: string
  state?: string
  country?: string
  postal_code?: string
  logo_url?: string
  principal_name: string
  principal_email: string
  principal_phone?: string
  plan_id?: string
}

export interface OnboardingStatus {
  tenant_id: string
  institution_name: string
  institution_type: 'SCHOOL' | 'COLLEGE'
  is_completed: boolean
  current_step: number
  steps_status: Record<string, boolean>
}

export const institutionsApi = {
  checkSubdomain: async (slug: string) => {
    const res = await client.get<{ success: boolean; data: { slug: string; available: boolean; suggestion?: string } }>(
      '/institutions/check-subdomain',
      { params: { slug } }
    )
    return res.data.data
  },

  register: async (payload: InstitutionRegistrationPayload) => {
    const res = await client.post<{ success: boolean; data: { tenant_id: string; slug: string; invitation_token: string; message: string } }>(
      '/institutions/register',
      payload
    )
    return res.data.data
  },

  verifyInvitation: async (token: string) => {
    const res = await client.get<{
      success: boolean
      data: {
        valid: boolean
        email: string
        institution_name: string
        institution_slug: string
        role_name: string
        first_name?: string
      }
    }>('/institutions/invitations/verify', { params: { token } })
    return res.data.data
  },

  acceptInvitation: async (payload: { token: string; password: string; full_name?: string; phone?: string }) => {
    const res = await client.post<{ success: boolean; data: { user_id: string; message: string } }>(
      '/institutions/invitations/accept',
      payload
    )
    return res.data.data
  },

  getProfile: async () => {
    const res = await client.get<{ success: boolean; data: Record<string, unknown> }>('/institutions/profile')
    return res.data.data
  },

  updateProfile: async (payload: Record<string, unknown>) => {
    const res = await client.put<{ success: boolean; message: string }>('/institutions/profile', payload)
    return res.data
  },

  getOnboardingStatus: async (): Promise<OnboardingStatus> => {
    const res = await client.get<{ success: boolean; data: OnboardingStatus }>('/institutions/onboarding/status')
    return res.data.data
  },

  setupAcademicSession: async (payload: { name: string; code: string; start_date: string; end_date: string }) => {
    const res = await client.post<{ success: boolean; message: string }>('/institutions/onboarding/academic-session', payload)
    return res.data
  },

  setupStructure: async (payload: { items: Array<{ name: string; code: string; sub_items: string[] }> }) => {
    const res = await client.post<{ success: boolean; message: string }>('/institutions/onboarding/structure', payload)
    return res.data
  },

  setupSubjects: async (payload: { subjects: Array<{ name: string; code: string; subject_type: string; credits?: number }> }) => {
    const res = await client.post<{ success: boolean; message: string }>('/institutions/onboarding/subjects', payload)
    return res.data
  },

  inviteTeachers: async (payload: { teachers: Array<{ email: string; full_name: string; designation?: string; phone?: string }> }) => {
    const res = await client.post<{ success: boolean; message: string }>('/institutions/onboarding/teachers', payload)
    return res.data
  },

  setupNotifications: async (payload: { email_notifications: boolean; sms_notifications: boolean; whatsapp_notifications: boolean }) => {
    const res = await client.post<{ success: boolean; message: string }>('/institutions/onboarding/notifications', payload)
    return res.data
  },

  completeOnboarding: async () => {
    const res = await client.post<{ success: boolean; message: string }>('/institutions/onboarding/complete')
    return res.data
  },

  downloadTemplate: async (type: 'students' | 'teachers') => {
    const res = await client.get(`/institutions/templates/${type}`, { responseType: 'blob' })
    const url = window.URL.createObjectURL(new Blob([res.data]))
    const link = document.createElement('a')
    link.href = url
    link.setAttribute('download', `${type}_template.csv`)
    document.body.appendChild(link)
    link.click()
    link.remove()
  },

  importStudents: async (file: File) => {
    const formData = new FormData()
    formData.append('file', file)
    const res = await client.post<{
      success: boolean
      data: { total_rows: number; imported_count: number; skipped_count: number; errors: string[] }
    }>('/institutions/import/students', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    return res.data.data
  },
}
