import React, { useCallback, useEffect, useState } from 'react'
import { ActivityIndicator, Alert, Image, Modal, ScrollView, StyleSheet, Text, TextInput, TouchableOpacity, View } from 'react-native'
import { SafeAreaView } from 'react-native-safe-area-context'
import { Ionicons } from '@expo/vector-icons'
import { apiClient } from '../../api/client'
import { useAuthStore } from '../../store/authStore'

type Student = {
  id: string
  full_name: string
  admission_number: string
  class_name?: string | null
  section_name?: string | null
  course_name?: string | null
  semester?: number | null
  roll_number?: string | null
  phone?: string | null
  status: string
}
type StudentCard = {
  full_name: string
  admission_number: string
  institution_name: string
  class_or_course: string
  section_or_semester: string
  photo_url?: string | null
}

export default function StudentsScreen() {
  const user = useAuthStore((state) => state.user)
  const role = user?.current_role || user?.role
  const isAdmin = role === 'INSTITUTION_ADMIN'
  const institution = user?.institutions?.find((item) => item.tenant_id === (user.current_tenant_id || user.tenant_id))
  const isSchool = institution?.institution_type === 'SCHOOL'
  const [students, setStudents] = useState<Student[]>([])
  const [query, setQuery] = useState('')
  const [search, setSearch] = useState('')
  const [page, setPage] = useState(1)
  const [pages, setPages] = useState(1)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [selected, setSelected] = useState<Student | null>(null)
  const [card, setCard] = useState<StudentCard | null>(null)
  const [editing, setEditing] = useState(false)
  const [name, setName] = useState('')
  const [phone, setPhone] = useState('')
  const [roll, setRoll] = useState('')
  const [saving, setSaving] = useState(false)

  const load = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const response = await apiClient.get('/students', { params: { search: search || undefined, page, size: 20 } })
      setStudents(response.data.data.items)
      setPages(response.data.data.pages || 1)
    } catch (err: any) {
      setStudents([])
      setError(err.message || 'Unable to load students.')
    } finally { setLoading(false) }
  }, [search, page, user?.current_tenant_id, user?.tenant_id])
  useEffect(() => { void load() }, [load])

  const openStudent = (student: Student, edit: boolean) => {
    setSelected(student)
    setName(student.full_name)
    setPhone(student.phone || '')
    setRoll(student.roll_number || '')
    setEditing(edit)
  }
  const save = async () => {
    if (!selected || !name.trim() || saving) return
    setSaving(true)
    try {
      await apiClient.put('/students/' + selected.id, { full_name: name.trim(), phone, roll_number: roll })
      setSelected(null)
      await load()
    } catch (err: any) { Alert.alert('Student', err.message || 'Unable to save student.') }
    finally { setSaving(false) }
  }
  const openCard = async (student: Student) => {
    try {
      const response = await apiClient.get('/students/' + student.id + '/id-card')
      setCard(response.data.data)
    } catch (err: any) { Alert.alert('ID card', err.message || 'Unable to load the ID card.') }
  }
  const photoUrl = card?.photo_url?.startsWith('/api/v1/')
    ? (apiClient.defaults.baseURL || '').replace(/\/api\/v1\/?$/, '') + card.photo_url
    : card?.photo_url
  const deactivate = (student: Student) => Alert.alert('Deactivate student?', student.full_name, [
    { text: 'Cancel', style: 'cancel' },
    { text: 'Deactivate', style: 'destructive', onPress: async () => {
      try { await apiClient.delete('/students/' + student.id); await load() }
      catch (err: any) { Alert.alert('Student', err.message || 'Unable to deactivate student.') }
    } },
  ])

  return <SafeAreaView style={styles.screen}>
    <ScrollView contentContainerStyle={styles.content} keyboardShouldPersistTaps="handled">
      <Text style={styles.title}>Students</Text>
      <View style={styles.searchRow}>
        <TextInput accessibilityLabel="Search students" placeholder="Name, admission or roll number" value={query} onChangeText={setQuery} style={styles.input} />
        <TouchableOpacity accessibilityRole="button" accessibilityLabel="Search" style={styles.searchButton} onPress={() => { setPage(1); setSearch(query.trim()) }}><Ionicons name="search" size={20} color="white" /></TouchableOpacity>
      </View>
      {error ? <Text style={styles.error}>{error}</Text> : null}
      {loading ? <ActivityIndicator color="#6366f1" /> : students.length === 0 ? <Text style={styles.muted}>No students found.</Text> : students.map((student) => <View key={student.id} style={styles.card}>
        <View style={styles.cardHeader}><View style={{ flex: 1 }}><Text style={styles.name}>{student.full_name}</Text><Text style={styles.muted}>{student.admission_number}</Text></View><Text style={styles.status}>{student.status}</Text></View>
        <Text style={styles.detail}>{isSchool ? 'Class' : 'Course'}  {isSchool ? student.class_name || '—' : student.course_name || '—'}</Text>
        <Text style={styles.detail}>{isSchool ? 'Section' : 'Semester'}  {isSchool ? student.section_name || '—' : student.semester ? String(student.semester) : '—'}</Text>
        <View style={styles.actions}>
          <TouchableOpacity accessibilityRole="button" accessibilityLabel={'View profile for ' + student.full_name} style={styles.icon} onPress={() => openStudent(student, false)}><Ionicons name="eye-outline" size={18} color="#334155" /></TouchableOpacity>
          {isAdmin && <TouchableOpacity accessibilityRole="button" accessibilityLabel={'Edit ' + student.full_name} style={styles.icon} onPress={() => openStudent(student, true)}><Ionicons name="create-outline" size={18} color="#334155" /></TouchableOpacity>}
          {(isAdmin || role === 'TEACHER') && <TouchableOpacity accessibilityRole="button" accessibilityLabel={'View ID card for ' + student.full_name} style={styles.icon} onPress={() => void openCard(student)}><Ionicons name="card-outline" size={18} color="#334155" /></TouchableOpacity>}
          {isAdmin && student.status === 'ACTIVE' && <TouchableOpacity accessibilityRole="button" accessibilityLabel={'Deactivate ' + student.full_name} style={[styles.icon, styles.danger]} onPress={() => deactivate(student)}><Ionicons name="person-remove-outline" size={18} color="#ef4444" /></TouchableOpacity>}
        </View>
      </View>)}
      {pages > 1 && <View style={styles.pagination}><TouchableOpacity disabled={page <= 1} onPress={() => setPage(page - 1)}><Text style={styles.link}>Previous</Text></TouchableOpacity><Text>{page} / {pages}</Text><TouchableOpacity disabled={page >= pages} onPress={() => setPage(page + 1)}><Text style={styles.link}>Next</Text></TouchableOpacity></View>}
    </ScrollView>
    <Modal visible={Boolean(card)} animationType="slide" transparent onRequestClose={() => setCard(null)}><View style={styles.overlay}><View style={styles.dialog}>
      <Text style={styles.name}>{card?.institution_name}</Text>
      {photoUrl ? <Image source={{ uri: photoUrl }} style={{ width: 76, height: 76, borderRadius: 38, marginTop: 16 }} /> : null}
      <Text style={styles.name}>{card?.full_name}</Text>
      <Text style={styles.detail}>Admission number  {card?.admission_number}</Text>
      <Text style={styles.detail}>{isSchool ? 'Class' : 'Course'}  {card?.class_or_course}</Text>
      <Text style={styles.detail}>{isSchool ? 'Section' : 'Semester'}  {card?.section_or_semester}</Text>
      <View style={styles.dialogActions}><TouchableOpacity onPress={() => setCard(null)}><Text style={styles.link}>Close</Text></TouchableOpacity></View>
    </View></View></Modal>
    <Modal visible={Boolean(selected)} animationType="slide" transparent onRequestClose={() => setSelected(null)}><View style={styles.overlay}><View style={styles.dialog}>
      <Text style={styles.name}>{editing ? 'Edit student' : 'Student profile'}</Text>
      {editing ? <><Text style={styles.label}>Full name</Text><TextInput accessibilityLabel="Full name" style={styles.field} value={name} onChangeText={setName} /><Text style={styles.label}>Phone</Text><TextInput accessibilityLabel="Phone" style={styles.field} value={phone} onChangeText={setPhone} keyboardType="phone-pad" /><Text style={styles.label}>Roll number</Text><TextInput accessibilityLabel="Roll number" style={styles.field} value={roll} onChangeText={setRoll} /></> : <><Text style={styles.detail}>{selected?.full_name}</Text><Text style={styles.detail}>Admission number  {selected?.admission_number}</Text><Text style={styles.detail}>{isSchool ? 'Class' : 'Course'}  {(isSchool ? selected?.class_name : selected?.course_name) || '—'}</Text><Text style={styles.detail}>{isSchool ? 'Section' : 'Semester'}  {(isSchool ? selected?.section_name : selected?.semester) || '—'}</Text><Text style={styles.detail}>Roll number  {selected?.roll_number || '—'}</Text><Text style={styles.detail}>Phone  {selected?.phone || '—'}</Text></>}
      <View style={styles.dialogActions}><TouchableOpacity onPress={() => setSelected(null)} disabled={saving}><Text style={styles.link}>Close</Text></TouchableOpacity>{editing && <TouchableOpacity onPress={save} disabled={saving || !name.trim()}><Text style={styles.link}>{saving ? 'Saving…' : 'Save'}</Text></TouchableOpacity>}</View>
    </View></View></Modal>
  </SafeAreaView>
}

