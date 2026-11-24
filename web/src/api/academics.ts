import apiClient from './client'

export interface AcademicSession {
  id: string
  tenant_id: string
  name: string
  code: string
  start_date: string
  end_date: string
  is_current: boolean
  status: string
  description?: string
  created_at: string
}

export interface AcademicFaculty {
  id: string
  tenant_id: string
  name: string
  code: string
  dean_teacher_id?: string
  dean_name?: string
  description?: string
  department_count: number
  created_at: string
}

export interface AcademicDegree {
  id: string
  tenant_id: string
  name: string
  code: string
  level: string
  description?: string
  created_at: string
}

export interface Department {
  id: string
  tenant_id: string
  name: string
  code: string
  faculty_id?: string
  faculty_name?: string
  hod_teacher_id?: string
  hod_name?: string
  courses_count: number
  created_at: string
}

export interface SchoolClass {
  id: string
  tenant_id: string
  name: string
  code: string
  order_index: number
  category: string
  class_teacher_id?: string
  class_teacher_name?: string
  sections_count: number
  created_at: string
}

export interface Section {
  id: string
  tenant_id: string
  name: string
  capacity: number
  class_id?: string
  class_name?: string
  course_id?: string
  course_name?: string
  semester_id?: string
  batch_id?: string
  room_number?: string
  class_teacher_id?: string
  class_teacher_name?: string
  created_at: string
}

export interface Course {
  id: string
  tenant_id: string
  name: string
  code: string
  department_id?: string
  department_name?: string
  degree_id?: string
  degree_name?: string
  duration_years: number
  duration_semesters: number
  coordinator_teacher_id?: string
  coordinator_name?: string
  created_at: string
}

export interface CollegeSemester {
  id: string
  tenant_id: string
  course_id: string
  course_name?: string
  semester_number: number
  name: string
  credits_required: number
  status: string
  created_at: string
}

export interface CollegeBatch {
  id: string
  tenant_id: string
  course_id: string
  course_name?: string
  name: string
  start_year: number
  end_year: number
  current_semester_number: number
  is_active: boolean
  created_at: string
}

export interface Subject {
  id: string
  tenant_id: string
  name: string
  code: string
  subject_type: string
  credits?: number
  department_id?: string
  department_name?: string
  hours_per_week: number
  is_elective: boolean
  description?: string
  created_at: string
}

export interface AcademicSubjectMapping {
  id: string
  tenant_id: string
  academic_session_id: string
  subject_id: string
  subject_name?: string
  subject_code?: string
  class_id?: string
  class_name?: string
  course_id?: string
  course_name?: string
  semester_id?: string
  semester_number?: number
  is_elective: boolean
  credits: number
  weekly_hours: number
  created_at: string
}

export interface TeacherSubjectMapping {
  id: string
  tenant_id: string
  teacher_id: string
  teacher_name?: string
  teacher_emp_id?: string
  subject_id: string
  subject_name?: string
  academic_session_id?: string
  class_id?: string
  class_name?: string
  section_id?: string
  section_name?: string
  course_id?: string
  course_name?: string
  semester_id?: string
  is_primary: boolean
  created_at: string
}

export interface StudentEnrollment {
  id: string
  tenant_id: string
  student_id: string
  student_name?: string
  admission_number?: string
  academic_session_id: string
  session_name?: string
  enrollment_type: 'SCHOOL' | 'COLLEGE'
  enrollment_number: string
  enrollment_date: string
  status: string
  roll_number?: string
  school_detail?: {
    id: string
    class_id: string
    class_name?: string
    section_id: string
    section_name?: string
    stream?: string
  }
  college_detail?: {
    id: string
    faculty_id?: string
    faculty_name?: string
    department_id?: string
    department_name?: string
    course_id: string
    course_name?: string
    degree_id?: string
    degree_name?: string
    batch_id?: string
    batch_name?: string
    semester_id?: string
    semester_number: number
    year_number: number
    specialization?: string
  }
  created_at: string
}

export interface AcademicHierarchy {
  id: string
  tenant_id: string
  institution_type: string
  academic_system: string
  has_departments: boolean
  has_faculties: boolean
  has_batches: boolean
  has_sections: boolean
  grading_system: string
  pass_percentage: number
  allow_cross_department_electives: boolean
  max_electives_per_student: number
  settings: Record<string, any>
  created_at: string
  updated_at: string
}

export interface StudentAcademicHistory {
  student_id: string
  admission_number: string
  student_name: string
  enrollments: StudentEnrollment[]
  promotions: Array<{
    id: string
    from_session_id: string
    to_session_id: string
    action: string
    promotion_date: string
    remarks?: string
    created_at: string
  }>
}

