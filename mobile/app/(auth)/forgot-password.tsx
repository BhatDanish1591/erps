import React, { useState } from 'react'
import {
  View,
  Text,
  StyleSheet,
  TextInput,
  TouchableOpacity,
  ActivityIndicator,
} from 'react-native'
import { useRouter } from 'expo-router'
import { SafeAreaView } from 'react-native-safe-area-context'
import { Ionicons } from '@expo/vector-icons'
import { mobileAuthApi } from '../../api/auth'

export default function ForgotPasswordScreen() {
  const router = useRouter()
  const [email, setEmail] = useState('')
  const [loading, setLoading] = useState(false)
  const [statusMsg, setStatusMsg] = useState<{ type: 'success' | 'error'; text: string } | null>(null)

  const handleSendReset = async () => {
    if (!email.trim()) {
      setStatusMsg({ type: 'error', text: 'Please enter your registered email address.' })
      return
    }

    try {
      setLoading(true)
      setStatusMsg(null)
      const res = await mobileAuthApi.forgotPassword(email.trim())
      setStatusMsg({
        type: 'success',
        text: res.message || 'Password reset instructions dispatched to your inbox.',
      })
    } catch (err: any) {
      setStatusMsg({
        type: 'error',
        text: err.message || 'Unable to process request. Please check email address.',
      })
    } finally {
      setLoading(false)
    }
  }

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.content}>
        <TouchableOpacity style={styles.backBtn} onPress={() => router.back()}>
          <Ionicons name="arrow-back" size={24} color="#0f172a" />
        </TouchableOpacity>

        <View style={styles.header}>
          <Text style={styles.title}>Password Recovery</Text>
          <Text style={styles.subtitle}>
            Enter the email associated with your institution profile to receive reset instructions.
          </Text>
        </View>

        {statusMsg && (
          <View
            style={[
              styles.msgBox,
              statusMsg.type === 'success' ? styles.successBox : styles.errorBox,
            ]}
          >
            <Ionicons
              name={statusMsg.type === 'success' ? 'checkmark-circle' : 'alert-circle'}
              size={20}
              color={statusMsg.type === 'success' ? '#16a34a' : '#ef4444'}
            />
            <Text
              style={[
                styles.msgText,
                statusMsg.type === 'success' ? styles.successText : styles.errorText,
              ]}
            >
              {statusMsg.text}
            </Text>
          </View>
        )}

        <View style={styles.formCard}>
          <Text style={styles.inputLabel}>Registered Email</Text>
          <View style={styles.inputWrapper}>
            <Ionicons name="mail-outline" size={20} color="#64748b" style={styles.inputIcon} />
            <TextInput
              style={styles.input}
              placeholder="user@sterling.edu"
              placeholderTextColor="#94a3b8"
              autoCapitalize="none"
              keyboardType="email-address"
              value={email}
              onChangeText={setEmail}
            />
          </View>

          <TouchableOpacity
            style={[styles.button, loading && styles.buttonDisabled]}
            onPress={handleSendReset}
            disabled={loading}
          >
            {loading ? (
              <ActivityIndicator color="#ffffff" />
            ) : (
              <Text style={styles.buttonText}>Send Reset Link</Text>
            )}
          </TouchableOpacity>
        </View>

        <TouchableOpacity style={styles.backLoginRow} onPress={() => router.replace('/(auth)/login')}>
          <Text style={styles.backLoginText}>Remember your password? Sign in</Text>
        </TouchableOpacity>
      </View>
    </SafeAreaView>
  )
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#f8fafc' },
  content: { flex: 1, padding: 24, justifyContent: 'center' },
  backBtn: { position: 'absolute', top: 20, left: 24, zIndex: 10 },
  header: { marginBottom: 24 },
  title: { fontSize: 26, fontWeight: '800', color: '#0f172a', marginBottom: 8 },
  subtitle: { fontSize: 14, color: '#64748b', lineHeight: 20 },
  msgBox: {
    flexDirection: 'row',
    alignItems: 'center',
    borderRadius: 10,
    padding: 12,
    marginBottom: 20,
    gap: 8,
  },
  successBox: { backgroundColor: '#f0fdf4', borderWidth: 1, borderColor: '#bbf7d0' },
  errorBox: { backgroundColor: '#fef2f2', borderWidth: 1, borderColor: '#fecaca' },
  msgText: { fontSize: 13, flex: 1 },
  successText: { color: '#15803d' },
  errorText: { color: '#b91c1c' },
  formCard: {
    backgroundColor: '#ffffff',
    borderRadius: 16,
    padding: 24,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.05,
    shadowRadius: 10,
    elevation: 2,
  },
  inputLabel: { fontSize: 13, fontWeight: '600', color: '#334155', marginBottom: 8 },
  inputWrapper: {
    flexDirection: 'row',
    alignItems: 'center',
    borderWidth: 1,
    borderColor: '#e2e8f0',
    borderRadius: 10,
    paddingHorizontal: 12,
    backgroundColor: '#f8fafc',
    marginBottom: 20,
    height: 48,
  },
  inputIcon: { marginRight: 8 },
  input: { flex: 1, fontSize: 15, color: '#0f172a' },
  button: {
    backgroundColor: '#2563eb',
    borderRadius: 10,
    height: 48,
    justifyContent: 'center',
    alignItems: 'center',
  },
  buttonDisabled: { opacity: 0.6 },
  buttonText: { color: '#ffffff', fontWeight: '700', fontSize: 16 },
  backLoginRow: { marginTop: 24, alignItems: 'center' },
  backLoginText: { fontSize: 14, color: '#2563eb', fontWeight: '600' },
})
