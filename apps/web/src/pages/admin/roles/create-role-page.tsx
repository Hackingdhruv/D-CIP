import { useNavigate } from 'react-router-dom';
import { toast } from 'sonner';
import { PageHeader } from '@/components/common/page-header';
import { RoleForm } from '@/components/roles/role-form';
import { useCreateRole } from '@/hooks/use-roles';
import { ApiRequestError } from '@/lib/api-client';
import type { RoleCreate } from '@/types/role';

export function CreateRolePage() {
  const navigate = useNavigate();
  const { mutateAsync: createRole, isPending } = useCreateRole();

  const onSubmit = async (data: RoleCreate) => {
    try {
      const role = await createRole(data);
      navigate(`/admin/roles/${role.id}`);
    } catch (err) {
      toast.error(err instanceof ApiRequestError ? err.message : 'Failed to create role.');
    }
  };

  return (
    <div className="space-y-6">
      <PageHeader title="Create role" description="Define a new role and assign permissions." />
      <RoleForm mode="create" onSubmit={onSubmit} isLoading={isPending} />
    </div>
  );
}
