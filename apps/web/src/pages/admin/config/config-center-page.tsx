import { useState } from 'react'
import { Edit2, Eye, EyeOff, Save, X } from 'lucide-react'
import { PageHeader } from '@/components/common/page-header'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Skeleton } from '@/components/ui/skeleton'
import { useAdminConfig, useSetConfig } from '@/hooks/use-admin'
import type { ConfigEntry } from '@/types/admin'

function fmt(dateStr: string) {
  try { return new Date(dateStr).toLocaleString('en-GB', { day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' }) } catch { return dateStr }
}

function ConfigRow({ entry }: { entry: ConfigEntry }) {
  const [editing, setEditing] = useState(false)
  const [newValue, setNewValue] = useState(entry.value ?? '')
  const [showSecret, setShowSecret] = useState(false)
  const setConfig = useSetConfig()

  function handleSave() {
    setConfig.mutate({ key: entry.key, body: { value: newValue } }, {
      onSuccess: () => setEditing(false),
    })
  }

  return (
    <tr className="hover:bg-gray-50">
      <td className="px-4 py-3 font-mono text-sm">{entry.key}</td>
      <td className="px-4 py-3 text-sm text-gray-600 max-w-xs">{entry.description ?? '—'}</td>
      <td className="px-4 py-3">
        {editing ? (
          <div className="flex items-center gap-1">
            <Input
              value={newValue}
              onChange={e => setNewValue(e.target.value)}
              className="h-7 text-sm font-mono w-36"
              autoFocus
            />
            <Button size="sm" onClick={handleSave} disabled={setConfig.isPending} className="h-7 px-2">
              <Save className="size-3.5" />
            </Button>
            <Button size="sm" variant="ghost" onClick={() => setEditing(false)} className="h-7 px-2">
              <X className="size-3.5" />
            </Button>
          </div>
        ) : (
          <div className="flex items-center gap-2">
            {entry.isSecret ? (
              <>
                <span className="font-mono text-sm">
                  {showSecret ? (entry.value ?? '—') : '••••••••'}
                </span>
                <button onClick={() => setShowSecret(s => !s)} className="text-gray-400 hover:text-gray-600">
                  {showSecret ? <EyeOff className="size-3.5" /> : <Eye className="size-3.5" />}
                </button>
              </>
            ) : (
              <span className="font-mono text-sm">{entry.value ?? '—'}</span>
            )}
          </div>
        )}
      </td>
      <td className="px-4 py-3 text-xs text-gray-400">{fmt(entry.updatedAt)}</td>
      <td className="px-4 py-3 text-xs text-gray-400">{entry.updatedByEmail ?? '—'}</td>
      <td className="px-4 py-3">
        {!editing && (
          <Button variant="ghost" size="sm" onClick={() => setEditing(true)} className="h-7 px-2">
            <Edit2 className="size-3.5" />
          </Button>
        )}
      </td>
    </tr>
  )
}

export function ConfigCenterPage() {
  const { data, isLoading } = useAdminConfig()

  return (
    <div className="space-y-6 p-6">
      <PageHeader
        title="Configuration Center"
        description="System-level configuration. Changes take effect immediately. Secrets are masked."
      />

      <div className="rounded-lg border bg-white shadow-sm overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 text-xs text-gray-500 uppercase tracking-wide">
            <tr>
              {['Key', 'Description', 'Value', 'Last Updated', 'Updated By', ''].map(h => (
                <th key={h} className="px-4 py-2 text-left font-medium">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y">
            {isLoading
              ? Array.from({ length: 10 }).map((_, i) => (
                  <tr key={i}><td colSpan={6} className="p-2"><Skeleton className="h-6 w-full" /></td></tr>
                ))
              : data?.map(entry => <ConfigRow key={entry.key} entry={entry} />)
            }
          </tbody>
        </table>
      </div>
    </div>
  )
}
