import { Navigate, Outlet, useLocation } from 'react-router-dom';
import { LoadingScreen } from '@/components/common/loading-screen';
import { useAuth } from '@/contexts/auth-context';

interface ProtectedRouteProps {
  redirectTo?: string;
}

/**
 * Renders child routes only when the user is authenticated. While the auth
 * state is loading it shows a full-screen spinner. Unauthenticated users are
 * redirected to the login page with the original URL preserved so they land
 * back after a successful sign-in.
 */
export function ProtectedRoute({ redirectTo = '/login' }: ProtectedRouteProps) {
  const { isAuthenticated, isLoading } = useAuth();
  const location = useLocation();

  if (isLoading) return <LoadingScreen />;

  if (!isAuthenticated) {
    return <Navigate to={redirectTo} state={{ from: location }} replace />;
  }

  return <Outlet />;
}
