import { apiFetch } from '@/lib/api-client'
import type {
  AiChatMessage,
  CaseSummary,
  ChatHistoryResponse,
  EntityListResponse,
  EvidenceSummary,
  GraphResponse,
  KeywordListResponse,
  ProcessingStatus,
  SearchResponse,
  TimelineListResponse,
} from '@/types/ai'

const base = (caseId: string) => `/v1/cases/${caseId}/ai`

// ── Case summary ──────────────────────────────────────────────────────────────

export const aiApi = {
  getCaseSummary: (caseId: string) =>
    apiFetch<CaseSummary | null>(`${base(caseId)}/summary`),

  regenerateCaseSummary: (caseId: string) =>
    apiFetch<CaseSummary | null>(`${base(caseId)}/summary/regenerate`, {
      method: 'POST',
    }),

  sendChatMessage: (caseId: string, message: string) =>
    apiFetch<AiChatMessage>(`${base(caseId)}/chat`, {
      method: 'POST',
      body: { message },
    }),

  getChatHistory: (caseId: string, page = 1, pageSize = 50) =>
    apiFetch<ChatHistoryResponse>(
      `${base(caseId)}/chat/history?page=${page}&page_size=${pageSize}`
    ),

  listEntities: (
    caseId: string,
    params?: { entityType?: string; q?: string; page?: number; pageSize?: number }
  ) => {
    const sp = new URLSearchParams()
    if (params?.entityType) sp.set('entity_type', params.entityType)
    if (params?.q) sp.set('q', params.q)
    if (params?.page) sp.set('page', String(params.page))
    if (params?.pageSize) sp.set('page_size', String(params.pageSize))
    const qs = sp.toString()
    return apiFetch<EntityListResponse>(`${base(caseId)}/entities${qs ? `?${qs}` : ''}`)
  },

  listKeywords: (
    caseId: string,
    params?: { page?: number; pageSize?: number }
  ) => {
    const sp = new URLSearchParams()
    if (params?.page) sp.set('page', String(params.page))
    if (params?.pageSize) sp.set('page_size', String(params.pageSize))
    const qs = sp.toString()
    return apiFetch<KeywordListResponse>(`${base(caseId)}/keywords${qs ? `?${qs}` : ''}`)
  },

  listTimeline: (
    caseId: string,
    params?: { eventType?: string; page?: number; pageSize?: number }
  ) => {
    const sp = new URLSearchParams()
    if (params?.eventType) sp.set('event_type', params.eventType)
    if (params?.page) sp.set('page', String(params.page))
    if (params?.pageSize) sp.set('page_size', String(params.pageSize))
    const qs = sp.toString()
    return apiFetch<TimelineListResponse>(`${base(caseId)}/timeline${qs ? `?${qs}` : ''}`)
  },

  searchEvidence: (caseId: string, query: string) =>
    apiFetch<SearchResponse>(`${base(caseId)}/search?q=${encodeURIComponent(query)}`),

  getEvidenceSummary: (caseId: string, evidenceId: string) =>
    apiFetch<EvidenceSummary | null>(`${base(caseId)}/evidence/${evidenceId}/summary`),

  getProcessingStatus: (caseId: string) =>
    apiFetch<ProcessingStatus[]>(`${base(caseId)}/processing-status`),

  getRelationshipGraph: (caseId: string, maxNodes = 80) =>
    apiFetch<GraphResponse>(`${base(caseId)}/graph?max_nodes=${maxNodes}`),
}
