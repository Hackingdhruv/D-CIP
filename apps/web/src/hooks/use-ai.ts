import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { aiApi } from '@/lib/api/ai'

// ── Query keys ────────────────────────────────────────────────────────────────

export const aiKeys = {
  all: (caseId: string) => ['ai', caseId] as const,
  summary: (caseId: string) => ['ai', caseId, 'summary'] as const,
  chat: (caseId: string) => ['ai', caseId, 'chat'] as const,
  entities: (caseId: string, params?: object) => ['ai', caseId, 'entities', params] as const,
  keywords: (caseId: string, params?: object) => ['ai', caseId, 'keywords', params] as const,
  timeline: (caseId: string, params?: object) => ['ai', caseId, 'timeline', params] as const,
  processingStatus: (caseId: string) => ['ai', caseId, 'processing-status'] as const,
}

// ── Case summary ──────────────────────────────────────────────────────────────

export function useCaseSummary(caseId: string) {
  return useQuery({
    queryKey: aiKeys.summary(caseId),
    queryFn: () => aiApi.getCaseSummary(caseId),
    enabled: Boolean(caseId),
    staleTime: 5 * 60 * 1000,
  })
}

export function useRegenerateCaseSummary(caseId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: () => aiApi.regenerateCaseSummary(caseId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: aiKeys.summary(caseId) })
    },
  })
}

// ── Chat ──────────────────────────────────────────────────────────────────────

export function useChatHistory(caseId: string) {
  return useQuery({
    queryKey: aiKeys.chat(caseId),
    queryFn: () => aiApi.getChatHistory(caseId),
    enabled: Boolean(caseId),
    staleTime: 0,
  })
}

export function useSendChatMessage(caseId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (message: string) => aiApi.sendChatMessage(caseId, message),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: aiKeys.chat(caseId) })
    },
  })
}

// ── Entities ──────────────────────────────────────────────────────────────────

export function useEntities(
  caseId: string,
  params?: { entityType?: string; q?: string; page?: number; pageSize?: number }
) {
  return useQuery({
    queryKey: aiKeys.entities(caseId, params),
    queryFn: () => aiApi.listEntities(caseId, params),
    enabled: Boolean(caseId),
    staleTime: 2 * 60 * 1000,
  })
}

// ── Keywords ──────────────────────────────────────────────────────────────────

export function useKeywords(
  caseId: string,
  params?: { page?: number; pageSize?: number }
) {
  return useQuery({
    queryKey: aiKeys.keywords(caseId, params),
    queryFn: () => aiApi.listKeywords(caseId, params),
    enabled: Boolean(caseId),
    staleTime: 2 * 60 * 1000,
  })
}

// ── Timeline ──────────────────────────────────────────────────────────────────

export function useTimeline(
  caseId: string,
  params?: { eventType?: string; page?: number; pageSize?: number }
) {
  return useQuery({
    queryKey: aiKeys.timeline(caseId, params),
    queryFn: () => aiApi.listTimeline(caseId, params),
    enabled: Boolean(caseId),
    staleTime: 2 * 60 * 1000,
  })
}

// ── Processing status ─────────────────────────────────────────────────────────

export function useRelationshipGraph(caseId: string, maxNodes = 80) {
  return useQuery({
    queryKey: ['ai', caseId, 'graph', maxNodes] as const,
    queryFn: () => aiApi.getRelationshipGraph(caseId, maxNodes),
    enabled: Boolean(caseId),
    staleTime: 5 * 60 * 1000,
  })
}

export function useProcessingStatus(caseId: string) {
  return useQuery({
    queryKey: aiKeys.processingStatus(caseId),
    queryFn: () => aiApi.getProcessingStatus(caseId),
    enabled: Boolean(caseId),
    refetchInterval: 10_000,
  })
}
