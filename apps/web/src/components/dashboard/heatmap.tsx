import { cn } from '@/lib/utils'
import type { DateCount } from '@/types/dashboard'

interface HeatmapProps {
  data: DateCount[]
  className?: string
}

function intensityClass(count: number, max: number): string {
  if (count === 0) return 'bg-gray-100'
  const ratio = count / max
  if (ratio < 0.25) return 'bg-blue-200'
  if (ratio < 0.5) return 'bg-blue-400'
  if (ratio < 0.75) return 'bg-blue-600'
  return 'bg-blue-800'
}

export function Heatmap({ data, className }: HeatmapProps) {
  const max = Math.max(...data.map((d) => d.count), 1)
  const byDate = Object.fromEntries(data.map((d) => [d.date, d.count]))

  // Build last 30 days grid
  const days: { date: string; count: number }[] = []
  for (let i = 29; i >= 0; i--) {
    const d = new Date()
    d.setDate(d.getDate() - i)
    const iso = d.toISOString().slice(0, 10)
    days.push({ date: iso, count: byDate[iso] ?? 0 })
  }

  return (
    <div className={cn('flex flex-col gap-1', className)}>
      <div className="flex gap-1 flex-wrap">
        {days.map(({ date, count }) => (
          <div
            key={date}
            title={`${date}: ${count} event${count !== 1 ? 's' : ''}`}
            className={cn(
              'h-5 w-5 rounded-sm cursor-default transition-colors',
              intensityClass(count, max)
            )}
          />
        ))}
      </div>
      <div className="flex items-center gap-1 text-xs text-gray-400 mt-1">
        <span>Less</span>
        {['bg-gray-100', 'bg-blue-200', 'bg-blue-400', 'bg-blue-600', 'bg-blue-800'].map(
          (cls) => (
            <div key={cls} className={cn('h-3 w-3 rounded-sm', cls)} />
          )
        )}
        <span>More</span>
      </div>
    </div>
  )
}
