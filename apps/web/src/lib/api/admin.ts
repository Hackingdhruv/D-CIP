import { apiFetch } from '@/lib/api-client'
import type {
  AdminOverviewStats,
  AdminUserListResponse,
  AdminUserRead,
  AiConfigRead,
  AiUsageStats,
  AuditSearchResponse,
  AuditStats,
  ConfigEntry,
  ConfigUpdateRequest,
  InviteUserRequest,
  LockUserRequest,
  RecommendationsResponse,
  SecurityOverview,
  SessionListResponse,
  StorageOverview,
  SystemHealthResponse,
} from '@/types/admin'

const BASE = '/v1/admin'

export const adminApi = {
  // Overview
  getStats: (): Promise<AdminOverviewStats> =>
    apiFetch(`${BASE}/stats`),

  // Identity — Users
  listUsers: (params?: {
    q?: string
    isActive?: boolean
    isLocked?: boolean
    page?: number
    pageSize?: number
  }): Promise<AdminUserListResponse> => {
    const sp = new URLSearchParams()
    if (params?.q) sp.set('q', params.q)
    if (params?.isActive !== undefined) sp.set('is_active', String(params.isActive))
    if (params?.isLocked !== undefined) sp.set('is_locked', String(params.isLocked))
    if (params?.page) sp.set('page', String(params.page))
    if (params?.pageSize) sp.set('page_size', String(params.pageSize))
    const qs = sp.toString()
    return apiFetch(`${BASE}/users${qs ? `?${qs}` : ''}`)
  },

  getUser: (id: string): Promise<AdminUserRead> =>
    apiFetch(`${BASE}/users/${id}`),

  lockUser: (id: string, body: LockUserRequest): Promise<AdminUserRead> =>
    apiFetch(`${BASE}/users/${id}/lock`, { method: 'POST', body }),

  unlockUser: (id: string): Promise<AdminUserRead> =>
    apiFetch(`${BASE}/users/${id}/unlock`, { method: 'POST' }),

  inviteUser: (body: InviteUserRequest): Promise<AdminUserRead> =>
    apiFetch(`${BASE}/users/invite`, { method: 'POST', body }),

  forcePasswordReset: (id: string): Promise<void> =>
    apiFetch(`${BASE}/users/${id}/force-password-reset`, { method: 'POST' }),

  // Sessions
  listSessions: (params?: {
    userId?: string
    isActive?: boolean
    page?: number
    pageSize?: number
  }): Promise<SessionListResponse> => {
    const sp = new URLSearchParams()
    if (params?.userId) sp.set('user_id', params.userId)
    if (params?.isActive !== undefined) sp.set('is_active', String(params.isActive))
    if (params?.page) sp.set('page', String(params.page))
    if (params?.pageSize) sp.set('page_size', String(params.pageSize))
    const qs = sp.toString()
    return apiFetch(`${BASE}/sessions${qs ? `?${qs}` : ''}`)
  },

  revokeSession: (id: string): Promise<void> =>
    apiFetch(`${BASE}/sessions/${id}`, { method: 'DELETE' }),

  revokeUserSessions: (userId: string): Promise<void> =>
    apiFetch(`${BASE}/users/${userId}/sessions`, { method: 'DELETE' }),

  // Audit Center
  searchAudit: (params?: {
    q?: string
    eventType?: string
    userId?: string
    dateFrom?: string
    dateTo?: string
    page?: number
    pageSize?: number
  }): Promise<AuditSearchResponse> => {
    const sp = new URLSearchParams()
    if (params?.q) sp.set('q', params.q)
    if (params?.eventType) sp.set('event_type', params.eventType)
    if (params?.userId) sp.set('user_id', params.userId)
    if (params?.dateFrom) sp.set('date_from', params.dateFrom)
    if (params?.dateTo) sp.set('date_to', params.dateTo)
    if (params?.page) sp.set('page', String(params.page))
    if (params?.pageSize) sp.set('page_size', String(params.pageSize))
    const qs = sp.toString()
    return apiFetch(`${BASE}/audit${qs ? `?${qs}` : ''}`)
  },

  getAuditStats: (): Promise<AuditStats> =>
    apiFetch(`${BASE}/audit/stats`),

  // Security Center
  getSecurityOverview: (): Promise<SecurityOverview> =>
    apiFetch(`${BASE}/security`),

  // System Health
  getSystemHealth: (): Promise<SystemHealthResponse> =>
    apiFetch(`${BASE}/system/health`),

  getRecommendations: (): Promise<RecommendationsResponse> =>
    apiFetch(`${BASE}/system/recommendations`),

  // AI Administration
  getAiConfig: (): Promise<AiConfigRead> =>
    apiFetch(`${BASE}/ai/config`),

  getAiStats: (): Promise<AiUsageStats> =>
    apiFetch(`${BASE}/ai/stats`),

  // Storage Center
  getStorageOverview: (): Promise<StorageOverview> =>
    apiFetch(`${BASE}/storage`),

  // Configuration Center
  listConfig: (): Promise<ConfigEntry[]> =>
    apiFetch(`${BASE}/config`),

  getConfig: (key: string): Promise<ConfigEntry> =>
    apiFetch(`${BASE}/config/${encodeURIComponent(key)}`),

  setConfig: (key: string, body: ConfigUpdateRequest): Promise<ConfigEntry> =>
    apiFetch(`${BASE}/config/${encodeURIComponent(key)}`, { method: 'PUT', body }),
}
