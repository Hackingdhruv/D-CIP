import { AlertCircle, Briefcase, Database, FileText, RefreshCw, Shield, Users } from 'lucide-react'
import { PageHeader } from '@/components/common/page-header'
import { ChartBar } from '@/components/dashboard/chart-bar'
import { ChartLine } from '@/components/dashboard/chart-line'
import { ChartPie } from '@/components/dashboard/chart-pie'
import { HealthBadge } from '@/components/dashboard/health-badge'
import { Heatmap } from '@/components/dashboard/heatmap'
import { StatCard } from '@/components/dashboard/stat-card'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import {
  useExecutiveDashboard,
  useIntelligenceDashboard,
  useInvestigatorDashboard,
  useOperationsDashboard,
} from '@/hooks/use-dashboard'

// ── Shared helpers ─────────────────────────────────────────────────────────────

function SectionTitle({ children }: { children: React.ReactNode }) {
  return <h3 className="text-sm font-semibold text-foreground/70 uppercase tracking-wide mb-3">{children}</h3>
}

function Card({ children, className = '' }: { children: React.ReactNode; className?: string }) {
  return <div className={`rounded-lg border bg-card p-4 shadow-sm ${className}`}>{children}</div>
}

function DashboardError({ message }: { message: string }) {
  return (
    <div className="flex items-center gap-2 rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700">
      <AlertCircle className="h-4 w-4 shrink-0" />
      <span>{message}</span>
    </div>
  )
}

function LoadingGrid({ count = 4 }: { count?: number }) {
  return (
    <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
      {Array.from({ length: count }).map((_, i) => (
        <Skeleton key={i} className="h-24 rounded-lg" />
      ))}
    </div>
  )
}

const PRIORITY_COLORS = ['#10b981', '#3b82f6', '#f59e0b', '#ef4444']
const STATUS_COLORS = ['#6b7280', '#3b82f6', '#8b5cf6', '#f59e0b', '#94a3b8', '#10b981', '#374151']
const ENTITY_COLORS = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#06b6d4', '#f97316', '#ec4899', '#14b8a6', '#6366f1']

// ── Executive Tab ─────────────────────────────────────────────────────────────

