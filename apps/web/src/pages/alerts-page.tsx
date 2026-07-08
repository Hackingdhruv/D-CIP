import { useState } from 'react'
import { AlertTriangle, Bell, CheckCircle, GitCompare, RefreshCw, XCircle } from 'lucide-react'
import { PageHeader } from '@/components/common/page-header'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import {
  useAlerts,
  useAlertStats,
  useAcknowledgeAlert,
  useResolveAlert,
  useDismissAlert,
} from '@/hooks/use-watchlist'
import type { AlertSeverity, AlertStatus, AlertType, WatchlistAlertRead } from '@/types/watchlist'

function fmt(d: string) {
  try {
    return new Date(d).toLocaleString('en-GB', {
      day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit',
    })
  } catch { return d }
}

const SEVERITY_STYLES: Record<AlertSeverity, string> = {
  critical: 'bg-red-100 text-red-700 border-red-200',
  high: 'bg-orange-100 text-orange-700 border-orange-200',
  medium: 'bg-yellow-100 text-yellow-700 border-yellow-200',
  low: 'bg-blue-100 text-blue-700 border-blue-200',
  info: 'bg-gray-100 text-gray-600 border-gray-200',
}

const STATUS_STYLES: Record<AlertStatus, string> = {
  new: 'bg-red-50 text-red-600',
  acknowledged: 'bg-yellow-50 text-yellow-700',
  resolved: 'bg-green-50 text-green-700',
  dismissed: 'bg-gray-50 text-gray-400',
}

const ALERT_TYPE_LABELS: Record<AlertType, string> = {
  exact_match: 'Exact Match',
  regex_match: 'Regex Match',
  fuzzy_match: 'Fuzzy Match',
  cross_case_match: 'Cross-Case',
  high_risk_match: 'High Risk',
  repeated_appearance: 'Repeated',
  ai_alert: 'AI Alert',
  manual_alert: 'Manual',
  system_alert: 'System',
}

function SeverityBadge({ severity }: { severity: AlertSeverity }) {
  return (
    <span className={`rounded-full border px-2 py-0.5 text-xs font-semibold capitalize ${SEVERITY_STYLES[severity]}`}>
      {severity}
    </span>
  )
}

