import {
  Activity,
  AlertTriangle,
  Bot,
  CheckCircle,
  FileText,
  HardDrive,
  Lock,
  ScrollText,
  Shield,
  Users,
  XCircle,
} from 'lucide-react'
import { Link } from 'react-router-dom'
import { PageHeader } from '@/components/common/page-header'
import { StatCard } from '@/components/dashboard/stat-card'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import { useAdminStats, useRecommendations } from '@/hooks/use-admin'
import type { ServiceStatus } from '@/types/admin'

function StatusIcon({ status }: { status: ServiceStatus }) {
  if (status === 'healthy') return <CheckCircle className="size-4 text-green-500" />
  if (status === 'degraded') return <AlertTriangle className="size-4 text-yellow-500" />
  return <XCircle className="size-4 text-red-500" />
}

function SeverityBadge({ severity }: { severity: string }) {
  const map: Record<string, string> = {
    critical: 'bg-red-100 text-red-700',
    warning: 'bg-yellow-100 text-yellow-700',
    info: 'bg-blue-100 text-blue-700',
  }
  return (
    <span className={`rounded-full px-2 py-0.5 text-xs font-semibold capitalize ${map[severity] ?? 'bg-gray-100 text-gray-600'}`}>
      {severity}
    </span>
  )
}

export function AdminOverviewPage() {
  const { data: stats, isLoading: statsLoading } = useAdminStats()
  const { data: recs, isLoading: recsLoading } = useRecommendations()

  return (
    <div className="space-y-6 p-6">
      <PageHeader
        title="Enterprise Administration"
        description="System health, user management, and platform operations at a glance."
      />

      {/* Overview stats */}
      {statsLoading ? (
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
          {Array.from({ length: 8 }).map((_, i) => <Skeleton key={i} className="h-24 rounded-lg" />)}
        </div>
      ) : stats ? (
        <>
          <div className="flex items-center gap-2 text-sm">
            <StatusIcon status={stats.systemStatus} />
            <span className="font-medium capitalize">{stats.systemStatus}</span>
            <span className="text-gray-400">— system status</span>
          </div>
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
            <StatCard label="Total Users" value={stats.totalUsers} icon={<Users className="size-4" />} colorClass="text-blue-600" />
            <StatCard label="Active Users" value={stats.activeUsers} icon={<Users className="size-4" />} colorClass="text-green-600" />
            <StatCard label="Locked Accounts" value={stats.lockedUsers} icon={<Lock className="size-4" />} colorClass={stats.lockedUsers > 0 ? 'text-red-600' : 'text-gray-600'} />
            <StatCard label="Active Sessions" value={stats.activeSessions} icon={<Activity className="size-4" />} colorClass="text-purple-600" />
            <StatCard label="Total Cases" value={stats.totalCases} icon={<FileText className="size-4" />} colorClass="text-indigo-600" />
            <StatCard label="Evidence Items" value={stats.evidenceItems} icon={<HardDrive className="size-4" />} colorClass="text-teal-600" />
            <StatCard label="Audit Events Today" value={stats.auditEventsToday} icon={<ScrollText className="size-4" />} colorClass="text-gray-600" />
            <StatCard label="Failed Logins 24h" value={stats.failedLogins24h} icon={<Shield className="size-4" />} colorClass={stats.failedLogins24h > 10 ? 'text-red-600' : 'text-gray-600'} />
          </div>
        </>
      ) : null}

      {/* Recommendations */}
      <div className="rounded-lg border bg-white shadow-sm">
        <div className="flex items-center justify-between border-b px-4 py-3">
          <h3 className="font-semibold">Recommendations</h3>
          {recs && recs.criticalCount > 0 && (
            <Badge variant="destructive">{recs.criticalCount} Critical</Badge>
          )}
        </div>
        {recsLoading ? (
          <div className="space-y-2 p-4">
            {[1, 2, 3].map(i => <Skeleton key={i} className="h-10 rounded" />)}
          </div>
        ) : !recs || recs.recommendations.length === 0 ? (
          <div className="flex items-center gap-2 p-6 text-sm text-gray-500">
            <CheckCircle className="size-4 text-green-500" />
            No active recommendations. Platform is operating normally.
          </div>
        ) : (
          <ul className="divide-y">
            {recs.recommendations.map(rec => (
              <li key={rec.id} className="flex items-start gap-3 px-4 py-3">
                <SeverityBadge severity={rec.severity} />
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium">{rec.title}</p>
                  <p className="text-xs text-gray-500">{rec.description}</p>
                  {rec.action && <p className="text-xs text-blue-600 mt-0.5">{rec.action}</p>}
                </div>
                {rec.metricValue && (
                  <span className="shrink-0 text-xs font-mono text-gray-500">{rec.metricValue}</span>
                )}
              </li>
            ))}
          </ul>
        )}
      </div>

      {/* Quick nav cards */}
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        {[
          { to: '/admin/users', label: 'Manage Users', icon: <Users className="size-5" />, color: 'text-blue-600' },
          { to: '/admin/sessions', label: 'Active Sessions', icon: <Lock className="size-5" />, color: 'text-purple-600' },
          { to: '/admin/system', label: 'System Health', icon: <Activity className="size-5" />, color: 'text-green-600' },
          { to: '/admin/queue', label: 'Queue Monitor', icon: <Bot className="size-5" />, color: 'text-indigo-600' },
          { to: '/admin/storage', label: 'Storage Center', icon: <HardDrive className="size-5" />, color: 'text-teal-600' },
          { to: '/admin/audit', label: 'Audit Center', icon: <ScrollText className="size-5" />, color: 'text-gray-600' },
          { to: '/admin/security', label: 'Security Center', icon: <Shield className="size-5" />, color: 'text-red-600' },
          { to: '/admin/config', label: 'Configuration', icon: <FileText className="size-5" />, color: 'text-orange-600' },
        ].map(item => (
          <Link
            key={item.to}
            to={item.to}
            className="flex items-center gap-3 rounded-lg border bg-white p-4 shadow-sm hover:bg-gray-50 transition-colors"
          >
            <span className={item.color}>{item.icon}</span>
            <span className="text-sm font-medium">{item.label}</span>
          </Link>
        ))}
      </div>
    </div>
  )
}
