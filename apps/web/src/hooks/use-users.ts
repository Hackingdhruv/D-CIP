import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { usersApi } from '@/lib/api/users';
import type { UserCreate, UserUpdate } from '@/types/user';
import type { AssignRolesRequest } from '@/types/role';

interface ListUsersParams {
  q?: string;
  isActive?: boolean;
  page?: number;
  pageSize?: number;
  enabled?: boolean;
}

export function useUsers({ q, isActive, page = 1, pageSize = 20, enabled = true }: ListUsersParams = {}) {
  return useQuery({
    queryKey: ['users', { q, isActive, page, pageSize }],
    queryFn: () => usersApi.list({ q, isActive, page, pageSize }),
    enabled,
  });
}

export function useUser(id: string, enabled = true) {
  return useQuery({
    queryKey: ['users', id],
    queryFn: () => usersApi.get(id),
    enabled: !!id && enabled,
  });
}

export function useCreateUser() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: UserCreate) => usersApi.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['users'] });
      toast.success('User created successfully.');
    },
  });
}

export function useUpdateUser(id: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: UserUpdate) => usersApi.update(id, data),
    onSuccess: (user) => {
      queryClient.setQueryData(['users', id], user);
      queryClient.invalidateQueries({ queryKey: ['users'] });
      toast.success('User updated.');
    },
  });
}

export function useDeleteUser() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => usersApi.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['users'] });
      toast.success('User deleted.');
    },
  });
}

export function useEnableUser() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => usersApi.enable(id),
    onSuccess: (user) => {
      queryClient.setQueryData(['users', user.id], user);
      queryClient.invalidateQueries({ queryKey: ['users'] });
      toast.success(`${user.fullName} enabled.`);
    },
  });
}

export function useDisableUser() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => usersApi.disable(id),
    onSuccess: (user) => {
      queryClient.setQueryData(['users', user.id], user);
      queryClient.invalidateQueries({ queryKey: ['users'] });
      toast.success(`${user.fullName} disabled.`);
    },
  });
}

export function useUnlockUser() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => usersApi.unlock(id),
    onSuccess: (user) => {
      queryClient.setQueryData(['users', user.id], user);
      queryClient.invalidateQueries({ queryKey: ['users'] });
      toast.success(`${user.fullName} unlocked.`);
    },
  });
}

export function useAssignRoles(userId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: AssignRolesRequest) => usersApi.assignRoles(userId, data),
    onSuccess: (user) => {
      queryClient.setQueryData(['users', userId], user);
      toast.success('Roles updated.');
    },
  });
}
