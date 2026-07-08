import { useMutation, useQuery } from '@tanstack/react-query'
import { searchApi } from '@/lib/api/search'
import type { SearchFilters, SearchResponse } from '@/types/search'

export function useSearch() {
  return useMutation<
    SearchResponse,
    Error,
    { query: string; filters?: SearchFilters; page?: number; pageSize?: number }
  >({
    mutationFn: ({ query, filters, page = 1, pageSize = 20 }) =>
      searchApi.search({ query, filters, page, pageSize }),
  })
}

export function useSearchSuggestions(query: string, enabled = true) {
  return useQuery({
    queryKey: ['search-suggestions', query],
    queryFn: () => searchApi.suggestions(query),
    enabled: enabled && query.length >= 2,
    staleTime: 30_000,
  })
}