function AlertRow({
  alert,
  onAcknowledge,
  onResolve,
  onDismiss,
  isPending,
}: {
  alert: WatchlistAlertRead
  onAcknowledge: () => void
  onResolve: () => void
  onDismiss: () => void
  isPending: boolean
}) {
  return (
    <div className={`rounded-lg border p-4 space-y-2 ${alert.status === 'dismissed' ? 'opacity-50' : ''}`}>
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <SeverityBadge severity={alert.severity} />
            <span className={`rounded px-1.5 py-0.5 text-xs font-medium ${STATUS_STYLES[alert.status]}`}>
              {alert.status}
            </span>
            <span className="rounded bg-gray-100 px-1.5 py-0.5 text-xs text-gray-600">
              {ALERT_TYPE_LABELS[alert.alertType] ?? alert.alertType}
            </span>
            {alert.isCrossCase && (
              <span className="flex items-center gap-0.5 rounded bg-purple-100 px-1.5 py-0.5 text-xs font-medium text-purple-700">
                <GitCompare className="size-3" />
                Cross-case ({alert.crossCaseCount})
              </span>
            )}
          </div>
          <p className="mt-1 font-medium text-sm">{alert.title}</p>
          {alert.description && (
            <p className="text-xs text-gray-500 mt-0.5">{alert.description}</p>
          )}
          {/* Cross-case restricted message */}
          {alert.isCrossCase && !alert.crossCaseAccessible && (
            <p className="mt-1 text-xs text-purple-600 italic">
              Matching intelligence exists in another investigation. Additional permissions required.
            </p>
          )}
        </div>
        <div className="shrink-0 text-right space-y-1">
          {alert.caseReference && (
            <p className="text-xs font-mono text-gray-500">{alert.caseReference}</p>
          )}
          {alert.evidenceFilename && (
            <p className="text-xs text-gray-400 truncate max-w-[150px]">{alert.evidenceFilename}</p>
          )}
          <p className="text-xs text-gray-400">{fmt(alert.createdAt)}</p>
        </div>
      </div>

      {alert.matchedValue && (
        <div className="rounded bg-gray-50 border px-3 py-1.5">
          <span className="text-xs text-gray-500">Matched: </span>
          <span className="font-mono text-sm text-gray-800">{alert.matchedValue}</span>
          {alert.matchedEntityType && (
            <span className="ml-2 text-xs text-gray-400">({alert.matchedEntityType})</span>
          )}
          {alert.watchlistName && (
            <span className="ml-2 text-xs text-blue-600">→ {alert.watchlistName}</span>
          )}
        </div>
      )}

      {alert.status === 'new' && (
        <div className="flex items-center gap-2 pt-1">
          <Button size="sm" variant="outline" onClick={onAcknowledge} disabled={isPending}
            className="h-7 text-xs text-yellow-600 border-yellow-200 hover:bg-yellow-50">
            <Bell className="size-3 mr-1" /> Acknowledge
          </Button>
          <Button size="sm" variant="outline" onClick={onResolve} disabled={isPending}
            className="h-7 text-xs text-green-600 border-green-200 hover:bg-green-50">
            <CheckCircle className="size-3 mr-1" /> Resolve
          </Button>
          <Button size="sm" variant="ghost" onClick={onDismiss} disabled={isPending}
            className="h-7 text-xs text-gray-400">
            <XCircle className="size-3 mr-1" /> Dismiss
          </Button>
        </div>
      )}
      {alert.status === 'acknowledged' && (
        <div className="flex items-center gap-2 pt-1">
          <Button size="sm" variant="outline" onClick={onResolve} disabled={isPending}
            className="h-7 text-xs text-green-600 border-green-200 hover:bg-green-50">
            <CheckCircle className="size-3 mr-1" /> Resolve
          </Button>
          <Button size="sm" variant="ghost" onClick={onDismiss} disabled={isPending}
            className="h-7 text-xs text-gray-400">
            <XCircle className="size-3 mr-1" /> Dismiss
          </Button>
        </div>
      )}
    </div>
  )
}

