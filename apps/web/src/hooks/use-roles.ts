import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { rolesApi } from '@/lib/api/roles';
import { permissionsApi } from '@/lib/api/permissions';
import type { AssignPermissionsRequest, RoleCreate, RoleUpdate } from '@/types/role';

export function useRoles(enabled = true) {
  return useQuery({
    queryKey: ['roles'],
    queryFn: rolesApi.list,
    enabled,
  });
}

export function useRole(id: string, enabled = true) {
  return useQuery({
    queryKey: ['roles', id],
    queryFn: () => rolesApi.get(id),
    enabled: !!id && enabled,
  });
}

export function usePermissions(enabled = true) {
  return useQuery({
    queryKey: ['permissions'],
    queryFn: permissionsApi.list,
    enabled,
  });
}

export function useCreateRole() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: RoleCreate) => rolesApi.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['roles'] });
      toast.success('Role created.');
    },
  });
}

export function useUpdateRole(id: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: RoleUpdate) => rolesApi.update(id, data),
    onSuccess: (role) => {
      queryClient.setQueryData(['roles', id], role);
      queryClient.invalidateQueries({ queryKey: ['roles'] });
      toast.success('Role updated.');
    },
  });
}

export function useDeleteRole() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => rolesApi.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['roles'] });
      toast.success('Role deleted.');
    },
  });
}

export function useAssignPermissions(roleId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: AssignPermissionsRequest) => rolesApi.assignPermissions(roleId, data),
    onSuccess: (role) => {
      queryClient.setQueryData(['roles', roleId], role);
      toast.success('Permissions updated.');
    },
  });
}
