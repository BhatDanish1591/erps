import React, { useEffect } from 'react'
import { Platform, View, StyleSheet } from 'react-native'
import { Tabs, useRouter } from 'expo-router'
import { Ionicons } from '@expo/vector-icons'
import { useAuthStore } from '../../store/authStore'
import { theme } from '../../theme'

const ACTIVE_COLOR = '#6366f1' // Purple accent matching screenshot
const INACTIVE_COLOR = '#94a3b8'

export default function AppLayout() {
  const router = useRouter()
  const { user, is_authenticated, clearAuth } = useAuthStore()

  useEffect(() => {
    if (!is_authenticated) {
      router.replace('/(auth)/login')
      return
    }
    if (user) {
      const rawRole = (user.current_role || user.role || '').toUpperCase()
      const isStudent = rawRole === 'STUDENT'
      const isTeacher = rawRole === 'TEACHER' || rawRole === 'FACULTY'
      const isParent = rawRole === 'PARENT' || rawRole === 'GUARDIAN'
      const isStaffManager = ['INSTITUTION_ADMIN', 'PRINCIPAL', 'HOD'].includes(rawRole)

      if (user.is_superadmin || (!isStudent && !isTeacher && !isParent && !isStaffManager)) {
        clearAuth().then(() => router.replace('/(auth)/login'))
      }
    }
  }, [is_authenticated, user])
  return (
    <Tabs
      screenOptions={{
        headerShown: false,
        tabBarActiveTintColor: ACTIVE_COLOR,
        tabBarInactiveTintColor: INACTIVE_COLOR,
        tabBarStyle: styles.tabBar,
        tabBarLabelStyle: styles.tabBarLabel,
        tabBarItemStyle: styles.tabBarItem,
      }}
    >
      <Tabs.Screen
        name="dashboard"
        options={{
          title: 'Home',
          tabBarIcon: ({ color, focused }) => (
            <Ionicons
              name={focused ? 'home' : 'home-outline'}
              size={23}
              color={focused ? ACTIVE_COLOR : ((color as string) || INACTIVE_COLOR)}
            />
          ),
        }}
      />

      <Tabs.Screen
        name="lms"
        options={{
          title: 'LMS',
          tabBarIcon: ({ color, focused }) => (
            <Ionicons
              name={focused ? 'book' : 'book-outline'}
              size={23}
              color={focused ? ACTIVE_COLOR : ((color as string) || INACTIVE_COLOR)}
            />
          ),
        }}
      />

      <Tabs.Screen
        name="attendance"
        options={{
          title: 'Academics',
          tabBarIcon: ({ color, focused }) => (
            <Ionicons
              name={focused ? 'school' : 'school-outline'}
              size={23}
              color={focused ? ACTIVE_COLOR : ((color as string) || INACTIVE_COLOR)}
            />
          ),
        }}
      />

      <Tabs.Screen
        name="notifications"
        options={{
          title: 'Notifications',
          tabBarIcon: ({ color, focused }) => (
            <View style={{ position: 'relative' }}>
              <Ionicons
                name={focused ? 'notifications' : 'notifications-outline'}
                size={23}
                color={focused ? ACTIVE_COLOR : ((color as string) || INACTIVE_COLOR)}
              />
              <View style={styles.tabBadgeDot} />
            </View>
          ),
        }}
      />

      <Tabs.Screen
        name="profile"
        options={{
          title: 'Profile',
          tabBarIcon: ({ color, focused }) => (
            <Ionicons
              name={focused ? 'person' : 'person-outline'}
              size={23}
              color={focused ? ACTIVE_COLOR : ((color as string) || INACTIVE_COLOR)}
            />
          ),
        }}
      />

      {/* Auxiliary screens kept accessible via router.push() without cluttering bottom bar */}
      <Tabs.Screen
        name="students"
        options={{ href: null, title: 'Students' }}
      />
      <Tabs.Screen
        name="fees"
        options={{
          href: null,
          title: 'Fees',
        }}
      />
      <Tabs.Screen
        name="examinations"
        options={{
          href: null,
          title: 'Examinations',
        }}
      />
      <Tabs.Screen
        name="results"
        options={{
          href: null,
          title: 'Results',
        }}
      />
    </Tabs>
  )
}

const styles = StyleSheet.create({
  tabBar: {
    backgroundColor: '#ffffff',
    borderTopWidth: 1,
    borderTopColor: '#f1f5f9',
    height: Platform.OS === 'ios' ? 86 : 64,
    paddingTop: 8,
    paddingBottom: Platform.OS === 'ios' ? 26 : 8,
    ...theme.shadows.md,
  },
  tabBarItem: {
    paddingVertical: 2,
  },
  tabBarLabel: {
    fontSize: 11,
    fontWeight: '600',
    marginTop: 2,
    letterSpacing: -0.2,
  },
  tabBadgeDot: {
    position: 'absolute',
    top: -1,
    right: -1,
    width: 7,
    height: 7,
    borderRadius: 3.5,
    backgroundColor: '#ef4444',
    borderWidth: 1,
    borderColor: '#ffffff',
  },
})
