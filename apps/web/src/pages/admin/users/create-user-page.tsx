import { useNavigate } from 'react-router-dom';
import { toast } from 'sonner';
import { PageHeader } from '@/components/common/page-header';
import { UserForm } from '@/components/users/user-form';
import { useCreateUser } from '@/hooks/use-users';
import { ApiRequestError } from '@/lib/api-client';
import type { UserCreate } from '@/types/user';

export function CreateUserPage() {
  const navigate = useNavigate();
  const { mutateAsync: createUser, isPending } = useCreateUser();

  const onSubmit = async (data: UserCreate) => {
    try {
      await createUser(data);
      navigate('/admin/users');
    } catch (err) {
      toast.error(err instanceof ApiRequestError ? err.message : 'Failed to create user.');
    }
  };

  return (
    <div className="space-y-6">
      <PageHeader
        title="Create user"
        description="Add a new user to the platform."
      />
      <UserForm mode="create" onSubmit={onSubmit} isLoading={isPending} />
    </div>
  );
}
