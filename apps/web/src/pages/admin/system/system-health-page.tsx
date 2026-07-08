import { AlertTriangle, CheckCircle, RefreshCw, XCircle } from 'lucide-react'
import { PageHeader } from '@/components/common/page-header'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { useSystemHealth } from '@/hooks/use-admin'
import type { ServiceStatus } from '@/types/admin'

function StatusIcon({ status }: { status: ServiceStatus }) {
  if (status === 'healthy') return <CheckCircle className="size-4 text-green-500" />
  if (status === 'degraded') return <AlertTriangle className="size-4 text-yellow-500" />
  return <XCircle className="size-4 text-red-500" />
}

function statusColor(status: ServiceStatus) {
  if (status === 'healthy') return 'bg-green-50 text-green-700 border-green-200'
  if (status === 'degraded') return 'bg-yellow-50 text-yellow-700 border-yellow-200'
  return 'bg-red-50 text-red-700 border-red-200'
}

function fmt(dateStr: string) {
  try { return new Date(dateStr).toLocaleTimeString('en-GB') } catch { return dateStr }
}

export function SystemHealthPage() {
  const { data, isLoading, refetch } = useSystemHealth()

  return (
    <div className="space-y-6 p-6">
      <div className="flex items-start justify-between">
        <PageHeader title="System Health" description="Infrastructure status and queue monitor. Auto-refreshes every 15 seconds." />
        <Button variant="outline" size="sm" onClick={() => refetch()}>
          <RefreshCw className="size-4 mr-1" /> Refresh
        </Button>
      </div>

      {/* Services */}
      <section>
        <h3 className="mb-3 text-sm font-semibold text-gray-700 uppercase tracking-wide">Services</h3>
        {isLoading ? (
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
            {Array.from({ length: 5 }).map((_, i) => <Skeleton key={i} className="h-24 rounded-lg" />)}
          </div>
        ) : (
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
            {data?.services.map(svc => (
              <div key={svc.name} className={`rounded-lg border p-4 ${statusColor(svc.status)}`}>
                <div className="flex items-center gap-2 mb-1">
                  <StatusIcon status={svc.status} />
                  <span className="font-semibold">{svc.name}</span>
                </div>
                <p className="text-xs capitalize">{svc.status}</p>
                {svc.latencyMs != null && (
                  <p className="text-xs mt-0.5">{svc.latencyMs} ms</p>
                )}
                {svc.version && <p className="text-xs opacity-70">v{svc.version}</p>}
                {svc.message && <p className="text-xs opacity-70 truncate" title={svc.message}>{svc.message}</p>}
                <p className="text-xs opacity-50 mt-1">Last check: {fmt(svc.lastCheck)}</p>
              </div>
            ))}
          </div>
        )}
      </section>

      {/* Queues */}
      <section>
        <h3 className="mb-3 text-sm font-semibold text-gray-700 uppercase tracking-wide">Celery Queues</h3>
        <div className="rounded-lg border bg-white shadow-sm overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 text-xs text-gray-500 uppercase tracking-wide">
              <tr>
                {['Queue', 'Pending', 'Active', 'Failed', 'Processed Total'].map(h => (
                  <th key={h} className="px-4 py-2 text-left font-medium">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y">
              {isLoading
                ? Array.from({ length: 5 }).map((_, i) => (
                    <tr key={i}><td colSpan={5} className="p-2"><Skeleton className="h-5 w-full" /></td></tr>
                  ))
                : data?.queues.map(q => (
                    <tr key={q.name} className="hover:bg-gray-50">
                      <td className="px-4 py-2 font-medium capitalize">{q.name}</td>
                      <td className="px-4 py-2">
                        <span className={q.pending > 0 ? 'font-semibold text-yellow-700' : ''}>{q.pending}</span>
                      </td>
                      <td className="px-4 py-2">{q.active}</td>
                      <td className="px-4 py-2">
                        <span className={q.failed > 0 ? 'font-semibold text-red-600' : ''}>{q.failed}</span>
                      </td>
                      <td className="px-4 py-2 text-gray-500">{q.processedTotal.toLocaleString()}</td>
                    </tr>
                  ))}
            </tbody>
          </table>
        </div>
      </section>

      {/* Workers */}
      {data && data.workers.length > 0 && (
        <section>
          <h3 className="mb-3 text-sm font-semibold text-gray-700 uppercase tracking-wide">Workers</h3>
          <div className="rounded-lg border bg-white shadow-sm overflow-hidden">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 text-xs text-gray-500 uppercase tracking-wide">
                <tr>
                  {['Worker', 'Status', 'Active Tasks', 'Processed', 'Failed'].map(h => (
                    <th key={h} className="px-4 py-2 text-left font-medium">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y">
                {data.workers.map(w => (
                  <tr key={w.name} className="hover:bg-gray-50">
                    <td className="px-4 py-2 font-mono text-xs">{w.name}</td>
                    <td className="px-4 py-2">
                      <span className={`rounded-full px-2 py-0.5 text-xs font-semibold ${w.status === 'online' ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500'}`}>
                        {w.status}
                      </span>
                    </td>
                    <td className="px-4 py-2">{w.activeTasks}</td>
                    <td className="px-4 py-2">{w.processed.toLocaleString()}</td>
                    <td className="px-4 py-2">{w.failed}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}

      {data?.workers.length === 0 && (
        <p className="text-sm text-gray-400 italic">No Celery workers online.</p>
      )}
    </div>
  )
}
