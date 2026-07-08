import { Download, FileCode, FileJson, FileText, Globe, Loader2 } from 'lucide-react'
import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { Separator } from '@/components/ui/separator'
import { useNewVersion } from '@/hooks/use-reports'
import { reportsApi } from '@/lib/api/reports'
import type { ReportRead } from '@/types/report'

interface Props {
  report: ReportRead
  onNewVersion?: (newId: string) => void
}

const FORMATS = [
  { key: 'pdf' as const, label: 'PDF', icon: FileText, description: 'Formatted report with cover page, headers, footers' },
  { key: 'docx' as const, label: 'DOCX', icon: FileCode, description: 'Microsoft Word document with styles' },
  { key: 'html' as const, label: 'HTML', icon: Globe, description: 'Standalone HTML file with embedded styles' },
  { key: 'json' as const, label: 'JSON', icon: FileJson, description: 'Machine-readable structured data export' },
]

export function ExportPanel({ report, onNewVersion }: Props) {
  const [downloading, setDownloading] = useState<string | null>(null)
  const { mutate: createVersion, isPending: isVersioning } = useNewVersion(report.caseId)

  const canExport = report.status === 'ready' || report.status === 'published'

  async function handleDownload(format: 'pdf' | 'docx' | 'html' | 'json') {
    setDownloading(format)
    try {
      const url = reportsApi.exportUrl(report.caseId, report.id, format)
      // Use fetch to trigger download so we get the auth header from apiFetch
      const a = document.createElement('a')
      a.href = url
      a.download = `report-${report.id}.${format}`
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
    } finally {
      setTimeout(() => setDownloading(null), 800)
    }
  }

  function handleNewVersion() {
    createVersion(
      { reportId: report.id },
      { onSuccess: (r) => onNewVersion?.(r.id) }
    )
  }

  return (
    <div className="space-y-5">
      <div>
        <p className="text-sm font-medium mb-1">Export Report</p>
        <p className="text-xs text-muted-foreground">
          {canExport
            ? 'Download this report in your preferred format.'
            : 'Generate the report first to enable exports.'}
        </p>
      </div>

      <div className="space-y-2">
        {FORMATS.map(({ key, label, icon: Icon, description }) => (
          <div
            key={key}
            className={`flex items-center justify-between rounded-lg border px-3 py-2.5 ${
              canExport ? 'bg-card' : 'bg-muted/30 opacity-60'
            }`}
          >
            <div className="flex items-center gap-2.5 min-w-0">
              <div className="rounded-md bg-muted p-1.5 shrink-0">
                <Icon className="h-4 w-4 text-muted-foreground" />
              </div>
              <div className="min-w-0">
                <p className="text-sm font-medium">{label}</p>
                <p className="text-xs text-muted-foreground truncate">{description}</p>
              </div>
            </div>
            <Button
              size="sm"
              variant="outline"
              disabled={!canExport || downloading === key}
              onClick={() => handleDownload(key)}
              className="shrink-0 ml-3"
            >
              {downloading === key ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Download className="h-4 w-4" />
              )}
              <span className="ml-1.5">{label}</span>
            </Button>
          </div>
        ))}
      </div>

      {(report.status === 'published') && (
        <>
          <Separator />
          <div className="space-y-2">
            <p className="text-sm font-medium">Version Control</p>
            <p className="text-xs text-muted-foreground">
              This report is published and immutable. Create a new version to regenerate
              with updated case data.
            </p>
            <Button
              variant="outline"
              size="sm"
              disabled={isVersioning}
              onClick={handleNewVersion}
              className="w-full"
            >
              {isVersioning && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              Create New Version
            </Button>
          </div>
        </>
      )}

      {report.exports.length > 0 && (
        <>
          <Separator />
          <div className="space-y-1.5">
            <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
              Export History
            </p>
            {report.exports.slice(0, 5).map((exp) => (
              <div key={exp.id} className="flex items-center justify-between text-xs text-muted-foreground">
                <span className="uppercase font-mono">{exp.format}</span>
                <span>{new Date(exp.createdAt).toLocaleString()}</span>
                {exp.fileSize && (
                  <span>{(exp.fileSize / 1024).toFixed(1)} KB</span>
                )}
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  )
}
