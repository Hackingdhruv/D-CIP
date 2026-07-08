import { useCallback, useEffect, useRef, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { Search, Loader2, ChevronLeft, ChevronRight } from 'lucide-react'
import { PageHeader } from '@/components/common/page-header'
import { EmptyState } from '@/components/common/empty-state'
import { SearchResultCard } from '@/components/search/search-result-card'
import { SearchFiltersPanel } from '@/components/search/search-filters'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Skeleton } from '@/components/ui/skeleton'
import { useSearch } from '@/hooks/use-search'
import type { SearchFilters, SearchResponse, SearchResultType } from '@/types/search'
import { RESULT_TYPE_LABELS } from '@/types/search'

// ── Facet sidebar ─────────────────────────────────────────────────────────────

function FacetSidebar({
  sources,
  activeType,
  onToggle,
}: {
  sources: Record<string, number>
  activeType: SearchResultType | ''
  onToggle: (t: SearchResultType | '') => void
}) {
  const entries = Object.entries(sources).sort(([, a], [, b]) => b - a)
  if (!entries.length) return null

  return (
    <div className="w-44 shrink-0 space-y-1">
      <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wide mb-2">
        Results by type
      </p>
      <button
        onClick={() => onToggle('')}
        className={`flex w-full items-center justify-between rounded px-2 py-1 text-xs ${
          activeType === '' ? 'bg-primary/10 text-primary font-semibold' : 'hover:bg-muted'
        }`}
      >
        <span>All</span>
        <span className="text-muted-foreground">
          {Object.values(sources).reduce((a, b) => a + b, 0)}
        </span>
      </button>
      {entries.map(([type, count]) => (
        <button
          key={type}
          onClick={() => onToggle(activeType === type ? '' : (type as SearchResultType))}
          className={`flex w-full items-center justify-between rounded px-2 py-1 text-xs ${
            activeType === type ? 'bg-primary/10 text-primary font-semibold' : 'hover:bg-muted'
          }`}
        >
          <span>{RESULT_TYPE_LABELS[type as SearchResultType] ?? type}</span>
          <span className="text-muted-foreground">{count}</span>
        </button>
      ))}
    </div>
  )
}

// ── Result list ───────────────────────────────────────────────────────────────

function ResultList({
  data,
  query,
  activeType,
}: {
  data: SearchResponse
  query: string
  activeType: SearchResultType | ''
}) {
  const items = activeType
    ? data.items.filter((i) => i.type === activeType)
    : data.items

  if (!items.length) {
    return (
      <p className="py-8 text-center text-sm text-muted-foreground">
        No results for this type. Try a different filter.
      </p>
    )
  }

  return (
    <div className="space-y-2">
      {items.map((item) => (
        <SearchResultCard key={`${item.type}:${item.id}`} item={item} query={query} />
      ))}
    </div>
  )
}

// ── Pagination ────────────────────────────────────────────────────────────────

function Pagination({
  page,
  pages,
  onPage,
}: {
  page: number
  pages: number
  onPage: (p: number) => void
}) {
  if (pages <= 1) return null
  return (
    <div className="flex items-center justify-center gap-2 pt-4">
      <Button
        variant="outline"
        size="sm"
        disabled={page <= 1}
        onClick={() => onPage(page - 1)}
      >
        <ChevronLeft className="h-4 w-4" />
        Prev
      </Button>
      <span className="text-sm text-muted-foreground">
        Page {page} of {pages}
      </span>
      <Button
        variant="outline"
        size="sm"
        disabled={page >= pages}
        onClick={() => onPage(page + 1)}
      >
        Next
        <ChevronRight className="h-4 w-4" />
      </Button>
    </div>
  )
}

// ── Main page ─────────────────────────────────────────────────────────────────

