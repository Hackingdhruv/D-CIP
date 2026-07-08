import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { adminApi } from '@/lib/api/admin'
import type {
  ConfigUpdateRequest,
  InviteUserRequest,
  LockUserRequest,
} from '@/types/admin'

// ── Query keys ─────────────────────────────────────────────────────────────────
export const adminKeys = {
  stats: ['admin', 'stats'] as const,
  users: (params?: object) => ['admin', 'users', params] as const,
  user: (id: string) => ['admin', 'users', id] as const,
  sessions: (params?: object) => ['admin', 'sessions', params] as const,
  audit: (params?: object) => ['admin', 'audit', params] as const,
  auditStats: ['admin', 'audit', 'stats'] as const,
  security: ['admin', 'security'] as const,
  health: ['admin', 'system', 'health'] as const,
  recommendations: ['admin', 'system', 'recommendations'] as const,
  aiConfig: ['admin', 'ai', 'config'] as const,
  aiStats: ['admin', 'ai', 'stats'] as const,
  storage: ['admin', 'storage'] as const,
  config: ['admin', 'config'] as const,
  configKey: (key: string) => ['admin', 'config', key] as const,
}

// ── Overview ───────────────────────────────────────────────────────────────────
export function useAdminStats() {
  return useQuery({
    queryKey: adminKeys.stats,
    queryFn: adminApi.getStats,
    refetchInterval: 30_000,
  })
}

// ── Identity ───────────────────────────────────────────────────────────────────
export function useAdminUsers(params?: {
  q?: string
  isActive?: boolean
  isLocked?: boolean
  page?: number
  pageSize?: number
}) {
  return useQuery({
    queryKey: adminKeys.users(params),
    queryFn: () => adminApi.listUsers(params),
    placeholderData: (prev) => prev,
  })
}

export function useAdminUser(id: string) {
  return useQuery({
    queryKey: adminKeys.user(id),
    queryFn: () => adminApi.getUser(id),
    enabled: !!id,
  })
}

export function useLockUser() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, body }: { id: string; body: LockUserRequest }) =>
      adminApi.lockUser(id, body),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['admin', 'users'] }) },
  })
}

export function useUnlockUser() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => adminApi.unlockUser(id),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['admin', 'users'] }) },
  })
}

export function useInviteUser() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: InviteUserRequest) => adminApi.inviteUser(body),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['admin', 'users'] }) },
  })
}

export function useForcePasswordReset() {
  return useMutation({
    mutationFn: (id: string) => adminApi.forcePasswordReset(id),
  })
}

// ── Sessions ───────────────────────────────────────────────────────────────────
export function useAdminSessions(params?: {
  userId?: string
  isActive?: boolean
  page?: number
  pageSize?: number
}) {
  return useQuery({
    queryKey: adminKeys.sessions(params),
    queryFn: () => adminApi.listSessions(params),
    refetchInterval: 30_000,
    placeholderData: (prev) => prev,
  })
}

export function useRevokeSession() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => adminApi.revokeSession(id),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['admin', 'sessions'] }) },
  })
}

export function useRevokeUserSessions() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (userId: string) => adminApi.revokeUserSessions(userId),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['admin', 'sessions'] }) },
  })
}

// ── Audit Center ───────────────────────────────────────────────────────────────
export function useAuditSearch(params?: {
  q?: string
  eventType?: string
  userId?: string
  dateFrom?: string
  dateTo?: string
  page?: number
  pageSize?: number
}) {
  return useQuery({
    queryKey: adminKeys.audit(params),
    queryFn: () => adminApi.searchAudit(params),
    placeholderData: (prev) => prev,
  })
}

export function useAuditStats() {
  return useQuery({
    queryKey: adminKeys.auditStats,
    queryFn: adminApi.getAuditStats,
    refetchInterval: 60_000,
  })
}

// ── Security Center ────────────────────────────────────────────────────────────
export function useSecurityOverview() {
  return useQuery({
    queryKey: adminKeys.security,
    queryFn: adminApi.getSecurityOverview,
    refetchInterval: 30_000,
  })
}

// ── System Health ──────────────────────────────────────────────────────────────
export function useSystemHealth() {
  return useQuery({
    queryKey: adminKeys.health,
    queryFn: adminApi.getSystemHealth,
    refetchInterval: 15_000,
  })
}

export function useRecommendations() {
  return useQuery({
    queryKey: adminKeys.recommendations,
    queryFn: adminApi.getRecommendations,
    refetchInterval: 60_000,
  })
}

// ── AI Administration ──────────────────────────────────────────────────────────
export function useAiConfig() {
  return useQuery({
    queryKey: adminKeys.aiConfig,
    queryFn: adminApi.getAiConfig,
  })
}

export function useAiStats() {
  return useQuery({
    queryKey: adminKeys.aiStats,
    queryFn: adminApi.getAiStats,
    refetchInterval: 60_000,
  })
}

// ── Storage Center ─────────────────────────────────────────────────────────────
export function useStorageOverview() {
  return useQuery({
    queryKey: adminKeys.storage,
    queryFn: adminApi.getStorageOverview,
    refetchInterval: 120_000,
  })
}

// ── Configuration Center ───────────────────────────────────────────────────────
export function useAdminConfig() {
  return useQuery({
    queryKey: adminKeys.config,
    queryFn: adminApi.listConfig,
  })
}

export function useSetConfig() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ key, body }: { key: string; body: ConfigUpdateRequest }) =>
      adminApi.setConfig(key, body),
    onSuccess: () => { qc.invalidateQueries({ queryKey: adminKeys.config }) },
  })
}
