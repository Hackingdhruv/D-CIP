import * as React from 'react';
import { useAuth } from '@/contexts/auth-context';
import { useNotificationCount } from '@/hooks/use-watchlist';

interface NotificationContextValue {
  unreadCount: number;
}

const NotificationContext = React.createContext<NotificationContextValue>({ unreadCount: 0 });

export function NotificationProvider({ children }: { children: React.ReactNode }) {
  const { isAuthenticated } = useAuth();
  const { data } = useNotificationCount(isAuthenticated);
  const unreadCount = data?.unreadCount ?? 0;

  const value = React.useMemo(() => ({ unreadCount }), [unreadCount]);

  return <NotificationContext.Provider value={value}>{children}</NotificationContext.Provider>;
}

export function useNotifications(): NotificationContextValue {
  return React.useContext(NotificationContext);
}