export function AlertsPage() {
  const [page, setPage] = useState(1)
  const [statusFilter, setStatusFilter] = useState<string>('')
  const [severityFilter, setSeverityFilter] = useState<string>('')
  const [typeFilter, setTypeFilter] = useState<string>('')
  const [crossCaseOnly, setCrossCaseOnly] = useState(false)

  const { data: stats } = useAlertStats()
  const { data, isLoading, refetch } = useAlerts({
    page,
    pageSize: 20,
    status: statusFilter || undefined,
    severity: severityFilter || undefined,
    alertType: typeFilter || undefined,
    isCrossCase: crossCaseOnly || undefined,
  })
  const acknowledge = useAcknowledgeAlert()
  const resolve = useResolveAlert()
  const dismiss = useDismissAlert()
  const isPending = acknowledge.isPending || resolve.isPending || dismiss.isPending

  return (
    <div className="space-y-6 p-6">
      <div className="flex items-start justify-between">
        <PageHeader
          title="Alert Center"
          description="Watchlist matches, cross-case correlations, and anomaly detections."
        />
        <Button variant="outline" size="sm" onClick={() => refetch()}>
          <RefreshCw className="size-4 mr-1" /> Refresh
        </Button>
      </div>

      {/* Stats grid */}
      {stats && (
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-5">
          {[
            { label: 'Total Alerts', value: stats.total, alert: false },
            { label: 'New', value: stats.newCount, alert: stats.newCount > 0 },
            { label: 'Critical', value: stats.criticalCount, alert: stats.criticalCount > 0 },
            { label: 'Cross-Case', value: stats.crossCaseCount, alert: false },
            { label: 'This Week', value: stats.alertsThisWeek, alert: false },
          ].map(s => (
            <div
              key={s.label}
              className={`rounded-lg border p-4 shadow-sm ${s.alert ? 'border-red-200 bg-red-50' : 'bg-white'}`}
            >
              <p className="text-xs text-gray-500">{s.label}</p>
              <p className={`text-2xl font-bold mt-0.5 ${s.alert ? 'text-red-600' : 'text-gray-800'}`}>
                {s.value.toLocaleString()}
              </p>
            </div>
          ))}
        </div>
      )}

      {/* Filters */}
      <div className="flex flex-wrap items-center gap-3">
        <select
          value={statusFilter}
          onChange={e => { setStatusFilter(e.target.value); setPage(1) }}
          className="rounded-md border border-gray-300 px-2 py-1 text-sm"
        >
          <option value="">All Status</option>
          <option value="new">New</option>
          <option value="acknowledged">Acknowledged</option>
          <option value="resolved">Resolved</option>
          <option value="dismissed">Dismissed</option>
        </select>
        <select
          value={severityFilter}
          onChange={e => { setSeverityFilter(e.target.value); setPage(1) }}
          className="rounded-md border border-gray-300 px-2 py-1 text-sm"
        >
          <option value="">All Severity</option>
          <option value="critical">Critical</option>
          <option value="high">High</option>
          <option value="medium">Medium</option>
          <option value="low">Low</option>
          <option value="info">Info</option>
        </select>
        <select
          value={typeFilter}
          onChange={e => { setTypeFilter(e.target.value); setPage(1) }}
          className="rounded-md border border-gray-300 px-2 py-1 text-sm"
        >
          <option value="">All Types</option>
          <option value="exact_match">Exact Match</option>
          <option value="regex_match">Regex Match</option>
          <option value="cross_case_match">Cross-Case</option>
          <option value="high_risk_match">High Risk</option>
          <option value="repeated_appearance">Repeated</option>
        </select>
        <label className="flex items-center gap-1.5 text-sm text-gray-600">
          <input
            type="checkbox"
            checked={crossCaseOnly}
            onChange={e => { setCrossCaseOnly(e.target.checked); setPage(1) }}
            className="size-4"
          />
          Cross-case only
        </label>
      </div>

      {/* Alert list */}
      <div className="space-y-3">
        {isLoading ? (
          Array.from({ length: 5 }).map((_, i) => <Skeleton key={i} className="h-28 rounded-lg" />)
        ) : data?.items.length === 0 ? (
          <div className="rounded-lg border border-dashed bg-white p-8 text-center">
            <AlertTriangle className="size-10 text-gray-300 mx-auto mb-2" />
            <p className="text-sm text-gray-500">No alerts match the current filters.</p>
          </div>
        ) : (
          data?.items.map(alert => (
            <AlertRow
              key={alert.id}
              alert={alert}
              isPending={isPending}
              onAcknowledge={() => acknowledge.mutate(alert.id)}
              onResolve={() => resolve.mutate(alert.id)}
              onDismiss={() => dismiss.mutate(alert.id)}
            />
          ))
        )}
      </div>

      {/* Pagination */}
      {data && data.pages > 1 && (
        <div className="flex items-center justify-between text-sm text-gray-500">
          <span>{data.total} alert{data.total !== 1 ? 's' : ''}</span>
          <div className="flex gap-2">
            <Button variant="outline" size="sm" disabled={page <= 1} onClick={() => setPage(p => p - 1)}>Prev</Button>
            <span className="self-center">Page {page} of {data.pages}</span>
            <Button variant="outline" size="sm" disabled={page >= data.pages} onClick={() => setPage(p => p + 1)}>Next</Button>
          </div>
        </div>
      )}
    </div>
  )
}
