import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import {
  Form,
  FormControl,
  FormDescription,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from '@/components/ui/form';
import type { UserCreate, UserUpdate } from '@/types/user';

const passwordRules = z
  .string()
  .min(8, 'At least 8 characters.')
  .regex(/[A-Z]/, 'Uppercase required.')
  .regex(/[a-z]/, 'Lowercase required.')
  .regex(/[0-9]/, 'Digit required.')
  .regex(/[^A-Za-z0-9]/, 'Special character required.');

const createSchema = z.object({
  email: z.string().email('Valid email required.'),
  username: z
    .string()
    .min(3, 'At least 3 characters.')
    .max(50)
    .regex(/^[a-zA-Z0-9_.-]+$/, 'Only letters, numbers, _, . and - allowed.'),
  fullName: z.string().min(1, 'Full name is required.').max(255),
  password: passwordRules,
});

const editSchema = z.object({
  email: z.string().email('Valid email required.').optional().or(z.literal('')),
  username: z
    .string()
    .min(3)
    .max(50)
    .regex(/^[a-zA-Z0-9_.-]+$/)
    .optional()
    .or(z.literal('')),
  fullName: z.string().min(1).max(255).optional().or(z.literal('')),
});

type CreateFormValues = z.infer<typeof createSchema>;
type EditFormValues = z.infer<typeof editSchema>;

interface UserFormCreateProps {
  mode: 'create';
  onSubmit: (data: UserCreate) => void;
  isLoading: boolean;
  defaultValues?: undefined;
}

interface UserFormEditProps {
  mode: 'edit';
  onSubmit: (data: UserUpdate) => void;
  isLoading: boolean;
  defaultValues?: { email?: string; username?: string; fullName?: string };
}

type UserFormProps = UserFormCreateProps | UserFormEditProps;

export function UserForm({ mode, onSubmit, isLoading, defaultValues }: UserFormProps) {
  const isCreate = mode === 'create';

  const form = useForm<CreateFormValues | EditFormValues>({
    resolver: zodResolver(isCreate ? createSchema : editSchema),
    defaultValues: isCreate
      ? { email: '', username: '', fullName: '', password: '' }
      : {
          email: defaultValues?.email ?? '',
          username: defaultValues?.username ?? '',
          fullName: defaultValues?.fullName ?? '',
        },
  });

  const handleSubmit = (values: CreateFormValues | EditFormValues) => {
    if (isCreate) {
      (onSubmit as (d: UserCreate) => void)(values as UserCreate);
    } else {
      const data: UserUpdate = {};
      const v = values as EditFormValues;
      if (v.email) data.email = v.email;
      if (v.username) data.username = v.username;
      if (v.fullName) data.fullName = v.fullName;
      (onSubmit as (d: UserUpdate) => void)(data);
    }
  };

  return (
    <Card className="max-w-lg">
      <CardHeader>
        <CardTitle>{isCreate ? 'New user' : 'Edit profile'}</CardTitle>
      </CardHeader>
      <CardContent>
        <Form {...form}>
          <form onSubmit={form.handleSubmit(handleSubmit)} className="space-y-4">
            <FormField
              control={form.control}
              name="fullName"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Full name</FormLabel>
                  <FormControl>
                    <Input placeholder="Jane Smith" {...field} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="email"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Email address</FormLabel>
                  <FormControl>
                    <Input type="email" placeholder="jane@dcip.local" {...field} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="username"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Username</FormLabel>
                  <FormControl>
                    <Input placeholder="jsmith" {...field} />
                  </FormControl>
                  <FormDescription>3–50 characters; letters, numbers, _, . and -</FormDescription>
                  <FormMessage />
                </FormItem>
              )}
            />

            {isCreate && (
              <FormField
                control={form.control as ReturnType<typeof useForm<CreateFormValues>>['control']}
                name="password"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Password</FormLabel>
                    <FormControl>
                      <Input type="password" autoComplete="new-password" {...field} />
                    </FormControl>
                    <FormDescription>
                      Min. 8 chars with uppercase, lowercase, digit and special character.
                    </FormDescription>
                    <FormMessage />
                  </FormItem>
                )}
              />
            )}

            <div className="flex gap-3 pt-2">
              <Button type="submit" disabled={isLoading}>
                {isLoading ? 'Saving…' : isCreate ? 'Create user' : 'Save changes'}
              </Button>
            </div>
          </form>
        </Form>
      </CardContent>
    </Card>
  );
}
