import { Routes, Route, Navigate } from 'react-router-dom'
import { Suspense, lazy } from 'react'
import { CircularProgress, Box } from '@mui/material'
import { ProtectedRoute } from '@/components/auth/ProtectedRoute'
import { AppLayout } from '@/components/layout/AppLayout'
import { useAuthStore } from '@/store/authStore'

// Public Auth Pages
const LoginPage = lazy(() => import('@/pages/auth/LoginPage'))
const RegisterPage = lazy(() => import('@/pages/auth/RegisterPage'))
const ForgotPasswordPage = lazy(() => import('@/pages/auth/ForgotPasswordPage'))
const ResetPasswordPage = lazy(() => import('@/pages/auth/ResetPasswordPage'))
const InstitutionSelectPage = lazy(() => import('@/pages/auth/InstitutionSelectPage'))
const UnauthorizedPage = lazy(() => import('@/pages/auth/UnauthorizedPage'))
const MobileOnlyPage = lazy(() => import('@/pages/auth/MobileOnlyPage'))
const AcceptInvitationPage = lazy(() => import('@/pages/auth/AcceptInvitationPage'))
const InstitutionRegistrationPage = lazy(() => import('@/pages/onboarding/InstitutionRegistrationPage'))
const OnboardingWizardPage = lazy(() => import('@/pages/onboarding/OnboardingWizardPage'))

// Role-based Dashboards
const DashboardRouter = lazy(() => import('@/pages/dashboards/DashboardRouter'))
const SuperAdminDashboard = lazy(() => import('@/pages/dashboards/SuperAdminDashboard'))
const InstitutionsPage = lazy(() => import('@/pages/super-admin/InstitutionsPage'))
const SubscriptionPlansPage = lazy(() => import('@/pages/super-admin/SubscriptionPlansPage'))
const CouponsPage = lazy(() => import('@/pages/super-admin/CouponsPage').then(m => ({ default: m.CouponsPage })))
const AnnouncementsPage = lazy(() => import('@/pages/super-admin/AnnouncementsPage'))
const SupportTicketsPage = lazy(() => import('@/pages/super-admin/SupportTicketsPage'))
const AuditLogsPage = lazy(() => import('@/pages/super-admin/AuditLogsPage'))
const SettingsIntegrationsPage = lazy(() => import('@/pages/super-admin/SettingsIntegrationsPage'))
const BillingSubscriptionPage = lazy(() => import('@/pages/subscription/BillingSubscriptionPage').then(m => ({ default: m.BillingSubscriptionPage })))

// Student Management
const StudentsListPage = lazy(() => import('@/pages/students/StudentsListPage').then(m => ({ default: m.StudentsListPage })))
const StudentProfilePage = lazy(() => import('@/pages/students/StudentProfilePage').then(m => ({ default: m.StudentProfilePage })))
const StudentPromotionPage = lazy(() => import('@/pages/students/StudentPromotionPage').then(m => ({ default: m.StudentPromotionPage })))

// Teacher & Staff Management
const TeachersListPage = lazy(() => import('@/pages/teachers/TeachersListPage').then(m => ({ default: m.TeachersListPage })))
const TeacherProfilePage = lazy(() => import('@/pages/teachers/TeacherProfilePage').then(m => ({ default: m.TeacherProfilePage })))
const TeacherDashboardPage = lazy(() => import('@/pages/teachers/TeacherDashboardPage').then(m => ({ default: m.TeacherDashboardPage })))

// Academic Management
const AcademicsPage = lazy(() => import('@/pages/academics/AcademicsPage'))
const SubjectsPage = lazy(() => import('@/pages/academics/SubjectsPage'))
const StaffAcademicOverview = lazy(() => import('@/pages/academics/StaffAcademicOverview'))

// Attendance Management
const AttendancePage = lazy(() => import('@/pages/attendance/AttendancePage'))

// Examination Management
const ExaminationsPage = lazy(() => import('@/pages/examinations/ExaminationsPage'))

// Results & Report Card Management
const ResultsManagementPage = lazy(() => import('@/pages/results/ResultsManagementPage'))

// LMS & Study Material Management
const LMSPage = lazy(() => import('@/pages/lms/LMSPage'))

// Timetable Management
const TimetablePage = lazy(() => import('@/pages/timetable/TimetablePage'))

// Student Fees & Finance Management
const FeesManagementPage = lazy(() => import('@/pages/fees/FeesManagementPage'))

// Notifications & Integrations
const NotificationIntegrationPage = lazy(() => import('@/pages/notifications/NotificationIntegrationPage'))

// Advanced Institution Modules (Library, Transport, Hostel)
const LibraryManagementPage = lazy(() => import('@/pages/library/LibraryManagementPage'))
const TransportManagementPage = lazy(() => import('@/pages/transport/TransportManagementPage'))
const HostelManagementPage = lazy(() => import('@/pages/hostel/HostelManagementPage'))

// Analytics & Reporting Engine
const ReportsPage = lazy(() => import('@/pages/reports/ReportsPage'))

// Health & System
const HealthPage = lazy(() => import('@/pages/HealthPage'))
const NotFoundPage = lazy(() => import('@/pages/NotFoundPage'))

