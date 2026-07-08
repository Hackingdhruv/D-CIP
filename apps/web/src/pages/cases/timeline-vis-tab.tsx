import { useMemo, useState } from 'react'
import { Bar } from 'react-chartjs-2'
import {
  BarElement,
  CategoryScale,
  Chart as ChartJS,
  LinearScale,
  Title,
  Tooltip,
} from 'chart.js'
import { CalendarClock, Clock } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { useTimeline } from '@/hooks/use-ai'
import type { EvidenceTimelineEvent, TimelineEventType } from '@/types/ai'

ChartJS.register(BarElement, CategoryScale, LinearScale, Title, Tooltip)

// ── Event type config ─────────────────────────────────────────────────────────

const EVENT_CONFIG: Record<TimelineEventType, { color: string; label: string }> = {
  email_sent:       { color: '#22c55e', label: 'Email Sent' },
  email_received:   { color: '#86efac', label: 'Email Received' },
  login:            { color: '#3b82f6', label: 'Login' },
  logout:           { color: '#93c5fd', label: 'Logout' },
  purchase:         { color: '#f97316', label: 'Purchase' },
  travel:           { color: '#a855f7', label: 'Travel' },
  meeting:          { color: '#6366f1', label: 'Meeting' },
  transaction:      { color: '#ef4444', label: 'Transaction' },
  upload:           { color: '#14b8a6', label: 'Upload' },
  download:         { color: '#06b6d4', label: 'Download' },
  phone_call:       { color: '#eab308', label: 'Phone Call' },
  message:          { color: '#84cc16', label: 'Message' },
  file_created:     { color: '#f59e0b', label: 'File Created' },
  file_modified:    { color: '#d97706', label: 'File Modified' },
  document_created: { color: '#b45309', label: 'Document Created' },
  unknown:          { color: '#94a3b8', label: 'Unknown' },
}

function cfg(type: string) {
  return EVENT_CONFIG[type as TimelineEventType] ?? EVENT_CONFIG.unknown
}

function fmtDate(iso: string) {
  return new Date(iso).toLocaleDateString('en-US', {
    weekday: 'short',
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  })
}

function fmtTime(iso: string) {
  return new Date(iso).toLocaleTimeString('en-US', {
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
  })
}

// ── Events per-day bar chart ──────────────────────────────────────────────────

function ActivityChart({ events }: { events: EvidenceTimelineEvent[] }) {
  const dated = events.filter((e) => e.eventTimestamp)
  if (dated.length < 2) return null

  const dayCounts: Record<string, number> = {}
  for (const ev of dated) {
    const day = ev.eventTimestamp!.slice(0, 10)
    dayCounts[day] = (dayCounts[day] ?? 0) + 1
  }
  const labels = Object.keys(dayCounts).sort()
  const counts = labels.map((d) => dayCounts[d])

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-sm">Event Activity by Day</CardTitle>
      </CardHeader>
      <CardContent>
        <div style={{ height: 140 }}>
          <Bar
            data={{
              labels: labels.map((d) =>
                new Date(d).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
              ),
              datasets: [
                {
                  data: counts,
                  backgroundColor: '#6366f1aa',
                  borderColor: '#6366f1',
                  borderWidth: 1,
                  borderRadius: 3,
                },
              ],
            }}
            options={{
              responsive: true,
              maintainAspectRatio: false,
              plugins: { legend: { display: false } },
              scales: {
                x: { ticks: { font: { size: 10 } } },
                y: { ticks: { stepSize: 1 }, beginAtZero: true },
              },
            }}
          />
        </div>
      </CardContent>
    </Card>
  )
}

// ── Grouped timeline list ─────────────────────────────────────────────────────

