import { Redirect } from 'expo-router'
import { useAuthStore } from '@/store/authStore'

export default function Index() {
  const { is_authenticated } = useAuthStore()
  return <Redirect href={is_authenticated ? '/(app)/dashboard' : '/(auth)/login'} />
}
