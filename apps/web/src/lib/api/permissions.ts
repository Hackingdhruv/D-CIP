import { apiFetch } from '@/lib/api-client';
import type { PermissionRead } from '@/types/permission';

export const permissionsApi = {
  list: () => apiFetch<PermissionRead[]>('/v1/permissions'),
};
