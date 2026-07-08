import { cn } from '@/lib/utils'
import type { ServiceHealth, ServiceStatus } from '@/types/dashboard'

const STATUS_CONFIG: Record<ServiceStatus, { label: string; dot: string; text: string }> = {
  healthy: { label: 'Healthy', dot: 'bg-green-500', text: 'text-green-700' },
  degraded: { label: 'Degraded', dot: 'bg-yellow-500', text: 'text-yellow-700' },
  down: { label: 'Down', dot: 'bg-red-500', text: 'text-red-700' },
  unknown: { label: 'Unknown', dot: 'bg-gray-400', text: 'text-gray-600' },
}

interface HealthBadgeProps {
  service: ServiceHealth
  className?: string
}

export function HealthBadge({ service, className }: HealthBadgeProps) {
  const cfg = STATUS_CONFIG[service.status]
  return (
    <div
      className={cn(
        'flex items-center justify-between rounded-lg border bg-white px-4 py-3',
        className
      )}
    >
      <div className="flex items-center gap-2">
        <span className={cn('h-2.5 w-2.5 rounded-full animate-pulse', cfg.dot)} />
        <span className="font-medium text-sm">{service.name}</span>
      </div>
      <div className="flex items-center gap-3 text-right">
        {service.latencyMs != null && (
          <span className="text-xs text-gray-400">{service.latencyMs}ms</span>
        )}
        <span className={cn('text-xs font-semibold', cfg.text)}>{cfg.label}</span>
      </div>
      {service.message && (
        <span className="sr-only">{service.message}</span>
      )}
    </div>
  )
}
