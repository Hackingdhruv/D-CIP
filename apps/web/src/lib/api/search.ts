import { apiFetch } from '@/lib/api-client'
import type {
  SearchRequest,
  SearchResponse,
  SuggestionsResponse,
} from '@/types/search'

export const searchApi = {
  search: (body: SearchRequest): Promise<SearchResponse> =>
    apiFetch<SearchResponse>('/v1/search', { method: 'POST', body }),

  suggestions: (q: string): Promise<SuggestionsResponse> =>
    apiFetch<SuggestionsResponse>(
      `/v1/search/suggestions?q=${encodeURIComponent(q)}`
    ),
}
