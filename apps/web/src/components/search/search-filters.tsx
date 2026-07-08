import { useState } from 'react'
import { ChevronDown, ChevronUp, FilterX } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import type { SearchFilters, SearchResultType } from '@/types/search'
import { RESULT_TYPE_LABELS } from '@/types/search'

const ALL_TYPES = Object.keys(RESULT_TYPE_LABELS) as SearchResultType[]

interface Props {
  filters: SearchFilters
  onChange: (filters: SearchFilters) => void
}

export function SearchFiltersPanel({ filters, onChange }: Props) {
  const [expanded, setExpanded] = useState(false)

  function toggleType(t: SearchResultType) {
    const current = filters.types ?? []
    const next = current.includes(t) ? current.filter((x) => x !== t) : [...current, t]
    onChange({ ...filters, types: next.length ? next : undefined })
  }

  function setDateFrom(v: string) {
    onChange({ ...filters, dateFrom: v || undefined })
  }

  function setDateTo(v: string) {
    onChange({ ...filters, dateTo: v || undefined })
  }

  function setCaseStatus(v: string) {
    onChange({ ...filters, caseStatus: v === '_all' ? undefined : v })
  }

  function setPriority(v: string) {
    onChange({ ...filters, priority: v === '_all' ? undefined : v })
  }

  function clearAll() {
    onChange({})
  }

  const hasFilters =
    (filters.types?.length ?? 0) > 0 ||
    filters.dateFrom ||
    filters.dateTo ||
    filters.caseStatus ||
    filters.priority

  return (
    <div className="rounded-lg border bg-card p-3 space-y-3">
      {/* Header row */}
      <div className="flex items-center justify-between">
        <button
          className="flex items-center gap-1.5 text-sm font-medium"
          onClick={() => setExpanded((e) => !e)}
        >
          Filters
          {expanded ? (
            <ChevronUp className="h-3.5 w-3.5" />
          ) : (
            <ChevronDown className="h-3.5 w-3.5" />
          )}
          {hasFilters && (
            <span className="ml-1 rounded-full bg-primary px-1.5 py-0.5 text-[10px] text-primary-foreground">
              active
            </span>
          )}
        </button>
        {hasFilters && (
          <Button variant="ghost" size="sm" className="h-6 text-xs" onClick={clearAll}>
            <FilterX className="mr-1 h-3 w-3" />
            Clear
          </Button>
        )}
      </div>

      {/* Result-type chips — always visible */}
      <div className="flex flex-wrap gap-1.5">
        {ALL_TYPES.map((t) => {
          const active = filters.types?.includes(t)
          return (
            <button
              key={t}
              onClick={() => toggleType(t)}
              className={`rounded-full border px-2.5 py-0.5 text-xs transition-colors ${
                active
                  ? 'bg-primary text-primary-foreground border-primary'
                  : 'border-border hover:border-primary/40'
              }`}
            >
              {RESULT_TYPE_LABELS[t]}
            </button>
          )
        })}
      </div>

      {/* Expanded advanced filters */}
      {expanded && (
        <div className="grid grid-cols-2 gap-3 pt-1 sm:grid-cols-4">
          <div className="space-y-1">
            <Label className="text-xs">From date</Label>
            <Input
              type="date"
              className="h-8 text-xs"
              value={filters.dateFrom ?? ''}
              onChange={(e) => setDateFrom(e.target.value)}
            />
          </div>
          <div className="space-y-1">
            <Label className="text-xs">To date</Label>
            <Input
              type="date"
              className="h-8 text-xs"
              value={filters.dateTo ?? ''}
              onChange={(e) => setDateTo(e.target.value)}
            />
          </div>
          <div className="space-y-1">
            <Label className="text-xs">Case status</Label>
            <Select
              value={filters.caseStatus ?? '_all'}
              onValueChange={setCaseStatus}
            >
              <SelectTrigger className="h-8 text-xs">
                <SelectValue placeholder="Any" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="_all">Any</SelectItem>
                <SelectItem value="open">Open</SelectItem>
                <SelectItem value="under_review">Under Review</SelectItem>
                <SelectItem value="closed">Closed</SelectItem>
                <SelectItem value="archived">Archived</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-1">
            <Label className="text-xs">Priority</Label>
            <Select
              value={filters.priority ?? '_all'}
              onValueChange={setPriority}
            >
              <SelectTrigger className="h-8 text-xs">
                <SelectValue placeholder="Any" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="_all">Any</SelectItem>
                <SelectItem value="critical">Critical</SelectItem>
                <SelectItem value="high">High</SelectItem>
                <SelectItem value="medium">Medium</SelectItem>
                <SelectItem value="low">Low</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </div>
      )}
    </div>
  )
}
