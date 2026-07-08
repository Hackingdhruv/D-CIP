import { Archive, Bell, CheckCheck, Trash2 } from 'lucide-react';
import { PageHeader } from '@/components/common/page-header';
import { EmptyState } from '@/components/common/empty-state';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import {
  useNotificationList,
  useMarkAllNotificationsRead,
  useMarkNotificationRead,
  useArchiveNotification,
  useDeleteNotification,
  useNotificationCount,
} from '@/hooks/use-watchlist';
import { cn } from '@/lib/utils';

const LEVEL_DOT: Record<string, string> = {
  critical: 'bg-red-500',
  error: 'bg-red-400',
  warning: 'bg-yellow-400',
  info: 'bg-primary',
};

function fmt(d: string) {
  try {
    return new Date(d).toLocaleString('en-GB', {
      day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit',
    })
  } catch { return d }
}

export function NotificationsPage() {
  const { data: countData } = useNotificationCount();
  const { data, isLoading } = useNotificationList({ pageSize: 50 });
  const markAllRead = useMarkAllNotificationsRead();
  const markRead = useMarkNotificationRead();
  const archive = useArchiveNotification();
  const remove = useDeleteNotification();

  const unreadCount = countData?.unreadCount ?? 0;
  const notifications = data?.items ?? [];

  return (
    <div className="space-y-6">
      <PageHeader
        title="Notifications"
        description="Activity that needs your attention — watchlist alerts, assignments, and system events."
        actions={
          <Button
            variant="outline"
            onClick={() => markAllRead.mutate()}
            disabled={unreadCount === 0 || markAllRead.isPending}
          >
            <CheckCheck className="h-4 w-4" /> Mark all read
          </Button>
        }
      />
      {isLoading ? (
        <div className="space-y-2">
          {Array.from({ length: 5 }).map((_, i) => <Skeleton key={i} className="h-14 rounded-lg" />)}
        </div>
      ) : notifications.length === 0 ? (
        <EmptyState
          icon={Bell}
          title="You're all caught up"
          description="There are no notifications right now. New activity on your cases will show up here."
        />
      ) : (
        <ul className="divide-y divide-border overflow-hidden rounded-lg border border-border">
          {notifications.map((n) => (
            <li
              key={n.id}
              className={cn('flex items-start gap-3 px-4 py-3', !n.isRead && 'bg-surface-2/60')}
            >
              <span
                className={cn('mt-1.5 h-2 w-2 shrink-0 rounded-full', LEVEL_DOT[n.level] ?? 'bg-primary')}
              />
              <div className="min-w-0 flex-1">
                <p className="text-sm font-medium">{n.title}</p>
                {n.message && <p className="text-sm text-muted-foreground">{n.message}</p>}
                <p className="mt-0.5 text-xs text-muted-foreground">{fmt(n.createdAt)}</p>
              </div>
              <div className="flex shrink-0 items-center gap-1">
                {!n.isRead && (
                  <Button
                    variant="ghost"
                    size="icon"
                    className="h-7 w-7"
                    title="Mark as read"
                    onClick={() => markRead.mutate(n.id)}
                  >
                    <CheckCheck className="h-3.5 w-3.5" />
                  </Button>
                )}
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-7 w-7 text-muted-foreground"
                  title="Archive"
                  onClick={() => archive.mutate(n.id)}
                >
                  <Archive className="h-3.5 w-3.5" />
                </Button>
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-7 w-7 text-muted-foreground hover:text-destructive"
                  title="Delete"
                  onClick={() => remove.mutate(n.id)}
                >
                  <Trash2 className="h-3.5 w-3.5" />
                </Button>
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
