import { AlertTriangle, RefreshCw, Unlock } from 'lucide-react'
import { PageHeader } from '@/components/common/page-header'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { useSecurityOverview, useUnlockUser } from '@/hooks/use-admin'

function fmt(dateStr: string) {
  try { return new Date(dateStr).toLocaleString('en-GB', { day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' }) } catch { return dateStr }
}

export function SecurityCenterPage() {
  const { data, isLoading, refetch } = useSecurityOverview()
  const unlock = useUnlockUser()

  return (
    <div className="space-y-6 p-6">
      <div className="flex items-start justify-between">
        <PageHeader title="Security Center" description="Failed logins, locked accounts, session anomalies, and suspicious IPs." />
        <Button variant="outline" size="sm" onClick={() => refetch()}>
          <RefreshCw className="size-4 mr-1" /> Refresh
        </Button>
      </div>

      {/* Overview stats */}
      {isLoading ? (
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
          {Array.from({ length: 5 }).map((_, i) => <Skeleton key={i} className="h-20 rounded-lg" />)}
        </div>
      ) : data ? (
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-5">
          {[
            { label: 'Locked Accounts', value: data.lockedUsersCount, alert: data.lockedUsersCount > 0 },
            { label: 'Inactive Users', value: data.inactiveUsersCount, alert: false },
            { label: 'Failed Logins 24h', value: data.failedLogins24h, alert: data.failedLogins24h > 10 },
            { label: 'Active Sessions', value: data.activeSessions, alert: false },
            { label: 'Expired Sessions 24h', value: data.expiredSessions24h, alert: false },
          ].map(card => (
            <div key={card.label} className={`rounded-lg border p-4 shadow-sm ${card.alert ? 'border-red-200 bg-red-50' : 'bg-white'}`}>
              <p className="text-sm text-gray-500">{card.label}</p>
              <p className={`text-3xl font-bold mt-1 ${card.alert ? 'text-red-600' : 'text-gray-800'}`}>
                {card.value.toLocaleString()}
              </p>
            </div>
          ))}
        </div>
      ) : null}

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        {/* Locked users */}
        <div className="rounded-lg border bg-white shadow-sm">
          <div className="border-b px-4 py-3">
            <h3 className="font-semibold text-sm">Locked Accounts</h3>
          </div>
          {isLoading ? (
            <div className="p-4 space-y-2">{Array.from({ length: 4 }).map((_, i) => <Skeleton key={i} className="h-8 rounded" />)}</div>
          ) : data?.lockedUsers.length === 0 ? (
            <p className="p-4 text-sm text-gray-400 italic">No locked accounts.</p>
          ) : (
            <ul className="divide-y">
              {data?.lockedUsers.map(u => (
                <li key={u.id} className="flex items-center justify-between px-4 py-2">
                  <div>
                    <p className="text-sm font-medium">{u.fullName}</p>
                    <p className="text-xs text-gray-500">{u.email}</p>
                    {u.lockedUntil && (
                      <p className="text-xs text-red-500">Until {fmt(u.lockedUntil)}</p>
                    )}
                  </div>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => unlock.mutate(u.id)}
                    disabled={unlock.isPending}
                    className="text-green-600 border-green-200 hover:bg-green-50"
                  >
                    <Unlock className="size-3.5 mr-1" /> Unlock
                  </Button>
                </li>
              ))}
            </ul>
          )}
        </div>

        {/* Top failed logins */}
        <div className="rounded-lg border bg-white shadow-sm">
          <div className="border-b px-4 py-3">
            <h3 className="font-semibold text-sm">Top Failed Login Sources (24h)</h3>
          </div>
          {isLoading ? (
            <div className="p-4 space-y-2">{Array.from({ length: 4 }).map((_, i) => <Skeleton key={i} className="h-8 rounded" />)}</div>
          ) : data?.topFailedLogins.length === 0 ? (
            <p className="p-4 text-sm text-gray-400 italic">No failed login attempts.</p>
          ) : (
            <ul className="divide-y">
              {data?.topFailedLogins.map((fl, i) => (
                <li key={i} className="px-4 py-2 flex items-start justify-between">
                  <div>
                    <p className="text-sm font-medium">{fl.userEmail ?? 'Unknown user'}</p>
                    <p className="text-xs text-gray-500">Last: {fmt(fl.lastAttempt)}</p>
                    {fl.ipAddresses.length > 0 && (
                      <p className="text-xs font-mono text-gray-400">{fl.ipAddresses.slice(0, 3).join(', ')}</p>
                    )}
                  </div>
                  <span className="ml-2 shrink-0 rounded-full bg-red-100 px-2 py-0.5 text-xs font-bold text-red-700">
                    {fl.attemptCount}x
                  </span>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>

      {/* Suspicious IPs */}
      {data && data.recentSuspiciousIps.length > 0 && (
        <div className="rounded-lg border border-yellow-200 bg-yellow-50 p-4">
          <div className="flex items-center gap-2 mb-2">
            <AlertTriangle className="size-4 text-yellow-600" />
            <h3 className="text-sm font-semibold text-yellow-800">Suspicious IP Addresses (3+ failed logins in 24h)</h3>
          </div>
          <div className="flex flex-wrap gap-2">
            {data.recentSuspiciousIps.map(ip => (
              <span key={ip} className="rounded border border-yellow-300 bg-white px-2 py-0.5 font-mono text-xs text-yellow-800">
                {ip}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
