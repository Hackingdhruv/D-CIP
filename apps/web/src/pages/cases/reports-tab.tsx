import { useState } from 'react'
import { FileText, Plus, RefreshCw } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { ReportBuilderDialog } from '@/components/reports/report-builder-dialog'
import { ReportCard } from '@/components/reports/report-card'
import { ReportPreview } from '@/components/reports/report-preview'
import { ExportPanel } from '@/components/reports/export-panel'
import { useReport, useReports } from '@/hooks/use-reports'

interface Props {
  caseId: string
}

function ReportDetailPane({ caseId, reportId }: { caseId: string; reportId: string }) {
  const [activeTab, setActiveTab] = useState<'preview' | 'export'>('preview')
  const { data: report, isLoading } = useReport(caseId, reportId)

  if (isLoading) {
    return (
      <div className="space-y-4 p-6">
        <Skeleton className="h-6 w-1/2" />
        <Skeleton className="h-4 w-1/3" />
        <Skeleton className="h-64" />
      </div>
    )
  }

  if (!report) return null

  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center gap-1 border-b px-4 pt-2 shrink-0">
        {(['preview', 'export'] as const).map((t) => (
          <button
            key={t}
            onClick={() => setActiveTab(t)}
            className={`px-3 py-2 text-sm font-medium border-b-2 transition-colors capitalize ${
              activeTab === t
                ? 'border-primary text-foreground'
                : 'border-transparent text-muted-foreground hover:text-foreground'
            }`}
          >
            {t}
          </button>
        ))}
      </div>

      <div className="flex-1 overflow-y-auto p-5">
        {activeTab === 'preview' ? (
          <ReportPreview report={report} />
        ) : (
          <ExportPanel
            report={report}
            onNewVersion={() => {/* list refetches via invalidateQueries in hook */}}
          />
        )}
      </div>
    </div>
  )
}

export function ReportsTab({ caseId }: Props) {
  const [builderOpen, setBuilderOpen] = useState(false)
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const { data: reports = [], isLoading, refetch, isFetching } = useReports(caseId)

  function handleCreated(id: string) {
    setSelectedId(id)
  }

  return (
    <div className="flex h-[calc(100vh-280px)] min-h-[500px] gap-0 rounded-lg border overflow-hidden">
      {/* Left panel — list */}
      <div className="w-72 shrink-0 flex flex-col border-r">
        <div className="flex items-center justify-between px-4 py-3 border-b">
          <div className="flex items-center gap-2">
            <span className="text-sm font-medium">Reports</span>
            {reports.length > 0 && (
              <span className="text-xs text-muted-foreground">({reports.length})</span>
            )}
          </div>
          <div className="flex items-center gap-1">
            <Button
              variant="ghost"
              size="icon"
              className="h-7 w-7"
              onClick={() => refetch()}
              disabled={isFetching}
            >
              <RefreshCw className={`h-3.5 w-3.5 ${isFetching ? 'animate-spin' : ''}`} />
            </Button>
            <Button size="sm" className="h-7 text-xs" onClick={() => setBuilderOpen(true)}>
              <Plus className="h-3.5 w-3.5 mr-1" />
              New
            </Button>
          </div>
        </div>

        <div className="flex-1 overflow-y-auto p-3 space-y-2">
          {isLoading ? (
            Array.from({ length: 3 }).map((_, i) => (
              <Skeleton key={i} className="h-24 rounded-lg" />
            ))
          ) : reports.length === 0 ? (
            <div className="flex flex-col items-center justify-center gap-3 py-12 text-center">
              <div className="rounded-full bg-muted p-3">
                <FileText className="h-5 w-5 text-muted-foreground" />
              </div>
              <div>
                <p className="text-sm font-medium">No reports yet</p>
                <p className="text-xs text-muted-foreground">
                  Click New to build an investigation report.
                </p>
              </div>
            </div>
          ) : (
            reports.map((r) => (
              <ReportCard
                key={r.id}
                report={r}
                onSelect={setSelectedId}
                isSelected={r.id === selectedId}
              />
            ))
          )}
        </div>
      </div>

      {/* Right panel — preview / export */}
      <div className="flex-1 overflow-hidden">
        {selectedId ? (
          <ReportDetailPane caseId={caseId} reportId={selectedId} />
        ) : (
          <div className="flex flex-col items-center justify-center h-full gap-3 text-center">
            <div className="rounded-full bg-muted p-4">
              <FileText className="h-6 w-6 text-muted-foreground" />
            </div>
            <div>
              <p className="text-sm font-medium">Select a report</p>
              <p className="text-xs text-muted-foreground max-w-xs">
                Select a report from the list or create a new one to preview its content and download exports.
              </p>
            </div>
            <Button size="sm" variant="outline" onClick={() => setBuilderOpen(true)}>
              <Plus className="h-4 w-4 mr-1" />
              Create Report
            </Button>
          </div>
        )}
      </div>

      <ReportBuilderDialog
        caseId={caseId}
        open={builderOpen}
        onOpenChange={setBuilderOpen}
        onCreated={handleCreated}
      />
    </div>
  )
}
