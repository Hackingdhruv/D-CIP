import { type ReactNode, useEffect, useRef, useState } from 'react'
import { cn } from '@/lib/utils'

interface StatCardProps {
  label: string
  value: number
  suffix?: string
  icon?: ReactNode
  trend?: 'up' | 'down' | 'neutral'
  trendLabel?: string
  colorClass?: string
  className?: string
}

function useAnimatedCount(target: number, duration = 600) {
  const [count, setCount] = useState(0)
  const frame = useRef<number>(0)

  useEffect(() => {
    const start = performance.now()
    const animate = (now: number) => {
      const progress = Math.min((now - start) / duration, 1)
      const ease = 1 - Math.pow(1 - progress, 3)
      setCount(Math.round(target * ease))
      if (progress < 1) frame.current = requestAnimationFrame(animate)
    }
    frame.current = requestAnimationFrame(animate)
    return () => cancelAnimationFrame(frame.current)
  }, [target, duration])

  return count
}

export function StatCard({
  label,
  value,
  suffix,
  icon,
  trend,
  trendLabel,
  colorClass = 'text-blue-600',
  className,
}: StatCardProps) {
  const animated = useAnimatedCount(value)

  const trendColor =
    trend === 'up'
      ? 'text-green-600'
      : trend === 'down'
        ? 'text-red-500'
        : 'text-muted-foreground'
  const trendArrow = trend === 'up' ? '↑' : trend === 'down' ? '↓' : '→'

  return (
    <div
      className={cn(
        'rounded-lg border bg-card p-4 shadow-sm flex flex-col gap-1',
        className
      )}
    >
      <div className="flex items-center justify-between">
        <span className="text-sm text-muted-foreground font-medium">{label}</span>
        {icon && <span className={cn('opacity-70', colorClass)}>{icon}</span>}
      </div>
      <div className={cn('text-3xl font-bold tabular-nums', colorClass)}>
        {animated.toLocaleString()}
        {suffix && (
          <span className="text-lg font-normal ml-1 text-muted-foreground">{suffix}</span>
        )}
      </div>
      {trendLabel && (
        <div className={cn('text-xs font-medium', trendColor)}>
          {trendArrow} {trendLabel}
        </div>
      )}
    </div>
  )
}
