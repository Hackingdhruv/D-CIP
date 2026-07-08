import {
  Download,
  FileText,
  Globe,
  Loader2,
  MoreHorizontal,
  RefreshCw,
  Trash2,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { useDeleteReport, useGenerateReport, usePublishReport } from '@/hooks/use-reports'
import { reportsApi } from '@/lib/api/reports'
import type { ReportListItem } from '@/types/report'
import { REPORT_STATUS_COLORS, REPORT_TYPE_LABELS } from '@/types/report'

interface Props {
  report: ReportListItem
  onSelect: (id: string) => void
  isSelected: boolean
}

function openExport(caseId: string, reportId: string, format: 'pdf' | 'docx' | 'html' | 'json') {
  const url = reportsApi.exportUrl(caseId, reportId, format)
  window.open(url, '_blank')
}

export function ReportCard({ report, onSelect, isSelected }: Props) {
  const { mutate: generate, isPending: isGenerating } = useGenerateReport(report.caseId)
  const { mutate: publish, isPending: isPublishing } = usePublishReport(report.caseId)
  const { mutate: remove } = useDeleteReport(report.caseId)

  const statusClass = REPORT_STATUS_COLORS[report.status] ?? 'bg-gray-100 text-gray-600'
  const typeLabel = REPORT_TYPE_LABELS[report.reportType] ?? report.reportType

  function handleGenerate() {
    generate({ reportId: report.id })
  }

  function handlePublish() {
    publish(report.id)
  }

  function handleDelete() {
    if (confirm(`Delete "${report.title}"? This cannot be undone.`)) {
      remove(report.id)
    }
  }

  return (
    <div
      className={`rounded-lg border bg-card p-4 transition-all cursor-pointer hover:border-primary/40 ${
        isSelected ? 'border-primary ring-1 ring-primary/30' : ''
      }`}
      onClick={() => onSelect(report.id)}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-start gap-3 min-w-0">
          <div className="mt-0.5 rounded-md bg-muted p-1.5 shrink-0">
            <FileText className="h-4 w-4 text-muted-foreground" />
          </div>
          <div className="min-w-0">
            <div className="flex items-center gap-2 flex-wrap mb-1">
              <span className={`rounded-full px-2 py-0.5 text-[11px] font-semibold ${statusClass}`}>
                {report.status}
              </span>
              <span className="text-[11px] text-muted-foreground">
                v{report.version}
              </span>
              {report.parentReportId && (
                <span className="text-[11px] text-muted-foreground">
                  (revised)
                </span>
              )}
            </div>
            <p className="text-sm font-medium leading-snug truncate">{report.title}</p>
            <p className="text-xs text-muted-foreground mt-0.5">{typeLabel}</p>
          </div>
        </div>

        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" size="icon" className="h-7 w-7 shrink-0" onClick={(e) => e.stopPropagation()}>
              <MoreHorizontal className="h-4 w-4" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-44">
            {report.status === 'draft' && (
              <DropdownMenuItem onClick={(e) => { e.stopPropagation(); handleGenerate() }}>
                {isGenerating ? (
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                ) : (
                  <RefreshCw className="mr-2 h-4 w-4" />
                )}
                Generate
              </DropdownMenuItem>
            )}
            {report.status === 'ready' && (
              <>
                <DropdownMenuItem onClick={(e) => { e.stopPropagation(); handleGenerate() }}>
                  <RefreshCw className="mr-2 h-4 w-4" />
                  Regenerate
                </DropdownMenuItem>
                <DropdownMenuItem onClick={(e) => { e.stopPropagation(); handlePublish() }}>
                  {isPublishing ? (
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  ) : (
                    <Globe className="mr-2 h-4 w-4" />
                  )}
                  Publish
                </DropdownMenuItem>
              </>
            )}
            {(report.status === 'ready' || report.status === 'published') && (
              <>
                <DropdownMenuSeparator />
                <DropdownMenuItem onClick={(e) => { e.stopPropagation(); openExport(report.caseId, report.id, 'pdf') }}>
                  <Download className="mr-2 h-4 w-4" />
                  Download PDF
                </DropdownMenuItem>
                <DropdownMenuItem onClick={(e) => { e.stopPropagation(); openExport(report.caseId, report.id, 'docx') }}>
                  <Download className="mr-2 h-4 w-4" />
                  Download DOCX
                </DropdownMenuItem>
                <DropdownMenuItem onClick={(e) => { e.stopPropagation(); openExport(report.caseId, report.id, 'html') }}>
                  <Download className="mr-2 h-4 w-4" />
                  Download HTML
                </DropdownMenuItem>
                <DropdownMenuItem onClick={(e) => { e.stopPropagation(); openExport(report.caseId, report.id, 'json') }}>
                  <Download className="mr-2 h-4 w-4" />
                  Download JSON
                </DropdownMenuItem>
              </>
            )}
            <DropdownMenuSeparator />
            <DropdownMenuItem
              className="text-destructive"
              onClick={(e) => { e.stopPropagation(); handleDelete() }}
            >
              <Trash2 className="mr-2 h-4 w-4" />
              Delete
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>

      <div className="mt-3 flex items-center gap-3 text-xs text-muted-foreground">
        <span>{new Date(report.createdAt).toLocaleDateString()}</span>
        {report.exportCount > 0 && (
          <span>{report.exportCount} export{report.exportCount !== 1 ? 's' : ''}</span>
        )}
        {report.generatedAt && (
          <span>Generated {new Date(report.generatedAt).toLocaleDateString()}</span>
        )}
      </div>
    </div>
  )
}
