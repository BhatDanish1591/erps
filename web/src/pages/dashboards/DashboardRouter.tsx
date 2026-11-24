import { useAuthStore } from '@/store/authStore'
import { Navigate } from 'react-router-dom'
import SuperAdminDashboard from './SuperAdminDashboard'
import InstitutionAdminDashboard from './InstitutionAdminDashboard'
import TeacherDashboard from './TeacherDashboard'
import StudentDashboard from './StudentDashboard'
import ParentDashboard from './ParentDashboard'

export default function DashboardRouter() {
  const { user } = useAuthStore()

  if (user?.is_superadmin) {
    return <SuperAdminDashboard />
  }

  const currentRole =
    user?.current_role ||
    user?.institutions?.find((i) => i.tenant_id === user?.current_tenant_id)?.role_code

  switch (currentRole) {
    case 'PRINCIPAL':
    case 'HOD':
      return <Navigate to="/teachers" replace />
    case 'INSTITUTION_ADMIN':
      return <InstitutionAdminDashboard />
    case 'TEACHER':
      return <TeacherDashboard />
    case 'STUDENT':
      return <StudentDashboard />
    case 'PARENT':
      return <ParentDashboard />
    default:
      return <InstitutionAdminDashboard />
  }
}
