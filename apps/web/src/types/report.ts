export type ReportType =
  | 'executive'
  | 'detailed'
  | 'evidence_inventory'
  | 'timeline'
  | 'entity_intelligence'
  | 'chain_of_custody'
  | 'ai_findings'
  | 'case_progress'
  | 'activity'

export type ReportTemplate =
  | 'professional'
  | 'police'
  | 'cyber'
  | 'incident_response'
  | 'executive_summary'
  | 'custom'

export type ReportStatus = 'draft' | 'generating' | 'ready' | 'published' | 'archived'

export type SectionType =
  | 'cover'
  | 'table_of_contents'
  | 'executive_summary'
  | 'case_overview'
  | 'evidence_inventory'
  | 'timeline'
  | 'entities'
  | 'ai_findings'
  | 'notes_tasks'
  | 'chain_of_custody'
  | 'appendix'

export type ExportFormat = 'pdf' | 'docx' | 'html' | 'json'

export interface SectionConfig {
  type: string
  title: string
  orderIndex: number
  enabled: boolean
}

export interface ReportFilters {
  dateFrom?: string
  dateTo?: string
  evidenceIds?: string[]
  entityTypes?: string[]
  includeAi?: boolean
  maxEntitiesPerType?: number
  includeChainOfCustody?: boolean
  classificationLabel?: string
  watermarkText?: string
}

export interface CreateReportRequest {
  reportType: ReportType
  template: ReportTemplate
  title: string
  sectionsConfig?: SectionConfig[]
  reportFilters?: ReportFilters
}

export interface GenerateReportRequest {
  sectionsConfig?: SectionConfig[]
  reportFilters?: ReportFilters
}

export interface ReportExportRecord {
  id: string
  reportId: string
  format: ExportFormat
  fileSize: number | null
  fileHash: string | null
  generatedById: string
  createdAt: string
}

export interface ReportRead {
  id: string
  caseId: string
  reportType: ReportType
  template: ReportTemplate
  title: string
  status: ReportStatus
  version: number
  contentHash: string | null
  parentReportId: string | null
  sectionsConfig: SectionConfig[]
  reportFilters: Record<string, unknown>
  sectionsContent: Record<string, unknown>
  generationError: string | null
  generatedById: string
  approvedById: string | null
  generatedAt: string | null
  publishedAt: string | null
  createdAt: string
  updatedAt: string
  exports: ReportExportRecord[]
}

export interface ReportListItem {
  id: string
  caseId: string
  reportType: ReportType
  template: ReportTemplate
  title: string
  status: ReportStatus
  version: number
  contentHash: string | null
  parentReportId: string | null
  generatedById: string
  generatedAt: string | null
  publishedAt: string | null
  createdAt: string
  exportCount: number
}

export interface TemplateDescriptor {
  key: ReportTemplate
  label: string
  description: string
  sections: SectionConfig[]
}

export interface ReportTypeDescriptor {
  key: ReportType
  label: string
  description: string
  defaultTemplate: ReportTemplate
}

// ── UI helpers ─────────────────────────────────────────────────────────────────

export const REPORT_TYPE_LABELS: Record<ReportType, string> = {
  executive: 'Executive Investigation Report',
  detailed: 'Detailed Investigation Report',
  evidence_inventory: 'Evidence Inventory Report',
  timeline: 'Timeline Report',
  entity_intelligence: 'Entity Intelligence Report',
  chain_of_custody: 'Chain of Custody Report',
  ai_findings: 'AI Findings Report',
  case_progress: 'Case Progress Report',
  activity: 'Investigation Activity Report',
}

export const REPORT_STATUS_COLORS: Record<ReportStatus, string> = {
  draft: 'bg-gray-100 text-gray-600',
  generating: 'bg-blue-100 text-blue-700',
  ready: 'bg-emerald-100 text-emerald-700',
  published: 'bg-violet-100 text-violet-700',
  archived: 'bg-amber-100 text-amber-700',
}

export const SECTION_LABELS: Record<string, string> = {
  cover: 'Cover Page',
  table_of_contents: 'Table of Contents',
  executive_summary: 'Executive Summary',
  case_overview: 'Case Overview',
  evidence_inventory: 'Evidence Inventory',
  timeline: 'Investigation Timeline',
  entities: 'Entity Intelligence',
  ai_findings: 'AI Analysis Findings',
  notes_tasks: 'Notes & Tasks',
  chain_of_custody: 'Chain of Custody',
  appendix: 'Appendix',
}
