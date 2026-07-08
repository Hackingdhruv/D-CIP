import { useState } from 'react'
import { Search } from 'lucide-react'
import { PageHeader } from '@/components/common/page-header'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { useAuditSearch, useAuditStats } from '@/hooks/use-admin'

const EVENT_TYPES = [
  'login_success', 'login_failed', 'logout', 'account_locked', 'account_unlocked',
  'user_created', 'user_updated', 'user_deleted', 'role_assigned', 'role_revoked',
  'password_changed', 'permission_changed',
]

function fmt(dateStr: string) {
  try { return new Date(dateStr).toLocaleString('en-GB', { day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit', second: '2-digit' }) } catch { return dateStr }
}

function EventTypeBadge({ type }: { type: string }) {
  const colors: Record<string, string> = {
    login_failed: 'bg-red-100 text-red-700',
    account_locked: 'bg-red-100 text-red-700',
    login_success: 'bg-green-100 text-green-700',
    logout: 'bg-gray-100 text-gray-600',
    user_created: 'bg-blue-100 text-blue-700',
    user_deleted: 'bg-red-100 text-red-700',
    role_assigned: 'bg-purple-100 text-purple-700',
    role_revoked: 'bg-yellow-100 text-yellow-700',
    permission_changed: 'bg-orange-100 text-orange-700',
  }
  const cls = colors[type] ?? 'bg-gray-100 text-gray-600'
  return (
    <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${cls}`}>
      {type.replace(/_/g, ' ')}
    </span>
  )
}

export function AuditCenterPage() {
  const [q, setQ] = useState('')
  const [eventType, setEventType] = useState<string | undefined>()
  const [page, setPage] = useState(1)
  const [inputVal, setInputVal] = useState('')

  const { data, isLoading } = useAuditSearch({ q, eventType, page, pageSize: 50 })
  const { data: stats } = useAuditStats()

  function handleSearch(e: React.FormEvent) {
    e.preventDefault()
    setQ(inputVal)
    setPage(1)
  }

  return (
    <div className="space-y-6 p-6">
      <PageHeader title="Audit Center" description="Complete searchable audit history of all platform events." />

      {/* Stats row */}
      {stats && (
        <div className="flex gap-4 flex-wrap text-sm">
          {[
            { label: 'Total Events', value: stats.totalEvents.toLocaleString() },
            { label: 'Today', value: stats.eventsToday.toLocaleString() },
            { label: 'This Week', value: stats.eventsThisWeek.toLocaleString() },
          ].map(s => (
            <div key={s.label} className="rounded-lg border bg-white px-4 py-2 shadow-sm">
              <span className="text-gray-500">{s.label}: </span>
              <span className="font-semibold">{s.value}</span>
            </div>
          ))}
        </div>
      )}

      {/* Filters */}
      <form onSubmit={handleSearch} className="flex items-center gap-3 flex-wrap">
        <div className="relative">
          <Search className="absolute left-2.5 top-2 size-4 text-gray-400" />
          <Input
            value={inputVal}
            onChange={e => setInputVal(e.target.value)}
            placeholder="Search event types…"
            className="pl-8 w-56"
          />
        </div>
        <select
          className="rounded-md border px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          value={eventType ?? ''}
          onChange={e => { setEventType(e.target.value || undefined); setPage(1) }}
        >
          <option value="">All event types</option>
          {EVENT_TYPES.map(t => <option key={t} value={t}>{t.replace(/_/g, ' ')}</option>)}
        </select>
        <Button type="submit" size="sm">Search</Button>
        <Button variant="ghost" size="sm" type="button" onClick={() => { setQ(''); setInputVal(''); setEventType(undefined); setPage(1) }}>
          Clear
        </Button>
      </form>

      {/* Table */}
      <div className="rounded-lg border bg-white shadow-sm overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 text-xs text-gray-500 uppercase tracking-wide">
            <tr>
              {['Timestamp', 'Event', 'User', 'Actor', 'IP Address', 'Details'].map(h => (
                <th key={h} className="px-4 py-2 text-left font-medium">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y">
            {isLoading
              ? Array.from({ length: 10 }).map((_, i) => (
                  <tr key={i}><td colSpan={6} className="p-2"><Skeleton className="h-5 w-full" /></td></tr>
                ))
              : data?.items.map(e => (
                  <tr key={e.id} className="hover:bg-gray-50">
                    <td className="px-4 py-2 text-xs font-mono whitespace-nowrap">{fmt(e.createdAt)}</td>
                    <td className="px-4 py-2"><EventTypeBadge type={e.eventType} /></td>
                    <td className="px-4 py-2 text-xs">
                      {e.userFullName ? <><p className="font-medium">{e.userFullName}</p><p className="text-gray-400">{e.userEmail}</p></> : <span className="text-gray-400">—</span>}
                    </td>
                    <td className="px-4 py-2 text-xs">
                      {e.actorEmail ? <><p className="font-medium">{e.actorFullName}</p><p className="text-gray-400">{e.actorEmail}</p></> : <span className="text-gray-400">—</span>}
                    </td>
                    <td className="px-4 py-2 font-mono text-xs">{e.ipAddress ?? '—'}</td>
                    <td className="px-4 py-2 text-xs text-gray-500">
                      {e.metadata ? (
                        <details className="cursor-pointer">
                          <summary className="text-blue-600">view</summary>
                          <pre className="mt-1 text-xs bg-gray-50 rounded p-1 max-w-xs overflow-auto">{JSON.stringify(e.metadata, null, 2)}</pre>
                        </details>
                      ) : '—'}
                    </td>
                  </tr>
                ))}
          </tbody>
        </table>
        {data && data.pages > 1 && (
          <div className="flex items-center justify-between border-t px-4 py-2 text-sm text-gray-500">
            <span>{data.total.toLocaleString()} events</span>
            <div className="flex gap-2">
              <Button variant="outline" size="sm" disabled={page <= 1} onClick={() => setPage(p => p - 1)}>Prev</Button>
              <span className="self-center">Page {page} of {data.pages}</span>
              <Button variant="outline" size="sm" disabled={page >= data.pages} onClick={() => setPage(p => p + 1)}>Next</Button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
