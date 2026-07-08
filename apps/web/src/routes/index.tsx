import { lazy, Suspense } from 'react';
import { createBrowserRouter, Outlet } from 'react-router-dom';
import { CommandPaletteProvider } from '@/components/providers/command-palette-provider';
import { AppLayout } from '@/components/layout/app-layout';
import { ProtectedRoute } from '@/components/auth/protected-route';
import { AdminLayout } from '@/components/admin/admin-layout';
import { RouteErrorBoundary } from '@/components/common/error-boundary';

// Auth pages — eagerly loaded (tiny, always needed on cold start)
import { LoginPage } from '@/pages/auth/login-page';
import { ForgotPasswordPage } from '@/pages/auth/forgot-password-page';
import { ResetPasswordPage } from '@/pages/auth/reset-password-page';
import { NotFoundPage } from '@/pages/not-found-page';

// Loading fallback shown while lazy chunks download
function PageLoader() {
  return (
    <div className="flex h-full items-center justify-center">
      <div className="h-8 w-8 animate-spin rounded-full border-4 border-muted border-t-primary" />
    </div>
  );
}

// Route layout: Suspense (for lazy chunk loading) + inline ErrorBoundary
// (so a broken page doesn't take down the app shell).
function LazyLayout() {
  return (
    <RouteErrorBoundary>
      <Suspense fallback={<PageLoader />}>
        <Outlet />
      </Suspense>
    </RouteErrorBoundary>
  );
}

// App pages — lazy-loaded per route for optimal bundle splitting
const DashboardPage = lazy(() => import('@/pages/dashboard-page').then(m => ({ default: m.DashboardPage })));
const CasesPage = lazy(() => import('@/pages/cases-page').then(m => ({ default: m.CasesPage })));
const CaseWorkspacePage = lazy(() => import('@/pages/cases/case-workspace-page').then(m => ({ default: m.CaseWorkspacePage })));
const EvidencePage = lazy(() => import('@/pages/evidence-page').then(m => ({ default: m.EvidencePage })));
const TimelinePage = lazy(() => import('@/pages/timeline-page').then(m => ({ default: m.TimelinePage })));
const GraphPage = lazy(() => import('@/pages/graph-page').then(m => ({ default: m.GraphPage })));
const ReportsPage = lazy(() => import('@/pages/reports-page').then(m => ({ default: m.ReportsPage })));
const SearchPage = lazy(() => import('@/pages/search-page').then(m => ({ default: m.SearchPage })));
const WatchlistsPage = lazy(() => import('@/pages/watchlists-page').then(m => ({ default: m.WatchlistsPage })));
const AlertsPage = lazy(() => import('@/pages/alerts-page').then(m => ({ default: m.AlertsPage })));
const NotificationsPage = lazy(() => import('@/pages/notifications-page').then(m => ({ default: m.NotificationsPage })));
const SettingsPage = lazy(() => import('@/pages/settings-page').then(m => ({ default: m.SettingsPage })));
const AuditPage = lazy(() => import('@/pages/audit-page').then(m => ({ default: m.AuditPage })));
const ProfilePage = lazy(() => import('@/pages/profile/profile-page').then(m => ({ default: m.ProfilePage })));

