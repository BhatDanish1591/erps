import React from 'react'
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
} from 'react-native'
import { SafeAreaView } from 'react-native-safe-area-context'
import { Ionicons } from '@expo/vector-icons'
import { useRouter } from 'expo-router'
import { theme } from '../../theme'

const NOTIFICATIONS_DATA = [
  {
    id: 'notif-1',
    type: 'EXAM',
    title: 'Mid-Semester Exam Schedule',
    desc: 'The finalized timetable for Semester 4 examinations has been released. Exams commence from March 10, 2025.',
    date: 'Today, 10:30 AM',
    read: false,
    icon: 'document-text',
    color: '#3b82f6',
    bg: '#eff6ff',
  },
  {
    id: 'notif-2',
    type: 'EVENT',
    title: 'Technical Fest 2025 Registrations Open',
    desc: 'Hackathons, robotics challenges, and coding competitions are now open for student team registrations.',
    date: 'Yesterday, 04:15 PM',
    read: false,
    icon: 'calendar',
    color: '#10b981',
    bg: '#ecfdf5',
  },
  {
    id: 'notif-3',
    type: 'FEE',
    title: 'Semester Fee Payment Receipt Generated',
    desc: 'Your payment for Term 1 Laboratory and Tuition fees has been processed and credited.',
    date: 'Feb 18, 2025',
    read: true,
    icon: 'wallet',
    color: '#f59e0b',
    bg: '#fffbeb',
  },
  {
    id: 'notif-4',
    type: 'ACADEMIC',
    title: 'Assignment #4 Deadline Reminder',
    desc: 'Complex Variables & Laplace Transforms assignment submission closes on Friday at 11:59 PM.',
    date: 'Feb 15, 2025',
    read: true,
    icon: 'school',
    color: '#7c3aed',
    bg: '#f5f3ff',
  },
]

export default function NotificationsScreen() {
  const router = useRouter()

  return (
    <SafeAreaView style={styles.container}>
      {/* Top Header */}
      <View style={styles.header}>
        <View style={{ flexDirection: 'row', alignItems: 'center', gap: 10 }}>
          <TouchableOpacity
            style={styles.backButton}
            onPress={() => router.push('/(app)/dashboard')}
            hitSlop={{ top: 10, bottom: 10, left: 10, right: 10 }}
          >
            <Ionicons name="arrow-back" size={22} color={theme.colors.textPrimary} />
          </TouchableOpacity>
          <View>
            <Text style={styles.headerTitle}>Notifications</Text>
            <Text style={styles.headerSubtitle}>Announcements & campus alerts</Text>
          </View>
        </View>
        <View style={styles.unreadBadge}>
          <Text style={styles.unreadBadgeText}>2 New</Text>
        </View>
      </View>

      <ScrollView contentContainerStyle={styles.scrollContent} showsVerticalScrollIndicator={false}>
        {NOTIFICATIONS_DATA.map((item) => (
          <View
            key={item.id}
            style={[styles.notifCard, !item.read && styles.notifCardUnread]}
          >
            <View style={[styles.iconBox, { backgroundColor: item.bg }]}>
              <Ionicons name={item.icon as any} size={22} color={item.color} />
            </View>
            <View style={styles.notifBody}>
              <View style={styles.notifTopRow}>
                <Text style={styles.notifTitle} numberOfLines={1}>
                  {item.title}
                </Text>
                {!item.read && <View style={styles.unreadDot} />}
              </View>
              <Text style={styles.notifDesc}>{item.desc}</Text>
              <Text style={styles.notifDate}>{item.date}</Text>
            </View>
          </View>
        ))}
      </ScrollView>
    </SafeAreaView>
  )
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#f8fafc' },
  header: {
    paddingHorizontal: 20,
    paddingVertical: 14,
    backgroundColor: '#ffffff',
    borderBottomWidth: 1,
    borderBottomColor: '#f1f5f9',
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  backButton: { padding: 4 },
  headerTitle: { fontSize: 20, fontWeight: '800', color: '#0f172a', letterSpacing: -0.3 },
  headerSubtitle: { fontSize: 12, color: '#64748b', marginTop: 2 },
  unreadBadge: {
    backgroundColor: '#eff6ff',
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: 20,
    borderWidth: 1,
    borderColor: '#dbeafe',
  },
  unreadBadgeText: { fontSize: 11, fontWeight: '700', color: '#2563eb' },
  scrollContent: { padding: 18, gap: 12 },
  notifCard: {
    flexDirection: 'row',
    backgroundColor: '#ffffff',
    borderRadius: 16,
    padding: 16,
    borderWidth: 1,
    borderColor: '#f1f5f9',
    gap: 14,
    shadowColor: '#0f172a',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.04,
    shadowRadius: 8,
    elevation: 2,
  },
  notifCardUnread: {
    borderColor: '#e0e7ff',
    backgroundColor: '#ffffff',
  },
  iconBox: {
    width: 44,
    height: 44,
    borderRadius: 14,
    alignItems: 'center',
    justifyContent: 'center',
  },
  notifBody: { flex: 1 },
  notifTopRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 4,
  },
  notifTitle: { fontSize: 14, fontWeight: '700', color: '#0f172a', flex: 1 },
  unreadDot: {
    width: 8,
    height: 8,
    borderRadius: 4,
    backgroundColor: '#ef4444',
    marginLeft: 6,
  },
  notifDesc: { fontSize: 12, color: '#475569', lineHeight: 18, marginBottom: 8 },
  notifDate: { fontSize: 11, color: '#94a3b8', fontWeight: '500' },
})
