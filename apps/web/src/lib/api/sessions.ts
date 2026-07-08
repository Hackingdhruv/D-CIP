import { apiFetch } from '@/lib/api-client';
import type { UserSession } from '@/types/session';

export const sessionsApi = {
  list: () => apiFetch<UserSession[]>('/v1/me/sessions'),

  revoke: (sessionId: string) =>
    apiFetch<void>(`/v1/me/sessions/${sessionId}`, { method: 'DELETE' }),

  revokeAll: () =>
    apiFetch<void>('/v1/me/sessions', { method: 'DELETE' }),

  uploadAvatar: async (file: File): Promise<{ avatarUrl: string }> => {
    const form = new FormData();
    form.append('file', file);
    const response = await fetch(`${import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000/api'}/v1/me/avatar`, {
      method: 'POST',
      credentials: 'include',
      body: form,
    });
    if (!response.ok) {
      const payload = await response.json().catch(() => undefined);
      throw new Error(payload?.error?.message ?? 'Avatar upload failed.');
    }
    const user = await response.json();
    return { avatarUrl: user.avatarUrl };
  },
};
