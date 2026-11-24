import type { ReactNode } from 'react'
import { matchPath } from 'react-router-dom'
import type { AuthUser } from '@/api/auth'
import DashboardIcon from '@mui/icons-material/Dashboard'
import PeopleIcon from '@mui/icons-material/People'
import SchoolIcon from '@mui/icons-material/School'
import HealthAndSafetyIcon from '@mui/icons-material/HealthAndSafety'
import BusinessIcon from '@mui/icons-material/Business'
import CardMembershipIcon from '@mui/icons-material/CardMembership'
import CampaignIcon from '@mui/icons-material/Campaign'
import SupportAgentIcon from '@mui/icons-material/SupportAgent'
import SecurityIcon from '@mui/icons-material/Security'
import SettingsIcon from '@mui/icons-material/Settings'
import LocalOfferIcon from '@mui/icons-material/LocalOffer'
import PaymentIcon from '@mui/icons-material/Payment'
import BadgeIcon from '@mui/icons-material/Badge'
import HowToRegIcon from '@mui/icons-material/HowToReg'
import QuizIcon from '@mui/icons-material/Quiz'
import AssessmentIcon from '@mui/icons-material/Assessment'
import MenuBookIcon from '@mui/icons-material/MenuBook'
import CalendarMonthIcon from '@mui/icons-material/CalendarMonth'
import AccountBalanceWalletIcon from '@mui/icons-material/AccountBalanceWallet'
import NotificationsIcon from '@mui/icons-material/Notifications'
import LocalLibraryIcon from '@mui/icons-material/LocalLibrary'
import DirectionsBusIcon from '@mui/icons-material/DirectionsBus'
import HotelIcon from '@mui/icons-material/Hotel'
import FamilyRestroomIcon from '@mui/icons-material/FamilyRestroom'

export interface NavItem {
  label: string
  path: string
  icon: ReactNode
}

const SUPER_ADMIN_NAV_ITEMS: NavItem[] = [
  { label: 'Overview', path: '/super-admin', icon: <DashboardIcon /> },
  { label: 'Institutions', path: '/super-admin/institutions', icon: <BusinessIcon /> },
  { label: 'Plans & Pricing', path: '/super-admin/plans', icon: <CardMembershipIcon /> },
  { label: 'Coupons', path: '/super-admin/coupons', icon: <LocalOfferIcon /> },
  { label: 'Announcements', path: '/super-admin/announcements', icon: <CampaignIcon /> },
  { label: 'Support Desk', path: '/super-admin/tickets', icon: <SupportAgentIcon /> },
  { label: 'Audit Trail', path: '/super-admin/audit-logs', icon: <SecurityIcon /> },
  { label: 'Platform Analytics', path: '/reports', icon: <AssessmentIcon /> },
  { label: 'Platform Settings', path: '/super-admin/settings', icon: <SettingsIcon /> },
]

const INSTITUTION_ADMIN_NAV_ITEMS: NavItem[] = [
  { label: 'Dashboard', path: '/dashboard', icon: <DashboardIcon /> },
  { label: 'Students',  path: '/students',  icon: <PeopleIcon /> },
  { label: 'Faculty & Staff', path: '/teachers', icon: <BadgeIcon /> },
  { label: 'Academic Structure',  path: '/academic',  icon: <SchoolIcon /> },
  { label: 'Subjects', path: '/academics/subjects', icon: <MenuBookIcon /> },
  { label: 'Attendance', path: '/attendance', icon: <HowToRegIcon /> },
  { label: 'Examinations', path: '/examinations', icon: <QuizIcon /> },
  { label: 'Results & Reports', path: '/results', icon: <AssessmentIcon /> },
  { label: 'LMS & Materials', path: '/lms', icon: <MenuBookIcon /> },
  { label: 'Timetable', path: '/timetable', icon: <CalendarMonthIcon /> },
  { label: 'Fees & Finance', path: '/fees', icon: <AccountBalanceWalletIcon /> },
  { label: 'Notifications & Hub', path: '/notifications', icon: <NotificationsIcon /> },
  { label: 'Library', path: '/library', icon: <LocalLibraryIcon /> },
  { label: 'Transport', path: '/transport', icon: <DirectionsBusIcon /> },
  { label: 'Hostel', path: '/hostel', icon: <HotelIcon /> },
  { label: 'Reports & Analytics', path: '/reports', icon: <AssessmentIcon /> },
  { label: 'Billing & Plan', path: '/subscription', icon: <PaymentIcon /> },
  { label: 'Health',    path: '/health',    icon: <HealthAndSafetyIcon /> },
]

