import { CheckCircle, XCircle } from 'lucide-react'
import { PageHeader } from '@/components/common/page-header'
import { Skeleton } from '@/components/ui/skeleton'
import { ChartBar } from '@/components/dashboard/chart-bar'
import { useAiConfig, useAiStats } from '@/hooks/use-admin'

function Row({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="flex items-start justify-between py-2 border-b last:border-0">
      <span className="text-sm text-gray-500">{label}</span>
      <span className="text-sm font-medium text-right">{value}</span>
    </div>
  )
}

export function AiAdminPage() {
  const { data: config, isLoading: configLoading } = useAiConfig()
  const { data: stats, isLoading: statsLoading } = useAiStats()

  return (
    <div className="space-y-6 p-6">
      <PageHeader title="AI Administration" description="AI provider configuration and usage statistics." />

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        {/* Config */}
        <div className="rounded-lg border bg-white shadow-sm">
          <div className="border-b px-4 py-3">
            <h3 className="font-semibold text-sm">AI Configuration</h3>
          </div>
          {configLoading ? (
            <div className="p-4 space-y-2">{Array.from({ length: 6 }).map((_, i) => <Skeleton key={i} className="h-6 rounded" />)}</div>
          ) : config ? (
            <div className="px-4 py-2">
              <Row label="Provider" value={config.provider} />
              <Row label="Model" value={<span className="font-mono text-xs">{config.model}</span>} />
              <Row label="Embedding Model" value={<span className="font-mono text-xs">{config.embeddingModel}</span>} />
              <Row label="Max Tokens" value={config.maxTokens.toLocaleString()} />
              <Row label="Temperature" value={config.temperature} />
              <Row label="API Base" value={<span className="font-mono text-xs">{config.apiBase}</span>} />
              <Row label="API Key" value={config.apiKeyConfigured ? <span className="flex items-center gap-1 text-green-600"><CheckCircle className="size-3.5" /> Configured</span> : <span className="flex items-center gap-1 text-red-500"><XCircle className="size-3.5" /> Not set</span>} />
              <Row label="OCR" value={config.ocrEnabled ? <span className="text-green-600">Enabled</span> : <span className="text-gray-400">Disabled</span>} />
            </div>
          ) : null}
        </div>

        {/* Usage stats */}
        <div className="rounded-lg border bg-white shadow-sm">
          <div className="border-b px-4 py-3">
            <h3 className="font-semibold text-sm">Usage Statistics</h3>
          </div>
          {statsLoading ? (
            <div className="p-4 space-y-2">{Array.from({ length: 5 }).map((_, i) => <Skeleton key={i} className="h-6 rounded" />)}</div>
          ) : stats ? (
            <div className="px-4 py-2">
              <Row label="Total AI Responses" value={stats.totalMessages.toLocaleString()} />
              <Row label="Today" value={stats.messagesToday.toLocaleString()} />
              <Row label="This Week" value={stats.messagesThisWeek.toLocaleString()} />
              <Row label="This Month" value={stats.messagesThisMonth.toLocaleString()} />
              <Row label="Avg per Case" value={stats.avgMessagesPerCase.toFixed(1)} />
            </div>
          ) : null}
        </div>
      </div>

      {/* Model usage chart */}
      {stats && stats.modelsUsed.length > 0 && (
        <div className="rounded-lg border bg-white p-4 shadow-sm">
          <h3 className="mb-3 text-sm font-semibold text-gray-700">Requests by Model</h3>
          <div className="h-48">
            <ChartBar
              labels={stats.modelsUsed.map(m => m.modelName)}
              datasets={[{ label: 'Messages', data: stats.modelsUsed.map(m => m.messageCount), backgroundColor: '#3b82f6' }]}
            />
          </div>
        </div>
      )}

      {/* Top users */}
      {stats && stats.topUsers.length > 0 && (
        <div className="rounded-lg border bg-white shadow-sm">
          <div className="border-b px-4 py-3">
            <h3 className="font-semibold text-sm">Top AI Users</h3>
          </div>
          <table className="w-full text-sm">
            <thead className="bg-gray-50 text-xs text-gray-500">
              <tr>
                <th className="px-4 py-2 text-left">#</th>
                <th className="px-4 py-2 text-left">User</th>
                <th className="px-4 py-2 text-left">Queries</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {stats.topUsers.map((u, i) => (
                <tr key={i} className="hover:bg-gray-50">
                  <td className="px-4 py-2 text-gray-400">{i + 1}</td>
                  <td className="px-4 py-2">{u.email}</td>
                  <td className="px-4 py-2 font-semibold">{u.count.toLocaleString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
