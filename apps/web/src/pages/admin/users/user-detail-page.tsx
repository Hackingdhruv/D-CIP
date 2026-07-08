import { useParams, useNavigate } from 'react-router-dom';
import { toast } from 'sonner';
import { LockOpen, UserCheck, UserX, Trash2 } from 'lucide-react';
import { PageHeader } from '@/components/common/page-header';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { UserForm } from '@/components/users/user-form';
import {
  useUser,
  useUpdateUser,
  useEnableUser,
  useDisableUser,
  useDeleteUser,
  useAssignRoles,
  useUnlockUser,
} from '@/hooks/use-users';
import { useRoles } from '@/hooks/use-roles';
import { ApiRequestError } from '@/lib/api-client';
import type { UserUpdate } from '@/types/user';

export function UserDetailPage() {
  const { id = '' } = useParams<{ id: string }>();
  const navigate = useNavigate();

  const { data: user, isLoading } = useUser(id);
  const { data: allRoles } = useRoles();
  const { mutateAsync: updateUser, isPending: saving } = useUpdateUser(id);
  const { mutateAsync: enableUser } = useEnableUser();
  const { mutateAsync: disableUser } = useDisableUser();
  const { mutateAsync: deleteUser } = useDeleteUser();
  const { mutateAsync: assignRoles } = useAssignRoles(id);
  const { mutateAsync: unlockUser } = useUnlockUser();

  if (isLoading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-10 w-64" />
        <Skeleton className="h-64 w-full" />
      </div>
    );
  }

  if (!user) return <p className="text-muted-foreground">User not found.</p>;

  const onUpdate = async (data: UserUpdate) => {
    try {
      await updateUser(data);
    } catch (err) {
      toast.error(err instanceof ApiRequestError ? err.message : 'Update failed.');
    }
  };

  const onEnable = async () => {
    try {
      await enableUser(id);
    } catch (err) {
      toast.error(err instanceof ApiRequestError ? err.message : 'Failed.');
    }
  };

  const onDisable = async () => {
    try {
      await disableUser(id);
    } catch (err) {
      toast.error(err instanceof ApiRequestError ? err.message : 'Failed.');
    }
  };

  const onUnlock = async () => {
    try {
      await unlockUser(id);
    } catch (err) {
      toast.error(err instanceof ApiRequestError ? err.message : 'Failed to unlock.');
    }
  };

  const onDelete = async () => {
    if (!confirm(`Delete ${user.fullName}? This action cannot be undone.`)) return;
    try {
      await deleteUser(id);
      navigate('/admin/users');
    } catch (err) {
      toast.error(err instanceof ApiRequestError ? err.message : 'Delete failed.');
    }
  };

  const onAssignRoles = async (roleIds: string[]) => {
    try {
      await assignRoles({ roleIds });
    } catch (err) {
      toast.error(err instanceof ApiRequestError ? err.message : 'Failed to update roles.');
    }
  };

  return (
    <div className="space-y-6">
      <PageHeader
        title={user.fullName}
        description={`${user.email} · @${user.username}`}
        actions={
          <div className="flex gap-2">
            {user.isLocked && (
              <Button variant="outline" size="sm" onClick={onUnlock}>
                <LockOpen className="h-4 w-4" />
                Unlock
              </Button>
            )}
            {user.isActive ? (
              <Button variant="outline" size="sm" onClick={onDisable}>
                <UserX className="h-4 w-4" />
                Disable
              </Button>
            ) : (
              <Button variant="outline" size="sm" onClick={onEnable}>
                <UserCheck className="h-4 w-4" />
                Enable
              </Button>
            )}
            <Button variant="destructive" size="sm" onClick={onDelete}>
              <Trash2 className="h-4 w-4" />
              Delete
            </Button>
          </div>
        }
      />

      <div className="flex items-center gap-2">
        <Badge variant={user.isActive ? 'default' : 'secondary'}>
          {user.isActive ? 'Active' : 'Inactive'}
        </Badge>
        {user.isLocked && <Badge variant="destructive">Locked</Badge>}
      </div>

      <Tabs defaultValue="profile">
        <TabsList>
          <TabsTrigger value="profile">Profile</TabsTrigger>
          <TabsTrigger value="roles">Roles</TabsTrigger>
        </TabsList>

        <TabsContent value="profile" className="mt-6">
          <UserForm
            mode="edit"
            defaultValues={{ email: user.email, username: user.username, fullName: user.fullName }}
            onSubmit={onUpdate}
            isLoading={saving}
          />
        </TabsContent>

        <TabsContent value="roles" className="mt-6">
          <Card>
            <CardHeader>
              <CardTitle>Assigned roles</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                {(allRoles ?? []).map((role) => {
                  const isAssigned = user.roles.some((r) => r.id === role.id);
                  return (
                    <label
                      key={role.id}
                      className="flex cursor-pointer items-center justify-between rounded-md border border-border p-3 hover:bg-muted/50"
                    >
                      <div>
                        <p className="text-sm font-medium">{role.name}</p>
                        {role.description && (
                          <p className="text-xs text-muted-foreground">{role.description}</p>
                        )}
                      </div>
                      <input
                        type="checkbox"
                        className="h-4 w-4 accent-primary"
                        defaultChecked={isAssigned}
                        onChange={(e) => {
                          const currentIds = user.roles.map((r) => r.id);
                          const newIds = e.target.checked
                            ? [...currentIds, role.id]
                            : currentIds.filter((rid) => rid !== role.id);
                          onAssignRoles(newIds);
                        }}
                      />
                    </label>
                  );
                })}
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
