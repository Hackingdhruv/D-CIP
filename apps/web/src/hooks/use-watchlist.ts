import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { alertApi, notificationApi, watchlistApi } from '@/lib/api/watchlist'
import type { WatchlistCreate, WatchlistEntryCreate, WatchlistUpdate } from '@/types/watchlist'

// ── Query keys ──────────────────────────────────────────────────────────────────

export const watchlistKeys = {
  all: ['watchlists'] as const,
  stats: ['watchlists', 'stats'] as const,
  list: (params?: object) => ['watchlists', 'list', params] as const,
  detail: (id: string) => ['watchlists', id] as const,
  entries: (id: string) => ['watchlists', id, 'entries'] as const,
}

export const alertKeys = {
  all: ['alerts'] as const,
  stats: (caseId?: string) => ['alerts', 'stats', caseId] as const,
  list: (params?: object) => ['alerts', 'list', params] as const,
  detail: (id: string) => ['alerts', id] as const,
}

export const notificationKeys = {
  count: ['notifications', 'count'] as const,
  list: (params?: object) => ['notifications', 'list', params] as const,
}

// ── Watchlist queries ───────────────────────────────────────────────────────────

export function useWatchlistStats() {
  return useQuery({
    queryKey: watchlistKeys.stats,
    queryFn: watchlistApi.getStats,
    refetchInterval: 60_000,
  })
}

export function useWatchlists(params?: {
  page?: number
  pageSize?: number
  watchlistType?: string
  isActive?: boolean
  caseId?: string
  includeGlobal?: boolean
}) {
  return useQuery({
    queryKey: watchlistKeys.list(params),
    queryFn: () => watchlistApi.list(params),
    placeholderData: (prev) => prev,
  })
}

export function useWatchlist(id: string) {
  return useQuery({
    queryKey: watchlistKeys.detail(id),
    queryFn: () => watchlistApi.get(id),
    enabled: Boolean(id),
  })
}

export function useWatchlistEntries(watchlistId: string) {
  return useQuery({
    queryKey: watchlistKeys.entries(watchlistId),
    queryFn: () => watchlistApi.listEntries(watchlistId),
    enabled: Boolean(watchlistId),
  })
}

// ── Watchlist mutations ─────────────────────────────────────────────────────────

export function useCreateWatchlist() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: WatchlistCreate) => watchlistApi.create(body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: watchlistKeys.all })
    },
  })
}

export function useUpdateWatchlist() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, body }: { id: string; body: WatchlistUpdate }) =>
      watchlistApi.update(id, body),
    onSuccess: (_data, { id }) => {
      qc.invalidateQueries({ queryKey: watchlistKeys.detail(id) })
      qc.invalidateQueries({ queryKey: watchlistKeys.all })
    },
  })
}

export function useDeleteWatchlist() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => watchlistApi.delete(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: watchlistKeys.all })
    },
  })
}

export function useAddWatchlistEntry() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ watchlistId, body }: { watchlistId: string; body: WatchlistEntryCreate }) =>
      watchlistApi.addEntry(watchlistId, body),
    onSuccess: (_data, { watchlistId }) => {
      qc.invalidateQueries({ queryKey: watchlistKeys.entries(watchlistId) })
      qc.invalidateQueries({ queryKey: watchlistKeys.detail(watchlistId) })
    },
  })
}

export function useDeleteWatchlistEntry() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ entryId }: { entryId: string; watchlistId: string }) =>
      watchlistApi.deleteEntry(entryId),
    onSuccess: (_data, { watchlistId }) => {
      qc.invalidateQueries({ queryKey: watchlistKeys.entries(watchlistId) })
      qc.invalidateQueries({ queryKey: watchlistKeys.detail(watchlistId) })
    },
  })
}

// ── Alert queries ───────────────────────────────────────────────────────────────

export function useAlertStats(caseId?: string) {
  return useQuery({
    queryKey: alertKeys.stats(caseId),
    queryFn: () => alertApi.getStats(caseId),
    refetchInterval: 30_000,
  })
}

export function useAlerts(params?: {
  page?: number
  pageSize?: number
  caseId?: string
  status?: string
  severity?: string
  alertType?: string
  isCrossCase?: boolean
}) {
  return useQuery({
    queryKey: alertKeys.list(params),
    queryFn: () => alertApi.list(params),
    refetchInterval: 30_000,
    placeholderData: (prev) => prev,
  })
}

export function useAlert(id: string) {
  return useQuery({
    queryKey: alertKeys.detail(id),
    queryFn: () => alertApi.get(id),
    enabled: Boolean(id),
  })
}

// ── Alert mutations ─────────────────────────────────────────────────────────────

export function useAcknowledgeAlert() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => alertApi.acknowledge(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: alertKeys.all }),
  })
}

export function useResolveAlert() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => alertApi.resolve(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: alertKeys.all }),
  })
}

export function useDismissAlert() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => alertApi.dismiss(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: alertKeys.all }),
  })
}

// ── Notification queries ────────────────────────────────────────────────────────

export function useNotificationCount(enabled = true) {
  return useQuery({
    queryKey: notificationKeys.count,
    queryFn: notificationApi.getCount,
    refetchInterval: 30_000,
    enabled,
  })
}

export function useNotificationList(params?: {
  page?: number
  pageSize?: number
  unreadOnly?: boolean
  includeArchived?: boolean
}) {
  return useQuery({
    queryKey: notificationKeys.list(params),
    queryFn: () => notificationApi.list(params),
    placeholderData: (prev) => prev,
  })
}

// ── Notification mutations ──────────────────────────────────────────────────────

export function useMarkNotificationRead() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => notificationApi.markRead(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: notificationKeys.count })
      qc.invalidateQueries({ queryKey: ['notifications', 'list'] })
    },
  })
}

export function useMarkAllNotificationsRead() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: notificationApi.markAllRead,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: notificationKeys.count })
      qc.invalidateQueries({ queryKey: ['notifications', 'list'] })
    },
  })
}

export function useArchiveNotification() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => notificationApi.archive(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['notifications', 'list'] }),
  })
}

export function useDeleteNotification() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => notificationApi.delete(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: notificationKeys.count })
      qc.invalidateQueries({ queryKey: ['notifications', 'list'] })
    },
  })
}
