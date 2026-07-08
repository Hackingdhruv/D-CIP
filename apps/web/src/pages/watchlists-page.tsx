import { useState } from 'react'
import { ChevronDown, ChevronRight, List, Plus, RefreshCw, Shield, Trash2 } from 'lucide-react'
import { PageHeader } from '@/components/common/page-header'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Skeleton } from '@/components/ui/skeleton'
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import {
  useWatchlistStats,
  useWatchlists,
  useCreateWatchlist,
  useDeleteWatchlist,
  useWatchlistEntries,
  useAddWatchlistEntry,
  useDeleteWatchlistEntry,
  useUpdateWatchlist,
} from '@/hooks/use-watchlist'
import type { WatchlistRead, WatchlistType } from '@/types/watchlist'

function fmt(d: string) {
  try { return new Date(d).toLocaleString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' }) } catch { return d }
}

const WATCHLIST_TYPE_LABELS: Record<WatchlistType, string> = {
  email: 'Email Address',
  phone: 'Phone Number',
  domain: 'Domain',
  url: 'URL',
  ip_address: 'IP Address',
  sha256: 'SHA-256 Hash',
  md5: 'MD5 Hash',
  crypto_wallet: 'Crypto Wallet',
  bank_account: 'Bank Account',
  vehicle_registration: 'Vehicle Registration',
  passport: 'Passport Number',
  device_id: 'Device ID',
  imei: 'IMEI',
  mac_address: 'MAC Address',
  regex: 'Custom Regex',
  keyword: 'Keyword',
}

const SEVERITY_COLORS: Record<string, string> = {
  email: 'bg-blue-100 text-blue-700',
  phone: 'bg-blue-100 text-blue-700',
  crypto_wallet: 'bg-red-100 text-red-700',
  bank_account: 'bg-red-100 text-red-700',
  sha256: 'bg-red-100 text-red-700',
  md5: 'bg-red-100 text-red-700',
  ip_address: 'bg-orange-100 text-orange-700',
  domain: 'bg-purple-100 text-purple-700',
  url: 'bg-purple-100 text-purple-700',
}

function typeBadge(wlType: WatchlistType) {
  const cls = SEVERITY_COLORS[wlType] || 'bg-gray-100 text-gray-700'
  return (
    <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${cls}`}>
      {WATCHLIST_TYPE_LABELS[wlType] ?? wlType}
    </span>
  )
}

// ── Create dialog ─────────────────────────────────────────────────────────────

function CreateDialog({ open, onClose }: { open: boolean; onClose: () => void }) {
  const [name, setName] = useState('')
  const [type, setType] = useState<WatchlistType>('email')
  const [description, setDescription] = useState('')
  const create = useCreateWatchlist()

  function submit() {
    if (!name.trim()) return
    create.mutate(
      { name: name.trim(), watchlistType: type, description: description || null },
      {
        onSuccess: () => {
          setName('')
          setDescription('')
          setType('email')
          onClose()
        },
      },
    )
  }

  return (
    <Dialog open={open} onOpenChange={(o) => { if (!o) onClose() }}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>New Watchlist</DialogTitle>
        </DialogHeader>
        <div className="space-y-3 py-2">
          <div>
            <label className="text-sm font-medium block mb-1">Name <span className="text-destructive">*</span></label>
            <Input value={name} onChange={e => setName(e.target.value)} placeholder="e.g. Suspect Email Addresses" />
          </div>
          <div>
            <label className="text-sm font-medium block mb-1">Type <span className="text-destructive">*</span></label>
            <Select value={type} onValueChange={(v) => setType(v as WatchlistType)}>
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {Object.entries(WATCHLIST_TYPE_LABELS).map(([v, l]) => (
                  <SelectItem key={v} value={v}>{l}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div>
            <label className="text-sm font-medium block mb-1">Description</label>
            <Input value={description} onChange={e => setDescription(e.target.value)} placeholder="Optional description" />
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={onClose}>Cancel</Button>
          <Button onClick={submit} disabled={create.isPending || !name.trim()}>Create</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

// ── Entry panel ───────────────────────────────────────────────────────────────

function EntryPanel({ watchlist }: { watchlist: WatchlistRead }) {
  const { data, isLoading } = useWatchlistEntries(watchlist.id)
  const addEntry = useAddWatchlistEntry()
  const deleteEntry = useDeleteWatchlistEntry()
  const [newValue, setNewValue] = useState('')
  const [isRegex, setIsRegex] = useState(false)

  function handleAdd() {
    if (!newValue.trim()) return
    addEntry.mutate(
      { watchlistId: watchlist.id, body: { value: newValue.trim(), isRegex } },
      { onSuccess: () => setNewValue('') },
    )
  }

  return (
    <div className="border-t bg-gray-50 px-4 py-3 space-y-3">
      <div className="flex items-center gap-2">
        <Input
          value={newValue}
          onChange={e => setNewValue(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && handleAdd()}
          placeholder={isRegex ? 'Enter regex pattern…' : 'Enter value to monitor…'}
          className="text-sm h-8"
        />
        <label className="flex items-center gap-1 text-xs text-gray-600 whitespace-nowrap">
          <input type="checkbox" checked={isRegex} onChange={e => setIsRegex(e.target.checked)} className="size-3" />
          Regex
        </label>
        <Button size="sm" onClick={handleAdd} disabled={addEntry.isPending || !newValue.trim()} className="h-8">
          <Plus className="size-3.5 mr-1" /> Add
        </Button>
      </div>
      {isLoading ? (
        <Skeleton className="h-16 rounded" />
      ) : (
        <div className="space-y-1 max-h-48 overflow-y-auto">
          {data?.items.length === 0 && (
            <p className="text-xs text-gray-400 italic">No entries yet. Add values above to monitor.</p>
          )}
          {data?.items.map(entry => (
            <div key={entry.id} className="flex items-center justify-between rounded border bg-white px-3 py-1.5">
              <div className="flex items-center gap-2 min-w-0">
                <span className="font-mono text-sm truncate">{entry.value}</span>
                {entry.isRegex && (
                  <span className="rounded bg-yellow-100 px-1.5 py-0.5 text-xs font-medium text-yellow-700">regex</span>
                )}
                {entry.hitCount > 0 && (
                  <span className="text-xs text-gray-400">{entry.hitCount} hit{entry.hitCount !== 1 ? 's' : ''}</span>
                )}
              </div>
              <button
                onClick={() => deleteEntry.mutate({ entryId: entry.id, watchlistId: watchlist.id })}
                disabled={deleteEntry.isPending}
                className="ml-2 text-gray-300 hover:text-red-500 shrink-0"
              >
                <Trash2 className="size-3.5" />
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

// ── Main page ─────────────────────────────────────────────────────────────────

export function WatchlistsPage() {
  const [showCreate, setShowCreate] = useState(false)
  const [expanded, setExpanded] = useState<string | null>(null)
  const [typeFilter, setTypeFilter] = useState<string>('')
  const [page, setPage] = useState(1)
  const { data: stats } = useWatchlistStats()
  const { data, isLoading, refetch } = useWatchlists({
    page,
    pageSize: 20,
    watchlistType: typeFilter || undefined,
  })
  const deleteWl = useDeleteWatchlist()
  const toggleActive = useUpdateWatchlist()

  return (
    <div className="space-y-6 p-6">
      <CreateDialog open={showCreate} onClose={() => setShowCreate(false)} />

      <div className="flex items-start justify-between">
        <PageHeader
          title="Watchlist Manager"
          description="Monitor entities of investigative interest across all incoming evidence."
        />
        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={() => refetch()}>
            <RefreshCw className="size-4 mr-1" /> Refresh
          </Button>
          <Button size="sm" onClick={() => setShowCreate(true)}>
            <Plus className="size-4 mr-1" /> New Watchlist
          </Button>
        </div>
      </div>

      {/* Stats */}
      {stats && (
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4 lg:grid-cols-6">
          {[
            { label: 'Watchlists', value: stats.totalWatchlists },
            { label: 'Active', value: stats.activeWatchlists },
            { label: 'Entries', value: stats.totalEntries },
            { label: 'Total Alerts', value: stats.totalAlerts },
            { label: 'Alerts Today', value: stats.alertsToday },
            { label: 'This Week', value: stats.alertsThisWeek },
          ].map(s => (
            <div key={s.label} className="rounded-lg border bg-white p-3 shadow-sm">
              <p className="text-xs text-gray-500">{s.label}</p>
              <p className="text-2xl font-bold text-gray-800 mt-0.5">{s.value.toLocaleString()}</p>
            </div>
          ))}
        </div>
      )}

      {/* Filters */}
      <div className="flex items-center gap-3">
        <div className="flex items-center gap-2">
          <label className="text-sm text-gray-600">Type:</label>
          <select
            value={typeFilter}
            onChange={e => { setTypeFilter(e.target.value); setPage(1) }}
            className="rounded-md border border-gray-300 px-2 py-1 text-sm focus:outline-none"
          >
            <option value="">All Types</option>
            {Object.entries(WATCHLIST_TYPE_LABELS).map(([v, l]) => (
              <option key={v} value={v}>{l}</option>
            ))}
          </select>
        </div>
      </div>

      {/* Watchlist table */}
      <div className="space-y-2">
        {isLoading ? (
          Array.from({ length: 5 }).map((_, i) => <Skeleton key={i} className="h-14 rounded-lg" />)
        ) : data?.items.length === 0 ? (
          <div className="rounded-lg border border-dashed bg-white p-8 text-center">
            <Shield className="size-10 text-gray-300 mx-auto mb-2" />
            <p className="text-sm text-gray-500">No watchlists yet. Create one to start monitoring entities.</p>
          </div>
        ) : (
          data?.items.map(wl => (
            <div key={wl.id} className="rounded-lg border bg-white shadow-sm overflow-hidden">
              <div className="flex items-center gap-3 px-4 py-3">
                <button
                  onClick={() => setExpanded(expanded === wl.id ? null : wl.id)}
                  className="text-gray-400 hover:text-gray-600"
                >
                  {expanded === wl.id
                    ? <ChevronDown className="size-4" />
                    : <ChevronRight className="size-4" />}
                </button>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="font-medium text-sm">{wl.name}</span>
                    {typeBadge(wl.watchlistType)}
                    {!wl.isActive && (
                      <span className="rounded-full bg-gray-100 px-2 py-0.5 text-xs text-gray-500">Inactive</span>
                    )}
                    {wl.caseId && (
                      <span className="rounded-full bg-blue-50 border border-blue-200 px-2 py-0.5 text-xs text-blue-600">Case-specific</span>
                    )}
                  </div>
                  {wl.description && <p className="text-xs text-gray-400 mt-0.5 truncate">{wl.description}</p>}
                </div>
                <div className="flex items-center gap-4 text-xs text-gray-500 shrink-0">
                  <span className="flex items-center gap-1">
                    <List className="size-3" /> {wl.entryCount} entries
                  </span>
                  <span className="text-red-500 font-medium">{wl.alertCount} alerts</span>
                  <span>{fmt(wl.createdAt)}</span>
                </div>
                <div className="flex items-center gap-1 ml-2">
                  <button
                    onClick={() => toggleActive.mutate({ id: wl.id, body: { isActive: !wl.isActive } })}
                    className={`text-xs px-2 py-1 rounded border ${wl.isActive ? 'border-green-200 text-green-600 hover:bg-green-50' : 'border-gray-200 text-gray-500 hover:bg-gray-50'}`}
                  >
                    {wl.isActive ? 'Active' : 'Inactive'}
                  </button>
                  <button
                    onClick={() => deleteWl.mutate(wl.id)}
                    disabled={deleteWl.isPending}
                    className="ml-1 text-gray-300 hover:text-red-500"
                  >
                    <Trash2 className="size-3.5" />
                  </button>
                </div>
              </div>
              {expanded === wl.id && <EntryPanel watchlist={wl} />}
            </div>
          ))
        )}
      </div>

      {/* Pagination */}
      {data && data.pages > 1 && (
        <div className="flex items-center justify-between text-sm text-gray-500">
          <span>{data.total} watchlists</span>
          <div className="flex gap-2">
            <Button variant="outline" size="sm" disabled={page <= 1} onClick={() => setPage(p => p - 1)}>Prev</Button>
            <span className="self-center">Page {page} of {data.pages}</span>
            <Button variant="outline" size="sm" disabled={page >= data.pages} onClick={() => setPage(p => p + 1)}>Next</Button>
          </div>
        </div>
      )}
    </div>
  )
}
