import { apiFetch } from '@/lib/api-client'
import type {
  AlertNotificationRead,
  AlertStats,
  NotificationCount,
  NotificationListResponse,
  WatchlistAlertListResponse,
  WatchlistAlertRead,
  WatchlistCreate,
  WatchlistEntryCreate,
  WatchlistEntryListResponse,
  WatchlistEntryRead,
  WatchlistListResponse,
  WatchlistRead,
  WatchlistStats,
  WatchlistUpdate,
} from '@/types/watchlist'

const WL = '/v1/watchlists'
const AL = '/v1/alerts'
const NL = '/v1/notifications'

// ── Watchlists ─────────────────────────────────────────────────────────────────

export const watchlistApi = {
  getStats: (): Promise<WatchlistStats> =>
    apiFetch(`${WL}/stats`),

  list: (params?: {
    page?: number
    pageSize?: number
    watchlistType?: string
    isActive?: boolean
    caseId?: string
    includeGlobal?: boolean
  }): Promise<WatchlistListResponse> => {
    const sp = new URLSearchParams()
    if (params?.page) sp.set('page', String(params.page))
    if (params?.pageSize) sp.set('page_size', String(params.pageSize))
    if (params?.watchlistType) sp.set('watchlist_type', params.watchlistType)
    if (params?.isActive !== undefined) sp.set('is_active', String(params.isActive))
    if (params?.caseId) sp.set('case_id', params.caseId)
    if (params?.includeGlobal !== undefined) sp.set('include_global', String(params.includeGlobal))
    return apiFetch(`${WL}?${sp}`)
  },

  get: (id: string): Promise<WatchlistRead> =>
    apiFetch(`${WL}/${id}`),

  create: (body: WatchlistCreate): Promise<WatchlistRead> =>
    apiFetch(WL, { method: 'POST', body }),

  update: (id: string, body: WatchlistUpdate): Promise<WatchlistRead> =>
    apiFetch(`${WL}/${id}`, { method: 'PUT', body }),

  delete: (id: string): Promise<void> =>
    apiFetch(`${WL}/${id}`, { method: 'DELETE' }),

  // Entries
  listEntries: (watchlistId: string): Promise<WatchlistEntryListResponse> =>
    apiFetch(`${WL}/${watchlistId}/entries`),

  addEntry: (watchlistId: string, body: WatchlistEntryCreate): Promise<WatchlistEntryRead> =>
    apiFetch(`${WL}/${watchlistId}/entries`, { method: 'POST', body }),

  deleteEntry: (entryId: string): Promise<void> =>
    apiFetch(`${WL}/entries/${entryId}`, { method: 'DELETE' }),
}

// ── Alerts ─────────────────────────────────────────────────────────────────────

export const alertApi = {
  getStats: (caseId?: string): Promise<AlertStats> => {
    const sp = new URLSearchParams()
    if (caseId) sp.set('case_id', caseId)
    return apiFetch(`${AL}/stats?${sp}`)
  },

  list: (params?: {
    page?: number
    pageSize?: number
    caseId?: string
    status?: string
    severity?: string
    alertType?: string
    isCrossCase?: boolean
  }): Promise<WatchlistAlertListResponse> => {
    const sp = new URLSearchParams()
    if (params?.page) sp.set('page', String(params.page))
    if (params?.pageSize) sp.set('page_size', String(params.pageSize))
    if (params?.caseId) sp.set('case_id', params.caseId)
    if (params?.status) sp.set('status', params.status)
    if (params?.severity) sp.set('severity', params.severity)
    if (params?.alertType) sp.set('alert_type', params.alertType)
    if (params?.isCrossCase !== undefined) sp.set('is_cross_case', String(params.isCrossCase))
    return apiFetch(`${AL}?${sp}`)
  },

  get: (id: string): Promise<WatchlistAlertRead> =>
    apiFetch(`${AL}/${id}`),

  acknowledge: (id: string): Promise<WatchlistAlertRead> =>
    apiFetch(`${AL}/${id}/acknowledge`, { method: 'POST' }),

  resolve: (id: string): Promise<WatchlistAlertRead> =>
    apiFetch(`${AL}/${id}/resolve`, { method: 'POST' }),

  dismiss: (id: string): Promise<WatchlistAlertRead> =>
    apiFetch(`${AL}/${id}/dismiss`, { method: 'POST' }),
}

// ── Notifications ──────────────────────────────────────────────────────────────

export const notificationApi = {
  getCount: (): Promise<NotificationCount> =>
    apiFetch(`${NL}/count`),

  list: (params?: {
    page?: number
    pageSize?: number
    unreadOnly?: boolean
    includeArchived?: boolean
  }): Promise<NotificationListResponse> => {
    const sp = new URLSearchParams()
    if (params?.page) sp.set('page', String(params.page))
    if (params?.pageSize) sp.set('page_size', String(params.pageSize))
    if (params?.unreadOnly) sp.set('unread_only', 'true')
    if (params?.includeArchived) sp.set('include_archived', 'true')
    return apiFetch(`${NL}?${sp}`)
  },

  markRead: (id: string): Promise<AlertNotificationRead> =>
    apiFetch(`${NL}/${id}/read`, { method: 'POST' }),

  markAllRead: (): Promise<{ marked_read: number }> =>
    apiFetch(`${NL}/read-all`, { method: 'POST' }),

  archive: (id: string): Promise<{ archived: boolean }> =>
    apiFetch(`${NL}/${id}/archive`, { method: 'POST' }),

  delete: (id: string): Promise<void> =>
    apiFetch(`${NL}/${id}`, { method: 'DELETE' }),
}
