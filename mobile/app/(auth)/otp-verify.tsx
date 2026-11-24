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

export default function OTPVerifyScreen() {
  const router = useRouter()
  const [phone, setPhone] = useState('')
  const [otp, setOtp] = useState('')
  const [loading, setLoading] = useState(false)
  const [errorMsg, setErrorMsg] = useState<string | null>(null)
  const [successMsg, setSuccessMsg] = useState<string | null>(null)

  const handleVerify = async () => {
    if (!phone.trim() || !otp.trim()) {
      setErrorMsg('Please enter both your mobile number and OTP code.')
      return
    }

    try {
      setLoading(true)
      setErrorMsg(null)
      const res = await mobileAuthApi.verifyOTP(phone.trim(), otp.trim())
      setSuccessMsg(res.message || 'OTP verified successfully!')
      setTimeout(() => {
        router.replace('/(auth)/login')
      }, 1500)
    } catch (err: any) {
      setErrorMsg(err.message || 'Invalid or expired OTP code.')
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
          <Text style={styles.title}>OTP Verification</Text>
          <Text style={styles.subtitle}>
            Enter the 6-digit one-time password dispatched to your registered mobile phone.
          </Text>
        </View>

        {errorMsg && (
          <View style={styles.errorBox}>
            <Ionicons name="alert-circle" size={20} color="#ef4444" />
            <Text style={styles.errorText}>{errorMsg}</Text>
          </View>
        )}

        {successMsg && (
          <View style={styles.successBox}>
            <Ionicons name="checkmark-circle" size={20} color="#16a34a" />
            <Text style={styles.successText}>{successMsg}</Text>
          </View>
        )}

        <View style={styles.formCard}>
          <Text style={styles.inputLabel}>Mobile Phone</Text>
          <View style={styles.inputWrapper}>
            <Ionicons name="call-outline" size={20} color="#64748b" style={styles.inputIcon} />
            <TextInput
              style={styles.input}
              placeholder="+91 98765 43210"
              placeholderTextColor="#94a3b8"
              keyboardType="phone-pad"
              value={phone}
              onChangeText={setPhone}
            />
          </View>

          <Text style={styles.inputLabel}>6-Digit OTP</Text>
          <View style={styles.inputWrapper}>
            <Ionicons name="key-outline" size={20} color="#64748b" style={styles.inputIcon} />
            <TextInput
              style={[styles.input, { letterSpacing: 4, fontWeight: '700' }]}
              placeholder="123456"
              placeholderTextColor="#94a3b8"
              keyboardType="number-pad"
              maxLength={6}
              value={otp}
              onChangeText={setOtp}
            />
          </View>

          <TouchableOpacity
            style={[styles.button, loading && styles.buttonDisabled]}
            onPress={handleVerify}
            disabled={loading}
          >
            {loading ? (
              <ActivityIndicator color="#ffffff" />
            ) : (
              <Text style={styles.buttonText}>Verify & Proceed</Text>
            )}
          </TouchableOpacity>
        </View>
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
  successBox: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#f0fdf4',
    borderWidth: 1,
    borderColor: '#bbf7d0',
    borderRadius: 10,
    padding: 12,
    marginBottom: 20,
    gap: 8,
  },
  successText: { color: '#15803d', fontSize: 13, flex: 1 },
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
    marginBottom: 16,
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
    marginTop: 8,
  },
  buttonDisabled: { opacity: 0.6 },
  buttonText: { color: '#ffffff', fontWeight: '700', fontSize: 16 },
})
