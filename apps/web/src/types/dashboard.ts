// Dashboard types — mirror backend app/schemas/dashboard.py

export interface DateCount {
  date: string // YYYY-MM-DD
  count: number
}

// ── Executive Dashboard ──────────────────────────────────────────────────────

export interface CaseStatusBreakdown {
  draft: number
  open: number
  inProgress: number
  underReview: number
  onHold: number
  closed: number
  archived: number
}

export interface CasePriorityBreakdown {
  low: number
  medium: number
  high: number
  critical: number
}

export interface InvestigatorWorkload {
  userId: string
  fullName: string
  activeCaseCount: number
  openTaskCount: number
}

export interface RecentCaseSummary {
  id: string
  referenceNumber: string
  title: string
  status: string
  priority: string
  updatedAt: string
}

export interface ExecutiveDashboard {
  activeCases: number
  highPriorityCases: number
  closedCases: number
  totalCases: number
  evidenceUploadedToday: number
  totalEvidence: number
  reportsGenerated: number
  reportsPublished: number
  aiQueueSize: number
  avgInvestigationDays: number
  statusBreakdown: CaseStatusBreakdown
  priorityBreakdown: CasePriorityBreakdown
  casesOpenedLast30Days: DateCount[]
  evidenceUploadedLast30Days: DateCount[]
  investigatorWorkload: InvestigatorWorkload[]
  recentlyActiveCases: RecentCaseSummary[]
  generatedAt: string
}

// ── Intelligence Dashboard ────────────────────────────────────────────────────

export interface EntityDistributionItem {
  entityType: string
  count: number
}

export interface EvidenceTypeItem {
  mimeType: string
  label: string
  count: number
}

export interface ConfidenceBucket {
  bucket: string
  count: number
}

export interface TopKeyword {
  keyword: string
  totalScore: number
  occurrenceCount: number
}

export interface TopEntity {
  value: string
  entityType: string
  occurrenceCount: number
  avgConfidence: number
}

export interface IntelligenceDashboard {
  entityDistribution: EntityDistributionItem[]
  topOrganizations: TopEntity[]
  topDevices: TopEntity[]
  topPersons: TopEntity[]
  evidenceTypeDistribution: EvidenceTypeItem[]
  aiConfidenceDistribution: ConfidenceBucket[]
  topKeywords: TopKeyword[]
  timelineHeatmap: DateCount[]
  avgEntitiesPerCase: number
  totalUniqueEntities: number
  generatedAt: string
}

// ── Operations Dashboard ─────────────────────────────────────────────────────

export type ServiceStatus = 'healthy' | 'degraded' | 'down' | 'unknown'

export interface ServiceHealth {
  name: string
  status: ServiceStatus
  latencyMs: number | null
  message: string | null
}

export interface QueueInfo {
  name: string
  pending: number
  active: number
}

export interface ProcessingStats {
  avgOcrSeconds: number | null
  avgAiSeconds: number | null
  avgTotalSeconds: number | null
  throughputPerHour: number | null
}

export interface StorageStats {
  usedBytes: number
  fileCount: number
}

export interface OperationsDashboard {
  services: ServiceHealth[]
  queues: QueueInfo[]
  evidenceByStatus: Record<string, number>
  failedProcessing24h: number
  processingStats: ProcessingStats
  storage: StorageStats
  generatedAt: string
}

// ── Investigator Dashboard ────────────────────────────────────────────────────

export interface MyCase {
  id: string
  referenceNumber: string
  title: string
  status: string
  priority: string
  openTaskCount: number
  updatedAt: string
}

export interface MyTask {
  id: string
  caseId: string
  caseReference: string
  title: string
  priority: string
  dueDate: string | null
  status: string
}

export interface MyNote {
  id: string
  caseId: string
  caseReference: string
  title: string
  isPinned: boolean
  updatedAt: string
}

export interface MyEvidence {
  id: string
  caseId: string
  caseReference: string
  originalFilename: string
  status: string
  createdAt: string
}

export interface ProductivityMetrics {
  casesActive: number
  casesClosed30d: number
  tasksCompleted30d: number
  evidenceItemsUploaded30d: number
  notesCreated30d: number
}

export interface InvestigatorDashboard {
  assignedCases: MyCase[]
  openTasks: MyTask[]
  recentNotes: MyNote[]
  recentEvidence: MyEvidence[]
  productivity: ProductivityMetrics
  generatedAt: string
}
