import React, { useEffect, useState, useRef } from 'react'
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  RefreshControl,
  ActivityIndicator,
  Alert,
} from 'react-native'
import { SafeAreaView } from 'react-native-safe-area-context'
import { useRouter } from 'expo-router'
import { Ionicons } from '@expo/vector-icons'
import {
  mobileExaminationsApi,
  MobileExaminationItem,
  MobileActiveAttempt,
} from '../../api/examinations'
import { theme } from '../../theme'

export default function ExaminationsScreen() {
  const router = useRouter()
  const [loading, setLoading] = useState(false)
  const [refreshing, setRefreshing] = useState(false)
  const [exams, setExams] = useState<MobileExaminationItem[]>([])
  const [activeAttempt, setActiveAttempt] = useState<MobileActiveAttempt | null>(null)
  const [currentQIndex, setCurrentQIndex] = useState(0)
  const [answers, setAnswers] = useState<Record<string, any>>({})
  const [remainingSeconds, setRemainingSeconds] = useState(0)
  const [autosaveStatus, setAutosaveStatus] = useState<string>('')
  const timerRef = useRef<any>(null)

  useEffect(() => {
    fetchExams()
  }, [])

  useEffect(() => {
    if (activeAttempt && remainingSeconds > 0) {
      timerRef.current = setInterval(() => {
        setRemainingSeconds((prev) => {
          if (prev <= 1) {
            clearInterval(timerRef.current!)
            handleAutoSubmit()
            return 0
          }
          return prev - 1
        })
      }, 1000)
    }
    return () => {
      if (timerRef.current) clearInterval(timerRef.current)
    }
  }, [activeAttempt, remainingSeconds])

  const fetchExams = async () => {
    try {
      setLoading(true)
      const data = await mobileExaminationsApi.listExaminations()
      setExams(data || [])
    } catch (err: any) {
      Alert.alert('Error', err.message || 'Failed to load examinations')
    } finally {
      setLoading(false)
      setRefreshing(false)
    }
  }

  const handleStartExam = async (examId: string) => {
    try {
      setLoading(true)
      const attempt = await mobileExaminationsApi.startOrResumeExam(examId)
      setActiveAttempt(attempt)
      setRemainingSeconds(attempt.remaining_seconds)
      setAnswers(attempt.saved_answers || {})
      setCurrentQIndex(0)
      setAutosaveStatus('Ready')
    } catch (err: any) {
      Alert.alert('Cannot Start Exam', err.message || 'Failed to start examination session.')
    } finally {
      setLoading(false)
    }
  }

  const handleSelectOption = (questionId: string, optionId: string) => {
    const updated = { ...answers, [questionId]: optionId }
    setAnswers(updated)
    setAutosaveStatus('Saving...')

    if (activeAttempt) {
      mobileExaminationsApi
        .autosaveAnswers(activeAttempt.attempt_id, [{ question_id: questionId, student_answer: optionId }])
        .then(() => setAutosaveStatus('Saved'))
        .catch(() => setAutosaveStatus('Save failed'))
    }
  }

  const handleSubmit = async () => {
    if (!activeAttempt) return

    Alert.alert(
      'Submit Examination',
      'Are you sure you want to finish and submit your exam?',
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Submit Now',
          style: 'destructive',
          onPress: async () => {
            try {
              setLoading(true)
              const answersList = Object.entries(answers).map(([qId, val]) => ({
                question_id: qId,
                student_answer: val,
              }))
              const result = await mobileExaminationsApi.submitExam(activeAttempt.attempt_id, {
                submission_hash: `mob-${Date.now()}`,
                final_answers: answersList,
              })
              setActiveAttempt(null)
              Alert.alert(
                'Submitted Successfully!',
                result.instant_score !== null && result.instant_score !== undefined
                  ? `Your score: ${result.instant_score} marks.\n${result.message}`
                  : result.message
              )
              fetchExams()
            } catch (err: any) {
              Alert.alert('Submission Error', err.message || 'Failed to submit exam.')
            } finally {
              setLoading(false)
            }
          },
        },
      ]
    )
  }

  const handleAutoSubmit = async () => {
    if (!activeAttempt) return
    try {
      const answersList = Object.entries(answers).map(([qId, val]) => ({
        question_id: qId,
        student_answer: val,
      }))
      await mobileExaminationsApi.submitExam(activeAttempt.attempt_id, {
        submission_hash: `mob-auto-${Date.now()}`,
        final_answers: answersList,
      })
      setActiveAttempt(null)
      Alert.alert('Time Up', 'Your exam time has expired and your answers have been automatically submitted.')
      fetchExams()
    } catch (e) {
      setActiveAttempt(null)
    }
  }

  const formatTimer = (secs: number) => {
    const m = Math.floor(secs / 60)
    const s = secs % 60
    return `${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`
  }

  // ── Render Active Exam Room ────────────────────────────────────────────────
  if (activeAttempt) {
    const currentQ = activeAttempt.questions[currentQIndex]
    return (
      <SafeAreaView style={styles.container}>
        {/* Exam Timer & Status Header */}
        <View style={styles.examHeader}>
          <View>
            <Text style={styles.examTitleText} numberOfLines={1}>
              {activeAttempt.exam_title}
            </Text>
            <Text style={styles.autosaveText}>Autosave: {autosaveStatus}</Text>
          </View>
          <View style={[styles.timerBadge, remainingSeconds < 300 ? styles.timerAlert : null]}>
            <Ionicons name="timer-outline" size={18} color="#fff" />
            <Text style={styles.timerText}>{formatTimer(remainingSeconds)}</Text>
          </View>
        </View>

        {/* Question Counter & Palette */}
        <View style={styles.progressContainer}>
          <Text style={styles.questionCounter}>
            Question {currentQIndex + 1} of {activeAttempt.questions.length}
          </Text>
          <TouchableOpacity style={styles.finishBtn} onPress={handleSubmit}>
            <Text style={styles.finishBtnText}>Submit</Text>
          </TouchableOpacity>
        </View>

        <ScrollView contentContainerStyle={styles.roomContent}>
          {currentQ && (
            <View style={styles.questionCard}>
              <View style={styles.qMetaRow}>
                <Text style={styles.qTypeBadge}>{currentQ.question_type}</Text>
                <Text style={styles.qMarksText}>
                  +{currentQ.marks} marks / -{currentQ.negative_marks} neg
                </Text>
              </View>

              <Text style={styles.questionBody}>{currentQ.question_text}</Text>

              {/* Options */}
              {currentQ.options?.map((opt) => {
                const isSelected = answers[currentQ.id] === opt.id
                return (
                  <TouchableOpacity
                    key={opt.id}
                    style={[styles.optionCard, isSelected ? styles.optionSelected : null]}
                    onPress={() => handleSelectOption(currentQ.id, opt.id)}
                  >
                    <Ionicons
                      name={isSelected ? 'radio-button-on' : 'radio-button-off'}
                      size={20}
                      color={isSelected ? '#2563eb' : '#64748b'}
                    />
                    <Text style={[styles.optionLabel, isSelected ? styles.optionLabelSelected : null]}>
                      {opt.text}
                    </Text>
                  </TouchableOpacity>
                )
              })}
            </View>
          )}
        </ScrollView>

        {/* Bottom Nav Controls */}
        <View style={styles.bottomNav}>
          <TouchableOpacity
            style={[styles.navBtn, currentQIndex === 0 ? styles.navBtnDisabled : null]}
            disabled={currentQIndex === 0}
            onPress={() => setCurrentQIndex((p) => p - 1)}
          >
            <Ionicons name="arrow-back" size={18} color="#1e293b" />
            <Text style={styles.navBtnText}>Previous</Text>
          </TouchableOpacity>

          <TouchableOpacity
            style={[
              styles.navBtn,
              currentQIndex === activeAttempt.questions.length - 1 ? styles.navBtnDisabled : null,
            ]}
            disabled={currentQIndex === activeAttempt.questions.length - 1}
            onPress={() => setCurrentQIndex((p) => p + 1)}
          >
            <Text style={styles.navBtnText}>Next</Text>
            <Ionicons name="arrow-forward" size={18} color="#1e293b" />
          </TouchableOpacity>
        </View>
      </SafeAreaView>
    )
  }

  // ── Render Exam Portal & List ──────────────────────────────────────────────
  return (
    <SafeAreaView style={styles.container}>
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
            <Text style={styles.headerTitle}>Examinations</Text>
            <Text style={styles.headerSubtitle}>Online testing & timed assessments</Text>
          </View>
        </View>
        <TouchableOpacity style={styles.refreshIcon} onPress={fetchExams}>
          <Ionicons name="refresh" size={20} color={theme.colors.primary} />
        </TouchableOpacity>
      </View>

      {loading && !refreshing ? (
        <View style={styles.centerContainer}>
          <ActivityIndicator size="large" color="#2563eb" />
        </View>
      ) : (
        <ScrollView
          contentContainerStyle={styles.listContent}
          refreshControl={<RefreshControl refreshing={refreshing} onRefresh={() => { setRefreshing(true); fetchExams() }} />}
        >
          {exams.length === 0 ? (
            <View style={styles.emptyContainer}>
              <Ionicons name="school-outline" size={48} color="#94a3b8" />
              <Text style={styles.emptyText}>No examinations scheduled at this time.</Text>
            </View>
          ) : (
            exams.map((exam) => (
              <View key={exam.id} style={styles.examCard}>
                <View style={styles.cardHeaderRow}>
                  <Text style={styles.cardType}>{exam.exam_type}</Text>
                  <Text style={[styles.cardStatus, exam.is_published ? styles.published : styles.draft]}>
                    {exam.is_published ? 'Available' : 'Upcoming'}
                  </Text>
                </View>

                <Text style={styles.cardTitle}>{exam.title}</Text>
                <Text style={styles.cardMeta}>
                  {exam.subject_name || 'General'} • {exam.class_name || 'All Classes'}
                </Text>

                <View style={styles.infoRow}>
                  <View style={styles.infoCol}>
                    <Text style={styles.infoLabel}>Duration</Text>
                    <Text style={styles.infoVal}>{exam.duration_minutes} mins</Text>
                  </View>
                  <View style={styles.infoCol}>
                    <Text style={styles.infoLabel}>Total Marks</Text>
                    <Text style={styles.infoVal}>{exam.total_marks}</Text>
                  </View>
                  <View style={styles.infoCol}>
                    <Text style={styles.infoLabel}>Passing</Text>
                    <Text style={styles.infoVal}>{exam.passing_marks}</Text>
                  </View>
                </View>

                {exam.is_published && (
                  <TouchableOpacity
                    style={styles.startBtn}
                    onPress={() => handleStartExam(exam.id)}
                  >
                    <Ionicons name="play" size={16} color="#fff" />
                    <Text style={styles.startBtnText}>Start Online Test</Text>
                  </TouchableOpacity>
                )}
              </View>
            ))
          )}
        </ScrollView>
      )}
    </SafeAreaView>
  )
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#f8fafc' },
  header: {
    paddingHorizontal: 20,
    paddingVertical: 14,
    backgroundColor: '#fff',
    borderBottomWidth: 1,
    borderBottomColor: '#e2e8f0',
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  headerTitle: { fontSize: 22, fontWeight: '700', color: '#0f172a' },
  headerSubtitle: { fontSize: 13, color: '#64748b', marginTop: 2 },
  backButton: { padding: 4, marginRight: 2 },
  refreshIcon: { padding: 8, borderRadius: 8, backgroundColor: '#eff6ff' },
  listContent: { padding: 16 },
  centerContainer: { flex: 1, justifyContent: 'center', alignItems: 'center' },
  emptyContainer: { padding: 40, alignItems: 'center', justifyContent: 'center' },
  emptyText: { marginTop: 12, color: '#64748b', fontSize: 14, textAlign: 'center' },
  examCard: {
    backgroundColor: '#fff',
    borderRadius: 12,
    padding: 16,
    marginBottom: 14,
    borderWidth: 1,
    borderColor: '#e2e8f0',
    shadowColor: '#000',
    shadowOpacity: 0.04,
    shadowRadius: 4,
    elevation: 2,
  },
  cardHeaderRow: { flexDirection: 'row', justifyContent: 'space-between', marginBottom: 6 },
  cardType: { fontSize: 12, fontWeight: '600', color: '#64748b', textTransform: 'uppercase' },
  cardStatus: { fontSize: 12, fontWeight: '600', paddingHorizontal: 8, paddingVertical: 2, borderRadius: 6 },
  published: { backgroundColor: '#dcfce7', color: '#16a34a' },
  draft: { backgroundColor: '#f1f5f9', color: '#64748b' },
  cardTitle: { fontSize: 17, fontWeight: '700', color: '#1e293b' },
  cardMeta: { fontSize: 13, color: '#64748b', marginTop: 2, marginBottom: 12 },
  infoRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    backgroundColor: '#f8fafc',
    padding: 10,
    borderRadius: 8,
    marginBottom: 12,
  },
  infoCol: { alignItems: 'center' },
  infoLabel: { fontSize: 11, color: '#64748b' },
  infoVal: { fontSize: 14, fontWeight: '700', color: '#0f172a', marginTop: 2 },
  startBtn: {
    backgroundColor: '#2563eb',
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: 10,
    borderRadius: 8,
    gap: 6,
  },
  startBtnText: { color: '#fff', fontSize: 14, fontWeight: '600' },

  // Room styles
  examHeader: {
    backgroundColor: '#0f172a',
    paddingHorizontal: 16,
    paddingVertical: 12,
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  examTitleText: { color: '#fff', fontSize: 16, fontWeight: '700', maxWidth: 220 },
  autosaveText: { color: '#94a3b8', fontSize: 11, marginTop: 2 },
  timerBadge: {
    backgroundColor: '#1e293b',
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 8,
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
  },
  timerAlert: { backgroundColor: '#dc2626' },
  timerText: { color: '#fff', fontWeight: '700', fontSize: 15 },
  progressContainer: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingHorizontal: 16,
    paddingVertical: 10,
    backgroundColor: '#fff',
    borderBottomWidth: 1,
    borderBottomColor: '#e2e8f0',
  },
  questionCounter: { fontSize: 13, fontWeight: '600', color: '#475569' },
  finishBtn: { backgroundColor: '#ef4444', paddingHorizontal: 12, paddingVertical: 6, borderRadius: 6 },
  finishBtnText: { color: '#fff', fontSize: 12, fontWeight: '700' },
  roomContent: { padding: 16 },
  questionCard: {
    backgroundColor: '#fff',
    padding: 16,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: '#e2e8f0',
  },
  qMetaRow: { flexDirection: 'row', justifyContent: 'space-between', marginBottom: 12 },
  qTypeBadge: {
    backgroundColor: '#eff6ff',
    color: '#2563eb',
    fontSize: 11,
    fontWeight: '700',
    paddingHorizontal: 8,
    paddingVertical: 2,
    borderRadius: 4,
  },
  qMarksText: { fontSize: 12, color: '#64748b' },
  questionBody: { fontSize: 16, fontWeight: '600', color: '#1e293b', marginBottom: 16, lineHeight: 22 },
  optionCard: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: 12,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: '#e2e8f0',
    marginBottom: 10,
    gap: 10,
  },
  optionSelected: { borderColor: '#2563eb', backgroundColor: '#eff6ff' },
  optionLabel: { fontSize: 14, color: '#334155', flex: 1 },
  optionLabelSelected: { color: '#1e40af', fontWeight: '600' },
  bottomNav: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    padding: 16,
    backgroundColor: '#fff',
    borderTopWidth: 1,
    borderTopColor: '#e2e8f0',
  },
  navBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: 8,
    paddingHorizontal: 14,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: '#cbd5e1',
    gap: 4,
  },
  navBtnDisabled: { opacity: 0.3 },
  navBtnText: { fontSize: 13, fontWeight: '600', color: '#1e293b' },
})
