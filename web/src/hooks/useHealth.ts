import { useQuery } from '@tanstack/react-query'
import { fetchHealth, fetchDetailedHealth } from '@/api/health'

export function useHealth() {
  return useQuery({
    queryKey: ['health'],
    queryFn: fetchHealth,
    refetchInterval: 30_000,
  })
}

export function useDetailedHealth() {
  return useQuery({
    queryKey: ['health', 'detailed'],
    queryFn: fetchDetailedHealth,
    refetchInterval: 60_000,
  })
}
