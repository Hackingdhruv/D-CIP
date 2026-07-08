import { Link } from 'react-router-dom';
import { PlusCircle } from 'lucide-react';
import { PageHeader } from '@/components/common/page-header';
import { Button } from '@/components/ui/button';
import { RoleTable } from '@/components/roles/role-table';
import { useRoles } from '@/hooks/use-roles';

export function RolesPage() {
  const { data: roles, isLoading } = useRoles();

  return (
    <div className="space-y-6">
      <PageHeader
        title="Roles"
        description="Manage roles and their associated permissions."
        actions={
          <Button asChild size="sm">
            <Link to="/admin/roles/create">
              <PlusCircle className="h-4 w-4" />
              New role
            </Link>
          </Button>
        }
      />
      <RoleTable roles={roles ?? []} isLoading={isLoading} />
    </div>
  );
}
