import React, { useState } from 'react'
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  ScrollView,
  ActivityIndicator,
} from 'react-native'
import { useRouter } from 'expo-router'
import { SafeAreaView } from 'react-native-safe-area-context'
import { Ionicons } from '@expo/vector-icons'
import { useAuthStore } from '../../store/authStore'

export default function SelectInstitutionScreen() {
  const router = useRouter()
  const { user, switchInstitution } = useAuthStore()
  const [loadingTenant, setLoadingTenant] = useState<string | null>(null)
  const [errorMsg, setErrorMsg] = useState<string | null>(null)

  const handleSelect = async (tenantId: string) => {
    try {
      setLoadingTenant(tenantId)
      setErrorMsg(null)
      await switchInstitution(tenantId)
      router.replace('/(app)/dashboard')
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to switch institution.')
    } finally {
      setLoadingTenant(null)
    }
  }

  const institutions = user?.institutions || []

  return (
    <SafeAreaView style={styles.container}>
      <ScrollView contentContainerStyle={styles.content}>
        <View style={styles.header}>
          <Text style={styles.title}>Select Institution</Text>
          <Text style={styles.subtitle}>
            Your account is associated with multiple campuses. Select your target institution to proceed.
          </Text>
        </View>

        {errorMsg && (
          <View style={styles.errorBox}>
            <Ionicons name="alert-circle" size={20} color="#ef4444" />
            <Text style={styles.errorText}>{errorMsg}</Text>
          </View>
        )}

        <View style={styles.cardList}>
          {institutions.map((inst) => {
            const isSelected = inst.tenant_id === user?.tenant_id
            const isLoadingThis = loadingTenant === inst.tenant_id

            return (
              <TouchableOpacity
                key={inst.tenant_id}
                style={[
                  styles.instCard,
                  isSelected && styles.instCardActive,
                ]}
                onPress={() => handleSelect(inst.tenant_id)}
                disabled={Boolean(loadingTenant)}
              >
                <View style={styles.instIconBadge}>
                  <Ionicons
                    name={inst.institution_type === 'COLLEGE' ? 'business' : 'school'}
                    size={28}
                    color="#2563eb"
                  />
                </View>

                <View style={styles.instInfo}>
                  <Text style={styles.instName}>{inst.institution_name}</Text>
                  <View style={styles.badgeRow}>
                    <View style={styles.roleTag}>
                      <Text style={styles.roleTagText}>{inst.role_name || inst.role_code}</Text>
                    </View>
                    <View style={styles.typeTag}>
                      <Text style={styles.typeTagText}>{inst.institution_type}</Text>
                    </View>
                  </View>
                </View>

                {isLoadingThis ? (
                  <ActivityIndicator color="#2563eb" />
                ) : (
                  <Ionicons name="chevron-forward" size={22} color="#94a3b8" />
                )}
              </TouchableOpacity>
            )
          })}
        </View>
      </ScrollView>
    </SafeAreaView>
  )
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#f8fafc' },
  content: { padding: 24 },
  header: { marginBottom: 24 },
  title: { fontSize: 26, fontWeight: '800', color: '#0f172a', marginBottom: 8 },
  subtitle: { fontSize: 14, color: '#64748b', lineHeight: 20 },
  errorBox: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#fef2f2',
    borderWidth: 1,
    borderColor: '#fecaca',
    borderRadius: 10,
    padding: 12,
    marginBottom: 20,
    gap: 8,
  },
  errorText: { color: '#b91c1c', fontSize: 13, flex: 1 },
  cardList: { gap: 14 },
  instCard: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#ffffff',
    borderRadius: 14,
    padding: 16,
    borderWidth: 1.5,
    borderColor: '#e2e8f0',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.05,
    shadowRadius: 6,
    elevation: 1,
  },
  instCardActive: {
    borderColor: '#2563eb',
    backgroundColor: '#eff6ff',
  },
  instIconBadge: {
    width: 52,
    height: 52,
    borderRadius: 14,
    backgroundColor: '#dbeafe',
    justifyContent: 'center',
    alignItems: 'center',
    marginRight: 14,
  },
  instInfo: { flex: 1 },
  instName: { fontSize: 16, fontWeight: '700', color: '#0f172a', marginBottom: 6 },
  badgeRow: { flexDirection: 'row', gap: 6 },
  roleTag: {
    backgroundColor: '#ede9fe',
    borderRadius: 6,
    paddingVertical: 2,
    paddingHorizontal: 8,
  },
  roleTagText: { fontSize: 11, fontWeight: '700', color: '#7c3aed' },
  typeTag: {
    backgroundColor: '#f1f5f9',
    borderRadius: 6,
    paddingVertical: 2,
    paddingHorizontal: 8,
  },
  typeTagText: { fontSize: 11, fontWeight: '600', color: '#475569' },
})
