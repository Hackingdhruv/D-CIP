import { RouterProvider } from 'react-router-dom';
import { TooltipProvider } from '@/components/ui/tooltip';
import { ThemeProvider } from '@/components/providers/theme-provider';
import { QueryProvider } from '@/components/providers/query-provider';
import { ModalProvider } from '@/components/providers/modal-provider';
import { NotificationProvider } from '@/components/providers/notification-provider';
import { ToastProvider } from '@/components/providers/toast-provider';
import { AuthProvider } from '@/contexts/auth-context';
import { ErrorBoundary } from '@/components/common/error-boundary';
import { router } from '@/routes';

/**
 * Non-router providers wrap RouterProvider so every route — public and
 * protected alike — has access to auth, query, theme, and notification
 * context. CommandPaletteProvider is kept inside the router (it calls
 * useNavigate) and lives in the authenticated layout only.
 */
export function App() {
  return (
    <ErrorBoundary>
      <ThemeProvider>
        <QueryProvider>
          <AuthProvider>
            <TooltipProvider delayDuration={200}>
              <NotificationProvider>
                <ModalProvider>
                  <RouterProvider router={router} />
                  <ToastProvider />
                </ModalProvider>
              </NotificationProvider>
            </TooltipProvider>
          </AuthProvider>
        </QueryProvider>
      </ThemeProvider>
    </ErrorBoundary>
  );
}
