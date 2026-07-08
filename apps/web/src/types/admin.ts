// Enterprise Administration TypeScript types
// All match camelCase serialization from BaseSchema (alias_generator=to_camel)

// ── Identity Administration ──────────────────────────────────────────────────

export interface AdminUserRead {
  id: string
  email: string
  username: string
  fullName: string
  isActive: boolean
  isLocked: boolean
  failedLoginAttempts: number
  lockedUntil: string | null
  lastLoginAt: string | null
  avatarUrl: string | null
  createdAt: string
  updatedAt: string
  deletedAt: string | null
  roles: string[]
}

export interface AdminUserListResponse {
  items: AdminUserRead[]
  total: number
  page: number
  pageSize: number
  pages: number
}

export interface LockUserRequest {
  reason?: string
  durationMinutes?: number
}

export interface InviteUserRequest {
  email: string
  fullName: string
  username: string
  roleIds: string[]
  tempPassword: string
}

export interface SessionRead {
  id: string
  userId: string
  userEmail: string
  userFullName: string
  ipAddress: string | null
  userAgent: string | null
  isActive: boolean
  createdAt: string
  lastActiveAt: string
  expiresAt: string
}

export interface SessionListResponse {
  items: SessionRead[]
  total: number
  page: number
  pageSize: number
  pages: number
}

// ── Audit Center ──────────────────────────────────────────────────────────────

export interface AuditEventRead {
  id: string
  eventType: string
  userId: string | null
  userEmail: string | null
  userFullName: string | null
  actorId: string | null
  actorEmail: string | null
  actorFullName: string | null
  ipAddress: string | null
  userAgent: string | null
  metadata: Record<string, unknown> | null
  createdAt: string
}

export interface AuditSearchResponse {
  items: AuditEventRead[]
  total: number
  page: number
  pageSize: number
  pages: number
}

export interface AuditStatItem {
  eventType: string
  count: number
}

export interface AuditStats {
  totalEvents: number
  eventsToday: number
  eventsThisWeek: number
  breakdown: AuditStatItem[]
  generatedAt: string
}

// ── Security Center ───────────────────────────────────────────────────────────

export interface FailedLoginSummary {
  userId: string | null
  userEmail: string | null
  attemptCount: number
  lastAttempt: string
  ipAddresses: string[]
}

export interface SecurityOverview {
  lockedUsersCount: number
  inactiveUsersCount: number
  failedLogins24h: number
  activeSessions: number
  expiredSessions24h: number
  topFailedLogins: FailedLoginSummary[]
  lockedUsers: AdminUserRead[]
  recentSuspiciousIps: string[]
  generatedAt: string
}

// ── System Health ─────────────────────────────────────────────────────────────

export type ServiceStatus = 'healthy' | 'degraded' | 'down' | 'unknown'

export interface ServiceHealthDetail {
  name: string
  status: ServiceStatus
  latencyMs: number | null
  message: string | null
  version: string | null
  lastCheck: string
}

export interface QueueDetail {
  name: string
  pending: number
  active: number
  failed: number
  processedTotal: number
}

export interface WorkerInfo {
  name: string
  status: string
  activeTasks: number
  processed: number
  failed: number
}

export interface SystemHealthResponse {
  services: ServiceHealthDetail[]
  queues: QueueDetail[]
  workers: WorkerInfo[]
  overallStatus: ServiceStatus
  generatedAt: string
}

// ── Recommendations ───────────────────────────────────────────────────────────

export type RecommendationSeverity = 'critical' | 'warning' | 'info'

export interface SystemRecommendation {
  id: string
  severity: RecommendationSeverity
  title: string
  description: string
  action: string | null
  metricValue: string | null
  generatedAt: string
}

export interface RecommendationsResponse {
  recommendations: SystemRecommendation[]
  criticalCount: number
  warningCount: number
  infoCount: number
  generatedAt: string
}

// ── AI Administration ─────────────────────────────────────────────────────────

export interface AiConfigRead {
  provider: string
  model: string
  embeddingModel: string
  maxTokens: number
  temperature: number
  apiBase: string
  apiKeyConfigured: boolean
  ocrEnabled: boolean
}

export interface AiModelStat {
  modelName: string
  messageCount: number
  lastUsed: string | null
}

export interface AiUsageStats {
  totalMessages: number
  messagesToday: number
  messagesThisWeek: number
  messagesThisMonth: number
  modelsUsed: AiModelStat[]
  avgMessagesPerCase: number
  topUsers: Array<{ email: string; count: number }>
  generatedAt: string
}

// ── Storage Center ────────────────────────────────────────────────────────────

export interface StorageBreakdown {
  mimeType: string
  label: string
  fileCount: number
  totalBytes: number
}

export interface LargestFile {
  evidenceId: string
  caseId: string
  caseReference: string
  originalFilename: string
  mimeType: string
  fileSize: number
  uploadedAt: string
}

export interface StorageOverview {
  totalUsedBytes: number
  totalFileCount: number
  evidenceBytes: number
  evidenceCount: number
  byType: StorageBreakdown[]
  growthLast7Days: number
  growthLast30Days: number
  warningThresholdPct: number
  usedPct: number
  largestFiles: LargestFile[]
  generatedAt: string
}

// ── Configuration Center ──────────────────────────────────────────────────────

export interface ConfigEntry {
  key: string
  value: string | null
  description: string | null
  isSecret: boolean
  updatedAt: string
  updatedByEmail: string | null
}

export interface ConfigUpdateRequest {
  value: string | null
}

// ── Admin Overview Stats ──────────────────────────────────────────────────────

export interface AdminOverviewStats {
  totalUsers: number
  activeUsers: number
  lockedUsers: number
  inactiveUsers: number
  totalRoles: number
  totalPermissions: number
  activeSessions: number
  auditEventsToday: number
  failedLogins24h: number
  evidenceItems: number
  totalCases: number
  systemStatus: ServiceStatus
  generatedAt: string
}
