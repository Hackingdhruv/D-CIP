import { PageHeader } from '@/components/common/page-header'
import { Skeleton } from '@/components/ui/skeleton'
import { ChartPie } from '@/components/dashboard/chart-pie'
import { useStorageOverview } from '@/hooks/use-admin'

function fmtBytes(b: number): string {
  if (b >= 1e9) return `${(b / 1e9).toFixed(2)} GB`
  if (b >= 1e6) return `${(b / 1e6).toFixed(1)} MB`
  if (b >= 1e3) return `${(b / 1e3).toFixed(0)} KB`
  return `${b} B`
}

function fmt(dateStr: string) {
  try {
    return new Date(dateStr).toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' })
  } catch { return dateStr }
}

export function StorageCenterPage() {
  const { data, isLoading } = useStorageOverview()

  return (
    <div className="space-y-6 p-6">
      <PageHeader title="Storage Center" description="Evidence storage analytics, breakdown by type, and largest files." />

      {/* Overview cards */}
      {isLoading ? (
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
          {Array.from({ length: 4 }).map((_, i) => <Skeleton key={i} className="h-24 rounded-lg" />)}
        </div>
      ) : data ? (
        <>
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
            {[
              { label: 'Total Storage Used', value: fmtBytes(data.totalUsedBytes), color: 'text-blue-600' },
              { label: 'Total Files', value: data.totalFileCount.toLocaleString(), color: 'text-indigo-600' },
              { label: 'Growth (7 days)', value: fmtBytes(data.growthLast7Days), color: 'text-teal-600' },
              { label: 'Growth (30 days)', value: fmtBytes(data.growthLast30Days), color: 'text-purple-600' },
            ].map(card => (
              <div key={card.label} className="rounded-lg border bg-white p-4 shadow-sm">
                <p className="text-sm text-gray-500 font-medium">{card.label}</p>
                <p className={`text-2xl font-bold ${card.color} mt-1`}>{card.value}</p>
              </div>
            ))}
          </div>

          {/* Storage usage bar */}
          <div className="rounded-lg border bg-white p-4 shadow-sm">
            <div className="flex items-center justify-between mb-2">
              <p className="text-sm font-medium">Storage Usage</p>
              <p className="text-sm text-gray-500">{data.usedPct.toFixed(1)}%</p>
            </div>
            <div className="h-3 rounded-full bg-gray-100 overflow-hidden">
              <div
                className={`h-full rounded-full transition-all ${data.usedPct >= 95 ? 'bg-red-500' : data.usedPct >= data.warningThresholdPct ? 'bg-yellow-500' : 'bg-blue-500'}`}
                style={{ width: `${Math.min(data.usedPct, 100)}%` }}
              />
            </div>
            {data.usedPct >= data.warningThresholdPct && (
              <p className="text-xs text-yellow-600 mt-1">Warning: storage above {data.warningThresholdPct}% threshold.</p>
            )}
          </div>

          <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
            {/* Breakdown by type */}
            <div className="rounded-lg border bg-white p-4 shadow-sm">
              <h3 className="mb-3 text-sm font-semibold text-gray-700">Storage by Type</h3>
              {data.byType.length > 0 ? (
                <div className="flex gap-4 items-start">
                  <div className="w-40 shrink-0">
                    <ChartPie
                      labels={data.byType.slice(0, 8).map(t => t.label)}
                      data={data.byType.slice(0, 8).map(t => t.totalBytes)}
                    />
                  </div>
                  <ul className="flex-1 space-y-1 text-xs">
                    {data.byType.slice(0, 10).map(t => (
                      <li key={t.mimeType} className="flex items-center justify-between">
                        <span className="text-gray-700">{t.label}</span>
                        <span className="font-medium">{fmtBytes(t.totalBytes)}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              ) : <p className="text-sm text-gray-400 italic">No evidence files stored.</p>}
            </div>

            {/* Largest files */}
            <div className="rounded-lg border bg-white p-4 shadow-sm">
              <h3 className="mb-3 text-sm font-semibold text-gray-700">Largest Files</h3>
              {data.largestFiles.length > 0 ? (
                <ul className="space-y-2">
                  {data.largestFiles.slice(0, 10).map(f => (
                    <li key={f.evidenceId} className="flex items-start justify-between gap-2 text-xs">
                      <div className="min-w-0">
                        <p className="font-medium truncate">{f.originalFilename}</p>
                        <p className="text-gray-500">{f.caseReference} · {fmt(f.uploadedAt)}</p>
                      </div>
                      <span className="shrink-0 font-mono text-gray-600">{fmtBytes(f.fileSize)}</span>
                    </li>
                  ))}
                </ul>
              ) : <p className="text-sm text-gray-400 italic">No files yet.</p>}
            </div>
          </div>
        </>
      ) : null}
    </div>
  )
}