function ExecutiveTab() {
  const { data, isLoading, error } = useExecutiveDashboard()

  if (isLoading) return <div className="space-y-6"><LoadingGrid /><LoadingGrid count={2} /></div>
  if (error) return <DashboardError message="Failed to load executive dashboard." />
  if (!data) return null

  const d = data

  const openedLabels = d.casesOpenedLast30Days.map((r) => r.date.slice(5))
  const openedData = d.casesOpenedLast30Days.map((r) => r.count)
  const evLabels = d.evidenceUploadedLast30Days.map((r) => r.date.slice(5))
  const evData = d.evidenceUploadedLast30Days.map((r) => r.count)

  const statusLabels = ['Draft', 'Open', 'In Progress', 'Under Review', 'On Hold', 'Closed', 'Archived']
  const statusData = [
    d.statusBreakdown.draft,
    d.statusBreakdown.open,
    d.statusBreakdown.inProgress,
    d.statusBreakdown.underReview,
    d.statusBreakdown.onHold,
    d.statusBreakdown.closed,
    d.statusBreakdown.archived,
  ]

  const priorityLabels = ['Low', 'Medium', 'High', 'Critical']
  const priorityData = [
    d.priorityBreakdown.low,
    d.priorityBreakdown.medium,
    d.priorityBreakdown.high,
    d.priorityBreakdown.critical,
  ]

  return (
    <div className="space-y-6">
      {/* Top stats */}
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        <StatCard label="Active Cases" value={d.activeCases} icon={<Briefcase className="h-4 w-4" />} colorClass="text-blue-600" />
        <StatCard label="High Priority" value={d.highPriorityCases} icon={<AlertCircle className="h-4 w-4" />} colorClass="text-red-500" />
        <StatCard label="Closed Cases" value={d.closedCases} icon={<Shield className="h-4 w-4" />} colorClass="text-green-600" />
        <StatCard label="Total Cases" value={d.totalCases} icon={<FileText className="h-4 w-4" />} colorClass="text-muted-foreground" />
      </div>

      <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        <StatCard label="Evidence Today" value={d.evidenceUploadedToday} colorClass="text-purple-600" />
        <StatCard label="Total Evidence" value={d.totalEvidence} colorClass="text-indigo-600" />
        <StatCard label="Reports Generated" value={d.reportsGenerated} colorClass="text-orange-500" />
        <StatCard label="Avg Investigation" value={Math.round(d.avgInvestigationDays)} suffix="days" colorClass="text-teal-600" />
      </div>

      {/* Charts row */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <Card>
          <SectionTitle>Cases Opened — Last 30 Days</SectionTitle>
          <ChartLine
            labels={openedLabels}
            datasets={[{ label: 'Cases', data: openedData, borderColor: '#3b82f6', backgroundColor: 'rgba(59,130,246,0.1)', fill: true, tension: 0.4 }]}
          />
        </Card>
        <Card>
          <SectionTitle>Evidence Uploaded — Last 30 Days</SectionTitle>
          <ChartLine
            labels={evLabels}
            datasets={[{ label: 'Evidence', data: evData, borderColor: '#8b5cf6', backgroundColor: 'rgba(139,92,246,0.1)', fill: true, tension: 0.4 }]}
          />
        </Card>
      </div>

      {/* Status / Priority charts */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <Card>
          <SectionTitle>Cases by Status</SectionTitle>
          <ChartPie labels={statusLabels} data={statusData} colors={STATUS_COLORS} />
        </Card>
        <Card>
          <SectionTitle>Cases by Priority</SectionTitle>
          <ChartPie labels={priorityLabels} data={priorityData} colors={PRIORITY_COLORS} />
        </Card>
      </div>

      {/* Investigator workload */}
      {d.investigatorWorkload.length > 0 && (
        <Card>
          <SectionTitle>Investigator Workload</SectionTitle>
          <ChartBar
            labels={d.investigatorWorkload.map((w) => w.fullName)}
            datasets={[
              { label: 'Active Cases', data: d.investigatorWorkload.map((w) => w.activeCaseCount), backgroundColor: '#3b82f6' },
              { label: 'Open Tasks', data: d.investigatorWorkload.map((w) => w.openTaskCount), backgroundColor: '#f59e0b' },
            ]}
            horizontal
            height={Math.max(200, d.investigatorWorkload.length * 40)}
          />
        </Card>
      )}

      {/* Recently active cases */}
      {d.recentlyActiveCases.length > 0 && (
        <Card>
          <SectionTitle>Recently Active Cases</SectionTitle>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-xs text-muted-foreground uppercase border-b">
                  <th className="pb-2 pr-4">Reference</th>
                  <th className="pb-2 pr-4">Title</th>
                  <th className="pb-2 pr-4">Status</th>
                  <th className="pb-2 pr-4">Priority</th>
                  <th className="pb-2">Last Updated</th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {d.recentlyActiveCases.map((c) => (
                  <tr key={c.id} className="hover:bg-accent/40">
                    <td className="py-2 pr-4 font-mono text-xs text-primary">{c.referenceNumber}</td>
                    <td className="py-2 pr-4 max-w-xs truncate">{c.title}</td>
                    <td className="py-2 pr-4"><Badge variant="secondary" className="text-xs">{c.status.replace('_', ' ')}</Badge></td>
                    <td className="py-2 pr-4 capitalize text-xs">{c.priority}</td>
                    <td className="py-2 text-xs text-muted-foreground">{new Date(c.updatedAt).toLocaleDateString()}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}
    </div>
  )
}

// ── Intelligence Tab ──────────────────────────────────────────────────────────

function IntelligenceTab() {
  const { data, isLoading, error } = useIntelligenceDashboard()

  if (isLoading) return <div className="space-y-6"><LoadingGrid /><LoadingGrid count={2} /></div>
  if (error) return <DashboardError message="Failed to load intelligence dashboard." />
  if (!data) return null

  const d = data

  return (
    <div className="space-y-6">
      {/* Summary stats */}
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-3">
        <StatCard label="Total Unique Entities" value={d.totalUniqueEntities} colorClass="text-blue-600" />
        <StatCard label="Avg Entities / Case" value={Math.round(d.avgEntitiesPerCase)} colorClass="text-purple-600" />
        <StatCard label="Top Keywords" value={d.topKeywords.length} colorClass="text-teal-600" />
      </div>

      {/* Entity distribution */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <Card>
          <SectionTitle>Entity Distribution</SectionTitle>
          <ChartBar
            labels={d.entityDistribution.map((e) => e.entityType.replace('_', ' '))}
            datasets={[{
              label: 'Count',
              data: d.entityDistribution.map((e) => e.count),
              backgroundColor: ENTITY_COLORS,
            }]}
            height={240}
          />
        </Card>
        <Card>
          <SectionTitle>AI Confidence Distribution</SectionTitle>
          <ChartBar
            labels={d.aiConfidenceDistribution.map((b) => b.bucket)}
            datasets={[{
              label: 'Entities',
              data: d.aiConfidenceDistribution.map((b) => b.count),
              backgroundColor: ['#ef4444', '#f59e0b', '#10b981', '#3b82f6'],
            }]}
            height={240}
          />
        </Card>
      </div>

      {/* Evidence type distribution */}
      {d.evidenceTypeDistribution.length > 0 && (
        <Card>
          <SectionTitle>Evidence by Type</SectionTitle>
          <ChartPie
            labels={d.evidenceTypeDistribution.map((e) => e.label)}
            data={d.evidenceTypeDistribution.map((e) => e.count)}
          />
        </Card>
      )}

      {/* Top entities */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        {[
          { label: 'Top Persons', items: d.topPersons },
          { label: 'Top Organizations', items: d.topOrganizations },
          { label: 'Top Devices', items: d.topDevices },
        ].map(({ label, items }) => (
          <Card key={label}>
            <SectionTitle>{label}</SectionTitle>
            {items.length === 0 ? (
              <p className="text-sm text-muted-foreground italic">No data</p>
            ) : (
              <ul className="space-y-1.5">
                {items.slice(0, 8).map((e) => (
                  <li key={e.value} className="flex items-center justify-between text-sm">
                    <span className="truncate max-w-[70%] font-medium">{e.value}</span>
                    <span className="text-xs text-muted-foreground">{e.occurrenceCount}×</span>
                  </li>
                ))}
              </ul>
            )}
          </Card>
        ))}
      </div>

      {/* Timeline heatmap */}
      <Card>
        <SectionTitle>Activity Heatmap — Last 30 Days</SectionTitle>
        <Heatmap data={d.timelineHeatmap} />
      </Card>

      {/* Top keywords */}
      {d.topKeywords.length > 0 && (
        <Card>
          <SectionTitle>Top Keywords</SectionTitle>
          <div className="flex flex-wrap gap-2">
            {d.topKeywords.slice(0, 30).map((kw) => (
              <span
                key={kw.keyword}
                className="inline-flex items-center gap-1 rounded-full bg-blue-50 px-3 py-1 text-xs font-medium text-blue-700"
              >
                {kw.keyword}
                <span className="text-blue-400">({kw.occurrenceCount})</span>
              </span>
            ))}
          </div>
        </Card>
      )}
    </div>
  )
}

// ── Operations Tab ────────────────────────────────────────────────────────────

function OperationsTab() {
  const { data, isLoading, error } = useOperationsDashboard()

  if (isLoading) return <div className="space-y-6"><LoadingGrid /><LoadingGrid count={2} /></div>
  if (error) return <DashboardError message="Failed to load operations dashboard." />
  if (!data) return null

  const d = data

  const totalEvidence = Object.values(d.evidenceByStatus).reduce((a, b) => a + b, 0)
  const failedPct = totalEvidence > 0 ? ((d.evidenceByStatus['failed'] ?? 0) / totalEvidence * 100).toFixed(1) : '0.0'

  return (
    <div className="space-y-6">
      {/* Processing stats */}
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-3">
        <StatCard label="Failed (24h)" value={d.failedProcessing24h} colorClass={d.failedProcessing24h > 0 ? 'text-red-500' : 'text-green-600'} />
        <StatCard label="Stored Files" value={d.storage.fileCount} colorClass="text-blue-600" />
        <StatCard
          label="Storage Used"
          value={Math.round(d.storage.usedBytes / 1_048_576)}
          suffix="MB"
          colorClass="text-purple-600"
        />
      </div>

      {/* Service health */}
      <Card>
        <SectionTitle>Service Health</SectionTitle>
        <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
          {d.services.map((svc) => (
            <HealthBadge key={svc.name} service={svc} />
          ))}
        </div>
      </Card>

      {/* Queue status */}
      {d.queues.length > 0 && (
        <Card>
          <SectionTitle>Queue Status</SectionTitle>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-xs text-muted-foreground uppercase border-b">
                  <th className="pb-2 pr-6">Queue</th>
                  <th className="pb-2 pr-6">Pending</th>
                  <th className="pb-2">Active</th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {d.queues.map((q) => (
                  <tr key={q.name} className="hover:bg-accent/40">
                    <td className="py-2 pr-6 font-mono text-xs">{q.name}</td>
                    <td className="py-2 pr-6">
                      <span className={q.pending > 0 ? 'text-yellow-600 font-semibold' : 'text-muted-foreground'}>
                        {q.pending}
                      </span>
                    </td>
                    <td className="py-2 text-foreground/70">{q.active}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}

      {/* Evidence pipeline */}
      {Object.keys(d.evidenceByStatus).length > 0 && (
        <Card>
          <SectionTitle>Evidence Pipeline</SectionTitle>
          <div className="flex items-center justify-between text-xs text-muted-foreground mb-3">
            <span>Total: {totalEvidence.toLocaleString()}</span>
            <span className={parseFloat(failedPct) > 5 ? 'text-red-500 font-semibold' : ''}>
              Failed: {failedPct}%
            </span>
          </div>
          <ChartBar
            labels={Object.keys(d.evidenceByStatus).map((s) => s.replace('_', ' '))}
            datasets={[{
              label: 'Evidence Items',
              data: Object.values(d.evidenceByStatus),
              backgroundColor: Object.keys(d.evidenceByStatus).map((s) =>
                s === 'failed' ? '#ef4444' : s === 'completed' ? '#10b981' : '#3b82f6'
              ),
            }]}
            horizontal
            height={Math.max(180, Object.keys(d.evidenceByStatus).length * 36)}
          />
        </Card>
      )}

      {/* Processing performance */}
      {d.processingStats.avgTotalSeconds != null && (
        <Card>
          <SectionTitle>Processing Performance</SectionTitle>
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 text-sm">
            {d.processingStats.avgOcrSeconds != null && (
              <div>
                <p className="text-muted-foreground">Avg OCR Time</p>
                <p className="text-lg font-semibold">{d.processingStats.avgOcrSeconds.toFixed(1)}s</p>
              </div>
            )}
            {d.processingStats.avgAiSeconds != null && (
              <div>
                <p className="text-muted-foreground">Avg AI Time</p>
                <p className="text-lg font-semibold">{d.processingStats.avgAiSeconds.toFixed(1)}s</p>
              </div>
            )}
            {d.processingStats.avgTotalSeconds != null && (
              <div>
                <p className="text-muted-foreground">Avg Total Time</p>
                <p className="text-lg font-semibold">{d.processingStats.avgTotalSeconds.toFixed(1)}s</p>
              </div>
            )}
          </div>
        </Card>
      )}
    </div>
  )
}

// ── Investigator Tab ──────────────────────────────────────────────────────────

function InvestigatorTab() {
  const { data, isLoading, error } = useInvestigatorDashboard()

  if (isLoading) return <div className="space-y-6"><LoadingGrid /><LoadingGrid count={2} /></div>
  if (error) return <DashboardError message="Failed to load your dashboard." />
  if (!data) return null

  const d = data
  const p = d.productivity

  return (
    <div className="space-y-6">
      {/* Productivity stats */}
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-5">
        <StatCard label="Active Cases" value={p.casesActive} colorClass="text-blue-600" />
        <StatCard label="Closed (30d)" value={p.casesClosed30d} colorClass="text-green-600" />
        <StatCard label="Tasks Done (30d)" value={p.tasksCompleted30d} colorClass="text-purple-600" />
        <StatCard label="Evidence (30d)" value={p.evidenceItemsUploaded30d} colorClass="text-orange-500" />
        <StatCard label="Notes (30d)" value={p.notesCreated30d} colorClass="text-teal-600" />
      </div>

      {/* My cases */}
      {d.assignedCases.length > 0 && (
        <Card>
          <SectionTitle>My Active Cases</SectionTitle>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-xs text-muted-foreground uppercase border-b">
                  <th className="pb-2 pr-4">Reference</th>
                  <th className="pb-2 pr-4">Title</th>
                  <th className="pb-2 pr-4">Status</th>
                  <th className="pb-2 pr-4">Priority</th>
                  <th className="pb-2">Open Tasks</th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {d.assignedCases.map((c) => (
                  <tr key={c.id} className="hover:bg-accent/40">
                    <td className="py-2 pr-4 font-mono text-xs text-primary">{c.referenceNumber}</td>
                    <td className="py-2 pr-4 max-w-xs truncate">{c.title}</td>
                    <td className="py-2 pr-4"><Badge variant="secondary" className="text-xs">{c.status.replace('_', ' ')}</Badge></td>
                    <td className="py-2 pr-4 capitalize text-xs">{c.priority}</td>
                    <td className="py-2">
                      {c.openTaskCount > 0
                        ? <Badge variant="destructive" className="text-xs">{c.openTaskCount}</Badge>
                        : <span className="text-xs text-muted-foreground">—</span>
                      }
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}

      {/* Open tasks */}
      {d.openTasks.length > 0 && (
        <Card>
          <SectionTitle>My Open Tasks</SectionTitle>
          <div className="space-y-2">
            {d.openTasks.map((t) => (
              <div key={t.id} className="flex items-start justify-between gap-2 rounded border p-2.5 text-sm hover:bg-accent/40">
                <div className="flex-1 min-w-0">
                  <p className="font-medium truncate">{t.title}</p>
                  <p className="text-xs text-muted-foreground mt-0.5">{t.caseReference}</p>
                </div>
                <div className="flex items-center gap-2 shrink-0">
                  <Badge variant="outline" className="text-xs capitalize">{t.priority}</Badge>
                  {t.dueDate && (
                    <span className={`text-xs ${new Date(t.dueDate) < new Date() ? 'text-red-500 font-medium' : 'text-muted-foreground'}`}>
                      {new Date(t.dueDate).toLocaleDateString()}
                    </span>
                  )}
                </div>
              </div>
            ))}
          </div>
        </Card>
      )}

      {/* Recent notes + evidence */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        {d.recentNotes.length > 0 && (
          <Card>
            <SectionTitle>Recent Notes</SectionTitle>
            <ul className="space-y-1.5">
              {d.recentNotes.map((n) => (
                <li key={n.id} className="flex items-center justify-between text-sm gap-2">
                  <span className="truncate">{n.isPinned ? '📌 ' : ''}{n.title}</span>
                  <span className="text-xs text-muted-foreground shrink-0">{n.caseReference}</span>
                </li>
              ))}
            </ul>
          </Card>
        )}
        {d.recentEvidence.length > 0 && (
          <Card>
            <SectionTitle>Recent Evidence</SectionTitle>
            <ul className="space-y-1.5">
              {d.recentEvidence.map((e) => (
                <li key={e.id} className="flex items-center justify-between text-sm gap-2">
                  <span className="truncate font-mono text-xs">{e.originalFilename}</span>
                  <span className="text-xs text-muted-foreground shrink-0">{e.caseReference}</span>
                </li>
              ))}
            </ul>
          </Card>
        )}
      </div>
    </div>
  )
}

// ── Page ──────────────────────────────────────────────────────────────────────

export function DashboardPage() {
  return (
    <div className="space-y-6">
      <PageHeader
        title="Investigation Intelligence Dashboard"
        description="Real-time platform metrics, entity analytics, infrastructure health, and your personal investigator view."
        actions={
          <div className="flex items-center gap-1 text-xs text-muted-foreground">
            <RefreshCw className="h-3 w-3" />
            Auto-refreshing
          </div>
        }
      />
      <Tabs defaultValue="executive">
        <TabsList className="grid w-full grid-cols-4">
          <TabsTrigger value="executive" className="flex items-center gap-1.5">
            <Briefcase className="h-3.5 w-3.5" />
            Executive
          </TabsTrigger>
          <TabsTrigger value="intelligence" className="flex items-center gap-1.5">
            <Database className="h-3.5 w-3.5" />
            Intelligence
          </TabsTrigger>
          <TabsTrigger value="operations" className="flex items-center gap-1.5">
            <Shield className="h-3.5 w-3.5" />
            Operations
          </TabsTrigger>
          <TabsTrigger value="investigator" className="flex items-center gap-1.5">
            <Users className="h-3.5 w-3.5" />
            My View
          </TabsTrigger>
        </TabsList>
        <TabsContent value="executive" className="mt-6">
          <ExecutiveTab />
        </TabsContent>
        <TabsContent value="intelligence" className="mt-6">
          <IntelligenceTab />
        </TabsContent>
        <TabsContent value="operations" className="mt-6">
          <OperationsTab />
        </TabsContent>
        <TabsContent value="investigator" className="mt-6">
          <InvestigatorTab />
        </TabsContent>
      </Tabs>
    </div>
  )
}