function GroupedTimeline({ events }: { events: EvidenceTimelineEvent[] }) {
  const dated = events.filter((e) => e.eventTimestamp)
  const undated = events.filter((e) => !e.eventTimestamp)

  // Group by date string
  const groups = useMemo(() => {
    const map = new Map<string, EvidenceTimelineEvent[]>()
    for (const ev of dated) {
      const day = ev.eventTimestamp!.slice(0, 10)
      if (!map.has(day)) map.set(day, [])
      map.get(day)!.push(ev)
    }
    // Sort groups ascending, events within group ascending
    return Array.from(map.entries())
      .sort(([a], [b]) => a.localeCompare(b))
      .map(([day, evs]) => ({
        day,
        events: evs.sort((a, b) =>
          (a.eventTimestamp ?? '').localeCompare(b.eventTimestamp ?? '')
        ),
      }))
  }, [dated])

  return (
    <div className="space-y-6">
      {groups.map(({ day, events: dayEvents }) => (
        <div key={day} className="space-y-2">
          {/* Date header */}
          <div className="flex items-center gap-3">
            <div className="h-px flex-1 bg-border" />
            <span className="shrink-0 rounded-full border bg-muted px-3 py-0.5 text-xs font-semibold">
              {fmtDate(day + 'T00:00:00')}
            </span>
            <div className="h-px flex-1 bg-border" />
          </div>

          {/* Events for this day */}
          <div className="ml-4 space-y-1.5 border-l-2 border-border pl-4">
            {dayEvents.map((ev) => {
              const { color, label } = cfg(ev.eventType)
              return (
                <div
                  key={ev.id}
                  className="relative flex items-start gap-3 rounded-md bg-card border px-3 py-2"
                >
                  {/* Timeline dot */}
                  <div
                    className="absolute -left-[1.375rem] top-3 h-2.5 w-2.5 rounded-full border-2 border-background"
                    style={{ backgroundColor: color }}
                  />

                  <div className="w-12 shrink-0 text-right text-xs text-muted-foreground font-mono">
                    {ev.eventTimestamp ? fmtTime(ev.eventTimestamp) : '—'}
                  </div>

                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="text-sm font-medium">{ev.eventTitle}</span>
                      <span
                        className="rounded px-1.5 py-0.5 text-[10px] font-medium text-white"
                        style={{ backgroundColor: color }}
                      >
                        {label}
                      </span>
                    </div>
                    {ev.description && (
                      <p className="mt-0.5 text-xs text-muted-foreground line-clamp-2">
                        {ev.description}
                      </p>
                    )}
                  </div>

                  <span className="shrink-0 text-xs text-muted-foreground">
                    {Math.round(ev.confidence * 100)}%
                  </span>
                </div>
              )
            })}
          </div>
        </div>
      ))}

      {/* Undated events */}
      {undated.length > 0 && (
        <div className="space-y-2">
          <div className="flex items-center gap-3">
            <div className="h-px flex-1 bg-border" />
            <span className="shrink-0 rounded-full border bg-muted px-3 py-0.5 text-xs font-semibold">
              No timestamp ({undated.length})
            </span>
            <div className="h-px flex-1 bg-border" />
          </div>
          <div className="ml-4 space-y-1.5 border-l-2 border-dashed border-border pl-4">
            {undated.map((ev) => {
              const { color, label } = cfg(ev.eventType)
              return (
                <div
                  key={ev.id}
                  className="relative flex items-start gap-3 rounded-md bg-card border px-3 py-2 opacity-80"
                >
                  <div
                    className="absolute -left-[1.375rem] top-3 h-2.5 w-2.5 rounded-full border-2 border-background border-dashed"
                    style={{ backgroundColor: color }}
                  />
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="text-sm font-medium">{ev.eventTitle}</span>
                      <span
                        className="rounded px-1.5 py-0.5 text-[10px] font-medium text-white"
                        style={{ backgroundColor: color }}
                      >
                        {label}
                      </span>
                    </div>
                    {ev.description && (
                      <p className="mt-0.5 text-xs text-muted-foreground line-clamp-1">
                        {ev.description}
                      </p>
                    )}
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      )}
    </div>
  )
}

// ── Filter bar ────────────────────────────────────────────────────────────────

function TypeFilter({
  types,
  active,
  onChange,
}: {
  types: string[]
  active: string
  onChange: (t: string) => void
}) {
  if (types.length === 0) return null
  return (
    <div className="flex flex-wrap gap-1.5">
      <button
        onClick={() => onChange('')}
        className={`rounded-full border px-2.5 py-0.5 text-xs transition-colors ${
          active === ''
            ? 'bg-primary text-primary-foreground border-primary'
            : 'border-border hover:border-primary/40'
        }`}
      >
        All
      </button>
      {types.map((t) => {
        const { color, label } = cfg(t)
        return (
          <button
            key={t}
            onClick={() => onChange(t === active ? '' : t)}
            className={`rounded-full border px-2.5 py-0.5 text-xs transition-colors ${
              active === t
                ? 'text-white border-transparent'
                : 'border-border hover:border-primary/40'
            }`}
            style={active === t ? { backgroundColor: color } : { color }}
          >
            {label}
          </button>
        )
      })}
    </div>
  )
}

// ── Main export ───────────────────────────────────────────────────────────────

export function TimelineVisTab({ caseId }: { caseId: string }) {
  const [activeType, setActiveType] = useState('')
  const { data, isLoading } = useTimeline(caseId, { pageSize: 500 })

  const allTypes = useMemo(() => {
    if (!data) return []
    return Array.from(new Set(data.items.map((e) => e.eventType))).sort()
  }, [data])

  const filtered = useMemo(() => {
    if (!data) return []
    return activeType ? data.items.filter((e) => e.eventType === activeType) : data.items
  }, [data, activeType])

  if (isLoading) {
    return (
      <div className="space-y-3">
        <Skeleton className="h-8 w-64" />
        <Skeleton className="h-40" />
        <Skeleton className="h-24" />
        <Skeleton className="h-24" />
      </div>
    )
  }

  if (!data || data.total === 0) {
    return (
      <div className="rounded-lg border border-dashed p-12 text-center">
        <CalendarClock className="mx-auto mb-3 h-10 w-10 text-muted-foreground/30" />
        <p className="text-sm text-muted-foreground">
          No timeline events found. Evidence must be processed through the AI pipeline first.
        </p>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      {/* Stats */}
      <div className="flex items-center gap-2 text-sm text-muted-foreground">
        <Clock className="h-4 w-4" />
        <span>
          {data.total} events ·{' '}
          {filtered.filter((e) => e.eventTimestamp).length} with timestamps
        </span>
        {activeType && (
          <Badge variant="secondary" className="text-xs">
            {cfg(activeType).label}
          </Badge>
        )}
      </div>

      {/* Activity bar chart */}
      <ActivityChart events={filtered} />

      {/* Event type filter */}
      <TypeFilter types={allTypes} active={activeType} onChange={setActiveType} />

      {/* Grouped timeline */}
      <div className="max-h-[600px] overflow-y-auto pr-1">
        <GroupedTimeline events={filtered} />
      </div>
    </div>
  )
}