export function SearchPage() {
  const [searchParams] = useSearchParams()
  const initialQ = searchParams.get('q') ?? ''

  const [query, setQuery] = useState(initialQ)
  const [committedQuery, setCommittedQuery] = useState('')
  const [filters, setFilters] = useState<SearchFilters>({})
  const [activeType, setActiveType] = useState<SearchResultType | ''>('')
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const initializedRef = useRef(false)

  const { mutate, data, isPending, reset } = useSearch()

  const runSearch = useCallback(
    (q: string, f: SearchFilters, p: number) => {
      if (!q.trim()) {
        reset()
        return
      }
      setCommittedQuery(q)
      mutate({ query: q, filters: f, page: p, pageSize: 20 })
    },
    [mutate, reset]
  )

  // Run search immediately if a `?q=` param was passed (from command palette)
  useEffect(() => {
    if (initialQ && !initializedRef.current) {
      initializedRef.current = true
      runSearch(initialQ, {}, 1)
    }
  }, [initialQ]) // eslint-disable-line react-hooks/exhaustive-deps

  // Debounced auto-search on query/filter change
  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current)
    if (!query.trim()) {
      reset()
      setCommittedQuery('')
      return
    }
    debounceRef.current = setTimeout(() => {
      setActiveType('')
      runSearch(query, filters, 1)
    }, 450)
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current)
    }
  }, [query, filters]) // eslint-disable-line react-hooks/exhaustive-deps

  function handlePageChange(p: number) {
    runSearch(committedQuery, filters, p)
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }

  function handleFilterChange(f: SearchFilters) {
    setFilters(f)
    setActiveType('')
  }

  const hasResults = data && data.total > 0
  const noResults = data && data.total === 0
  const showSkeleton = isPending

  return (
    <div className="space-y-6">
      <PageHeader
        title="Search"
        description="Full-text search across cases, evidence, entities, notes, tasks, and AI findings."
      />

      {/* Search bar */}
      <div className="relative max-w-2xl">
        {isPending ? (
          <Loader2 className="absolute left-3 top-2.5 h-5 w-5 animate-spin text-muted-foreground" />
        ) : (
          <Search className="absolute left-3 top-2.5 h-5 w-5 text-muted-foreground" />
        )}
        <Input
          autoFocus
          className="pl-10 h-10 text-base"
          placeholder="Search across the platform…"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && query.trim()) {
              if (debounceRef.current) clearTimeout(debounceRef.current)
              setActiveType('')
              runSearch(query, filters, 1)
            }
          }}
        />
      </div>

      {/* Filters */}
      <div className="max-w-2xl">
        <SearchFiltersPanel filters={filters} onChange={handleFilterChange} />
      </div>

      {/* Status line */}
      {data && !isPending && (
        <p className="text-sm text-muted-foreground">
          {data.total} result{data.total !== 1 ? 's' : ''} for{' '}
          <span className="font-medium text-foreground">"{data.query}"</span>
          {' '}· {data.tookMs}ms
        </p>
      )}

      {/* Results area */}
      {showSkeleton && (
        <div className="space-y-3 max-w-3xl">
          {Array.from({ length: 5 }).map((_, i) => (
            <Skeleton key={i} className="h-20 rounded-lg" />
          ))}
        </div>
      )}

      {noResults && !isPending && (
        <EmptyState
          icon={Search}
          title="No results found"
          description={`No matches for "${committedQuery}". Try different keywords or clear your filters.`}
        />
      )}

      {hasResults && !isPending && (
        <div className="flex gap-6">
          {/* Facet sidebar */}
          <FacetSidebar
            sources={data.sources}
            activeType={activeType}
            onToggle={setActiveType}
          />

          {/* Result list + pagination */}
          <div className="flex-1 min-w-0 space-y-4">
            <ResultList
              data={data}
              query={committedQuery}
              activeType={activeType}
            />
            <Pagination
              page={data.page}
              pages={data.pages}
              onPage={handlePageChange}
            />
          </div>
        </div>
      )}

      {/* Initial empty state (before any search) */}
      {!data && !isPending && (
        <EmptyState
          icon={Search}
          title="Start searching"
          description="Search across cases, evidence files, AI entities, timeline events, notes, and tasks. Use Ctrl+K anywhere for quick access."
        />
      )}
    </div>
  )
}