const styles = StyleSheet.create({
  screen: { flex: 1, backgroundColor: '#f8fafc' }, content: { padding: 18, paddingBottom: 40 }, title: { fontSize: 24, fontWeight: '800', color: '#0f172a', marginBottom: 16 }, searchRow: { flexDirection: 'row', gap: 8, marginBottom: 16 }, input: { flex: 1, backgroundColor: '#fff', borderWidth: 1, borderColor: '#e2e8f0', borderRadius: 10, padding: 12 }, searchButton: { backgroundColor: '#6366f1', borderRadius: 10, padding: 13 }, error: { color: '#b91c1c', marginBottom: 12 }, muted: { fontSize: 13, color: '#64748b', marginTop: 4 }, card: { backgroundColor: '#fff', borderColor: '#e2e8f0', borderWidth: 1, borderRadius: 12, padding: 14, marginBottom: 10 }, cardHeader: { flexDirection: 'row', alignItems: 'center', marginBottom: 8 }, name: { fontSize: 16, fontWeight: '700', color: '#0f172a' }, status: { color: '#4f46e5', fontSize: 12 }, detail: { fontSize: 14, color: '#334155', marginTop: 6 }, actions: { flexDirection: 'row', justifyContent: 'flex-end', gap: 8, marginTop: 10 }, icon: { width: 40, height: 40, borderWidth: 1, borderColor: '#e2e8f0', borderRadius: 8, alignItems: 'center', justifyContent: 'center' }, danger: { borderColor: '#fee2e2', backgroundColor: '#fff5f5' }, pagination: { flexDirection: 'row', justifyContent: 'space-between', padding: 12 }, link: { color: '#4f46e5', fontWeight: '700' }, overlay: { flex: 1, justifyContent: 'center', backgroundColor: '#0008', padding: 20 }, dialog: { backgroundColor: '#fff', borderRadius: 14, padding: 20 }, label: { color: '#475569', marginTop: 12 }, field: { borderWidth: 1, borderColor: '#cbd5e1', borderRadius: 8, padding: 10, marginTop: 4 }, dialogActions: { flexDirection: 'row', justifyContent: 'flex-end', gap: 24, marginTop: 22 },
})
