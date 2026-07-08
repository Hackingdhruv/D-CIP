export type SearchResultType =
  | 'case'
  | 'evidence'
  | 'evidence_summary'
  | 'entity'
  | 'timeline_event'
  | 'note'
  | 'task'
  | 'user'

export interface SearchFilters {
  types?: SearchResultType[]
  caseId?: string
  dateFrom?: string
  dateTo?: string
  caseStatus?: string
  priority?: string
  entityType?: string
  confidenceMin?: number
}

export interface SearchRequest {
  query: string
  filters?: SearchFilters
  page?: number
  pageSize?: number
}

export interface SearchResultItem {
  id: string
  type: SearchResultType
  title: string
  snippet: string
  caseId?: string | null
  caseTitle?: string | null
  caseReference?: string | null
  evidenceId?: string | null
  confidence?: number | null
  score: number
  createdAt: string
  url: string
}

export interface SearchResponse {
  items: SearchResultItem[]
  total: number
  page: number
  pageSize: number
  pages: number
  query: string
  tookMs: number
  sources: Record<string, number>
}

export interface SearchSuggestion {
  text: string
  suggestionType: string
}

export interface SuggestionsResponse {
  suggestions: SearchSuggestion[]
}

export const RESULT_TYPE_LABELS: Record<SearchResultType, string> = {
  case: 'Case',
  evidence: 'Evidence',
  evidence_summary: 'AI Summary',
  entity: 'Entity',
  timeline_event: 'Timeline',
  note: 'Note',
  task: 'Task',
  user: 'User',
}

export const RESULT_TYPE_COLORS: Record<SearchResultType, string> = {
  case: 'bg-blue-100 text-blue-700',
  evidence: 'bg-amber-100 text-amber-700',
  evidence_summary: 'bg-violet-100 text-violet-700',
  entity: 'bg-teal-100 text-teal-700',
  timeline_event: 'bg-green-100 text-green-700',
  note: 'bg-orange-100 text-orange-700',
  task: 'bg-red-100 text-red-700',
  user: 'bg-gray-100 text-gray-700',
}
