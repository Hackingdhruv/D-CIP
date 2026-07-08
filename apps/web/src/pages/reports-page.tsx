import { useState } from 'react'
import { Link } from 'react-router-dom'
import {
  ChevronLeft,
  ChevronRight,
  FileText,
  Loader2,
  RefreshCw,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { PageHeader } from '@/components/common/page-header'
import { useAllReports } from '@/hooks/use-reports'
import { REPORT_STATUS_COLORS, REPORT_TYPE_LABELS } from '@/types/report'

function openExport(caseId: string, reportId: string, format: string) {
  window.open(`/api/v1/cases/${caseId}/reports/${reportId}/export/${format}`, '_blank')
}

export function ReportsPage() {
  const [page, setPage] = useState(1)
  const { data = [], isLoading, isFetching, refetch } = useAllReports(page)

  return (
    <div className="space-y-6">
      <PageHeader
        title="Reports"
        description="All investigation reports across accessible cases."
        actions={
          <Button
            variant="outline"
            size="sm"
            onClick={() => refetch()}
            disabled={isFetching}
          >
            {isFetching ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <RefreshCw className="h-4 w-4" />
            )}
            <span className="ml-1.5">Refresh</span>
          </Button>
        }
      />

      {isLoading ? (
        <div className="space-y-3">
          {Array.from({ length: 5 }).map((_, i) => (
            <Skeleton key={i} className="h-20 rounded-lg" />
          ))}
        </div>
      ) : data.length === 0 ? (
        <div className="flex flex-col items-center justify-center gap-3 rounded-lg border border-dashed py-16 text-center">
          <div className="rounded-full bg-muted p-4">
            <FileText className="h-6 w-6 text-muted-foreground" />
          </div>
          <div>
            <p className="text-sm font-medium">No reports found</p>
            <p className="text-xs text-muted-foreground">
              Open a case and go to the Reports tab to build an investigation report.
            </p>
          </div>
        </div>
      ) : (
        <div className="rounded-lg border overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-muted/40 text-xs text-muted-foreground uppercase tracking-wider">
              <tr>
                <th className="px-4 py-3 text-left font-medium">Report</th>
                <th className="px-4 py-3 text-left font-medium">Type</th>
                <th className="px-4 py-3 text-left font-medium">Status</th>
                <th className="px-4 py-3 text-left font-medium">Version</th>
                <th className="px-4 py-3 text-left font-medium">Created</th>
                <th className="px-4 py-3 text-left font-medium">Exports</th>
                <th className="px-4 py-3 text-right font-medium">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {data.map((r) => {
                const statusClass = REPORT_STATUS_COLORS[r.status] ?? 'bg-gray-100 text-gray-600'
                const canExport = r.status === 'ready' || r.status === 'published'
                return (
                  <tr key={r.id} className="hover:bg-muted/20 transition-colors">
                    <td className="px-4 py-3">
                      <Link
                        to={`/cases/${r.caseId}`}
                        className="font-medium hover:underline line-clamp-1 max-w-xs"
                      >
                        {r.title}
                      </Link>
                    </td>
                    <td className="px-4 py-3 text-muted-foreground">
                      {REPORT_TYPE_LABELS[r.reportType] ?? r.reportType}
                    </td>
                    <td className="px-4 py-3">
                      <span className={`rounded-full px-2 py-0.5 text-[11px] font-semibold ${statusClass}`}>
                        {r.status}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-muted-foreground">
                      v{r.version}
                      {r.parentReportId && (
                        <span className="ml-1 text-[11px] text-muted-foreground">(revised)</span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-muted-foreground text-xs">
                      {new Date(r.createdAt).toLocaleDateString()}
                    </td>
                    <td className="px-4 py-3 text-muted-foreground">{r.exportCount}</td>
                    <td className="px-4 py-3 text-right">
                      <div className="flex items-center justify-end gap-1">
                        <Button
                          variant="ghost"
                          size="sm"
                          disabled={!canExport}
                          onClick={() => openExport(r.caseId, r.id, 'pdf')}
                          className="h-7 text-xs"
                        >
                          PDF
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          disabled={!canExport}
                          onClick={() => openExport(r.caseId, r.id, 'docx')}
                          className="h-7 text-xs"
                        >
                          DOCX
                        </Button>
                        <Link to={`/cases/${r.caseId}`}>
                          <Button variant="outline" size="sm" className="h-7 text-xs">
                            Open Case
                          </Button>
                        </Link>
                      </div>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}

      {/* Pagination */}
      {data.length > 0 && (
        <div className="flex items-center justify-between">
          <p className="text-xs text-muted-foreground">
            Page {page} · {data.length} reports
          </p>
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              disabled={page <= 1}
              onClick={() => setPage((p) => p - 1)}
            >
              <ChevronLeft className="h-4 w-4" />
            </Button>
            <Button
              variant="outline"
              size="sm"
              disabled={data.length < 20}
              onClick={() => setPage((p) => p + 1)}
            >
              <ChevronRight className="h-4 w-4" />
            </Button>
          </div>
        </div>
      )}
    </div>
  )
}