const TEACHER_NAV_ITEMS: NavItem[] = [
  { label: 'Faculty Portal', path: '/dashboard', icon: <DashboardIcon /> },
  { label: 'My Students', path: '/students', icon: <PeopleIcon /> },
  { label: 'Roll Call Attendance', path: '/attendance', icon: <HowToRegIcon /> },
  { label: 'Examinations', path: '/examinations', icon: <QuizIcon /> },
  { label: 'Results & Marks Entry', path: '/results', icon: <AssessmentIcon /> },
  { label: 'LMS & Assignments', path: '/lms', icon: <MenuBookIcon /> },
  { label: 'Class Timetable', path: '/timetable', icon: <CalendarMonthIcon /> },
  { label: 'Library Catalog', path: '/library', icon: <LocalLibraryIcon /> },
  { label: 'Cohort Analytics', path: '/reports', icon: <AssessmentIcon /> },
]

const STAFF_MANAGER_NAV_ITEMS: NavItem[] = [
  { label: 'Dashboard', path: '/dashboard', icon: <DashboardIcon /> },
  { label: 'Faculty & Staff', path: '/teachers', icon: <BadgeIcon /> },
  { label: 'Academic Overview', path: '/academic', icon: <SchoolIcon /> },
]

const STUDENT_NAV_ITEMS: NavItem[] = [
  { label: 'Student Portal', path: '/dashboard', icon: <DashboardIcon /> },
  { label: 'My Attendance', path: '/attendance', icon: <HowToRegIcon /> },
  { label: 'My Tests & Exams', path: '/examinations', icon: <QuizIcon /> },
  { label: 'Results & Report Card', path: '/results', icon: <AssessmentIcon /> },
  { label: 'Study Material & LMS', path: '/lms', icon: <MenuBookIcon /> },
  { label: 'Class Timetable', path: '/timetable', icon: <CalendarMonthIcon /> },
  { label: 'Fee Dues & Receipts', path: '/fees', icon: <AccountBalanceWalletIcon /> },
  { label: 'Library Books', path: '/library', icon: <LocalLibraryIcon /> },
]

const PARENT_NAV_ITEMS: NavItem[] = [
  { label: 'Parent Portal', path: '/dashboard', icon: <FamilyRestroomIcon /> },
  { label: 'Children Attendance', path: '/attendance', icon: <HowToRegIcon /> },
  { label: 'Report Cards & Marks', path: '/results', icon: <AssessmentIcon /> },
  { label: 'Timetable', path: '/timetable', icon: <CalendarMonthIcon /> },
  { label: 'Online Fee Payments', path: '/fees', icon: <AccountBalanceWalletIcon /> },
  { label: 'School Notices', path: '/notifications', icon: <NotificationsIcon /> },
]

export function getNavigationItems(user: AuthUser | null): NavItem[] {
  if (user?.is_superadmin) return SUPER_ADMIN_NAV_ITEMS
  switch (user?.current_role) {
    case 'PRINCIPAL':
    case 'HOD': return STAFF_MANAGER_NAV_ITEMS
    case 'TEACHER': return TEACHER_NAV_ITEMS
    case 'STUDENT': return STUDENT_NAV_ITEMS
    case 'PARENT': return PARENT_NAV_ITEMS
    default: return INSTITUTION_ADMIN_NAV_ITEMS
  }
}

const routeAliases: Record<string, string[]> = {
  '/academic': ['/academics'],
  '/examinations': ['/exams'],
  '/results': ['/report-cards'],
  '/lms': ['/materials'],
  '/fees': ['/finance'],
  '/notifications': ['/integrations'],
  '/reports': ['/analytics'],
}

export function isNavigationItemActive(path: string, pathname: string): boolean {
  return [path, ...(routeAliases[path] ?? [])].some((itemPath) =>
    Boolean(matchPath({ path: itemPath, end: itemPath === '/super-admin' }, pathname)),
  )
}
