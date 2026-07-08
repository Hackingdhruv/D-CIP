import type { ReactNode } from 'react';
import { useHasPermission } from '@/contexts/auth-context';

interface PermissionGuardProps {
  permission: string;
  children: ReactNode;
  fallback?: ReactNode;
}

/**
 * Renders children only when the current user holds the required permission.
 * Use `fallback` to render an alternative (e.g. a disabled button or nothing).
 */
export function PermissionGuard({ permission, children, fallback = null }: PermissionGuardProps) {
  const allowed = useHasPermission(permission);
  return allowed ? <>{children}</> : <>{fallback}</>;
}
