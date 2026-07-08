import { apiFetch } from '@/lib/api-client';
import type { AuthResponse, ChangePasswordPayload, ForgotPasswordPayload, LoginCredentials, MessageResponse, ResetPasswordPayload } from '@/types/auth';
import type { UserRead } from '@/types/user';

export const authApi = {
  login: (credentials: LoginCredentials) =>
    apiFetch<AuthResponse>('/v1/auth/login', { method: 'POST', body: credentials }),

  logout: () =>
    apiFetch<void>('/v1/auth/logout', { method: 'POST' }),

  refresh: () =>
    apiFetch<AuthResponse>('/v1/auth/refresh', { method: 'POST' }),

  forgotPassword: (payload: ForgotPasswordPayload) =>
    apiFetch<MessageResponse>('/v1/auth/forgot-password', { method: 'POST', body: payload }),

  resetPassword: (payload: ResetPasswordPayload) =>
    apiFetch<MessageResponse>('/v1/auth/reset-password', { method: 'POST', body: payload }),

  changePassword: (payload: ChangePasswordPayload) =>
    apiFetch<MessageResponse>('/v1/auth/change-password', { method: 'POST', body: payload }),

  getMe: () =>
    apiFetch<UserRead>('/v1/me'),

  updateMe: (data: { fullName?: string; avatarUrl?: string }) =>
    apiFetch<UserRead>('/v1/me', { method: 'PUT', body: data }),
};