function LoadingFallback() {
  return (
    <Box display="flex" alignItems="center" justifyContent="center" minHeight="100vh">
      <CircularProgress size={40} />
    </Box>
  )
}

function AcademicRoute() {
  const role = useAuthStore((state) => state.user?.current_role)
  const tenantId = useAuthStore((state) => state.user?.current_tenant_id)
  return role === 'HOD' || role === 'PRINCIPAL'
    ? <StaffAcademicOverview key={tenantId} />
    : <AcademicsPage key={tenantId} />
}

export default function App() {
  return (
    <Suspense fallback={<LoadingFallback />}>
      <Routes>
        {/* Public Authentication Routes */}
        <Route path="/login" element={<LoginPage />} />
        <Route path="/register" element={<RegisterPage />} />
        <Route path="/register-institution" element={<InstitutionRegistrationPage />} />
        <Route path="/accept-invitation" element={<AcceptInvitationPage />} />
        <Route path="/forgot-password" element={<ForgotPasswordPage />} />
        <Route path="/reset-password" element={<ResetPasswordPage />} />
        <Route path="/unauthorized" element={<UnauthorizedPage />} />
        <Route path="/mobile-only" element={<MobileOnlyPage />} />

        {/* Institution Onboarding Wizard */}
        <Route
          path="/onboarding"
          element={
            <ProtectedRoute>
              <OnboardingWizardPage />
            </ProtectedRoute>
          }
        />

        {/* Multi-Tenant Institution Selector */}
        <Route
          path="/select-institution"
          element={
            <ProtectedRoute requireTenant={false}>
              <InstitutionSelectPage />
            </ProtectedRoute>
          }
        />

        {/* Platform Super Admin Portal */}
        <Route
          path="/super-admin"
          element={
            <ProtectedRoute requireTenant={false} allowedRoles={['SUPER_ADMIN']}>
              <AppLayout />
            </ProtectedRoute>
          }
        >
          <Route index element={<SuperAdminDashboard />} />
          <Route path="institutions" element={<InstitutionsPage />} />
          <Route path="plans" element={<SubscriptionPlansPage />} />
          <Route path="coupons" element={<CouponsPage />} />
          <Route path="announcements" element={<AnnouncementsPage />} />
          <Route path="tickets" element={<SupportTicketsPage />} />
          <Route path="audit-logs" element={<AuditLogsPage />} />
          <Route path="settings" element={<SettingsIntegrationsPage />} />
        </Route>

        {/* Authenticated Application with AppLayout */}
        <Route
          path="/"
          element={
            <ProtectedRoute>
              <AppLayout />
            </ProtectedRoute>
          }
        >
          <Route index element={<Navigate to="/dashboard" replace />} />
          <Route path="dashboard" element={<DashboardRouter />} />
          <Route path="students" element={<StudentsListPage />} />
          <Route path="students/promote" element={<StudentPromotionPage />} />
          <Route path="students/:studentId" element={<StudentProfilePage />} />
          <Route path="teachers" element={<ProtectedRoute allowedRoles={['INSTITUTION_ADMIN', 'PRINCIPAL', 'HOD']}><TeachersListPage /></ProtectedRoute>} />
          <Route path="teachers/:teacherId" element={<ProtectedRoute allowedRoles={['INSTITUTION_ADMIN', 'PRINCIPAL', 'HOD', 'TEACHER']}><TeacherProfilePage /></ProtectedRoute>} />
          <Route path="teacher/dashboard" element={<TeacherDashboardPage />} />
          <Route path="academic" element={<AcademicRoute />} />
          <Route path="academics" element={<AcademicRoute />} />
          <Route path="academics/subjects" element={<ProtectedRoute allowedRoles={['INSTITUTION_ADMIN']}><SubjectsPage /></ProtectedRoute>} />
          <Route path="attendance" element={<AttendancePage />} />
          <Route path="examinations" element={<ExaminationsPage />} />
          <Route path="exams" element={<ExaminationsPage />} />
          <Route path="results" element={<ResultsManagementPage />} />
          <Route path="report-cards" element={<ResultsManagementPage />} />
          <Route path="lms" element={<LMSPage />} />
          <Route path="materials" element={<LMSPage />} />
          <Route path="timetable" element={<TimetablePage />} />
          <Route path="fees" element={<FeesManagementPage />} />
          <Route path="finance" element={<FeesManagementPage />} />
          <Route path="notifications" element={<NotificationIntegrationPage />} />
          <Route path="integrations" element={<NotificationIntegrationPage />} />
          <Route path="library" element={<LibraryManagementPage />} />
          <Route path="transport" element={<TransportManagementPage />} />
          <Route path="hostel" element={<HostelManagementPage />} />
          <Route path="reports" element={<ReportsPage />} />
          <Route path="analytics" element={<ReportsPage />} />
          <Route path="subscription" element={<BillingSubscriptionPage />} />
          <Route path="health" element={<HealthPage />} />
        </Route>

        {/* Catch-all 404 */}
        <Route path="*" element={<NotFoundPage />} />
      </Routes>
    </Suspense>
  )
}
