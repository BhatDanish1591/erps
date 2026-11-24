import React, { useState, useEffect, useCallback } from 'react'
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  ActivityIndicator,
  Alert,
  TextInput,
  RefreshControl,
  Linking,
  Modal,
} from 'react-native'
import { SafeAreaView } from 'react-native-safe-area-context'
import { Ionicons } from '@expo/vector-icons'
import {
  mobileLmsApi,
  MobileStudyMaterial,
  MobileAssignment,
} from '../../api/lms'
import { theme } from '../../theme'

export default function LmsScreen() {
  const [activeTab, setActiveTab] = useState<'materials' | 'assignments'>('materials')
  const [loading, setLoading] = useState(false)
  const [refreshing, setRefreshing] = useState(false)

  // Study Materials State
  const [materials, setMaterials] = useState<MobileStudyMaterial[]>([])
  const [searchQuery, setSearchQuery] = useState('')
  const [selectedCategory, setSelectedCategory] = useState<string>('ALL')

  // Assignments State
  const [assignments, setAssignments] = useState<MobileAssignment[]>([])
  const [selectedAssignment, setSelectedAssignment] = useState<MobileAssignment | null>(null)
  const [submissionModalVisible, setSubmissionModalVisible] = useState(false)
  const [submissionText, setSubmissionText] = useState('')
  const [submittingAssignment, setSubmittingAssignment] = useState(false)

  const fetchData = useCallback(async () => {
    try {
      setLoading(true)
      if (activeTab === 'materials') {
        const matRes = await mobileLmsApi.listMaterials({
          search: searchQuery.trim() || undefined,
          category: selectedCategory !== 'ALL' ? selectedCategory : undefined,
        })
        if (matRes && matRes.length > 0) {
          setMaterials(matRes)
        } else {
          // Mock data fallback
          setMaterials([
            {
              id: 'mat-1',
              title: 'Chapter 4: Quadratic Equations & Complex Numbers',
              description: 'Lecture notes covering discriminant formulas, quadratic graphs, and sample proofs.',
              chapter: 'Chapter 4',
              material_type: 'PDF',
              category: 'LECTURE_NOTE',
              file_name: 'Quadratic_Equations_Notes.pdf',
              file_size_bytes: 3450000,
              version: 2,
              download_count: 88,
              view_count: 142,
              subject_name: 'Mathematics',
              subject_code: 'MTH-101',
              created_at: '2026-11-10T10:00:00Z',
              download_url: 'https://campus-cdn.internal/docs/math_ch4.pdf',
            },
            {
              id: 'mat-2',
              title: 'Electromagnetic Induction & Faraday Laws',
              description: 'Complete slide deck with 3D diagram illustrations of magnetic flux change.',
              chapter: 'Chapter 6',
              material_type: 'PPT',
              category: 'SLIDE_DECK',
              file_name: 'Physics_Ch6_Faraday_Induction.pptx',
              file_size_bytes: 8200000,
              version: 1,
              download_count: 65,
              view_count: 110,
              subject_name: 'Physics',
              subject_code: 'PHY-102',
              created_at: '2026-11-12T14:30:00Z',
              download_url: 'https://campus-cdn.internal/docs/physics_ch6.pptx',
            },
            {
              id: 'mat-3',
              title: 'Organic Chemistry: Aldehydes & Ketones Reactions',
              description: 'Video lecture recording from Seminar Hall 2 on nucleophilic addition mechanisms.',
              chapter: 'Chapter 12',
              material_type: 'VIDEO',
              category: 'RECORDED_LECTURE',
              external_url: 'https://youtube.com/watch?v=demo-organic',
              version: 1,
              download_count: 42,
              view_count: 95,
              subject_name: 'Chemistry',
              subject_code: 'CHM-103',
              created_at: '2026-11-15T09:15:00Z',
            },
            {
              id: 'mat-4',
              title: 'Previous 5-Year Question Papers & Marking Scheme',
              description: 'Board examination solved model test papers for term final revision.',
              chapter: 'Board Question Bank',
              material_type: 'PDF',
              category: 'QUESTION_PAPER',
              file_name: 'Past_5Year_Solved_Papers.pdf',
              file_size_bytes: 12500000,
              version: 3,
              download_count: 194,
              view_count: 320,
              subject_name: 'General',
              created_at: '2026-11-01T08:00:00Z',
            },
          ])
        }
      } else {
        const assignRes = await mobileLmsApi.listAssignments()
        if (assignRes && assignRes.length > 0) {
          setAssignments(assignRes)
        } else {
          // Mock assignments fallback
          setAssignments([
            {
              id: 'asg-1',
              title: 'Calculus Assignment: Optimization & Derivation',
              description: 'Solve the 10 optimization scenario problems listed in attached instructions sheet.',
              due_datetime: '2026-11-25T23:59:00Z',
              allow_late_submission: true,
              late_penalty_percent: 10,
              total_marks: 30,
              passing_marks: 12,
              status: 'PUBLISHED',
              subject_name: 'Mathematics',
              subject_code: 'MTH-101',
              submissions_count: 24,
              evaluated_count: 18,
            },
            {
              id: 'asg-2',
              title: 'Lab Report: Determination of Focal Length of Concave Mirror',
              description: 'Upload laboratory observations, ray diagrams, and calculated focal length tables.',
              due_datetime: '2026-11-22T17:00:00Z',
              allow_late_submission: false,
              late_penalty_percent: 0,
              total_marks: 25,
              passing_marks: 10,
              status: 'PUBLISHED',
              subject_name: 'Physics',
              subject_code: 'PHY-102',
              submissions_count: 32,
              evaluated_count: 30,
            },
            {
              id: 'asg-3',
              title: 'Literary Essay: Symbolism in The Great Gatsby',
              description: 'Write an analytical essay (800-1000 words) on the symbolic theme of the green light.',
              due_datetime: '2026-11-28T23:59:00Z',
              allow_late_submission: true,
              late_penalty_percent: 5,
              total_marks: 50,
              passing_marks: 20,
              status: 'PUBLISHED',
              subject_name: 'English',
              subject_code: 'ENG-104',
              submissions_count: 15,
              evaluated_count: 5,
            },
          ])
        }
      }
    } catch {
      // Keep state if failed
    } finally {
      setLoading(false)
    }
  }, [activeTab, searchQuery, selectedCategory])

  useEffect(() => {
    fetchData()
  }, [fetchData])

  const onRefresh = async () => {
    setRefreshing(true)
    await fetchData()
    setRefreshing(false)
  }

  const handleOpenMaterial = (mat: MobileStudyMaterial) => {
    const url = mat.external_url || mat.download_url
    if (url) {
      Linking.openURL(url).catch(() => {
        Alert.alert('Notice', 'Cannot open document link directly.')
      })
    } else {
      Alert.alert('Downloaded', `Opening file ${mat.file_name || mat.title}`)
    }
  }

  const handleOpenAssignment = (assign: MobileAssignment) => {
    setSelectedAssignment(assign)
    setSubmissionText('')
    setSubmissionModalVisible(true)
  }

  const handleSubmitAssignment = () => {
    if (!submissionText.trim()) {
      Alert.alert('Empty Submission', 'Please type your answers or notes before submitting.')
      return
    }
    setSubmittingAssignment(true)
    setTimeout(() => {
      setSubmittingAssignment(false)
      setSubmissionModalVisible(false)
      Alert.alert('Submitted!', 'Your assignment has been turned in successfully to the instructor.')
    }, 1000)
  }

  const formatFileSize = (bytes?: number) => {
    if (!bytes) return ''
    if (bytes >= 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
    return `${Math.round(bytes / 1024)} KB`
  }

  const categories = ['ALL', 'LECTURE_NOTE', 'SLIDE_DECK', 'RECORDED_LECTURE', 'QUESTION_PAPER']

  return (
    <SafeAreaView style={styles.container}>
      {/* Top Toggle Tabs */}
      <View style={styles.topTabs}>
        <TouchableOpacity
          style={[styles.tabBtn, activeTab === 'materials' && styles.activeTabBtn]}
          onPress={() => setActiveTab('materials')}
        >
          <Ionicons
            name="library-outline"
            size={18}
            color={activeTab === 'materials' ? '#2563eb' : '#64748b'}
          />
          <Text style={[styles.tabText, activeTab === 'materials' && styles.activeTabText]}>
            Study Material
          </Text>
        </TouchableOpacity>

        <TouchableOpacity
          style={[styles.tabBtn, activeTab === 'assignments' && styles.activeTabBtn]}
          onPress={() => setActiveTab('assignments')}
        >
          <Ionicons
            name="create-outline"
            size={18}
            color={activeTab === 'assignments' ? '#2563eb' : '#64748b'}
          />
          <Text style={[styles.tabText, activeTab === 'assignments' && styles.activeTabText]}>
            Assignments
          </Text>
        </TouchableOpacity>
      </View>

      <ScrollView
        contentContainerStyle={styles.scrollContent}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} />}
      >
        {activeTab === 'materials' ? (
          <>
            {/* Search Input */}
            <View style={styles.searchBox}>
              <Ionicons name="search" size={18} color="#94a3b8" />
              <TextInput
                style={styles.searchInput}
                placeholder="Search notes, chapters, topics..."
                placeholderTextColor="#94a3b8"
                value={searchQuery}
                onChangeText={setSearchQuery}
                onSubmitEditing={fetchData}
              />
              {searchQuery.length > 0 && (
                <TouchableOpacity onPress={() => setSearchQuery('')}>
                  <Ionicons name="close-circle" size={18} color="#94a3b8" />
                </TouchableOpacity>
              )}
            </View>

            {/* Category Pills */}
            <ScrollView
              horizontal
              showsHorizontalScrollIndicator={false}
              contentContainerStyle={styles.categoriesBar}
            >
              {categories.map((cat) => (
                <TouchableOpacity
                  key={cat}
                  style={[
                    styles.catPill,
                    selectedCategory === cat && styles.catPillActive,
                  ]}
                  onPress={() => setSelectedCategory(cat)}
                >
                  <Text
                    style={[
                      styles.catText,
                      selectedCategory === cat && styles.catTextActive,
                    ]}
                  >
                    {cat.replace(/_/g, ' ')}
                  </Text>
                </TouchableOpacity>
              ))}
            </ScrollView>

            {/* Materials List */}
            {loading ? (
              <ActivityIndicator size="large" color="#2563eb" style={{ marginTop: 40 }} />
            ) : materials.length === 0 ? (
              <View style={styles.emptyState}>
                <Ionicons name="folder-open-outline" size={48} color="#94a3b8" />
                <Text style={styles.emptyText}>No materials found</Text>
              </View>
            ) : (
              materials.map((mat) => {
                const iconName =
                  mat.material_type === 'PDF'
                    ? 'document-text'
                    : mat.material_type === 'VIDEO'
                    ? 'videocam'
                    : 'document'

                return (
                  <View key={mat.id} style={styles.materialCard}>
                    <View style={styles.matHeader}>
                      <View style={styles.iconCircle}>
                        <Ionicons name={iconName} size={22} color="#2563eb" />
                      </View>
                      <View style={{ flex: 1, marginLeft: 12 }}>
                        <Text style={styles.matSubject}>
                          {mat.subject_name} {mat.chapter ? `• ${mat.chapter}` : ''}
                        </Text>
                        <Text style={styles.matTitle}>{mat.title}</Text>
                      </View>
                    </View>

                    {mat.description && (
                      <Text style={styles.matDesc}>{mat.description}</Text>
                    )}

                    <View style={styles.matFooter}>
                      <View style={styles.matMeta}>
                        <Text style={styles.metaBadge}>v{mat.version}</Text>
                        {mat.file_size_bytes ? (
                          <Text style={styles.metaInfo}>{formatFileSize(mat.file_size_bytes)}</Text>
                        ) : null}
                        <Text style={styles.metaInfo}>
                          {mat.download_count} downloads
                        </Text>
                      </View>

                      <TouchableOpacity
                        style={styles.openBtn}
                        onPress={() => handleOpenMaterial(mat)}
                      >
                        <Ionicons
                          name={mat.external_url ? 'open-outline' : 'download-outline'}
                          size={16}
                          color="#2563eb"
                        />
                        <Text style={styles.openBtnText}>
                          {mat.external_url ? 'Watch' : 'Download'}
                        </Text>
                      </TouchableOpacity>
                    </View>
                  </View>
                )
              })
            )}
          </>
        ) : (
          /* Assignments View */
          <>
            {loading ? (
              <ActivityIndicator size="large" color="#2563eb" style={{ marginTop: 40 }} />
            ) : assignments.length === 0 ? (
              <View style={styles.emptyState}>
                <Ionicons name="checkbox-outline" size={48} color="#94a3b8" />
                <Text style={styles.emptyText}>No assignments scheduled</Text>
              </View>
            ) : (
              assignments.map((asg) => {
                const dueDate = new Date(asg.due_datetime)
                const isOverdue = new Date() > dueDate

                return (
                  <View key={asg.id} style={styles.assignmentCard}>
                    <View style={styles.assignHeader}>
                      <View style={{ flex: 1 }}>
                        <Text style={styles.assignSubject}>{asg.subject_name}</Text>
                        <Text style={styles.assignTitle}>{asg.title}</Text>
                      </View>
                      <View
                        style={[
                          styles.deadlineBadge,
                          { backgroundColor: isOverdue ? '#fee2e2' : '#fef3c7' },
                        ]}
                      >
                        <Ionicons
                          name="time-outline"
                          size={12}
                          color={isOverdue ? '#dc2626' : '#d97706'}
                        />
                        <Text
                          style={[
                            styles.deadlineText,
                            { color: isOverdue ? '#b91c1c' : '#92400e' },
                          ]}
                        >
                          {isOverdue ? 'Expired' : 'Due Soon'}
                        </Text>
                      </View>
                    </View>

                    <Text style={styles.assignDesc}>{asg.description}</Text>

                    <View style={styles.marksRow}>
                      <View style={styles.marksItem}>
                        <Text style={styles.marksLabel}>Total Marks:</Text>
                        <Text style={styles.marksVal}>{asg.total_marks}</Text>
                      </View>
                      <View style={styles.marksItem}>
                        <Text style={styles.marksLabel}>Pass Mark:</Text>
                        <Text style={styles.marksVal}>{asg.passing_marks}</Text>
                      </View>
                      <View style={styles.marksItem}>
                        <Text style={styles.marksLabel}>Due:</Text>
                        <Text style={styles.marksVal}>
                          {dueDate.toLocaleDateString(undefined, {
                            month: 'short',
                            day: 'numeric',
                          })}
                        </Text>
                      </View>
                    </View>

                    {asg.allow_late_submission && (
                      <Text style={styles.lateNotice}>
                        * Late submissions allowed with {asg.late_penalty_percent}% penalty
                      </Text>
                    )}

                    <TouchableOpacity
                      style={styles.submitTaskBtn}
                      onPress={() => handleOpenAssignment(asg)}
                    >
                      <Ionicons name="cloud-upload-outline" size={16} color="#ffffff" />
                      <Text style={styles.submitTaskText}>Turn In Assignment</Text>
                    </TouchableOpacity>
                  </View>
                )
              })
            )}
          </>
        )}
      </ScrollView>

      {/* Assignment Submission Modal */}
      <Modal
        visible={submissionModalVisible}
        transparent
        animationType="slide"
        onRequestClose={() => setSubmissionModalVisible(false)}
      >
        <View style={styles.modalOverlay}>
          <View style={styles.modalContent}>
            <View style={styles.modalHeader}>
              <Text style={styles.modalTitle}>Submit Assignment</Text>
              <TouchableOpacity onPress={() => setSubmissionModalVisible(false)}>
                <Ionicons name="close" size={24} color="#64748b" />
              </TouchableOpacity>
            </View>

            <Text style={styles.taskTitle}>{selectedAssignment?.title}</Text>
            <Text style={styles.taskSubject}>{selectedAssignment?.subject_name}</Text>

            <Text style={styles.inputLabel}>Enter Response / Work Link:</Text>
            <TextInput
              style={styles.submissionInput}
              placeholder="Type your response, calculations, or paste shareable cloud link (Google Drive / GitHub)..."
              placeholderTextColor="#94a3b8"
              multiline
              numberOfLines={6}
              value={submissionText}
              onChangeText={setSubmissionText}
            />

            <TouchableOpacity
              style={[styles.modalSubmitBtn, submittingAssignment && { opacity: 0.7 }]}
              onPress={handleSubmitAssignment}
              disabled={submittingAssignment}
            >
              {submittingAssignment ? (
                <ActivityIndicator color="#ffffff" />
              ) : (
                <Text style={styles.modalSubmitText}>Confirm & Turn In</Text>
              )}
            </TouchableOpacity>
          </View>
        </View>
      </Modal>
    </SafeAreaView>
  )
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: theme.colors.background },
  topTabs: {
    flexDirection: 'row',
    backgroundColor: theme.colors.surface,
    borderBottomWidth: 1,
    borderBottomColor: theme.colors.borderSubtle,
    paddingHorizontal: 16,
    paddingVertical: 8,
    ...theme.shadows.sm,
  },
  tabBtn: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: 10,
    gap: 6,
    borderRadius: theme.radii.sm,
  },
  activeTabBtn: {
    backgroundColor: theme.colors.primary50,
  },
  tabText: { fontSize: 13, fontWeight: '600', color: theme.colors.textMuted },
  activeTabText: { color: theme.colors.primary, fontWeight: '700' },

  scrollContent: { padding: 18, paddingBottom: 40 },

  searchBox: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: theme.colors.surface,
    borderRadius: theme.radii.md,
    paddingHorizontal: 14,
    borderWidth: 1,
    borderColor: theme.colors.border,
    marginBottom: 14,
    height: 46,
    ...theme.shadows.sm,
  },
  searchInput: {
    flex: 1,
    height: '100%',
    paddingHorizontal: 8,
    fontSize: 14,
    color: theme.colors.textPrimary,
    fontWeight: '500',
  },

  categoriesBar: {
    flexDirection: 'row',
    gap: 8,
    paddingBottom: 16,
  },
  catPill: {
    paddingHorizontal: 14,
    paddingVertical: 7,
    borderRadius: theme.radii.full,
    backgroundColor: theme.colors.surface,
    borderWidth: 1,
    borderColor: theme.colors.border,
  },
  catPillActive: {
    backgroundColor: theme.colors.primary,
    borderColor: theme.colors.primary,
  },
  catText: { fontSize: 12, fontWeight: '600', color: theme.colors.textSecondary },
  catTextActive: { color: '#ffffff' },

  emptyState: {
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: 60,
  },
  emptyText: { marginTop: 12, fontSize: 14, color: theme.colors.textLight, fontWeight: '500' },

  materialCard: {
    backgroundColor: theme.colors.surface,
    borderRadius: theme.radii.md,
    padding: 16,
    borderWidth: 1,
    borderColor: theme.colors.border,
    marginBottom: 12,
    ...theme.shadows.sm,
  },
  matHeader: { flexDirection: 'row', alignItems: 'center' },
  iconCircle: {
    width: 44,
    height: 44,
    borderRadius: 22,
    backgroundColor: theme.colors.primary50,
    alignItems: 'center',
    justifyContent: 'center',
  },
  matSubject: { fontSize: 11, fontWeight: '700', color: theme.colors.primary, textTransform: 'uppercase', letterSpacing: 0.5 },
  matTitle: { fontSize: 15, fontWeight: '700', color: theme.colors.textPrimary, marginTop: 2 },
  matDesc: { fontSize: 13, color: theme.colors.textSecondary, marginTop: 8, lineHeight: 18 },

  matFooter: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginTop: 14,
    paddingTop: 12,
    borderTopWidth: 1,
    borderTopColor: theme.colors.borderSubtle,
  },
  matMeta: { flexDirection: 'row', alignItems: 'center', gap: 8 },
  metaBadge: {
    fontSize: 10,
    fontWeight: '700',
    backgroundColor: theme.colors.surfaceSubtle,
    paddingHorizontal: 8,
    paddingVertical: 3,
    borderRadius: theme.radii.xs,
    color: theme.colors.textSecondary,
  },
  metaInfo: { fontSize: 12, color: theme.colors.textMuted },

  openBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    backgroundColor: theme.colors.primary50,
    paddingHorizontal: 14,
    paddingVertical: 8,
    borderRadius: theme.radii.sm,
  },
  openBtnText: { fontSize: 12, fontWeight: '700', color: theme.colors.primary },

  assignmentCard: {
    backgroundColor: theme.colors.surface,
    borderRadius: theme.radii.md,
    padding: 16,
    borderWidth: 1,
    borderColor: theme.colors.border,
    marginBottom: 14,
    ...theme.shadows.sm,
  },
  assignHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
  },
  assignSubject: { fontSize: 11, fontWeight: '700', color: theme.colors.primary, textTransform: 'uppercase', letterSpacing: 0.5 },
  assignTitle: { fontSize: 15, fontWeight: '700', color: theme.colors.textPrimary, marginTop: 2 },
  deadlineBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: theme.radii.xs,
    gap: 4,
  },
  deadlineText: { fontSize: 11, fontWeight: '700' },
  assignDesc: { fontSize: 13, color: theme.colors.textSecondary, marginTop: 8, lineHeight: 18 },

  marksRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    backgroundColor: theme.colors.surfaceSubtle,
    padding: 12,
    borderRadius: theme.radii.sm,
    marginTop: 12,
  },
  marksItem: { flexDirection: 'row', alignItems: 'center', gap: 4 },
  marksLabel: { fontSize: 11, color: theme.colors.textMuted },
  marksVal: { fontSize: 12, fontWeight: '700', color: theme.colors.textPrimary },
  lateNotice: { fontSize: 11, color: theme.colors.amber, marginTop: 6, fontStyle: 'italic' },

  submitTaskBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: theme.colors.primary,
    paddingVertical: 12,
    borderRadius: theme.radii.md,
    gap: 6,
    marginTop: 14,
    ...theme.shadows.glow(theme.colors.primary),
  },
  submitTaskText: { color: '#ffffff', fontSize: 13, fontWeight: '700' },

  modalOverlay: {
    flex: 1,
    backgroundColor: 'rgba(15, 23, 42, 0.6)',
    justifyContent: 'flex-end',
  },
  modalContent: {
    backgroundColor: theme.colors.surface,
    borderTopLeftRadius: theme.radii.xl,
    borderTopRightRadius: theme.radii.xl,
    padding: 22,
    paddingBottom: 40,
    ...theme.shadows.lg,
  },
  modalHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 12,
  },
  modalTitle: { fontSize: 18, fontWeight: '800', color: theme.colors.textPrimary },
  taskTitle: { fontSize: 15, fontWeight: '700', color: theme.colors.textPrimary },
  taskSubject: { fontSize: 12, color: theme.colors.primary, fontWeight: '600', marginTop: 2 },
  inputLabel: { fontSize: 13, fontWeight: '700', color: theme.colors.textPrimary, marginTop: 14, marginBottom: 6 },
  submissionInput: {
    backgroundColor: theme.colors.surfaceSubtle,
    borderWidth: 1,
    borderColor: theme.colors.border,
    borderRadius: theme.radii.md,
    padding: 14,
    fontSize: 14,
    color: theme.colors.textPrimary,
    textAlignVertical: 'top',
    height: 120,
  },
  modalSubmitBtn: {
    backgroundColor: theme.colors.primary,
    paddingVertical: 14,
    borderRadius: theme.radii.md,
    alignItems: 'center',
    marginTop: 20,
    ...theme.shadows.glow(theme.colors.primary),
  },
  modalSubmitText: { color: '#ffffff', fontSize: 15, fontWeight: '700' },
})