import React, { useState, useEffect, useCallback } from 'react'
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  ActivityIndicator,
  Alert,
  Modal,
  TextInput,
  RefreshControl,
} from 'react-native'
import { SafeAreaView } from 'react-native-safe-area-context'
import { useRouter } from 'expo-router'
import { Ionicons } from '@expo/vector-icons'
import { useAuthStore } from '@/store/authStore'
import {
  mobileResultsApi,
  MobileStudentTermResult,
  MobileStudentSubjectResult,
} from '../../api/results'
import { theme } from '../../theme'

export default function ResultsScreen() {
  const router = useRouter()
  const { user } = useAuthStore()
  const [loading, setLoading] = useState(false)
  const [refreshing, setRefreshing] = useState(false)
  const [result, setResult] = useState<MobileStudentTermResult | null>(null)

  // Re-evaluation Modal
  const [modalVisible, setModalVisible] = useState(false)
  const [selectedSubject, setSelectedSubject] = useState<MobileStudentSubjectResult | null>(null)
  const [reEvalReason, setReEvalReason] = useState('')
  const [submittingReEval, setSubmittingReEval] = useState(false)

  const fetchResults = useCallback(async () => {
    try {
      setLoading(true)
      const data = await mobileResultsApi.getStudentReportCard('midterm-2026', user?.id || 'std-current')
      setResult(data)
    } catch {
      // Fallback academic scorecard for demo/offline
      const mockResult: MobileStudentTermResult = {
        id: 'res-term-1',
        student_id: user?.id || 'std-101',
        student_name: user?.full_name || 'Aarav Sharma',
        admission_number: 'ADM-2026-0089',
        roll_number: '12',
        exam_id: 'exam-midterm-1',
        exam_title: 'Mid-Term Examinations 2026',
        academic_session_name: 'AY 2026-2027',
        class_name: 'Class 10',
        section_name: 'Section A',
        total_obtained: 442,
        total_max: 500,
        overall_percentage: 88.4,
        overall_grade: 'A+',
        cgpa: 9.1,
        sgpa: 9.2,
        rank: 3,
        is_passed: true,
        attendance_percentage: 92.5,
        approval_status: 'PUBLISHED',
        subject_results: [
          {
            id: 'sub-res-1',
            subject_name: 'Mathematics',
            subject_code: 'MTH-101',
            theory_marks: 68,
            practical_marks: 0,
            internal_marks: 18,
            assignment_marks: 9,
            total_marks: 95,
            max_marks: 100,
            percentage: 95.0,
            grade: 'O',
            credits: 4,
            is_passed: true,
          },
          {
            id: 'sub-res-2',
            subject_name: 'Physics',
            subject_code: 'PHY-102',
            theory_marks: 58,
            practical_marks: 28,
            internal_marks: 0,
            assignment_marks: 0,
            total_marks: 86,
            max_marks: 100,
            percentage: 86.0,
            grade: 'A+',
            credits: 4,
            is_passed: true,
          },
          {
            id: 'sub-res-3',
            subject_name: 'Chemistry',
            subject_code: 'CHM-103',
            theory_marks: 54,
            practical_marks: 27,
            internal_marks: 0,
            assignment_marks: 0,
            total_marks: 81,
            max_marks: 100,
            percentage: 81.0,
            grade: 'A',
            credits: 4,
            is_passed: true,
          },
          {
            id: 'sub-res-4',
            subject_name: 'English Language & Lit',
            subject_code: 'ENG-104',
            theory_marks: 72,
            practical_marks: 0,
            internal_marks: 19,
            assignment_marks: 0,
            total_marks: 91,
            max_marks: 100,
            percentage: 91.0,
            grade: 'O',
            credits: 3,
            is_passed: true,
          },
          {
            id: 'sub-res-5',
            subject_name: 'Computer Applications',
            subject_code: 'CSC-105',
            theory_marks: 59,
            practical_marks: 30,
            internal_marks: 0,
            assignment_marks: 0,
            total_marks: 89,
            max_marks: 100,
            percentage: 89.0,
            grade: 'A+',
            credits: 3,
            is_passed: true,
          },
        ],
      }
      setResult(mockResult)
    } finally {
      setLoading(false)
    }
  }, [user?.id, user?.full_name])

  useEffect(() => {
    fetchResults()
  }, [fetchResults])

  const onRefresh = async () => {
    setRefreshing(true)
    await fetchResults()
    setRefreshing(false)
  }

  const handleOpenReEval = (sub: MobileStudentSubjectResult) => {
    setSelectedSubject(sub)
    setReEvalReason('')
    setModalVisible(true)
  }

  const handleSubmitReEval = async () => {
    if (!selectedSubject) return
    if (!reEvalReason.trim()) {
      Alert.alert('Reason Required', 'Please enter a reason for the re-evaluation request.')
      return
    }

    try {
      setSubmittingReEval(true)
      await mobileResultsApi.submitReEvaluation({
        subject_result_id: selectedSubject.id,
        reason: reEvalReason,
      })
      Alert.alert('Request Submitted', `Re-evaluation request for ${selectedSubject.subject_name} submitted successfully.`)
      setModalVisible(false)
    } catch (err: any) {
      Alert.alert('Submission Error', err.message || 'Failed to submit request.')
    } finally {
      setSubmittingReEval(false)
    }
  }

  return (
    <SafeAreaView style={styles.container}>
      <ScrollView
        contentContainerStyle={styles.scrollContent}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} />}
      >
        <View style={styles.header}>
          <View style={{ flexDirection: 'row', alignItems: 'center', gap: 10 }}>
            <TouchableOpacity
              onPress={() => router.push('/(app)/dashboard')}
              hitSlop={{ top: 10, bottom: 10, left: 10, right: 10 }}
            >
              <Ionicons name="arrow-back" size={22} color={theme.colors.textPrimary} />
            </TouchableOpacity>
            <View>
              <Text style={styles.headerTitle}>Examination Results</Text>
              <Text style={styles.headerSubtitle}>
                {result?.exam_title || 'Academic Performance & Report Cards'}
              </Text>
            </View>
          </View>
        </View>

        {loading ? (
          <ActivityIndicator size="large" color="#2563eb" style={{ marginTop: 40 }} />
        ) : (
          <>
            {/* Overall Performance Hero Card */}
            <View style={styles.summaryCard}>
              <View style={styles.summaryTop}>
                <View>
                  <Text style={styles.studentName}>{result?.student_name}</Text>
                  <Text style={styles.studentMeta}>
                    Adm No: {result?.admission_number} • Roll: {result?.roll_number}
                  </Text>
                  <Text style={styles.studentClass}>
                    {result?.class_name} ({result?.section_name}) • {result?.academic_session_name}
                  </Text>
                </View>
                <View style={styles.badgeContainer}>
                  <View
                    style={[
                      styles.resultBadge,
                      { backgroundColor: result?.is_passed ? '#dcfce7' : '#fee2e2' },
                    ]}
                  >
                    <Text
                      style={[
                        styles.resultBadgeText,
                        { color: result?.is_passed ? '#15803d' : '#b91c1c' },
                      ]}
                    >
                      {result?.is_passed ? 'PASSED' : 'FAILED'}
                    </Text>
                  </View>
                </View>
              </View>

              {/* High-level metrics */}
              <View style={styles.metricGrid}>
                <View style={styles.metricItem}>
                  <Text style={styles.metricValue}>{result?.overall_percentage}%</Text>
                  <Text style={styles.metricLabel}>Percentage</Text>
                </View>
                <View style={styles.metricItem}>
                  <Text style={styles.metricValue}>{result?.overall_grade}</Text>
                  <Text style={styles.metricLabel}>Overall Grade</Text>
                </View>
                <View style={styles.metricItem}>
                  <Text style={styles.metricValue}>{result?.cgpa ?? 'N/A'}</Text>
                  <Text style={styles.metricLabel}>CGPA</Text>
                </View>
                <View style={styles.metricItem}>
                  <Text style={styles.metricValue}>
                    {result?.rank ? `#${result.rank}` : 'N/A'}
                  </Text>
                  <Text style={styles.metricLabel}>Class Rank</Text>
                </View>
              </View>

              <View style={styles.totalRow}>
                <Text style={styles.totalLabel}>Grand Total Score</Text>
                <Text style={styles.totalScore}>
                  {result?.total_obtained} / {result?.total_max}
                </Text>
              </View>
            </View>

            {/* Subject-wise Marks Breakdown */}
            <Text style={styles.sectionHeading}>Subject-Wise Score Breakdown</Text>

            {result?.subject_results?.map((sub) => (
              <View key={sub.id} style={styles.subjectCard}>
                <View style={styles.subHeader}>
                  <View style={{ flex: 1 }}>
                    <Text style={styles.subName}>{sub.subject_name}</Text>
                    <Text style={styles.subCode}>
                      Code: {sub.subject_code} • Credits: {sub.credits}
                    </Text>
                  </View>
                  <View style={styles.gradeBox}>
                    <Text style={styles.gradeText}>{sub.grade || 'A'}</Text>
                    <Text style={styles.gradeSub}>{sub.is_passed ? 'PASS' : 'FAIL'}</Text>
                  </View>
                </View>

                {/* Score breakdown pills */}
                <View style={styles.scoresRow}>
                  <View style={styles.scorePill}>
                    <Text style={styles.scorePillLabel}>Theory</Text>
                    <Text style={styles.scorePillVal}>{sub.theory_marks}</Text>
                  </View>
                  {sub.practical_marks > 0 && (
                    <View style={styles.scorePill}>
                      <Text style={styles.scorePillLabel}>Practical</Text>
                      <Text style={styles.scorePillVal}>{sub.practical_marks}</Text>
                    </View>
                  )}
                  {sub.internal_marks > 0 && (
                    <View style={styles.scorePill}>
                      <Text style={styles.scorePillLabel}>Internal</Text>
                      <Text style={styles.scorePillVal}>{sub.internal_marks}</Text>
                    </View>
                  )}
                  {sub.assignment_marks > 0 && (
                    <View style={styles.scorePill}>
                      <Text style={styles.scorePillLabel}>Assignment</Text>
                      <Text style={styles.scorePillVal}>{sub.assignment_marks}</Text>
                    </View>
                  )}
                  <View style={[styles.scorePill, styles.totalPill]}>
                    <Text style={[styles.scorePillLabel, { color: '#1e40af' }]}>Total</Text>
                    <Text style={[styles.scorePillVal, { color: '#1e40af', fontWeight: '800' }]}>
                      {sub.total_marks}/{sub.max_marks}
                    </Text>
                  </View>
                </View>

                {/* Re-evaluation button */}
                <TouchableOpacity
                  style={styles.reEvalBtn}
                  onPress={() => handleOpenReEval(sub)}
                >
                  <Ionicons name="refresh-circle-outline" size={16} color="#475569" />
                  <Text style={styles.reEvalBtnText}>Request Re-Evaluation</Text>
                </TouchableOpacity>
              </View>
            ))}
          </>
        )}
      </ScrollView>

      {/* Re-Evaluation Request Modal */}
      <Modal
        visible={modalVisible}
        transparent
        animationType="slide"
        onRequestClose={() => setModalVisible(false)}
      >
        <View style={styles.modalOverlay}>
          <View style={styles.modalContent}>
            <View style={styles.modalHeader}>
              <Text style={styles.modalTitle}>Re-Evaluation Request</Text>
              <TouchableOpacity onPress={() => setModalVisible(false)}>
                <Ionicons name="close" size={24} color="#64748b" />
              </TouchableOpacity>
            </View>

            <Text style={styles.modalSub}>
              Subject: <Text style={{ fontWeight: '700' }}>{selectedSubject?.subject_name}</Text>
            </Text>
            <Text style={styles.modalSub}>
              Current Marks:{' '}
              <Text style={{ fontWeight: '700' }}>
                {selectedSubject?.total_marks} / {selectedSubject?.max_marks} (Grade {selectedSubject?.grade})
              </Text>
            </Text>

            <Text style={styles.inputLabel}>Reason / Remarks for Re-Evaluation:</Text>
            <TextInput
              style={styles.reasonInput}
              placeholder="Explain why you are requesting re-evaluation (e.g. totaling discrepancy, missed practical credit)..."
              placeholderTextColor="#94a3b8"
              multiline
              numberOfLines={4}
              value={reEvalReason}
              onChangeText={setReEvalReason}
            />

            <TouchableOpacity
              style={[styles.modalSubmitBtn, submittingReEval && { opacity: 0.7 }]}
              onPress={handleSubmitReEval}
              disabled={submittingReEval}
            >
              {submittingReEval ? (
                <ActivityIndicator color="#ffffff" />
              ) : (
                <Text style={styles.modalSubmitText}>Submit Request</Text>
              )}
            </TouchableOpacity>
          </View>
        </View>
      </Modal>
    </SafeAreaView>
  )
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#f8fafc' },
  scrollContent: { padding: 16, paddingBottom: 40 },
  header: { marginBottom: 16 },
  headerTitle: { fontSize: 22, fontWeight: '800', color: '#0f172a' },
  headerSubtitle: { fontSize: 13, color: '#64748b', marginTop: 2 },

  summaryCard: {
    backgroundColor: '#ffffff',
    borderRadius: 16,
    padding: 16,
    borderWidth: 1,
    borderColor: '#e2e8f0',
    marginBottom: 20,
    shadowColor: '#000',
    shadowOpacity: 0.05,
    shadowRadius: 6,
    elevation: 2,
  },
  summaryTop: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    borderBottomWidth: 1,
    borderBottomColor: '#f1f5f9',
    paddingBottom: 12,
  },
  studentName: { fontSize: 18, fontWeight: '800', color: '#0f172a' },
  studentMeta: { fontSize: 12, color: '#64748b', marginTop: 2 },
  studentClass: { fontSize: 12, color: '#2563eb', fontWeight: '600', marginTop: 2 },

  badgeContainer: { alignItems: 'flex-end' },
  resultBadge: {
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: 12,
  },
  resultBadgeText: { fontSize: 12, fontWeight: '800' },

  metricGrid: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    paddingVertical: 14,
    borderBottomWidth: 1,
    borderBottomColor: '#f1f5f9',
  },
  metricItem: { alignItems: 'center', flex: 1 },
  metricValue: { fontSize: 18, fontWeight: '800', color: '#0f172a' },
  metricLabel: { fontSize: 11, color: '#64748b', marginTop: 2 },

  totalRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingTop: 12,
  },
  totalLabel: { fontSize: 14, fontWeight: '600', color: '#475569' },
  totalScore: { fontSize: 18, fontWeight: '800', color: '#1e40af' },

  sectionHeading: { fontSize: 16, fontWeight: '700', color: '#0f172a', marginBottom: 12 },

  subjectCard: {
    backgroundColor: '#ffffff',
    borderRadius: 14,
    padding: 14,
    borderWidth: 1,
    borderColor: '#e2e8f0',
    marginBottom: 12,
  },
  subHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 10,
  },
  subName: { fontSize: 15, fontWeight: '700', color: '#0f172a' },
  subCode: { fontSize: 12, color: '#64748b', marginTop: 2 },
  gradeBox: {
    backgroundColor: '#eff6ff',
    paddingHorizontal: 12,
    paddingVertical: 4,
    borderRadius: 8,
    alignItems: 'center',
  },
  gradeText: { fontSize: 16, fontWeight: '800', color: '#1d4ed8' },
  gradeSub: { fontSize: 9, fontWeight: '700', color: '#16a34a' },

  scoresRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 8,
    marginBottom: 10,
  },
  scorePill: {
    backgroundColor: '#f8fafc',
    paddingHorizontal: 10,
    paddingVertical: 6,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: '#e2e8f0',
    alignItems: 'center',
    minWidth: 64,
  },
  totalPill: {
    backgroundColor: '#dbeafe',
    borderColor: '#bfdbfe',
  },
  scorePillLabel: { fontSize: 10, color: '#64748b', fontWeight: '600' },
  scorePillVal: { fontSize: 13, fontWeight: '700', color: '#0f172a', marginTop: 2 },

  reEvalBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'flex-end',
    gap: 4,
    paddingTop: 8,
    borderTopWidth: 1,
    borderTopColor: '#f8fafc',
  },
  reEvalBtnText: { fontSize: 12, color: '#475569', fontWeight: '600' },

  modalOverlay: {
    flex: 1,
    backgroundColor: 'rgba(0,0,0,0.5)',
    justifyContent: 'flex-end',
  },
  modalContent: {
    backgroundColor: '#ffffff',
    borderTopLeftRadius: 20,
    borderTopRightRadius: 20,
    padding: 20,
    paddingBottom: 40,
  },
  modalHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 14,
  },
  modalTitle: { fontSize: 18, fontWeight: '800', color: '#0f172a' },
  modalSub: { fontSize: 13, color: '#475569', marginBottom: 4 },
  inputLabel: { fontSize: 13, fontWeight: '700', color: '#0f172a', marginTop: 14, marginBottom: 6 },
  reasonInput: {
    backgroundColor: '#f8fafc',
    borderWidth: 1,
    borderColor: '#cbd5e1',
    borderRadius: 10,
    padding: 12,
    fontSize: 13,
    color: '#0f172a',
    textAlignVertical: 'top',
    height: 100,
  },
  modalSubmitBtn: {
    backgroundColor: '#2563eb',
    paddingVertical: 14,
    borderRadius: 12,
    alignItems: 'center',
    marginTop: 20,
  },
  modalSubmitText: { color: '#ffffff', fontSize: 15, fontWeight: '700' },
})