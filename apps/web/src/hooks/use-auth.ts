import { useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { authApi } from '@/lib/api/auth';
import { useAuth } from '@/contexts/auth-context';
import type { ChangePasswordPayload, ForgotPasswordPayload, LoginCredentials, ResetPasswordPayload } from '@/types/auth';

export { useAuth };

export function useLogin() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (credentials: LoginCredentials) => authApi.login(credentials),
    onSuccess: (data) => {
      queryClient.setQueryData(['me'], data.user);
    },
    onError: () => {},
  });
}

export function useLogout() {
  const { logout } = useAuth();
  return { logout };
}

export function useForgotPassword() {
  return useMutation({
    mutationFn: (payload: ForgotPasswordPayload) => authApi.forgotPassword(payload),
  });
}

export function useResetPassword() {
  return useMutation({
    mutationFn: (payload: ResetPasswordPayload) => authApi.resetPassword(payload),
    onSuccess: () => {
      toast.success('Password reset successfully. You can now sign in.');
    },
  });
}

export function useChangePassword() {
  return useMutation({
    mutationFn: (payload: ChangePasswordPayload) => authApi.changePassword(payload),
    onSuccess: () => {
      toast.success('Password changed successfully.');
    },
  });
}

export function useUpdateProfile() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: { fullName?: string; avatarUrl?: string }) => authApi.updateMe(data),
    onSuccess: (user) => {
      queryClient.setQueryData(['me'], user);
      toast.success('Profile updated.');
    },
  });
}
