import { useQuery } from '@tanstack/react-query'
import { dashboardApi } from '@/lib/api/dashboard'

// Executive — refresh every 60 seconds
export function useExecutiveDashboard() {
  return useQuery({
    queryKey: ['dashboard', 'executive'],
    queryFn: dashboardApi.executive,
    refetchInterval: 60_000,
    staleTime: 30_000,
  })
}

// Intelligence — refresh every 90 seconds (heavier queries)
export function useIntelligenceDashboard() {
  return useQuery({
    queryKey: ['dashboard', 'intelligence'],
    queryFn: dashboardApi.intelligence,
    refetchInterval: 90_000,
    staleTime: 60_000,
  })
}

// Operations — refresh every 15 seconds (health monitoring)
export function useOperationsDashboard() {
  return useQuery({
    queryKey: ['dashboard', 'operations'],
    queryFn: dashboardApi.operations,
    refetchInterval: 15_000,
    staleTime: 10_000,
  })
}

// Investigator — refresh every 30 seconds
export function useInvestigatorDashboard() {
  return useQuery({
    queryKey: ['dashboard', 'investigator'],
    queryFn: dashboardApi.investigator,
    refetchInterval: 30_000,
    staleTime: 20_000,
  })
}
