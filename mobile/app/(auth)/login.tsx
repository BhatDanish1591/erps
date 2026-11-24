import React, { useState } from 'react'
import {
  View,
  Text,
  StyleSheet,
  TextInput,
  TouchableOpacity,
  ActivityIndicator,
  KeyboardAvoidingView,
  Platform,
  ScrollView,
} from 'react-native'
import { useRouter } from 'expo-router'
import { SafeAreaView } from 'react-native-safe-area-context'
import { Ionicons } from '@expo/vector-icons'
import { mobileAuthApi } from '../../api/auth'
import { useAuthStore, AuthUser, UserRole } from '../../store/authStore'
import { theme } from '../../theme'

const DEMO_PRESETS = [
  { label: 'Student', role: 'STUDENT', email: 'student@apex.edu', icon: 'school-outline' },
  { label: 'Teacher', role: 'TEACHER', email: 'teacher@apex.edu', icon: 'person-outline' },
  { label: 'Parent', role: 'PARENT', email: 'parent@apex.edu', icon: 'people-outline' },
]

export default function LoginScreen() {
  const router = useRouter()
  const { setAuth } = useAuthStore()

  const [identifier, setIdentifier] = useState('student@apex.edu')
  const [password, setPassword] = useState('Password123!')
  const [showPassword, setShowPassword] = useState(false)
  const [loading, setLoading] = useState(false)
  const [errorMsg, setErrorMsg] = useState<string | null>(null)
  const [activePreset, setActivePreset] = useState<string>('Student')

  const applyPreset = (preset: typeof DEMO_PRESETS[0]) => {
    setActivePreset(preset.label)
    setIdentifier(preset.email)
    setPassword('Password123!')
    setErrorMsg(null)
  }

  const handleLogin = async () => {
    if (!identifier.trim() || !password) {
      setErrorMsg('Please enter both your email/phone and password.')
      return
    }

    try {
      setLoading(true)
      setErrorMsg(null)
      const response = await mobileAuthApi.login({
        identifier: identifier.trim(),
        password,
      })

      const data = (response as any)?.data ?? response
      const user = data?.user

      if (!user) {
        throw new Error('Authentication succeeded but user profile was not returned.')
      }

      const rawRole = (user.current_role || (user.is_superadmin ? 'SUPER_ADMIN' : 'STUDENT')).toUpperCase()
      const isStudent = rawRole === 'STUDENT'
      const isTeacher = rawRole === 'TEACHER' || rawRole === 'FACULTY'
      const isParent = rawRole === 'PARENT' || rawRole === 'GUARDIAN'

      const isStaffManager = ['INSTITUTION_ADMIN', 'PRINCIPAL', 'HOD'].includes(rawRole)
      const needsInstitution = !user.current_tenant_id && user.institutions?.length > 0
      if (user.is_superadmin || (!needsInstitution && !isStudent && !isTeacher && !isParent && !isStaffManager)) {
        throw new Error(
          'Mobile app access is exclusively for Students, Teachers, and Parents. Administrative accounts must use the Web Portal.'
        )
      }

      const normalizedRole = rawRole as UserRole
      const normalizedUser: AuthUser = {
        ...user,
        role: normalizedRole,
        tenant_id: user.current_tenant_id || null,
      }

      await setAuth(
        normalizedUser,
        data.access_token,
        data.refresh_token,
        user.current_tenant_id || undefined
      )

      if (!user.current_tenant_id && user.institutions && user.institutions.length > 0) {
        router.replace('/(auth)/select-institution')
      } else {
        router.replace('/(app)/dashboard')
      }
    } catch (err: any) {
      setErrorMsg(err.message || 'Invalid credentials. Please verify your email & password.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <SafeAreaView style={styles.container}>
      <KeyboardAvoidingView
        behavior={Platform.OS === 'ios' ? 'padding' : undefined}
        style={{ flex: 1 }}
      >
        <ScrollView
          contentContainerStyle={styles.scrollContent}
          keyboardShouldPersistTaps="handled"
          showsVerticalScrollIndicator={false}
        >
          {/* Brand Header */}
          <View style={styles.brandContainer}>
            <View style={styles.logoBadge}>
              <Ionicons name="school" size={34} color="#ffffff" />
            </View>
            <Text style={styles.title}>EduSaaS Mobile</Text>
            <Text style={styles.subtitle}>Unified Student, Faculty & Parent Portal</Text>
          </View>

          {/* Quick Demo Role Selector */}
          <View style={styles.presetsCard}>
            <Text style={styles.presetHeading}>⚡ Quick Demo Sign In</Text>
            <ScrollView
              horizontal
              showsHorizontalScrollIndicator={false}
              contentContainerStyle={styles.presetPillsRow}
            >
              {DEMO_PRESETS.map((p) => {
                const isActive = activePreset === p.label
                return (
                  <TouchableOpacity
                    key={p.label}
                    onPress={() => applyPreset(p)}
                    activeOpacity={0.7}
                    style={[styles.presetPill, isActive && styles.presetPillActive]}
                  >
                    <Ionicons
                      name={p.icon as any}
                      size={14}
                      color={isActive ? '#ffffff' : theme.colors.primary}
                    />
                    <Text style={[styles.presetPillText, isActive && styles.presetPillTextActive]}>
                      {p.label}
                    </Text>
                  </TouchableOpacity>
                )
              })}
            </ScrollView>
          </View>

          {/* Error Alert */}
          {errorMsg && (
            <View style={styles.errorBox}>
              <Ionicons name="alert-circle" size={20} color={theme.colors.danger} />
              <Text style={styles.errorText}>{errorMsg}</Text>
            </View>
          )}

          {/* Form Card */}
          <View style={styles.formCard}>
            <Text style={styles.inputLabel}>Institutional Email / User ID</Text>
            <View style={styles.inputWrapper}>
              <Ionicons name="mail-outline" size={19} color={theme.colors.textMuted} style={styles.inputIcon} />
              <TextInput
                style={styles.input}
                placeholder="student@apex.edu"
                placeholderTextColor={theme.colors.textLight}
                autoCapitalize="none"
                keyboardType="email-address"
                value={identifier}
                onChangeText={(val) => {
                  setIdentifier(val)
                  setActivePreset('')
                }}
              />
            </View>

            <Text style={[styles.inputLabel, { marginTop: 14 }]}>Password</Text>
            <View style={styles.inputWrapper}>
              <Ionicons name="lock-closed-outline" size={19} color={theme.colors.textMuted} style={styles.inputIcon} />
              <TextInput
                style={styles.input}
                placeholder="Enter account password"
                placeholderTextColor={theme.colors.textLight}
                secureTextEntry={!showPassword}
                value={password}
                onChangeText={setPassword}
              />
              <TouchableOpacity
                onPress={() => setShowPassword(!showPassword)}
                style={styles.eyeBtn}
                hitSlop={{ top: 10, bottom: 10, left: 10, right: 10 }}
              >
                <Ionicons
                  name={showPassword ? 'eye-off-outline' : 'eye-outline'}
                  size={19}
                  color={theme.colors.textMuted}
                />
              </TouchableOpacity>
            </View>

            {/* Links Row */}
            <View style={styles.forgotRow}>
              <TouchableOpacity onPress={() => router.push('/(auth)/otp-verify')}>
                <Text style={styles.linkText}>Sign in with OTP</Text>
              </TouchableOpacity>
              <TouchableOpacity onPress={() => router.push('/(auth)/forgot-password')}>
                <Text style={styles.linkText}>Forgot password?</Text>
              </TouchableOpacity>
            </View>

            {/* Submit Button */}
            <TouchableOpacity
              style={[styles.button, loading && styles.buttonDisabled]}
              onPress={handleLogin}
              disabled={loading}
              activeOpacity={0.8}
            >
              {loading ? (
                <ActivityIndicator color="#ffffff" size="small" />
              ) : (
                <View style={styles.buttonContent}>
                  <Text style={styles.buttonText}>Continue to Portal</Text>
                  <Ionicons name="arrow-forward" size={18} color="#ffffff" />
                </View>
              )}
            </TouchableOpacity>
          </View>

          {/* Trust & Security Badge */}
          <View style={styles.securityFooter}>
            <Ionicons name="shield-checkmark" size={15} color={theme.colors.emerald} />
            <Text style={styles.securityText}>End-to-End Encrypted Session · ISO 27001 Certified</Text>
          </View>
        </ScrollView>
      </KeyboardAvoidingView>
    </SafeAreaView>
  )
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: theme.colors.background,
  },
  scrollContent: {
    paddingHorizontal: 22,
    paddingVertical: 20,
    justifyContent: 'center',
    minHeight: '100%',
  },
  brandContainer: {
    alignItems: 'center',
    marginBottom: 20,
  },
  logoBadge: {
    width: 66,
    height: 66,
    borderRadius: 20,
    backgroundColor: theme.colors.primary,
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: 12,
    ...theme.shadows.glow(theme.colors.primary),
  },
  title: {
    fontSize: 26,
    fontWeight: '800',
    color: theme.colors.textPrimary,
    letterSpacing: -0.5,
  },
  subtitle: {
    fontSize: 13,
    color: theme.colors.textMuted,
    marginTop: 4,
    fontWeight: '500',
  },
  presetsCard: {
    backgroundColor: theme.colors.surface,
    borderRadius: theme.radii.md,
    padding: 14,
    marginBottom: 16,
    borderWidth: 1,
    borderColor: theme.colors.border,
    ...theme.shadows.sm,
  },
  presetHeading: {
    fontSize: 12,
    fontWeight: '700',
    color: theme.colors.textSecondary,
    marginBottom: 10,
    textTransform: 'uppercase',
    letterSpacing: 0.5,
  },
  presetPillsRow: {
    gap: 8,
    paddingRight: 8,
  },
  presetPill: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    backgroundColor: theme.colors.primary50,
    paddingHorizontal: 12,
    paddingVertical: 8,
    borderRadius: theme.radii.full,
    borderWidth: 1,
    borderColor: theme.colors.primary100,
  },
  presetPillActive: {
    backgroundColor: theme.colors.primary,
    borderColor: theme.colors.primary,
  },
  presetPillText: {
    fontSize: 12,
    fontWeight: '600',
    color: theme.colors.primaryDark,
  },
  presetPillTextActive: {
    color: '#ffffff',
  },
  errorBox: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: theme.colors.rose50,
    borderWidth: 1,
    borderColor: theme.colors.rose100,
    borderRadius: theme.radii.sm,
    padding: 12,
    marginBottom: 16,
    gap: 8,
  },
  errorText: {
    color: theme.colors.danger,
    fontSize: 13,
    flex: 1,
    fontWeight: '500',
  },
  formCard: {
    backgroundColor: theme.colors.surface,
    borderRadius: theme.radii.lg,
    padding: 22,
    borderWidth: 1,
    borderColor: theme.colors.border,
    ...theme.shadows.md,
  },
  inputLabel: {
    fontSize: 13,
    fontWeight: '600',
    color: theme.colors.textSecondary,
    marginBottom: 7,
  },
  inputWrapper: {
    flexDirection: 'row',
    alignItems: 'center',
    borderWidth: 1.5,
    borderColor: theme.colors.border,
    borderRadius: theme.radii.md,
    paddingHorizontal: 14,
    backgroundColor: theme.colors.surfaceSubtle,
    height: 50,
  },
  inputIcon: {
    marginRight: 10,
  },
  input: {
    flex: 1,
    fontSize: 15,
    color: theme.colors.textPrimary,
    fontWeight: '500',
  },
  eyeBtn: {
    padding: 6,
  },
  forgotRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginTop: 14,
    marginBottom: 20,
  },
  linkText: {
    fontSize: 13,
    color: theme.colors.primary,
    fontWeight: '600',
  },
  button: {
    backgroundColor: theme.colors.primary,
    borderRadius: theme.radii.md,
    height: 50,
    justifyContent: 'center',
    alignItems: 'center',
    ...theme.shadows.glow(theme.colors.primary),
  },
  buttonDisabled: {
    opacity: 0.65,
  },
  buttonContent: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  buttonText: {
    color: '#ffffff',
    fontWeight: '700',
    fontSize: 15,
    letterSpacing: -0.2,
  },
  securityFooter: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 6,
    marginTop: 22,
  },
  securityText: {
    fontSize: 11,
    color: theme.colors.textMuted,
    fontWeight: '500',
  },
})
