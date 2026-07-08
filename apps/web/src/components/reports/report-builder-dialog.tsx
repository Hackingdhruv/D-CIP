import { useState } from 'react'
import {
  Check,
  ChevronLeft,
  ChevronRight,
  GripVertical,
  Loader2,
  Plus,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { useCreateReport, useReportTemplates, useReportTypes } from '@/hooks/use-reports'
import type { ReportTemplate, ReportType, SectionConfig } from '@/types/report'

interface Props {
  caseId: string
  open: boolean
  onOpenChange: (v: boolean) => void
  onCreated?: (reportId: string) => void
}

// ── Step indicator ────────────────────────────────────────────────────────────

function Steps({ current }: { current: number }) {
  const steps = ['Report Type', 'Template', 'Sections', 'Confirm']
  return (
    <div className="flex items-center gap-2 mb-6">
      {steps.map((s, i) => (
        <div key={s} className="flex items-center gap-2">
          <div
            className={`h-6 w-6 rounded-full flex items-center justify-center text-xs font-bold ${
              i < current
                ? 'bg-primary text-primary-foreground'
                : i === current
                ? 'border-2 border-primary text-primary'
                : 'bg-muted text-muted-foreground'
            }`}
          >
            {i < current ? <Check className="h-3 w-3" /> : i + 1}
          </div>
          <span
            className={`text-xs ${
              i === current ? 'text-foreground font-medium' : 'text-muted-foreground'
            }`}
          >
            {s}
          </span>
          {i < steps.length - 1 && <div className="h-px w-6 bg-border" />}
        </div>
      ))}
    </div>
  )
}

// ── Section list with checkboxes ──────────────────────────────────────────────

function SectionToggleList({
  sections,
  onChange,
}: {
  sections: SectionConfig[]
  onChange: (sections: SectionConfig[]) => void
}) {
  function toggle(idx: number) {
    const next = sections.map((s, i) =>
      i === idx ? { ...s, enabled: !s.enabled } : s
    )
    onChange(next)
  }

  return (
    <div className="space-y-2 max-h-56 overflow-y-auto pr-1">
      {sections.map((s, i) => (
        <div
          key={s.type}
          className={`flex items-center gap-3 rounded-md border px-3 py-2 transition-colors ${
            s.enabled ? 'bg-card' : 'bg-muted/40 opacity-60'
          }`}
        >
          <GripVertical className="h-4 w-4 text-muted-foreground shrink-0" />
          <input
            type="checkbox"
            id={`sec-${s.type}`}
            checked={s.enabled}
            onChange={() => toggle(i)}
            className="accent-primary"
          />
          <label htmlFor={`sec-${s.type}`} className="text-sm cursor-pointer flex-1">
            {s.title}
          </label>
          <span className="text-[10px] text-muted-foreground">{i + 1}</span>
        </div>
      ))}
    </div>
  )
}

// ── Main dialog ───────────────────────────────────────────────────────────────

export function ReportBuilderDialog({ caseId, open, onOpenChange, onCreated }: Props) {
  const [step, setStep] = useState(0)
  const [reportType, setReportType] = useState<ReportType>('detailed')
  const [template, setTemplate] = useState<ReportTemplate>('professional')
  const [title, setTitle] = useState('')
  const [sections, setSections] = useState<SectionConfig[]>([])

  const { data: reportTypes = [] } = useReportTypes()
  const { data: templates = [] } = useReportTemplates()
  const { mutate: create, isPending } = useCreateReport(caseId)

  function handleTemplateSelect(key: ReportTemplate) {
    setTemplate(key)
    const tmpl = templates.find((t) => t.key === key)
    if (tmpl) setSections(tmpl.sections)
  }

  function handleTypeSelect(key: ReportType) {
    setReportType(key)
    const typeDef = reportTypes.find((t) => t.key === key)
    if (typeDef) handleTemplateSelect(typeDef.defaultTemplate as ReportTemplate)
  }

  function handleNext() {
    if (step === 1 && sections.length === 0) {
      const tmpl = templates.find((t) => t.key === template)
      if (tmpl) setSections(tmpl.sections)
    }
    if (step === 2 && !title) {
      const typeDef = reportTypes.find((t) => t.key === reportType)
      setTitle(typeDef?.label ?? 'Investigation Report')
    }
    setStep((s) => s + 1)
  }

  function handleCreate() {
    create(
      {
        reportType,
        template,
        title: title || 'Investigation Report',
        sectionsConfig: sections,
      },
      {
        onSuccess: (report) => {
          onOpenChange(false)
          setStep(0)
          onCreated?.(report.id)
        },
      }
    )
  }

  function handleClose(v: boolean) {
    if (!v) setStep(0)
    onOpenChange(v)
  }

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle>New Investigation Report</DialogTitle>
        </DialogHeader>

        <Steps current={step} />

        {/* Step 0: Report type */}
        {step === 0 && (
          <div className="space-y-3">
            <Label className="text-sm font-medium">Select report type</Label>
            <div className="grid grid-cols-1 gap-2 max-h-64 overflow-y-auto pr-1">
              {reportTypes.map((rt) => (
                <button
                  key={rt.key}
                  onClick={() => handleTypeSelect(rt.key)}
                  className={`text-left rounded-lg border px-3 py-2.5 transition-colors ${
                    reportType === rt.key
                      ? 'border-primary bg-primary/5'
                      : 'border-border hover:border-primary/40'
                  }`}
                >
                  <p className="text-sm font-medium">{rt.label}</p>
                  <p className="text-xs text-muted-foreground">{rt.description}</p>
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Step 1: Template */}
        {step === 1 && (
          <div className="space-y-3">
            <Label className="text-sm font-medium">Select template</Label>
            <div className="grid grid-cols-1 gap-2 max-h-64 overflow-y-auto pr-1">
              {templates.map((tmpl) => (
                <button
                  key={tmpl.key}
                  onClick={() => handleTemplateSelect(tmpl.key)}
                  className={`text-left rounded-lg border px-3 py-2.5 transition-colors ${
                    template === tmpl.key
                      ? 'border-primary bg-primary/5'
                      : 'border-border hover:border-primary/40'
                  }`}
                >
                  <p className="text-sm font-medium">{tmpl.label}</p>
                  <p className="text-xs text-muted-foreground">{tmpl.description}</p>
                  <p className="text-[11px] text-muted-foreground/70 mt-1">
                    {tmpl.sections.length} sections
                  </p>
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Step 2: Sections */}
        {step === 2 && (
          <div className="space-y-3">
            <div className="space-y-1">
              <Label className="text-sm font-medium">Report title</Label>
              <Input
                placeholder="e.g. Investigation Report — Case CASE-2024-001"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                className="h-9"
              />
            </div>
            <div className="space-y-1">
              <Label className="text-sm font-medium">
                Sections ({sections.filter((s) => s.enabled).length} enabled)
              </Label>
              <SectionToggleList sections={sections} onChange={setSections} />
            </div>
          </div>
        )}

        {/* Step 3: Confirm */}
        {step === 3 && (
          <div className="space-y-3">
            <p className="text-sm text-muted-foreground">
              Review your configuration before creating the report.
            </p>
            <div className="rounded-lg border bg-muted/30 p-4 space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-muted-foreground">Type</span>
                <span className="font-medium">
                  {reportTypes.find((t) => t.key === reportType)?.label ?? reportType}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Template</span>
                <span className="font-medium">
                  {templates.find((t) => t.key === template)?.label ?? template}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Title</span>
                <span className="font-medium truncate max-w-[200px]">{title}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Sections</span>
                <span className="font-medium">
                  {sections.filter((s) => s.enabled).length} of {sections.length}
                </span>
              </div>
            </div>
            <p className="text-xs text-muted-foreground">
              The report will be created in draft status. You can generate content after creation.
            </p>
          </div>
        )}

        <DialogFooter className="mt-2">
          {step > 0 && (
            <Button variant="outline" onClick={() => setStep((s) => s - 1)}>
              <ChevronLeft className="mr-1 h-4 w-4" />
              Back
            </Button>
          )}
          <div className="flex-1" />
          {step < 3 ? (
            <Button onClick={handleNext}>
              Next
              <ChevronRight className="ml-1 h-4 w-4" />
            </Button>
          ) : (
            <Button onClick={handleCreate} disabled={isPending}>
              {isPending ? (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              ) : (
                <Plus className="mr-2 h-4 w-4" />
              )}
              Create Report
            </Button>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