// Admin pages — lazy-loaded (admin section only used by admin users)
const AdminPage = lazy(() => import('@/pages/admin-page').then(m => ({ default: m.AdminPage })));
const UsersPage = lazy(() => import('@/pages/admin/users/users-page').then(m => ({ default: m.UsersPage })));
const CreateUserPage = lazy(() => import('@/pages/admin/users/create-user-page').then(m => ({ default: m.CreateUserPage })));
const UserDetailPage = lazy(() => import('@/pages/admin/users/user-detail-page').then(m => ({ default: m.UserDetailPage })));
const RolesPage = lazy(() => import('@/pages/admin/roles/roles-page').then(m => ({ default: m.RolesPage })));
const CreateRolePage = lazy(() => import('@/pages/admin/roles/create-role-page').then(m => ({ default: m.CreateRolePage })));
const RoleDetailPage = lazy(() => import('@/pages/admin/roles/role-detail-page').then(m => ({ default: m.RoleDetailPage })));
const PermissionsPage = lazy(() => import('@/pages/admin/permissions-page').then(m => ({ default: m.PermissionsPage })));
const SessionsPage = lazy(() => import('@/pages/admin/identity/sessions-page').then(m => ({ default: m.SessionsPage })));
const SystemHealthPage = lazy(() => import('@/pages/admin/system/system-health-page').then(m => ({ default: m.SystemHealthPage })));
const StorageCenterPage = lazy(() => import('@/pages/admin/storage/storage-center-page').then(m => ({ default: m.StorageCenterPage })));
const AuditCenterPage = lazy(() => import('@/pages/admin/audit/audit-center-page').then(m => ({ default: m.AuditCenterPage })));
const SecurityCenterPage = lazy(() => import('@/pages/admin/security/security-center-page').then(m => ({ default: m.SecurityCenterPage })));
const AiAdminPage = lazy(() => import('@/pages/admin/ai/ai-admin-page').then(m => ({ default: m.AiAdminPage })));
const ConfigCenterPage = lazy(() => import('@/pages/admin/config/config-center-page').then(m => ({ default: m.ConfigCenterPage })));

export const router: ReturnType<typeof createBrowserRouter> = createBrowserRouter([
  // ── Public routes (no auth, no layout) ──────────────────────────────────
  { path: '/login', element: <LoginPage /> },
  { path: '/forgot-password', element: <ForgotPasswordPage /> },
  { path: '/reset-password', element: <ResetPasswordPage /> },

  // ── Protected routes (require auth, full app layout) ────────────────────
  {
    element: <ProtectedRoute />,
    children: [
      {
        // CommandPaletteProvider lives here because it calls useNavigate
        // and must be inside the router tree.
        element: (
          <CommandPaletteProvider>
            <AppLayout />
          </CommandPaletteProvider>
        ),
        children: [
          {
            // Single Suspense boundary covers all lazy-loaded app pages.
            // LazyLayout renders <Outlet /> inside <Suspense> so every child
            // chunk shows the spinner while it loads.
            element: <LazyLayout />,
            children: [
              { index: true, element: <DashboardPage /> },
              { path: 'profile', element: <ProfilePage /> },
              { path: 'cases', element: <CasesPage /> },
              { path: 'cases/:id', element: <CaseWorkspacePage /> },
              { path: 'evidence', element: <EvidencePage /> },
              { path: 'timeline', element: <TimelinePage /> },
              { path: 'graph', element: <GraphPage /> },
              { path: 'reports', element: <ReportsPage /> },
              { path: 'search', element: <SearchPage /> },
              { path: 'watchlists', element: <WatchlistsPage /> },
              { path: 'alerts', element: <AlertsPage /> },
              { path: 'notifications', element: <NotificationsPage /> },
              { path: 'settings', element: <SettingsPage /> },
              { path: 'audit', element: <AuditPage /> },

              // ── Admin section (nested within AdminLayout sidebar) ──────────
              {
                path: 'admin',
                element: <AdminLayout />,
                children: [
                  { index: true, element: <AdminPage /> },

                  // Identity
                  { path: 'users', element: <UsersPage /> },
                  { path: 'users/create', element: <CreateUserPage /> },
                  { path: 'users/:id', element: <UserDetailPage /> },
                  { path: 'sessions', element: <SessionsPage /> },
                  { path: 'roles', element: <RolesPage /> },
                  { path: 'roles/create', element: <CreateRolePage /> },
                  { path: 'roles/:id', element: <RoleDetailPage /> },
                  { path: 'permissions', element: <PermissionsPage /> },

                  // Operations
                  { path: 'system', element: <SystemHealthPage /> },
                  { path: 'queue', element: <SystemHealthPage /> },
                  { path: 'storage', element: <StorageCenterPage /> },

                  // Intelligence
                  { path: 'ai', element: <AiAdminPage /> },

                  // Compliance
                  { path: 'audit', element: <AuditCenterPage /> },
                  { path: 'security', element: <SecurityCenterPage /> },

                  // Platform
                  { path: 'config', element: <ConfigCenterPage /> },
                ],
              },

              { path: '*', element: <NotFoundPage /> },
            ],
          },
        ],
      },
    ],
  },
]);
