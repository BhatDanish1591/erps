import SpaceDashboard from '@mui/icons-material/SpaceDashboardOutlined'
import MenuBook from '@mui/icons-material/MenuBookOutlined'
import School from '@mui/icons-material/SchoolOutlined'
import AccountBalanceWallet from '@mui/icons-material/AccountBalanceWalletOutlined'
import DirectionsBus from '@mui/icons-material/DirectionsBusOutlined'
import Apartment from '@mui/icons-material/ApartmentOutlined'
import LocalLibrary from '@mui/icons-material/LocalLibraryOutlined'
import Assignment from '@mui/icons-material/AssignmentOutlined'
import Badge from '@mui/icons-material/BadgeOutlined'
import Forum from '@mui/icons-material/ForumOutlined'
import Insights from '@mui/icons-material/InsightsOutlined'
import Event from '@mui/icons-material/EventOutlined'
import Description from '@mui/icons-material/DescriptionOutlined'
import Groups from '@mui/icons-material/GroupsOutlined'
import Notifications from '@mui/icons-material/NotificationsNone'
import Block from '@mui/icons-material/BlockOutlined'
import type { SvgIconComponent } from '@mui/icons-material'
import type { AuthUser } from '@/api/auth'
import { getNavigationItems, isNavigationItemActive } from './navigationItems'

interface Destination {
  label: string
  path?: string
  section?: string
  search?: string
}

export interface NavbarItem extends Destination {
  status?: string
}

export interface NavbarModule {
  id: string
  label: string
  icon: SvgIconComponent
  items: NavbarItem[]
}

const destination = (label: string, path?: string, section?: string, search?: string): Destination => ({ label, path, section, search })
const staffActions = new Set([
  'Fee Structure', 'Fee Collection', 'Scholarships', 'Discounts', 'Financial Reports',
  'Question Bank', 'Marks Entry', 'Grade Management', 'Staff Attendance', 'Email', 'SMS',
])