export const academicsApi = {
  // Sessions
  getSessions: (isCurrent?: boolean) =>
    apiClient.get('/academics/sessions', { params: { is_current: isCurrent } }).then((r) => r.data),
  createSession: (data: Partial<AcademicSession>) =>
    apiClient.post('/academics/sessions', data).then((r) => r.data),
  updateSession: (id: string, data: Partial<AcademicSession>) =>
    apiClient.patch(`/academics/sessions/${id}`, data).then((r) => r.data),
  deleteSession: (id: string) => apiClient.delete(`/academics/sessions/${id}`).then((r) => r.data),

  // Faculties
  getFaculties: () => apiClient.get('/academics/faculties').then((r) => r.data),
  createFaculty: (data: Partial<AcademicFaculty>) =>
    apiClient.post('/academics/faculties', data).then((r) => r.data),
  updateFaculty: (id: string, data: Partial<AcademicFaculty>) =>
    apiClient.patch(`/academics/faculties/${id}`, data).then((r) => r.data),
  deleteFaculty: (id: string) => apiClient.delete(`/academics/faculties/${id}`).then((r) => r.data),

  // Degrees
  getDegrees: () => apiClient.get('/academics/degrees').then((r) => r.data),
  createDegree: (data: Partial<AcademicDegree>) =>
    apiClient.post('/academics/degrees', data).then((r) => r.data),

  // Departments
  getDepartments: (facultyId?: string) =>
    apiClient.get('/academics/departments', { params: { faculty_id: facultyId } }).then((r) => r.data),
  createDepartment: (data: Partial<Department>) =>
    apiClient.post('/academics/departments', data).then((r) => r.data),
  updateDepartment: (id: string, data: Partial<Department>) =>
    apiClient.patch(`/academics/departments/${id}`, data).then((r) => r.data),
  deleteDepartment: (id: string) => apiClient.delete(`/academics/departments/${id}`).then((r) => r.data),

  // Classes
  getClasses: () => apiClient.get('/academics/classes').then((r) => r.data),
  createClass: (data: Partial<SchoolClass>) =>
    apiClient.post('/academics/classes', data).then((r) => r.data),
  updateClass: (id: string, data: Partial<SchoolClass>) =>
    apiClient.patch(`/academics/classes/${id}`, data).then((r) => r.data),
  deleteClass: (id: string) => apiClient.delete(`/academics/classes/${id}`).then((r) => r.data),

  // Sections
  getSections: (params?: { class_id?: string; course_id?: string; semester_id?: string }) =>
    apiClient.get('/academics/sections', { params }).then((r) => r.data),
  createSection: (data: Partial<Section>) =>
    apiClient.post('/academics/sections', data).then((r) => r.data),
  updateSection: (id: string, data: Partial<Section>) =>
    apiClient.patch(`/academics/sections/${id}`, data).then((r) => r.data),
  deleteSection: (id: string) => apiClient.delete(`/academics/sections/${id}`).then((r) => r.data),

  // Courses
  getCourses: (params?: { department_id?: string; degree_id?: string }) =>
    apiClient.get('/academics/courses', { params }).then((r) => r.data),
  createCourse: (data: Partial<Course>) =>
    apiClient.post('/academics/courses', data).then((r) => r.data),
  updateCourse: (id: string, data: Partial<Course>) =>
    apiClient.patch(`/academics/courses/${id}`, data).then((r) => r.data),
  deleteCourse: (id: string) => apiClient.delete(`/academics/courses/${id}`).then((r) => r.data),

  // Semesters
  getSemesters: (courseId?: string) =>
    apiClient.get('/academics/semesters', { params: { course_id: courseId } }).then((r) => r.data),
  createSemester: (data: Partial<CollegeSemester>) =>
    apiClient.post('/academics/semesters', data).then((r) => r.data),
  updateSemester: (id: string, data: Partial<CollegeSemester>) =>
    apiClient.patch(`/academics/semesters/${id}`, data).then((r) => r.data),
  deleteSemester: (id: string) => apiClient.delete(`/academics/semesters/${id}`).then((r) => r.data),

  // Batches
  getBatches: (courseId?: string) =>
    apiClient.get('/academics/batches', { params: { course_id: courseId } }).then((r) => r.data),
  createBatch: (data: Partial<CollegeBatch>) =>
    apiClient.post('/academics/batches', data).then((r) => r.data),

  // Subjects
  getSubjects: (params?: { department_id?: string; subject_type?: string }) =>
    apiClient.get('/academics/subjects', { params }).then((r) => r.data),
  createSubject: (data: Partial<Subject>) =>
    apiClient.post('/academics/subjects', data).then((r) => r.data),
  updateSubject: (id: string, data: Partial<Subject>) =>
    apiClient.patch(`/academics/subjects/${id}`, data).then((r) => r.data),
  deleteSubject: (id: string) => apiClient.delete(`/academics/subjects/${id}`).then((r) => r.data),

  // Subject Mappings
  getSubjectMappings: (params?: { session_id?: string; class_id?: string; course_id?: string }) =>
    apiClient.get('/academics/subject-mappings', { params }).then((r) => r.data),
  createSubjectMapping: (data: Partial<AcademicSubjectMapping>) =>
    apiClient.post('/academics/subject-mappings', data).then((r) => r.data),
  deleteSubjectMapping: (id: string) =>
    apiClient.delete(`/academics/subject-mappings/${id}`).then((r) => r.data),

  // Teacher Subject Mappings
  getTeacherSubjectMappings: (params?: { teacher_id?: string; class_id?: string; course_id?: string }) =>
    apiClient.get('/academics/teacher-subject-mappings', { params }).then((r) => r.data),
  createTeacherSubjectMapping: (data: Partial<TeacherSubjectMapping>) =>
    apiClient.post('/academics/teacher-subject-mappings', data).then((r) => r.data),
  deleteTeacherSubjectMapping: (id: string) =>
    apiClient.delete(`/academics/teacher-subject-mappings/${id}`).then((r) => r.data),

  // Enrollments
  getEnrollments: (params?: { session_id?: string; class_id?: string; course_id?: string }) =>
    apiClient.get('/academics/enrollments', { params }).then((r) => r.data),
  createEnrollment: (data: any) =>
    apiClient.post('/academics/enrollments', data).then((r) => r.data),

  // Promotions
  promoteCohort: (data: any) =>
    apiClient.post('/academics/promotions', data).then((r) => r.data),

  // Hierarchy
  getHierarchy: () => apiClient.get('/academics/hierarchy').then((r) => r.data),
  updateHierarchy: (data: Partial<AcademicHierarchy>) =>
    apiClient.put('/academics/hierarchy', data).then((r) => r.data),

  // Student Academic History
  getStudentHistory: (studentId: string) =>
    apiClient.get(`/academics/students/${studentId}/history`).then((r) => r.data),
}
