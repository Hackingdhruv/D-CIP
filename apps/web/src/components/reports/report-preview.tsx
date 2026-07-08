import { AlertTriangle, Bot, FileText, Lock, User } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Separator } from '@/components/ui/separator'
import type { ReportRead } from '@/types/report'

interface Props {
  report: ReportRead
}

function AiBadge() {
  return (
    <span className="inline-flex items-center gap-1 rounded-full bg-amber-100 px-2 py-0.5 text-[10px] font-semibold text-amber-700">
      <Bot className="h-2.5 w-2.5" />
      AI Analysis
    </span>
  )
}

function VerifiedBadge() {
  return (
    <span className="inline-flex items-center gap-1 rounded-full bg-emerald-100 px-2 py-0.5 text-[10px] font-semibold text-emerald-700">
      <Lock className="h-2.5 w-2.5" />
      Verified
    </span>
  )
}

function str(v: unknown): string {
  return String(v ?? '')
}

// Renders a single section of sections_content
function SectionBlock({ sectionKey, data }: { sectionKey: string; data: unknown }) {
  if (!data || typeof data !== 'object') return null
  const d = data as Record<string, unknown>
  const isAi = d['is_ai_generated'] === true

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold capitalize">
          {str(d['title'] ?? sectionKey).replace(/_/g, ' ')}
        </h3>
        {isAi ? <AiBadge /> : <VerifiedBadge />}
      </div>

      {isAi && !!d['disclaimer'] && (
        <div className="flex items-start gap-2 rounded-md bg-amber-50 border border-amber-200 p-2.5">
          <AlertTriangle className="h-3.5 w-3.5 shrink-0 text-amber-600 mt-0.5" />
          <p className="text-xs text-amber-700">{str(d['disclaimer'])}</p>
        </div>
      )}

      {!!d['content'] && typeof d['content'] === 'string' && (
        <p className="text-sm text-muted-foreground whitespace-pre-wrap">{d['content']}</p>
      )}

      {/* Items list (evidence inventory, entities, etc.) */}
      {Array.isArray(d['items']) && d['items'].length > 0 && (
        <div className="space-y-2">
          {(d['items'] as unknown[]).map((item, i) => {
            if (typeof item !== 'object' || !item) return null
            const it = item as Record<string, unknown>
            return (
              <div key={i} className="rounded-md border bg-muted/20 px-3 py-2 text-xs">
                {Object.entries(it)
                  .filter(([k]) => !k.startsWith('_') && k !== 'id')
                  .slice(0, 6)
                  .map(([k, v]) => (
                    <div key={k} className="flex gap-2">
                      <span className="text-muted-foreground capitalize shrink-0">
                        {k.replace(/_/g, ' ')}:
                      </span>
                      <span className="truncate">{str(v)}</span>
                    </div>
                  ))}
              </div>
            )
          })}
        </div>
      )}

      {/* Timeline entries */}
      {Array.isArray(d['entries']) && d['entries'].length > 0 && (
        <div className="relative space-y-3 pl-4 border-l-2 border-border">
          {(d['entries'] as unknown[]).map((entry, i) => {
            if (typeof entry !== 'object' || !entry) return null
            const e = entry as Record<string, unknown>
            return (
              <div key={i} className="relative">
                <div className="absolute -left-[17px] top-1 h-2.5 w-2.5 rounded-full bg-primary/70" />
                <p className="text-xs font-medium">{str(e['title'] ?? e['event'])}</p>
                {!!e['timestamp'] && (
                  <p className="text-[11px] text-muted-foreground">
                    {new Date(str(e['timestamp'])).toLocaleString()}
                  </p>
                )}
                {!!e['description'] && (
                  <p className="text-xs text-muted-foreground">{str(e['description'])}</p>
                )}
              </div>
            )
          })}
        </div>
      )}

      {!!d['summary'] && typeof d['summary'] === 'string' && (
        <p className="text-sm text-muted-foreground">{d['summary']}</p>
      )}

      {/* Key findings list */}
      {Array.isArray(d['key_findings']) && d['key_findings'].length > 0 && (
        <div className="space-y-1">
          <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider">Key Findings</p>
          <ul className="list-disc list-inside space-y-1">
            {(d['key_findings'] as unknown[]).map((f, i) => (
              <li key={i} className="text-sm">{str(f)}</li>
            ))}
          </ul>
        </div>
      )}

      {/* Notes */}
      {Array.isArray(d['notes']) && d['notes'].length > 0 && (
        <div className="space-y-1">
          <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider flex items-center gap-1">
            <User className="h-3 w-3" /> Investigator Notes
          </p>
          {(d['notes'] as unknown[]).map((n, i) => {
            if (typeof n !== 'object' || !n) return null
            const note = n as Record<string, unknown>
            return (
              <div key={i} className="rounded-md border-l-2 border-blue-300 bg-blue-50/50 px-3 py-1.5 text-xs">
                {!!note['title'] && <p className="font-medium">{str(note['title'])}</p>}
                {!!note['content'] && <p className="text-muted-foreground mt-0.5">{str(note['content'])}</p>}
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}

export function ReportPreview({ report }: Props) {
  const sections = report.sectionsContent as Record<string, unknown>
  const sectionKeys = Object.keys(sections)

  if (sectionKeys.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center gap-3 py-16 text-center">
        <div className="rounded-full bg-muted p-4">
          <FileText className="h-6 w-6 text-muted-foreground" />
        </div>
        <div>
          <p className="text-sm font-medium">No content yet</p>
          <p className="text-xs text-muted-foreground">
            Generate the report to populate sections with case data.
          </p>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-8 py-2">
      {/* Report header */}
      <div className="space-y-1 border-b pb-6">
        <div className="flex items-center gap-2 mb-2">
          <Badge variant="outline" className="text-[10px]">
            v{report.version}
          </Badge>
          <Badge variant="outline" className="text-[10px] capitalize">
            {report.status}
          </Badge>
          {report.contentHash && (
            <span className="text-[10px] text-muted-foreground font-mono">
              SHA-256: {report.contentHash.slice(0, 12)}…
            </span>
          )}
        </div>
        <h1 className="text-lg font-bold">{report.title}</h1>
        {report.generatedAt && (
          <p className="text-xs text-muted-foreground">
            Generated {new Date(report.generatedAt).toLocaleString()}
          </p>
        )}
        {report.publishedAt && (
          <p className="text-xs text-emerald-600">
            Published {new Date(report.publishedAt).toLocaleString()}
          </p>
        )}
      </div>

      {/* Sections */}
      {sectionKeys.map((key, i) => (
        <div key={key}>
          <SectionBlock sectionKey={key} data={sections[key]} />
          {i < sectionKeys.length - 1 && <Separator className="mt-8" />}
        </div>
      ))}

      {/* AI disclaimer footer */}
      <div className="rounded-md border border-amber-200 bg-amber-50 p-3 text-xs text-amber-700">
        <p className="font-semibold mb-1 flex items-center gap-1">
          <AlertTriangle className="h-3 w-3" /> AI Content Disclaimer
        </p>
        <p>
          Sections marked "AI Analysis" are generated by an AI assistant and must be reviewed
          and verified by a qualified investigator before use in legal, judicial, or official
          proceedings. AI-generated content does not constitute investigative findings.
        </p>
      </div>
    </div>
  )
}