export function getNavbarModules(user: AuthUser | null): NavbarModule[] {
  if (user?.is_superadmin) {
    const links = getNavigationItems(user)
    const group = (id: string, label: string, icon: SvgIconComponent, paths: string[]): NavbarModule => ({
      id, label, icon, items: links.filter((item) => paths.includes(item.path)),
    })
    return [
      group('platform', 'Platform', SpaceDashboard, ['/super-admin', '/reports']),
      group('institutions', 'Institutions', Apartment, ['/super-admin/institutions']),
      group('billing', 'Billing', AccountBalanceWallet, ['/super-admin/plans', '/super-admin/coupons']),
      group('operations', 'Operations', Forum, ['/super-admin/announcements', '/super-admin/tickets']),
      group('administration', 'Administration', Badge, ['/super-admin/audit-logs', '/super-admin/settings']),
    ]
  }
  const institution = user?.institutions.find((membership) => membership.tenant_id === user.current_tenant_id)
  const isSchool = institution?.institution_type === 'SCHOOL'
  const learner = user?.current_role === 'STUDENT' || user?.current_role === 'PARENT'
  const academicManager = user?.current_role === 'PRINCIPAL' || user?.current_role === 'HOD'
  const managerCatalogItems = new Set(isSchool ? ['Classes', 'Sections'] : ['Departments', 'Courses', 'Programs', 'Subjects'])
  const definitions: NavbarModule[] = [
    { id: 'erp', label: 'ERP', icon: SpaceDashboard, items: [
      destination('Dashboard', '/dashboard'),
      destination('Students', '/students'),
      destination('Attendance', '/attendance'),
      ...(user?.current_role === 'INSTITUTION_ADMIN'
        ? [destination('Admissions', '/students', 'New student admission', '?action=admit')]
        : [destination('Admissions')]),
      destination('Enrollment', '/academic', 'Enrollments & Promotion tab'),
      destination('Student Profiles', '/students', 'Select a student in the directory'),
      destination('Student Documents', '/students', 'Student profile → Documents'),
      destination('Alumni', '/students', 'Alumni / Graduated filter'),
    ] },
    { id: 'lms', label: 'LMS', icon: MenuBook, items: [
      destination('Study Materials', '/lms'),
      destination('Live Sessions'),
      destination('Recorded Lectures', '/lms', 'Materials Library → video materials'),
      destination('Assignments', '/lms', 'Assignments Board tab'),
      destination('Quizzes', '/examinations', 'Examinations & Schedules tab'),
      destination('Online Exams', '/examinations', 'Live Exam Room tab'),
      destination('Results', '/results', 'Results management'),
      destination('Question Bank', '/examinations', 'Question Bank tab'),
      destination('Learning Progress'),
    ] },
    { id: 'academics', label: 'Academics', icon: School, items: [
      ...(isSchool ? [
        destination('Classes', '/academic', 'School Structure tab', '?tab=classes'),
        destination('Sections', '/academic', 'School Structure tab', '?tab=sections'),
      ] : [
        destination('Departments', '/academic', 'College Departments', '?tab=departments'),
        destination('Courses', '/academic', 'College Courses', '?tab=courses'),
        destination('Programs', '/academic', 'College Courses', '?tab=courses'),
        destination('Batches'),
        destination('Semesters', '/academic', 'College Semesters', '?tab=semesters'),
      ]),
      destination('Subjects', !isSchool && (user?.is_superadmin || user?.current_role === 'INSTITUTION_ADMIN') ? '/academics/subjects' : '/academic'),
      destination('Academic Calendar', '/timetable', 'Bell Schedule & Holidays tab'),
      destination('Timetable', '/timetable'),
      destination('Syllabus', '/lms', 'Materials Library → Syllabus filter'),
    ] },
    { id: 'finance', label: 'Finance', icon: AccountBalanceWallet, items: [
      destination('Fee Structure', '/fees', 'Fee Structures & Categories tab'),
      destination('Fee Collection', '/fees', 'Invoices & Collections tab'),
      destination('Pending Fees', '/fees', learner ? 'My Fees & Receipts tab' : 'Outstanding Dues & Defaulters tab'),
      destination('Fee Payments', '/fees', learner ? 'My Fees & Receipts tab' : 'Invoices & Collections tab'),
      destination('Scholarships', '/fees', 'Discounts & Scholarships tab'),
      destination('Discounts', '/fees', 'Discounts & Scholarships tab'),
      destination('Receipts', '/fees', learner ? 'My Fees & Receipts tab' : 'Invoices & Collections tab'),
      destination('Expenses'),
      destination('Financial Reports', '/fees', 'Finance Dashboard / Transaction Ledger'),
    ] },
    { id: 'transport', label: 'Transport', icon: DirectionsBus, items: [
      destination('Vehicles', '/transport', 'Fleet Vehicles & Telemetry tab'),
      destination('Routes', '/transport', 'Routes & Bus Stops tab'),
      destination('Stops', '/transport', 'Routes & Bus Stops tab'),
      destination('Drivers', '/transport', 'Drivers & Maintenance tab'),
      destination('Student Allocation', '/transport', 'Student Route Allocations tab'),
      destination('Transport Fees'),
      destination('Vehicle Tracking', '/transport', 'Fleet Vehicles & Telemetry tab'),
      destination('Maintenance', '/transport', 'Drivers & Maintenance tab'),
    ] },
    { id: 'hostel', label: 'Hostel', icon: Apartment, items: [
      destination('Hostel Buildings', '/hostel', 'Buildings & Rooms tab'),
      destination('Rooms', '/hostel', 'Buildings & Rooms tab'),
      destination('Bed Allocation', '/hostel', 'Resident Allocations tab'),
      destination('Student Allocation', '/hostel', 'Resident Allocations tab'),
      destination('Hostel Attendance', '/hostel', 'Curfew Attendance tab'),
      destination('Hostel Fees'),
      destination('Visitors', '/hostel', 'Visitors & Maintenance tab'),
      destination('Complaints'),
    ] },
    { id: 'library', label: 'Library', icon: LocalLibrary, items: [
      destination('Book Catalog', '/library'),
      destination('Book Categories', '/library', 'Book Categories tab'),
      destination('Issue Books', '/library', 'Issue Book action'),
      destination('Return Books', '/library', 'Issue & Return History tab'),
      destination('Reservations'),
      destination('Overdue Books', '/library', 'Issue & Return History tab'),
      destination('Fines', '/library', 'Issue & Return History tab'),
      destination('Digital Library'),
    ] },
    { id: 'examinations', label: 'Examinations', icon: Assignment, items: [
      destination('Exam Schedule', '/examinations'),
      destination('Exam Timetable', '/examinations', 'Examinations & Schedules tab'),
      destination('Exam Registration'),
      destination('Admit Cards'),
      destination('Marks Entry', '/results', 'Subject Marks Entry tab'),
      destination('Grade Management', '/results', 'Marksheet & Approval Workflow tab'),
      destination('Results', '/results'),
      destination('Report Cards', '/results', 'Official Report Cards tab'),
      destination('Transcripts'),
    ] },
    { id: 'faculty', label: 'Faculty & HR', icon: Badge, items: [
      destination('Faculty Directory', '/teachers'),
      destination('Staff Management', '/teachers', 'Faculty directory'),
      destination('Staff Attendance', '/attendance', 'QR & Faculty Punch tab'),
      destination('Leave Management', '/teachers', 'Faculty profile → Attendance & Leaves'),
      destination('Payroll'),
      destination('Salary Slips'),
      destination('Faculty Workload', '/teachers', 'Faculty profile → Overview & Workload'),
      destination('Performance Evaluation'),
    ] },
    { id: 'communication', label: 'Communication', icon: Forum, items: [
      destination('Announcements', '/super-admin/announcements'),
      destination('Notices'),
      destination('Notifications', '/notifications'),
      destination('Email', '/notifications', 'Provider Integrations tab'),
      destination('SMS', '/notifications', 'Provider Integrations tab'),
      destination('Parent Communication', user?.current_role === 'PARENT' ? '/dashboard' : undefined, 'Parent Portal → Teacher Messages'),
      destination('Messages', user?.current_role === 'PARENT' ? '/dashboard' : undefined, 'Parent Portal → Teacher Messages'),
      destination('Feedback'),
      destination('Support Tickets', '/super-admin/tickets'),
    ] },
    { id: 'reports', label: 'Reports & Analytics', icon: Insights, items: [
      destination('Student Reports', '/reports', 'Student & Parent Progress tab'),
      destination('Attendance Reports', '/reports', 'Attendance Summary report'),
      destination('Academic Reports', '/reports', 'Academic & Teacher Analytics tab'),
      destination('Examination Reports', '/reports', 'Examination Performance report'),
      destination('Finance Reports', '/reports', 'Fee Collection report'),
      destination('Faculty Reports', '/reports', 'Academic & Teacher Analytics tab'),
      destination('Transport Reports'),
      ...(!isSchool ? [destination('Hostel Reports')] : []),
      destination('Library Reports'),
    ] },
  ]
  const existingLinks = getNavigationItems(user)
  const allowed = new Set(existingLinks.map(({ path }) => path))
  const existingExtras: Record<string, string[]> = {
    erp: ['/super-admin/institutions', '/super-admin/audit-logs', '/super-admin/settings', '/health'],
    finance: ['/super-admin/plans', '/super-admin/coupons', '/subscription'],
    reports: ['/reports'],
  }

  return definitions.filter((module) => !isSchool || module.id !== 'hostel').map((module) => ({
    ...module,
    items: [
      ...module.items.map((item) => {
        if (!item.path) return { ...item, status: 'Page unavailable' }
        if (!allowed.has(item.path) || (learner && staffActions.has(item.label)) || (
          academicManager && item.path === '/academic' && !managerCatalogItems.has(item.label)
        )) {
          return { label: item.label, status: 'Unavailable for your role' }
        }
        if (academicManager && item.path === '/academic') return { ...item, section: 'Academic overview', search: undefined }
        return item
      }),
      ...existingLinks.filter(({ path }) => existingExtras[module.id]?.includes(path)),
    ],
  }))
}

