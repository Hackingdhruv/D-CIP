import { apiFetch } from '@/lib/api-client';
import type { AssignPermissionsRequest, RoleCreate, RoleRead, RoleUpdate } from '@/types/role';

export const rolesApi = {
  list: () => apiFetch<RoleRead[]>('/v1/roles'),

  get: (id: string) => apiFetch<RoleRead>(`/v1/roles/${id}`),

  create: (data: RoleCreate) =>
    apiFetch<RoleRead>('/v1/roles', { method: 'POST', body: data }),

  update: (id: string, data: RoleUpdate) =>
    apiFetch<RoleRead>(`/v1/roles/${id}`, { method: 'PUT', body: data }),

  delete: (id: string) =>
    apiFetch<void>(`/v1/roles/${id}`, { method: 'DELETE' }),

  assignPermissions: (id: string, data: AssignPermissionsRequest) =>
    apiFetch<RoleRead>(`/v1/roles/${id}/permissions`, { method: 'PUT', body: data }),
};
