import { useParams, useNavigate } from 'react-router-dom';
import { toast } from 'sonner';
import { Trash2 } from 'lucide-react';
import { PageHeader } from '@/components/common/page-header';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { RoleForm } from '@/components/roles/role-form';
import { useRole, useUpdateRole, useDeleteRole, useAssignPermissions, usePermissions } from '@/hooks/use-roles';
import { ApiRequestError } from '@/lib/api-client';
import type { RoleUpdate } from '@/types/role';

export function RoleDetailPage() {
  const { id = '' } = useParams<{ id: string }>();
  const navigate = useNavigate();

  const { data: role, isLoading } = useRole(id);
  const { data: allPermissions } = usePermissions();
  const { mutateAsync: updateRole, isPending: saving } = useUpdateRole(id);
  const { mutateAsync: deleteRole } = useDeleteRole();
  const { mutateAsync: assignPermissions } = useAssignPermissions(id);

  if (isLoading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-10 w-64" />
        <Skeleton className="h-64 w-full" />
      </div>
    );
  }

  if (!role) return <p className="text-muted-foreground">Role not found.</p>;

  const onUpdate = async (data: RoleUpdate) => {
    try {
      await updateRole(data);
    } catch (err) {
      toast.error(err instanceof ApiRequestError ? err.message : 'Update failed.');
    }
  };

  const onDelete = async () => {
    if (role.isSystem) {
      toast.error('System roles cannot be deleted.');
      return;
    }
    if (!confirm(`Delete role "${role.name}"?`)) return;
    try {
      await deleteRole(id);
      navigate('/admin/roles');
    } catch (err) {
      toast.error(err instanceof ApiRequestError ? err.message : 'Delete failed.');
    }
  };

  const onTogglePermission = async (permId: string, checked: boolean) => {
    const currentIds = role.permissions.map((p) => p.id);
    const newIds = checked ? [...currentIds, permId] : currentIds.filter((pid) => pid !== permId);
    try {
      await assignPermissions({ permissionIds: newIds });
    } catch (err) {
      toast.error(err instanceof ApiRequestError ? err.message : 'Failed to update permissions.');
    }
  };

  // Group permissions by resource
  const grouped = (allPermissions ?? []).reduce<Record<string, typeof allPermissions>>((acc, p) => {
    if (!acc[p.resource]) acc[p.resource] = [];
    acc[p.resource]!.push(p);
    return acc;
  }, {});

  return (
    <div className="space-y-6">
      <PageHeader
        title={role.name}
        description={role.description ?? ''}
        actions={
          !role.isSystem && (
            <Button variant="destructive" size="sm" onClick={onDelete}>
              <Trash2 className="h-4 w-4" />
              Delete role
            </Button>
          )
        }
      />

      {role.isSystem && (
        <Badge variant="secondary">System role — cannot be deleted</Badge>
      )}

      <Tabs defaultValue="details">
        <TabsList>
          <TabsTrigger value="details">Details</TabsTrigger>
          <TabsTrigger value="permissions">Permissions</TabsTrigger>
        </TabsList>

        <TabsContent value="details" className="mt-6">
          <RoleForm
            mode="edit"
            defaultValues={{ name: role.name, description: role.description ?? '' }}
            onSubmit={onUpdate}
            isLoading={saving}
          />
        </TabsContent>

        <TabsContent value="permissions" className="mt-6">
          <div className="space-y-4">
            {Object.entries(grouped).map(([resource, perms]) => (
              <Card key={resource}>
                <CardHeader className="py-3">
                  <CardTitle className="text-sm font-semibold uppercase tracking-wider text-muted-foreground">
                    {resource}
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-2 pt-0">
                  {perms!.map((perm) => {
                    const isGranted = role.permissions.some((p) => p.id === perm.id);
                    return (
                      <label
                        key={perm.id}
                        className="flex cursor-pointer items-center justify-between rounded-md px-3 py-2 hover:bg-muted/50"
                      >
                        <div>
                          <span className="font-mono text-sm">{perm.codename}</span>
                          {perm.description && (
                            <p className="text-xs text-muted-foreground">{perm.description}</p>
                          )}
                        </div>
                        <input
                          type="checkbox"
                          className="h-4 w-4 accent-primary"
                          defaultChecked={isGranted}
                          onChange={(e) => onTogglePermission(perm.id, e.target.checked)}
                        />
                      </label>
                    );
                  })}
                </CardContent>
              </Card>
            ))}
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
}
