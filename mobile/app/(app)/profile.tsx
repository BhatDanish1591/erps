import React, { useState } from 'react'
import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  ScrollView,
  Alert,
} from 'react-native'
import { SafeAreaView } from 'react-native-safe-area-context'
import { useRouter } from 'expo-router'
import { Ionicons } from '@expo/vector-icons'
import { useAuthStore } from '@/store/authStore'
import { theme } from '../../theme'

export default function ProfileScreen() {
  const { user, clearAuth, switchInstitution } = useAuthStore()
  const router = useRouter()
  const [activeTab, setActiveTab] = useState<'id_card' | 'details' | 'institutions'>('id_card')

  const handleLogout = async () => {
    Alert.alert('Confirm Sign Out', 'Are you sure you want to log out of your session?', [
      { text: 'Cancel', style: 'cancel' },
      {
        text: 'Sign Out',
        style: 'destructive',
        onPress: async () => {
          await clearAuth()
          router.replace('/(auth)/login')
        },
      },
    ])
  }

  const handleSwitchInstitution = async (tenantId: string, instName: string) => {
    try {
      await switchInstitution(tenantId)
      Alert.alert('Switched Institution', `Active campus switched to ${instName}`)
    } catch {
      Alert.alert('Switch Error', 'Failed to switch active institution.')
    }
  }

  const activeInstitution = user?.institutions?.find(
    (i) => i.tenant_id === (user.current_tenant_id || user.tenant_id)
  )

  return (
    <SafeAreaView style={styles.container}>
      <ScrollView contentContainerStyle={styles.scrollContent}>
        {/* Header Profile Info */}
        <View style={styles.header}>
          <View style={styles.avatar}>
            <Text style={styles.avatarText}>
              {user?.full_name ? user.full_name.charAt(0).toUpperCase() : 'U'}
            </Text>
          </View>
          <Text style={styles.name}>{user?.full_name ?? 'User Profile'}</Text>
          <Text style={styles.email}>{user?.email ?? 'user@campus.internal'}</Text>
          <View style={styles.roleBadge}>
            <Text style={styles.roleText}>{user?.role ?? 'STUDENT'}</Text>
          </View>
          {activeInstitution && (
            <Text style={styles.institutionHeaderTag}>
              🏛️ {activeInstitution.institution_name}
            </Text>
          )}
        </View>

        {/* Tab Toggle */}
        <View style={styles.tabContainer}>
          <TouchableOpacity
            style={[styles.tabButton, activeTab === 'id_card' && styles.activeTabButton]}
            onPress={() => setActiveTab('id_card')}
          >
            <Text style={[styles.tabText, activeTab === 'id_card' && styles.activeTabText]}>
              Digital ID
            </Text>
          </TouchableOpacity>
          <TouchableOpacity
            style={[styles.tabButton, activeTab === 'details' && styles.activeTabButton]}
            onPress={() => setActiveTab('details')}
          >
            <Text style={[styles.tabText, activeTab === 'details' && styles.activeTabText]}>
              Details
            </Text>
          </TouchableOpacity>
          <TouchableOpacity
            style={[styles.tabButton, activeTab === 'institutions' && styles.activeTabButton]}
            onPress={() => setActiveTab('institutions')}
          >
            <Text style={[styles.tabText, activeTab === 'institutions' && styles.activeTabText]}>
              Campuses ({user?.institutions?.length || 1})
            </Text>
          </TouchableOpacity>
        </View>

        {/* Tab 1: Digital ID Card */}
        {activeTab === 'id_card' && (
          <View style={styles.idCard}>
            <View style={styles.idCardHeader}>
              <Text style={styles.idCardInst}>
                {activeInstitution?.institution_name || 'CAMPUS SaaS CRM'}
              </Text>
              <Text style={styles.idCardSub}>OFFICIAL STUDENT / MEMBER ID</Text>
            </View>
            <View style={styles.idCardBody}>
              <View style={styles.idRow}>
                <Text style={styles.idLabel}>Member Name:</Text>
                <Text style={styles.idValue}>{user?.full_name}</Text>
              </View>
              <View style={styles.idRow}>
                <Text style={styles.idLabel}>Admission / ID No:</Text>
                <Text style={styles.idValue}>ADM-2026-0042</Text>
              </View>
              <View style={styles.idRow}>
                <Text style={styles.idLabel}>Role / Designation:</Text>
                <Text style={styles.idValue}>{user?.role}</Text>
              </View>
              <View style={styles.idRow}>
                <Text style={styles.idLabel}>Academic Session:</Text>
                <Text style={styles.idValue}>AY 2026-2027</Text>
              </View>
              <View style={styles.idRow}>
                <Text style={styles.idLabel}>Status:</Text>
                <Text style={[styles.idValue, { color: '#16a34a' }]}>ACTIVE</Text>
              </View>
            </View>
            <View style={styles.idCardFooter}>
              <Text style={styles.barcodeText}>||| | |||| | ||| |||| |</Text>
            </View>
          </View>
        )}

        {/* Tab 2: Profile Details */}
        {activeTab === 'details' && (
          <View style={styles.detailsCard}>
            <Text style={styles.sectionTitle}>Account & Guardian Information</Text>
            <View style={styles.detailRow}>
              <Text style={styles.detailLabel}>Email Address:</Text>
              <Text style={styles.detailVal}>{user?.email}</Text>
            </View>
            <View style={styles.detailRow}>
              <Text style={styles.detailLabel}>Mobile Phone:</Text>
              <Text style={styles.detailVal}>{user?.phone || '+91 98765 43210'}</Text>
            </View>
            <View style={styles.detailRow}>
              <Text style={styles.detailLabel}>Parent / Guardian:</Text>
              <Text style={styles.detailVal}>Rajesh Sharma</Text>
            </View>
            <View style={styles.detailRow}>
              <Text style={styles.detailLabel}>Tenant ID:</Text>
              <Text style={styles.detailVal}>{user?.current_tenant_id || user?.tenant_id || 'Global'}</Text>
            </View>
            <View style={styles.detailRow}>
              <Text style={styles.detailLabel}>Security Sync:</Text>
              <Text style={[styles.detailVal, { color: '#16a34a' }]}>FCM Push Active</Text>
            </View>
          </View>
        )}

        {/* Tab 3: Multi-Institution Switching */}
        {activeTab === 'institutions' && (
          <View style={styles.institutionsList}>
            <Text style={styles.sectionTitle}>Linked Institutions & Campuses</Text>
            {user?.institutions && user.institutions.length > 0 ? (
              user.institutions.map((inst) => {
                const isActive = inst.tenant_id === (user.current_tenant_id || user.tenant_id)
                return (
                  <TouchableOpacity
                    key={inst.tenant_id}
                    style={[
                      styles.instCard,
                      isActive && styles.instCardActive,
                    ]}
                    onPress={() => handleSwitchInstitution(inst.tenant_id, inst.institution_name)}
                  >
                    <View style={{ flex: 1 }}>
                      <Text style={[styles.instName, isActive && { color: '#2563eb' }]}>
                        {inst.institution_name}
                      </Text>
                      <Text style={styles.instMeta}>
                        Type: {inst.institution_type} • Role: {inst.role_name || inst.role_code}
                      </Text>
                    </View>
                    {isActive ? (
                      <View style={styles.activePill}>
                        <Ionicons name="checkmark-circle" size={16} color="#16a34a" />
                        <Text style={styles.activePillText}>Current</Text>
                      </View>
                    ) : (
                      <Ionicons name="chevron-forward" size={18} color="#94a3b8" />
                    )}
                  </TouchableOpacity>
                )
              })
            ) : (
              <View style={styles.instCard}>
                <Text style={styles.instName}>Standard Single Campus Tenant</Text>
              </View>
            )}
          </View>
        )}

        {/* Log Out Button */}
        <TouchableOpacity style={styles.logoutBtn} onPress={handleLogout}>
          <Ionicons name="log-out-outline" size={18} color="#dc2626" />
          <Text style={styles.logoutText}>Sign Out</Text>
        </TouchableOpacity>
      </ScrollView>
    </SafeAreaView>
  )
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: theme.colors.background },
  scrollContent: { padding: 18, alignItems: 'center', paddingBottom: 40 },
  header: { alignItems: 'center', marginBottom: 22, width: '100%' },
  avatar: {
    width: 76,
    height: 76,
    borderRadius: 38,
    backgroundColor: theme.colors.primary,
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: 12,
    ...theme.shadows.glow(theme.colors.primary),
  },
  avatarText: { fontSize: 28, color: '#ffffff', fontWeight: '800' },
  name: { fontSize: 22, fontWeight: '800', color: theme.colors.textPrimary, letterSpacing: -0.4 },
  email: { fontSize: 13, color: theme.colors.textMuted, marginTop: 2, fontWeight: '500' },
  roleBadge: {
    marginTop: 8,
    paddingHorizontal: 12,
    paddingVertical: 4,
    backgroundColor: theme.colors.primary50,
    borderRadius: theme.radii.full,
    borderWidth: 1,
    borderColor: theme.colors.primary100,
  },
  roleText: { color: theme.colors.primaryDark, fontSize: 11, fontWeight: '700', textTransform: 'uppercase' },
  institutionHeaderTag: {
    marginTop: 6,
    fontSize: 12,
    color: theme.colors.textSecondary,
    fontWeight: '600',
  },

  tabContainer: {
    flexDirection: 'row',
    backgroundColor: theme.colors.surfaceSubtle,
    borderRadius: theme.radii.md,
    padding: 4,
    marginBottom: 20,
    width: '100%',
    borderWidth: 1,
    borderColor: theme.colors.border,
  },
  tabButton: {
    flex: 1,
    paddingVertical: 8,
    alignItems: 'center',
    borderRadius: theme.radii.sm,
  },
  activeTabButton: {
    backgroundColor: theme.colors.surface,
    ...theme.shadows.sm,
  },
  tabText: { fontSize: 12, fontWeight: '600', color: theme.colors.textMuted },
  activeTabText: { color: theme.colors.textPrimary, fontWeight: '700' },

  idCard: {
    width: '100%',
    backgroundColor: theme.colors.surface,
    borderRadius: theme.radii.lg,
    borderWidth: 1,
    borderColor: theme.colors.border,
    overflow: 'hidden',
    ...theme.shadows.md,
  },
  idCardHeader: {
    backgroundColor: theme.colors.primary,
    paddingVertical: 16,
    paddingHorizontal: 16,
    alignItems: 'center',
  },
  idCardInst: { color: '#ffffff', fontSize: 16, fontWeight: '800', letterSpacing: 0.5 },
  idCardSub: { color: theme.colors.primary100, fontSize: 11, fontWeight: '700', marginTop: 2, letterSpacing: 0.8 },
  idCardBody: { padding: 18 },
  idRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    paddingVertical: 8,
    borderBottomWidth: 1,
    borderBottomColor: theme.colors.borderSubtle,
  },
  idLabel: { fontSize: 13, color: theme.colors.textMuted, fontWeight: '500' },
  idValue: { fontSize: 13, color: theme.colors.textPrimary, fontWeight: '700' },
  idCardFooter: {
    padding: 14,
    backgroundColor: theme.colors.surfaceSubtle,
    borderTopWidth: 1,
    borderTopColor: theme.colors.borderSubtle,
    alignItems: 'center',
  },
  barcodeText: { fontFamily: 'monospace', letterSpacing: 3, fontSize: 13, color: theme.colors.textSecondary },

  detailsCard: {
    width: '100%',
    backgroundColor: theme.colors.surface,
    borderRadius: theme.radii.lg,
    padding: 18,
    borderWidth: 1,
    borderColor: theme.colors.border,
    ...theme.shadows.sm,
  },
  sectionTitle: { fontSize: 15, fontWeight: '700', color: theme.colors.textPrimary, marginBottom: 12 },
  detailRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    paddingVertical: 10,
    borderBottomWidth: 1,
    borderBottomColor: theme.colors.borderSubtle,
  },
  detailLabel: { fontSize: 13, color: theme.colors.textMuted },
  detailVal: { fontSize: 13, fontWeight: '600', color: theme.colors.textPrimary },

  institutionsList: {
    width: '100%',
  },
  instCard: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    backgroundColor: theme.colors.surface,
    padding: 16,
    borderRadius: theme.radii.md,
    borderWidth: 1,
    borderColor: theme.colors.border,
    marginBottom: 10,
    ...theme.shadows.sm,
  },
  instCardActive: {
    borderColor: theme.colors.primary,
    backgroundColor: theme.colors.primary50,
  },
  instName: { fontSize: 14, fontWeight: '700', color: theme.colors.textPrimary },
  instMeta: { fontSize: 12, color: theme.colors.textMuted, marginTop: 2 },
  activePill: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    backgroundColor: theme.colors.emerald50,
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: theme.radii.xs,
  },
  activePillText: { fontSize: 11, fontWeight: '700', color: theme.colors.emerald },

  logoutBtn: {
    marginTop: 28,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
    backgroundColor: theme.colors.rose50,
    borderWidth: 1,
    borderColor: theme.colors.rose100,
    paddingVertical: 14,
    paddingHorizontal: 40,
    borderRadius: theme.radii.md,
    width: '100%',
  },
  logoutText: { color: theme.colors.danger, fontWeight: '700', fontSize: 14 },
})