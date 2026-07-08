import { useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { toast } from 'sonner';
import { Eye, EyeOff, Lock } from 'lucide-react';
import dcipMark from '@/assets/dcip-mark.svg';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from '@/components/ui/form';
import { PasswordStrength } from '@/components/common/password-strength';
import { useResetPassword } from '@/hooks/use-auth';
import { ApiRequestError } from '@/lib/api-client';

const passwordRules = z
  .string()
  .min(8, 'At least 8 characters.')
  .regex(/[A-Z]/, 'At least one uppercase letter.')
  .regex(/[a-z]/, 'At least one lowercase letter.')
  .regex(/[0-9]/, 'At least one digit.')
  .regex(/[^A-Za-z0-9]/, 'At least one special character.');

const schema = z
  .object({
    newPassword: passwordRules,
    confirmPassword: z.string().min(1, 'Confirm your password.'),
  })
  .refine((d) => d.newPassword === d.confirmPassword, {
    message: "Passwords don't match.",
    path: ['confirmPassword'],
  });

type FormValues = z.infer<typeof schema>;

export function ResetPasswordPage() {
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const token = params.get('token') ?? '';
  const { mutateAsync: resetPassword, isPending } = useResetPassword();
  const [showNew, setShowNew] = useState(false);
  const [showConfirm, setShowConfirm] = useState(false);
  const [newPasswordValue, setNewPasswordValue] = useState('');

  const form = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: { newPassword: '', confirmPassword: '' },
  });

  const onSubmit = async (values: FormValues) => {
    if (!token) {
      toast.error('Invalid or missing reset token.');
      return;
    }
    try {
      await resetPassword({ token, newPassword: values.newPassword });
      navigate('/login', { replace: true });
    } catch (err) {
      toast.error(err instanceof ApiRequestError ? err.message : 'Reset failed. Please try again.');
    }
  };

  if (!token) {
    return (
      <div className="flex min-h-dvh items-center justify-center">
        <div className="rounded-2xl border border-destructive/30 bg-destructive/5 p-8 text-center">
          <p className="text-destructive font-medium">Invalid reset link.</p>
          <p className="mt-1 text-sm text-muted-foreground">Please request a new password reset.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex min-h-dvh items-center justify-center bg-background px-4">
      <div className="w-full max-w-md space-y-8">
        <div className="flex flex-col items-center gap-3">
          <img src={dcipMark} alt="D-CIP" className="h-14 w-14" />
          <div className="text-center">
            <h1 className="text-2xl font-bold tracking-tight">Set a new password</h1>
            <p className="text-sm text-muted-foreground">Choose a strong password for your account.</p>
          </div>
        </div>

        <div className="rounded-2xl border border-border bg-card p-8 shadow-lg">
          <Form {...form}>
            <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-5">
              <FormField
                control={form.control}
                name="newPassword"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>New password</FormLabel>
                    <FormControl>
                      <div className="relative">
                        <Lock className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                        <Input
                          type={showNew ? 'text' : 'password'}
                          className="pl-9 pr-10"
                          autoComplete="new-password"
                          autoFocus
                          {...field}
                          onChange={(e) => {
                            field.onChange(e);
                            setNewPasswordValue(e.target.value);
                          }}
                        />
                        <button
                          type="button"
                          onClick={() => setShowNew((v) => !v)}
                          className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                          tabIndex={-1}
                        >
                          {showNew ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                        </button>
                      </div>
                    </FormControl>
                    <PasswordStrength password={newPasswordValue} />
                    <FormMessage />
                  </FormItem>
                )}
              />

              <FormField
                control={form.control}
                name="confirmPassword"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Confirm password</FormLabel>
                    <FormControl>
                      <div className="relative">
                        <Lock className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                        <Input
                          type={showConfirm ? 'text' : 'password'}
                          className="pl-9 pr-10"
                          autoComplete="new-password"
                          {...field}
                        />
                        <button
                          type="button"
                          onClick={() => setShowConfirm((v) => !v)}
                          className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                          tabIndex={-1}
                        >
                          {showConfirm ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                        </button>
                      </div>
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <Button type="submit" className="w-full" size="lg" disabled={isPending}>
                {isPending ? (
                  <span className="flex items-center gap-2">
                    <span className="h-4 w-4 animate-spin rounded-full border-2 border-current border-t-transparent" />
                    Resetting…
                  </span>
                ) : (
                  'Reset password'
                )}
              </Button>
            </form>
          </Form>
        </div>
      </div>
    </div>
  );
}
