import { apiFetch } from '@/lib/api-client';
import type { UserCreate, UserListResponse, UserRead, UserUpdate } from '@/types/user';
import type { AssignRolesRequest } from '@/types/role';

interface ListUsersParams {
  q?: string;
  isActive?: boolean;
  page?: number;
  pageSize?: number;
}

export const usersApi = {
  list: ({ q, isActive, page = 1, pageSize = 20 }: ListUsersParams = {}) => {
    const params = new URLSearchParams();
    if (q) params.set('q', q);
    if (isActive !== undefined) params.set('is_active', String(isActive));
    params.set('page', String(page));
    params.set('page_size', String(pageSize));
    return apiFetch<UserListResponse>(`/v1/users?${params}`);
  },

  get: (id: string) => apiFetch<UserRead>(`/v1/users/${id}`),

  create: (data: UserCreate) =>
    apiFetch<UserRead>('/v1/users', { method: 'POST', body: data }),

  update: (id: string, data: UserUpdate) =>
    apiFetch<UserRead>(`/v1/users/${id}`, { method: 'PUT', body: data }),

  delete: (id: string) =>
    apiFetch<void>(`/v1/users/${id}`, { method: 'DELETE' }),

  enable: (id: string) =>
    apiFetch<UserRead>(`/v1/users/${id}/enable`, { method: 'POST' }),

  disable: (id: string) =>
    apiFetch<UserRead>(`/v1/users/${id}/disable`, { method: 'POST' }),

  unlock: (id: string) =>
    apiFetch<UserRead>(`/v1/users/${id}/unlock`, { method: 'POST' }),

  assignRoles: (id: string, data: AssignRolesRequest) =>
    apiFetch<UserRead>(`/v1/users/${id}/roles`, { method: 'PUT', body: data }),
};