const primaryPaths: Record<string, string[]> = {
  erp: ['/dashboard', '/students', '/attendance', '/health', '/super-admin', '/super-admin/institutions', '/super-admin/audit-logs', '/super-admin/settings'],
  lms: ['/lms'],
  academics: ['/academic', '/academics/subjects', '/timetable'],
  finance: ['/fees', '/subscription', '/super-admin/plans', '/super-admin/coupons'],
  transport: ['/transport'],
  hostel: ['/hostel'],
  library: ['/library'],
  examinations: ['/examinations', '/results'],
  faculty: ['/teachers', '/teacher/dashboard'],
  communication: ['/notifications', '/super-admin/announcements', '/super-admin/tickets'],
  reports: ['/reports'],
}

export function isModuleActive(module: NavbarModule, pathname: string): boolean {
  return (primaryPaths[module.id] ?? module.items.flatMap((item) => item.path ? [item.path] : []))
    .some((path) => isNavigationItemActive(path, pathname))
}

const sectionIcons: Record<string, SvgIconComponent> = {
  Attendance: Event,
  'Academic Calendar': Event,
  Timetable: Event,
  'Exam Schedule': Event,
  'Exam Timetable': Event,
  Students: Groups,
  'Student Profiles': Groups,
  'Student Allocation': Groups,
  'Student Documents': Description,
  Receipts: Description,
  'Report Cards': Description,
  Notifications,
}

export function getSubmenuIcon(module: NavbarModule, item: NavbarItem): SvgIconComponent {
  return item.path ? sectionIcons[item.label] ?? module.icon : Block
}

export function isSubmenuItemActive(module: NavbarModule, item: NavbarItem, pathname: string, search = ''): boolean {
  if (!item.path || !isModuleActive(module, pathname) || !isNavigationItemActive(item.path, pathname)) return false
  const matching = module.items.filter(({ path }) => path === item.path)
  return item === (matching.find((candidate) => candidate.search && candidate.search === search)
    ?? matching.find((candidate) => !candidate.search && !candidate.section)
    ?? matching[0])
}
