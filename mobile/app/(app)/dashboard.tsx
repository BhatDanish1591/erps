import React, { useEffect, useState } from 'react'
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  RefreshControl,
  Image,
} from 'react-native'
import { SafeAreaView } from 'react-native-safe-area-context'
import { useRouter } from 'expo-router'
import { Ionicons } from '@expo/vector-icons'
import { useAuthStore } from '../../store/authStore'
import { mobileReportsApi } from '../../api/reports'
import { mobileParentsApi, LinkedChildSummary } from '../../api/parents'
import { theme } from '../../theme'

export default function DashboardScreen() {
  const router = useRouter()
  const { user } = useAuthStore()

  const [refreshing, setRefreshing] = useState(false)
  const [studentStats, setStudentStats] = useState<any | null>(null)
  const [teacherStats, setTeacherStats] = useState<any | null>(null)
  const [parentStats, setParentStats] = useState<any | null>(null)
  const [children, setChildren] = useState<LinkedChildSummary[]>([])
  const [selectedChildId, setSelectedChildId] = useState<string | null>(null)

  const rawRole = (user?.current_role || user?.role || 'STUDENT').toUpperCase()
  const isTeacher = rawRole === 'TEACHER' || rawRole === 'FACULTY'
  const isParent = rawRole === 'PARENT' || rawRole === 'GUARDIAN'
  const isAdmin = rawRole === 'INSTITUTION_ADMIN' || user?.is_superadmin
  const isStaffManager = isAdmin || ['PRINCIPAL', 'HOD'].includes(rawRole)

  const activeInstitution = user?.institutions?.find(
    (i) => i.tenant_id === (user.current_tenant_id || user.tenant_id)
  )

  const loadData = async () => {
    try {
      if (isStaffManager) {
        return
      } else if (isTeacher) {
        const tData = await mobileReportsApi.getTeacherAnalytics()
        setTeacherStats(tData)
      } else if (isParent) {
        const pData = await mobileReportsApi.getParentAnalytics()
        setParentStats(pData)
        const kids = await mobileParentsApi.getLinkedChildren()
        setChildren(kids || [])
        if (kids && kids.length > 0 && !selectedChildId) {
          setSelectedChildId(kids[0].student_id)
        }
      } else {
        const sData = await mobileReportsApi.getStudentAnalytics()
        setStudentStats(sData)
      }
    } catch {
      // Offline fallback
    }
  }

  useEffect(() => {
    loadData()
  }, [user?.tenant_id, rawRole])

  const onRefresh = async () => {
    setRefreshing(true)
    await loadData()
    setRefreshing(false)
  }

  const institutionName = activeInstitution?.institution_name || 'Institution'
  const userName = user?.full_name || (isTeacher ? 'Prof. Ananya Verma' : isParent ? 'Suresh Patel' : 'Aarav Sharma')

  // ─────────────────────────────────────────────────────────────────────────────
  // 1. STUDENT SERVICES (3 Rows x 4 Columns)
  // ─────────────────────────────────────────────────────────────────────────────
  const studentServices = [
    { label: 'Study\nMaterials', icon: 'book-outline', color: '#8b5cf6', bg: '#f5f3ff', borderColor: '#ede9fe', route: '/(app)/lms' },
    { label: 'Live\nSessions', icon: 'videocam-outline', color: '#ec4899', bg: '#fdf2f8', borderColor: '#fce7f3', route: '/(app)/lms' },
    { label: 'Assignments', icon: 'clipboard-outline', color: '#10b981', bg: '#ecfdf5', borderColor: '#d1fae5', route: '/(app)/lms' },
    { label: 'Exams', icon: 'document-text-outline', color: '#0284c7', bg: '#f0f9ff', borderColor: '#e0f2fe', route: '/(app)/examinations' },
    { label: 'Results', icon: 'bar-chart-outline', color: '#f59e0b', bg: '#fffbeb', borderColor: '#fef3c7', route: '/(app)/results' },
    { label: 'Timetable', icon: 'calendar-outline', color: '#7c3aed', bg: '#f5f3ff', borderColor: '#ede9fe', route: '/(app)/attendance' },
    { label: 'Attendance', icon: 'checkmark-circle-outline', color: '#06b6d4', bg: '#ecfeff', borderColor: '#cffafe', route: '/(app)/attendance' },
    { label: 'Fees', icon: 'wallet-outline', color: '#ea580c', bg: '#fff7ed', borderColor: '#ffedd5', route: '/(app)/fees' },
    { label: 'Library', icon: 'library-outline', color: '#059669', bg: '#ecfdf5', borderColor: '#d1fae5', route: '/(app)/lms' },
    { label: 'Notices', icon: 'megaphone-outline', color: '#d946ef', bg: '#fdf4ff', borderColor: '#fae8ff', route: '/(app)/notifications' },
    { label: 'Messages', icon: 'chatbubble-ellipses-outline', color: '#3b82f6', bg: '#eff6ff', borderColor: '#dbeafe', route: '/(app)/notifications' },
    { label: 'Profile', icon: 'person-outline', color: '#6366f1', bg: '#eef2ff', borderColor: '#e0e7ff', route: '/(app)/profile' },
  ]

  // ─────────────────────────────────────────────────────────────────────────────
  // 2. TEACHER SERVICES (3 Rows x 4 Columns)
  // ─────────────────────────────────────────────────────────────────────────────
  const teacherServices = [
    { label: 'Roll Call', icon: 'checkbox-outline', color: '#10b981', bg: '#ecfdf5', borderColor: '#d1fae5', route: '/(app)/attendance' },
    { label: 'Grade Tasks', icon: 'document-text-outline', color: '#ec4899', bg: '#fdf2f8', borderColor: '#fce7f3', route: '/(app)/lms' },
    { label: 'Create Exam', icon: 'add-circle-outline', color: '#0284c7', bg: '#f0f9ff', borderColor: '#e0f2fe', route: '/(app)/examinations' },
    { label: 'Enter Marks', icon: 'create-outline', color: '#8b5cf6', bg: '#f5f3ff', borderColor: '#ede9fe', route: '/(app)/results' },
    { label: 'Timetable', icon: 'calendar-outline', color: '#7c3aed', bg: '#f5f3ff', borderColor: '#ede9fe', route: '/(app)/attendance' },
    { label: 'Course Notes', icon: 'book-outline', color: '#059669', bg: '#ecfdf5', borderColor: '#d1fae5', route: '/(app)/lms' },
    { label: 'Students', icon: 'people-outline', color: '#3b82f6', bg: '#eff6ff', borderColor: '#dbeafe', route: '/(app)/students' },
    { label: 'Cohort Report', icon: 'bar-chart-outline', color: '#f59e0b', bg: '#fffbeb', borderColor: '#fef3c7', route: '/(app)/attendance' },
    { label: 'Library', icon: 'library-outline', color: '#059669', bg: '#ecfdf5', borderColor: '#d1fae5', route: '/(app)/lms' },
    { label: 'Staff Circular', icon: 'megaphone-outline', color: '#d946ef', bg: '#fdf4ff', borderColor: '#fae8ff', route: '/(app)/notifications' },
    { label: 'Parent Chat', icon: 'chatbubbles-outline', color: '#06b6d4', bg: '#ecfeff', borderColor: '#cffafe', route: '/(app)/notifications' },
    { label: 'Faculty ID', icon: 'person-outline', color: '#6366f1', bg: '#eef2ff', borderColor: '#e0e7ff', route: '/(app)/profile' },
  ]

  // ─────────────────────────────────────────────────────────────────────────────
  // 3. PARENT SERVICES (3 Rows x 4 Columns)
  // ─────────────────────────────────────────────────────────────────────────────
  const parentServices = [
    { label: 'Attendance', icon: 'checkmark-circle-outline', color: '#06b6d4', bg: '#ecfeff', borderColor: '#cffafe', route: '/(app)/attendance' },
    { label: 'Pay Fees', icon: 'wallet-outline', color: '#ea580c', bg: '#fff7ed', borderColor: '#ffedd5', route: '/(app)/fees' },
    { label: 'Receipts', icon: 'receipt-outline', color: '#10b981', bg: '#ecfdf5', borderColor: '#d1fae5', route: '/(app)/fees' },
    { label: 'Report Card', icon: 'ribbon-outline', color: '#8b5cf6', bg: '#f5f3ff', borderColor: '#ede9fe', route: '/(app)/results' },
    { label: 'Exam Hall', icon: 'document-text-outline', color: '#0284c7', bg: '#f0f9ff', borderColor: '#e0f2fe', route: '/(app)/examinations' },
    { label: 'Timetable', icon: 'calendar-outline', color: '#7c3aed', bg: '#f5f3ff', borderColor: '#ede9fe', route: '/(app)/attendance' },
    { label: 'Study Notes', icon: 'book-outline', color: '#059669', bg: '#ecfdf5', borderColor: '#d1fae5', route: '/(app)/lms' },
    { label: 'Teacher Note', icon: 'chatbox-outline', color: '#ec4899', bg: '#fdf2f8', borderColor: '#fce7f3', route: '/(app)/notifications' },
    { label: 'Leave Apply', icon: 'mail-outline', color: '#3b82f6', bg: '#eff6ff', borderColor: '#dbeafe', route: '/(app)/attendance' },
    { label: 'School News', icon: 'megaphone-outline', color: '#d946ef', bg: '#fdf4ff', borderColor: '#fae8ff', route: '/(app)/notifications' },
    { label: 'Contact', icon: 'call-outline', color: '#059669', bg: '#ecfdf5', borderColor: '#d1fae5', route: '/(app)/notifications' },
    { label: 'Student ID', icon: 'card-outline', color: '#6366f1', bg: '#eef2ff', borderColor: '#e0e7ff', route: '/(app)/profile' },
  ]

  const activeServices = isStaffManager
    ? teacherServices.filter((service) => service.label === 'Students')
    : isTeacher ? teacherServices : isParent ? parentServices : studentServices

  // Selected child progress for parent view
  const selectedChildProgress = parentStats?.children?.find(
    (c: any) => c.student_id === selectedChildId
  ) || parentStats?.children?.[0]

  return (
    <View style={styles.container}>
      <ScrollView
        contentContainerStyle={styles.scrollContent}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} colors={['#6366f1']} />}
        showsVerticalScrollIndicator={false}
      >
        {/* ── Top Header with Purple Wave Background ── */}
        <View style={styles.headerBackground}>
          <SafeAreaView edges={['top']}>
            <View style={styles.headerContent}>
              {/* Profile Avatar with white ring */}
              <TouchableOpacity
                style={styles.avatarWrapper}
                onPress={() => router.push('/(app)/profile')}
                activeOpacity={0.8}
              >
                {user?.avatar_url ? (
                  <Image source={{ uri: user.avatar_url }} style={styles.avatarImage} />
                ) : isStaffManager ? (
                  <Ionicons name="person-circle-outline" size={64} color="#ffffff" />
                ) : isTeacher ? (
                  <Image
                    source={{
                      uri: 'https://images.unsplash.com/photo-1573496359142-b8d87734a5a2?w=150&auto=format&fit=crop&q=80',
                    }}
                    style={styles.avatarImage}
                  />
                ) : isParent ? (
                  <Image
                    source={{
                      uri: 'https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=150&auto=format&fit=crop&q=80',
                    }}
                    style={styles.avatarImage}
                  />
                ) : (
                  <Image
                    source={{
                      uri: 'https://images.unsplash.com/photo-1539571696357-5a69c17a67c6?w=150&auto=format&fit=crop&q=80',
                    }}
                    style={styles.avatarImage}
                  />
                )}
              </TouchableOpacity>

              {/* User Identity info */}
              <View style={styles.headerUserInfo}>
                <Text style={styles.headerUserName} numberOfLines={1}>
                  {userName}
                </Text>
                <View style={styles.headerInstRow}>
                  <Ionicons name="business-outline" size={13} color="#ffffff" style={{ opacity: 0.9 }} />
                  <Text style={styles.headerInstName} numberOfLines={1}>
                    {institutionName}
                  </Text>
                </View>
                <Text style={styles.headerAcademicMeta} numberOfLines={1}>
                  {isStaffManager ? rawRole.replace('_', ' ') : isTeacher
                    ? 'Dept of Computer Science | Assistant Professor | TCH-102'
                    : isParent
                    ? `Parent of ${selectedChildProgress?.student_name || 'Aarav Patel'} (B.Tech CSE, Sem 4)`
                    : 'B.Tech (CSE) | Semester 4 | Roll No. CSE2301'}
                </Text>
              </View>

              {/* Notification Bell with Red Badge */}
              <TouchableOpacity
                style={styles.notifBellBtn}
                onPress={() => router.push('/(app)/notifications')}
                activeOpacity={0.7}
              >
                <Ionicons name="notifications-outline" size={24} color="#ffffff" />
                <View style={styles.notifBadge}>
                  <Text style={styles.notifBadgeText}>3</Text>
                </View>
              </TouchableOpacity>
            </View>

            {/* Parent Child Switcher Pills */}
            {isParent && children.length > 1 && (
              <ScrollView
                horizontal
                showsHorizontalScrollIndicator={false}
                contentContainerStyle={styles.childPillsRow}
              >
                {children.map((k) => (
                  <TouchableOpacity
                    key={k.student_id}
                    onPress={() => setSelectedChildId(k.student_id)}
                    style={[
                      styles.childPill,
                      selectedChildId === k.student_id && styles.childPillActive,
                    ]}
                  >
                    <Ionicons
                      name="person"
                      size={12}
                      color={selectedChildId === k.student_id ? '#4338ca' : '#ffffff'}
                    />
                    <Text
                      style={[
                        styles.childPillText,
                        selectedChildId === k.student_id && styles.childPillTextActive,
                      ]}
                    >
                      {k.student_name}
                    </Text>
                  </TouchableOpacity>
                ))}
              </ScrollView>
            )}
          </SafeAreaView>
        </View>

        {/* ── Floating 4-Column KPI Summary Card ── */}
        {!isStaffManager && <View style={styles.kpiContainer}>
          {isTeacher ? (
            // TEACHER KPIS
            <>
              <TouchableOpacity style={styles.kpiItem} onPress={() => router.push('/(app)/attendance')}>
                <Ionicons name="people-outline" size={20} color="#2563eb" />
                <Text style={styles.kpiValue}>{teacherStats?.assigned_students ?? 128}</Text>
                <Text style={styles.kpiLabel}>Students</Text>
              </TouchableOpacity>

              <TouchableOpacity style={styles.kpiItem} onPress={() => router.push('/(app)/attendance')}>
                <Ionicons name="checkmark-circle-outline" size={20} color="#10b981" />
                <Text style={styles.kpiValue}>{teacherStats?.class_attendance_percentage ?? 91}%</Text>
                <Text style={styles.kpiLabel}>Attendance</Text>
              </TouchableOpacity>

              <TouchableOpacity style={styles.kpiItem} onPress={() => router.push('/(app)/lms')}>
                <Ionicons name="clipboard-outline" size={20} color="#f59e0b" />
                <Text style={styles.kpiValue}>{teacherStats?.pending_assignment_evaluation ?? 6}</Text>
                <Text style={styles.kpiLabel}>Pending</Text>
              </TouchableOpacity>

              <TouchableOpacity style={styles.kpiItem} onPress={() => router.push('/(app)/lms')}>
                <Ionicons name="library-outline" size={20} color="#8b5cf6" />
                <Text style={styles.kpiValue}>{teacherStats?.subject_performance?.length ?? 4}</Text>
                <Text style={styles.kpiLabel}>Courses</Text>
              </TouchableOpacity>
            </>
          ) : isParent ? (
            // PARENT KPIS (For selected child)
            <>
              <TouchableOpacity style={styles.kpiItem} onPress={() => router.push('/(app)/attendance')}>
                <Ionicons name="calendar-outline" size={20} color="#2563eb" />
                <Text style={styles.kpiValue}>
                  {selectedChildProgress?.attendance_percentage ?? 88.5}%
                </Text>
                <Text style={styles.kpiLabel}>Attendance</Text>
              </TouchableOpacity>

              <TouchableOpacity style={styles.kpiItem} onPress={() => router.push('/(app)/fees')}>
                <Ionicons name="wallet-outline" size={20} color="#10b981" />
                <Text style={styles.kpiValue}>
                  ₹{(selectedChildProgress?.total_fee_dues ?? 0).toLocaleString('en-IN')}
                </Text>
                <Text style={styles.kpiLabel}>Fee Dues</Text>
              </TouchableOpacity>

              <TouchableOpacity style={styles.kpiItem} onPress={() => router.push('/(app)/results')}>
                <Ionicons name="ribbon-outline" size={20} color="#8b5cf6" />
                <Text style={styles.kpiValue}>
                  {selectedChildProgress?.latest_exam_score ? `${selectedChildProgress.latest_exam_score}%` : '88.4%'}
                </Text>
                <Text style={styles.kpiLabel}>Term Score</Text>
              </TouchableOpacity>

              <TouchableOpacity style={styles.kpiItem} onPress={() => router.push('/(app)/results')}>
                <Ionicons name="trophy-outline" size={20} color="#f59e0b" />
                <Text style={styles.kpiValue}>
                  {selectedChildProgress?.overall_grade || 'A+'}
                </Text>
                <Text style={styles.kpiLabel}>Grade</Text>
              </TouchableOpacity>
            </>
          ) : (
            // STUDENT KPIS
            <>
              <TouchableOpacity style={styles.kpiItem} onPress={() => router.push('/(app)/attendance')}>
                <Ionicons name="calendar-outline" size={20} color="#2563eb" />
                <Text style={styles.kpiValue}>
                  {studentStats?.attendance_percentage ?? 85}%
                </Text>
                <Text style={styles.kpiLabel}>Attendance</Text>
              </TouchableOpacity>

              <TouchableOpacity style={styles.kpiItem} onPress={() => router.push('/(app)/lms')}>
                <Ionicons name="school-outline" size={20} color="#7c3aed" />
                <Text style={styles.kpiValue}>
                  {studentStats?.assignment_completion?.pending ?? 4}
                </Text>
                <Text style={styles.kpiLabel}>Assignments</Text>
              </TouchableOpacity>

              <TouchableOpacity style={styles.kpiItem} onPress={() => router.push('/(app)/results')}>
                <Ionicons name="ribbon-outline" size={20} color="#8b5cf6" />
                <Text style={styles.kpiValue}>3.8</Text>
                <Text style={styles.kpiLabel}>CGPA</Text>
              </TouchableOpacity>

              <TouchableOpacity style={styles.kpiItem} onPress={() => router.push('/(app)/results')}>
                <Ionicons name="trophy-outline" size={20} color="#f59e0b" />
                <Text style={styles.kpiValue}>2</Text>
                <Text style={styles.kpiLabel}>Achievements</Text>
              </TouchableOpacity>
            </>
          )}
        </View>}

        {/* ── 12 Service Action Cards Grid (3 Rows x 4 Columns) ── */}
        <View style={styles.servicesGrid}>
          {activeServices.map((item, idx) => (
            <TouchableOpacity
              key={idx}
              style={styles.serviceCard}
              onPress={() => router.push(item.route as any)}
              activeOpacity={0.7}
            >
              <View
                style={[
                  styles.serviceIconContainer,
                  { backgroundColor: item.bg, borderColor: item.borderColor },
                ]}
              >
                <Ionicons name={item.icon as any} size={22} color={item.color} />
              </View>
              <Text style={styles.serviceLabel} numberOfLines={2}>
                {item.label}
              </Text>
            </TouchableOpacity>
          ))}
        </View>

        {/* ── Recent Notices / Alerts Section ── */}
        <View style={styles.sectionContainer}>
          <View style={styles.sectionHeader}>
            <Text style={styles.sectionTitle}>
              {isTeacher ? 'Faculty Circulars' : isParent ? 'School Bulletins' : 'Recent Notices'}
            </Text>
            <TouchableOpacity
              onPress={() => router.push('/(app)/notifications')}
              activeOpacity={0.7}
              style={styles.viewAllBtn}
            >
              <Text style={styles.viewAllText}>View All</Text>
              <Ionicons name="chevron-forward" size={14} color="#6366f1" />
            </TouchableOpacity>
          </View>

          <TouchableOpacity
            style={styles.noticeCard}
            onPress={() => router.push('/(app)/notifications')}
            activeOpacity={0.7}
          >
            <View style={styles.noticeIconBox}>
              <Ionicons name="megaphone-outline" size={22} color="#7c3aed" />
            </View>
            <View style={styles.noticeContent}>
              <Text style={styles.noticeTitle}>
                {isTeacher
                  ? 'Semester 4 Internal Marks Entry Deadline'
                  : isParent
                  ? 'Parent-Teacher Meeting (PTM) Scheduled'
                  : 'Mid-Semester Exam Schedule'}
              </Text>
              <Text style={styles.noticeDesc}>
                {isTeacher
                  ? 'All faculty members must finalize mid-term grade books by Friday 05:00 PM.'
                  : isParent
                  ? 'Discuss your ward academic progress in person on March 28 at 10:00 AM.'
                  : 'Exam will be held from Mar 10 – Mar 15, 2025.'}
              </Text>
              <View style={styles.noticeDateRow}>
                <Ionicons name="calendar-outline" size={12} color="#94a3b8" />
                <Text style={styles.noticeDateText}>Feb 28, 2025</Text>
              </View>
            </View>
          </TouchableOpacity>
        </View>

        {/* ── Upcoming Events / Actions Section ── */}
        <View style={styles.sectionContainer}>
          <View style={styles.sectionHeader}>
            <Text style={styles.sectionTitle}>Upcoming Events</Text>
            <TouchableOpacity
              onPress={() => router.push('/(app)/notifications')}
              activeOpacity={0.7}
              style={styles.viewAllBtn}
            >
              <Text style={styles.viewAllText}>View All</Text>
              <Ionicons name="chevron-forward" size={14} color="#6366f1" />
            </TouchableOpacity>
          </View>

          <TouchableOpacity
            style={styles.eventCard}
            onPress={() => router.push('/(app)/notifications')}
            activeOpacity={0.7}
          >
            <View style={styles.eventIconBox}>
              <Ionicons name="calendar-outline" size={22} color="#10b981" />
            </View>
            <View style={styles.eventContent}>
              <Text style={styles.eventTitle}>
                {isTeacher
                  ? 'Academic Council Curriculum Meeting'
                  : isParent
                  ? 'Annual Sports Day & Exhibition 2025'
                  : 'Technical Fest 2025'}
              </Text>
              <Text style={styles.eventDate}>Mar 20 – Mar 22, 2025</Text>
            </View>
            <Ionicons name="chevron-forward" size={18} color="#94a3b8" />
          </TouchableOpacity>
        </View>
      </ScrollView>
    </View>
  )
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f8fafc',
  },
  scrollContent: {
    paddingBottom: 40,
  },

  /* Top Purple Header */
  headerBackground: {
    backgroundColor: '#4338ca',
    borderBottomLeftRadius: 36,
    borderBottomRightRadius: 36,
    paddingHorizontal: 20,
    paddingTop: 10,
    paddingBottom: 46,
    ...theme.shadows.md,
  },
  headerContent: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
  },
  avatarWrapper: {
    width: 58,
    height: 58,
    borderRadius: 29,
    borderWidth: 2.5,
    borderColor: '#ffffff',
    overflow: 'hidden',
    backgroundColor: '#ffffff',
  },
  avatarImage: {
    width: '100%',
    height: '100%',
    borderRadius: 29,
  },
  avatarInner: {
    width: '100%',
    height: '100%',
    backgroundColor: '#6366f1',
    alignItems: 'center',
    justifyContent: 'center',
  },
  avatarText: {
    fontSize: 22,
    fontWeight: '800',
    color: '#ffffff',
  },
  headerUserInfo: {
    flex: 1,
  },
  headerUserName: {
    fontSize: 20,
    fontWeight: '800',
    color: '#ffffff',
    letterSpacing: -0.3,
  },
  headerInstRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    marginTop: 2,
  },
  headerInstName: {
    fontSize: 13,
    fontWeight: '600',
    color: '#ffffff',
    opacity: 0.95,
  },
  headerAcademicMeta: {
    fontSize: 11,
    color: '#c7d2fe',
    fontWeight: '500',
    marginTop: 3,
  },
  notifBellBtn: {
    position: 'relative',
    width: 40,
    height: 40,
    borderRadius: 20,
    alignItems: 'center',
    justifyContent: 'center',
  },
  notifBadge: {
    position: 'absolute',
    top: 4,
    right: 4,
    backgroundColor: '#ef4444',
    width: 17,
    height: 17,
    borderRadius: 8.5,
    alignItems: 'center',
    justifyContent: 'center',
    borderWidth: 1.5,
    borderColor: '#4338ca',
  },
  notifBadgeText: {
    color: '#ffffff',
    fontSize: 9,
    fontWeight: '800',
  },
  childPillsRow: {
    flexDirection: 'row',
    gap: 8,
    marginTop: 14,
    paddingBottom: 4,
  },
  childPill: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    backgroundColor: 'rgba(255, 255, 255, 0.2)',
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 16,
    borderWidth: 1,
    borderColor: 'rgba(255, 255, 255, 0.3)',
  },
  childPillActive: {
    backgroundColor: '#ffffff',
    borderColor: '#ffffff',
  },
  childPillText: {
    fontSize: 12,
    fontWeight: '600',
    color: '#ffffff',
  },
  childPillTextActive: {
    color: '#4338ca',
    fontWeight: '700',
  },

  /* Floating 4-Column KPI Card */
  kpiContainer: {
    flexDirection: 'row',
    backgroundColor: '#ffffff',
    borderRadius: 20,
    marginTop: -26,
    marginHorizontal: 16,
    paddingVertical: 14,
    paddingHorizontal: 6,
    borderWidth: 1,
    borderColor: '#f1f5f9',
    justifyContent: 'space-around',
    shadowColor: '#0f172a',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.07,
    shadowRadius: 12,
    elevation: 3,
  },
  kpiItem: {
    alignItems: 'center',
    flex: 1,
  },
  kpiValue: {
    fontSize: 16,
    fontWeight: '800',
    color: '#0f172a',
    marginTop: 4,
  },
  kpiLabel: {
    fontSize: 11,
    color: '#64748b',
    marginTop: 2,
    fontWeight: '500',
  },

  /* 12 Services Grid (3 Rows x 4 Columns) */
  servicesGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    justifyContent: 'space-between',
    paddingHorizontal: 16,
    marginTop: 18,
  },
  serviceCard: {
    width: '23%',
    backgroundColor: '#ffffff',
    borderRadius: 16,
    paddingVertical: 12,
    paddingHorizontal: 4,
    alignItems: 'center',
    marginBottom: 12,
    borderWidth: 1,
    borderColor: '#f1f5f9',
    shadowColor: '#0f172a',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.04,
    shadowRadius: 6,
    elevation: 1,
  },
  serviceIconContainer: {
    width: 44,
    height: 44,
    borderRadius: 14,
    alignItems: 'center',
    justifyContent: 'center',
    borderWidth: 1,
    marginBottom: 6,
  },
  serviceLabel: {
    fontSize: 11,
    fontWeight: '600',
    color: '#1e293b',
    textAlign: 'center',
    lineHeight: 14,
  },

  /* Sections */
  sectionContainer: {
    paddingHorizontal: 16,
    marginTop: 10,
  },
  sectionHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 12,
  },
  sectionTitle: {
    fontSize: 16,
    fontWeight: '800',
    color: '#0f172a',
    letterSpacing: -0.2,
  },
  viewAllBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 2,
  },
  viewAllText: {
    fontSize: 13,
    fontWeight: '700',
    color: '#6366f1',
  },

  /* Recent Notice Card */
  noticeCard: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#ffffff',
    borderRadius: 16,
    padding: 14,
    borderWidth: 1,
    borderColor: '#f1f5f9',
    gap: 12,
    shadowColor: '#0f172a',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.04,
    shadowRadius: 8,
    elevation: 2,
  },
  noticeIconBox: {
    width: 44,
    height: 44,
    borderRadius: 12,
    backgroundColor: '#f5f3ff',
    borderWidth: 1,
    borderColor: '#ede9fe',
    alignItems: 'center',
    justifyContent: 'center',
  },
  noticeContent: {
    flex: 1,
  },
  noticeTitle: {
    fontSize: 14,
    fontWeight: '700',
    color: '#0f172a',
  },
  noticeDesc: {
    fontSize: 12,
    color: '#64748b',
    marginTop: 2,
    lineHeight: 17,
  },
  noticeDateRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    marginTop: 5,
  },
  noticeDateText: {
    fontSize: 11,
    color: '#94a3b8',
    fontWeight: '500',
  },

  /* Upcoming Event Card */
  eventCard: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#ffffff',
    borderRadius: 16,
    padding: 14,
    borderWidth: 1,
    borderColor: '#f1f5f9',
    shadowColor: '#0f172a',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.04,
    shadowRadius: 8,
    elevation: 2,
  },
  eventIconBox: {
    width: 44,
    height: 44,
    borderRadius: 12,
    backgroundColor: '#ecfdf5',
    borderWidth: 1,
    borderColor: '#d1fae5',
    alignItems: 'center',
    justifyContent: 'center',
  },
  eventContent: {
    flex: 1,
    marginLeft: 12,
  },
  eventTitle: {
    fontSize: 14,
    fontWeight: '700',
    color: '#0f172a',
  },
  eventDate: {
    fontSize: 12,
    color: '#64748b',
    marginTop: 2,
  },
})
