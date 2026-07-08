// Watchlist & Alert domain types

export type WatchlistType =
  | 'email'
  | 'phone'
  | 'domain'
  | 'url'
  | 'ip_address'
  | 'sha256'
  | 'md5'
  | 'crypto_wallet'
  | 'bank_account'
  | 'vehicle_registration'
  | 'passport'
  | 'device_id'
  | 'imei'
  | 'mac_address'
  | 'regex'
  | 'keyword'

export type AlertType =
  | 'exact_match'
  | 'regex_match'
  | 'fuzzy_match'
  | 'cross_case_match'
  | 'high_risk_match'
  | 'repeated_appearance'
  | 'ai_alert'
  | 'manual_alert'
  | 'system_alert'

export type AlertSeverity = 'critical' | 'high' | 'medium' | 'low' | 'info'

export type AlertStatus = 'new' | 'acknowledged' | 'resolved' | 'dismissed'

export type NotificationLevel = 'info' | 'warning' | 'error' | 'critical'

// ── Watchlist ──────────────────────────────────────────────────────────────────

export interface WatchlistRead {
  id: string
  name: string
  description: string | null
  watchlistType: WatchlistType
  isActive: boolean
  caseId: string | null
  createdById: string | null
  createdByEmail: string | null
  entryCount: number
  alertCount: number
  createdAt: string
  updatedAt: string
}

export interface WatchlistListResponse {
  items: WatchlistRead[]
  total: number
  page: number
  pages: number
}

export interface WatchlistCreate {
  name: string
  description?: string | null
  watchlistType: WatchlistType
  isActive?: boolean
  caseId?: string | null
}

export interface WatchlistUpdate {
  name?: string
  description?: string | null
  watchlistType?: WatchlistType
  isActive?: boolean
}

export interface WatchlistStats {
  totalWatchlists: number
  activeWatchlists: number
  totalEntries: number
  totalAlerts: number
  alertsToday: number
  alertsThisWeek: number
  topHitWatchlists: Array<{ id: string; name: string; alertCount: number }>
}

// ── WatchlistEntry ─────────────────────────────────────────────────────────────

export interface WatchlistEntryRead {
  id: string
  watchlistId: string
  value: string
  normalizedValue: string
  isRegex: boolean
  description: string | null
  isActive: boolean
  hitCount: number
  createdById: string | null
  createdAt: string
  updatedAt: string
}

export interface WatchlistEntryListResponse {
  items: WatchlistEntryRead[]
  total: number
}

export interface WatchlistEntryCreate {
  value: string
  isRegex?: boolean
  description?: string | null
}

// ── WatchlistAlert ─────────────────────────────────────────────────────────────

export interface WatchlistAlertRead {
  id: string
  watchlistId: string | null
  watchlistEntryId: string | null
  evidenceId: string | null
  caseId: string
  alertType: AlertType
  severity: AlertSeverity
  title: string
  description: string | null
  matchedValue: string | null
  matchedEntityType: string | null
  confidence: number
  status: AlertStatus
  isCrossCase: boolean
  crossCaseCount: number
  crossCaseAccessible: boolean
  alertMetadata: Record<string, unknown>
  acknowledgedAt: string | null
  resolvedAt: string | null
  createdAt: string
  updatedAt: string
  watchlistName: string | null
  evidenceFilename: string | null
  caseReference: string | null
}

export interface WatchlistAlertListResponse {
  items: WatchlistAlertRead[]
  total: number
  page: number
  pages: number
  newCount: number
  criticalCount: number
}

export interface AlertStats {
  total: number
  newCount: number
  acknowledgedCount: number
  resolvedCount: number
  dismissedCount: number
  criticalCount: number
  highCount: number
  crossCaseCount: number
  alertsToday: number
  alertsThisWeek: number
}

// ── AlertNotification ──────────────────────────────────────────────────────────

export interface AlertNotificationRead {
  id: string
  alertId: string | null
  caseId: string | null
  title: string
  message: string | null
  level: NotificationLevel
  isRead: boolean
  isArchived: boolean
  readAt: string | null
  createdAt: string
}

export interface NotificationListResponse {
  items: AlertNotificationRead[]
  total: number
  unreadCount: number
}

export interface NotificationCount {
  unreadCount: number
}
