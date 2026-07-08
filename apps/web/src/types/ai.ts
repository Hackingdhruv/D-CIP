export type EntityType =
  | 'person'
  | 'email'
  | 'phone'
  | 'organization'
  | 'domain'
  | 'url'
  | 'ip_address'
  | 'date'
  | 'location'
  | 'country'
  | 'city'
  | 'device'
  | 'os'
  | 'browser'
  | 'filename'
  | 'file_hash'
  | 'bank_account'
  | 'crypto_wallet'
  | 'vehicle_number'
  | 'unknown'

export type TimelineEventType =
  | 'email_sent'
  | 'email_received'
  | 'login'
  | 'logout'
  | 'purchase'
  | 'travel'
  | 'meeting'
  | 'transaction'
  | 'upload'
  | 'download'
  | 'phone_call'
  | 'message'
  | 'file_created'
  | 'file_modified'
  | 'document_created'
  | 'unknown'

export interface EvidenceEntity {
  id: string
  evidenceId: string
  caseId: string
  entityType: EntityType
  value: string
  normalizedValue: string
  confidence: number
  context: string | null
  source: string
  createdAt: string
}

export interface EntityListResponse {
  items: EvidenceEntity[]
  total: number
  page: number
  pageSize: number
  pages: number
}

export interface EvidenceKeyword {
  id: string
  evidenceId: string
  caseId: string
  keyword: string
  score: number
  createdAt: string
}

export interface KeywordListResponse {
  items: EvidenceKeyword[]
  total: number
  page: number
  pageSize: number
  pages: number
}

export interface EvidenceTimelineEvent {
  id: string
  evidenceId: string
  caseId: string
  eventType: TimelineEventType
  eventTitle: string
  description: string | null
  eventTimestamp: string | null
  confidence: number
  sourceText: string | null
  createdAt: string
}

export interface TimelineListResponse {
  items: EvidenceTimelineEvent[]
  total: number
  page: number
  pageSize: number
  pages: number
}

export interface EvidenceSummary {
  id: string
  evidenceId: string
  summaryText: string
  keyFindings: string[]
  modelUsed: string | null
  createdAt: string
  updatedAt: string
}

export interface CaseSummary {
  id: string
  caseId: string
  summaryText: string
  keyFindings: string[]
  potentialLeads: string[]
  missingInformation: string[]
  openQuestions: string[]
  modelUsed: string | null
  createdAt: string
  updatedAt: string
}

export interface AiChatMessage {
  id: string
  caseId: string
  userId: string | null
  role: 'user' | 'assistant'
  content: string
  evidenceReferences: string[]
  modelUsed: string | null
  createdAt: string
}

export interface ChatHistoryResponse {
  items: AiChatMessage[]
  total: number
  page: number
  pageSize: number
  pages: number
}

export interface SearchResultItem {
  evidenceId: string
  filename: string
  score: number
  highlights: string[]
}

export interface SearchResponse {
  query: string
  results: SearchResultItem[]
  total: number
}

export interface GraphNode {
  id: string
  label: string
  nodeType: string
  confidence: number
  evidenceCount: number
}

export interface GraphEdge {
  source: string
  target: string
  weight: number
}

export interface GraphResponse {
  nodes: GraphNode[]
  edges: GraphEdge[]
  nodeCount: number
  edgeCount: number
}

export interface ProcessingStatus {
  evidenceId: string
  filename: string
  status: string
  processingStartedAt: string | null
  processingCompletedAt: string | null
  processingError: string | null
  wordCount: number | null
  language: string | null
  entityCount: number
  keywordCount: number
  timelineEventCount: number
  hasSummary: boolean
}
