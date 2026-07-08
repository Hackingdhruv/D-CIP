import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from '@/components/ui/form';
import type { RoleCreate, RoleUpdate } from '@/types/role';

const createSchema = z.object({
  name: z.string().min(1, 'Name is required.').max(100),
  description: z.string().max(500).optional(),
});

const editSchema = z.object({
  name: z.string().min(1, 'Name is required.').max(100).optional(),
  description: z.string().max(500).optional(),
});

type CreateForm = z.infer<typeof createSchema>;
type EditForm = z.infer<typeof editSchema>;

interface RoleFormCreateProps {
  mode: 'create';
  onSubmit: (data: RoleCreate) => void;
  isLoading: boolean;
  defaultValues?: undefined;
}

interface RoleFormEditProps {
  mode: 'edit';
  onSubmit: (data: RoleUpdate) => void;
  isLoading: boolean;
  defaultValues?: { name?: string; description?: string };
}

type RoleFormProps = RoleFormCreateProps | RoleFormEditProps;

export function RoleForm({ mode, onSubmit, isLoading, defaultValues }: RoleFormProps) {
  const isCreate = mode === 'create';

  const form = useForm<CreateForm | EditForm>({
    resolver: zodResolver(isCreate ? createSchema : editSchema),
    defaultValues: {
      name: defaultValues?.name ?? '',
      description: defaultValues?.description ?? '',
    },
  });

  const handleSubmit = (values: CreateForm | EditForm) => {
    onSubmit(values as RoleCreate & RoleUpdate);
  };

  return (
    <Card className="max-w-lg">
      <CardHeader>
        <CardTitle>{isCreate ? 'New role' : 'Edit role'}</CardTitle>
      </CardHeader>
      <CardContent>
        <Form {...form}>
          <form onSubmit={form.handleSubmit(handleSubmit)} className="space-y-4">
            <FormField
              control={form.control}
              name="name"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Role name</FormLabel>
                  <FormControl>
                    <Input placeholder="Senior Analyst" {...field} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="description"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Description</FormLabel>
                  <FormControl>
                    <Input placeholder="Brief description of this role's purpose." {...field} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            <div className="pt-2">
              <Button type="submit" disabled={isLoading}>
                {isLoading ? 'Saving…' : isCreate ? 'Create role' : 'Save changes'}
              </Button>
            </div>
          </form>
        </Form>
      </CardContent>
    </Card>
  );
}
