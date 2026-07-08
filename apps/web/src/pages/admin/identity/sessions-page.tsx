import { useState } from 'react'
import { LogOut, RefreshCw } from 'lucide-react'
import { PageHeader } from '@/components/common/page-header'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { useAdminSessions, useRevokeSession } from '@/hooks/use-admin'

function fmt(dateStr: string) {
  try { return new Date(dateStr).toLocaleString('en-GB', { day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' }) } catch { return dateStr }
}

export function SessionsPage() {
  const [page, setPage] = useState(1)
  const [isActiveFilter, setIsActiveFilter] = useState<boolean | undefined>(true)
  const { data, isLoading, refetch } = useAdminSessions({ page, pageSize: 50, isActive: isActiveFilter })
  const revoke = useRevokeSession()

  return (
    <div className="space-y-4 p-6">
      <PageHeader title="Active Sessions" description="Monitor and revoke user sessions." />

      <div className="flex items-center gap-3">
        <div className="flex rounded-md border text-sm overflow-hidden">
          {[{ label: 'Active', value: true as boolean | undefined }, { label: 'Expired', value: false }, { label: 'All', value: undefined }].map(opt => (
            <button
              key={String(opt.value)}
              onClick={() => { setIsActiveFilter(opt.value as boolean | undefined); setPage(1) }}
              className={`px-3 py-1.5 ${isActiveFilter === opt.value ? 'bg-blue-600 text-white' : 'text-gray-600 hover:bg-gray-50'}`}
            >
              {opt.label}
            </button>
          ))}
        </div>
        <Button variant="outline" size="sm" onClick={() => refetch()}>
          <RefreshCw className="size-4 mr-1" /> Refresh
        </Button>
      </div>

      <div className="rounded-lg border bg-white shadow-sm overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 text-xs text-gray-500 uppercase tracking-wide">
            <tr>
              {['User', 'IP Address', 'User Agent', 'Created', 'Last Active', 'Expires', 'Status', ''].map(h => (
                <th key={h} className="px-4 py-2 text-left font-medium">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y">
            {isLoading
              ? Array.from({ length: 10 }).map((_, i) => (
                  <tr key={i}><td colSpan={8} className="p-2"><Skeleton className="h-6 w-full" /></td></tr>
                ))
              : data?.items.map(s => (
                  <tr key={s.id} className="hover:bg-gray-50">
                    <td className="px-4 py-2">
                      <p className="font-medium">{s.userFullName}</p>
                      <p className="text-xs text-gray-500">{s.userEmail}</p>
                    </td>
                    <td className="px-4 py-2 font-mono text-xs">{s.ipAddress ?? '—'}</td>
                    <td className="px-4 py-2 text-xs text-gray-500 max-w-xs truncate">{s.userAgent ?? '—'}</td>
                    <td className="px-4 py-2 text-xs">{fmt(s.createdAt)}</td>
                    <td className="px-4 py-2 text-xs">{fmt(s.lastActiveAt)}</td>
                    <td className="px-4 py-2 text-xs">{fmt(s.expiresAt)}</td>
                    <td className="px-4 py-2">
                      <span className={`rounded-full px-2 py-0.5 text-xs font-semibold ${s.isActive ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500'}`}>
                        {s.isActive ? 'Active' : 'Expired'}
                      </span>
                    </td>
                    <td className="px-4 py-2">
                      {s.isActive && (
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => revoke.mutate(s.id)}
                          disabled={revoke.isPending}
                          className="text-red-600 hover:text-red-700"
                        >
                          <LogOut className="size-3.5 mr-1" /> Revoke
                        </Button>
                      )}
                    </td>
                  </tr>
                ))}
          </tbody>
        </table>
        {data && data.pages > 1 && (
          <div className="flex items-center justify-between border-t px-4 py-2 text-sm text-gray-500">
            <span>{data.total} session{data.total !== 1 ? 's' : ''}</span>
            <div className="flex gap-2">
              <Button variant="outline" size="sm" disabled={page <= 1} onClick={() => setPage(p => p - 1)}>Prev</Button>
              <span className="self-center">Page {page} of {data.pages}</span>
              <Button variant="outline" size="sm" disabled={page >= data.pages} onClick={() => setPage(p => p + 1)}>Next</Button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
