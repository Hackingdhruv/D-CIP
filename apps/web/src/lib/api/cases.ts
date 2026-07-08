import { apiFetch } from '@/lib/api-client';
import { env } from '@/config/env';
import type {
  CaseAssignRequest,
  CaseActivityRead,
  CaseCreate,
  CaseImportPreview,
  CaseListResponse,
  CaseNoteCreate,
  CaseNoteRead,
  CaseNoteUpdate,
  CaseRead,
  CaseTaskCreate,
  CaseTaskRead,
  CaseTaskUpdate,
  CaseUpdate,
} from '@/types/case';

interface ListCasesParams {
  q?: string;
  status?: string;
  priority?: string;
  category?: string;
  isStarred?: boolean;
  includeArchived?: boolean;
  page?: number;
  pageSize?: number;
}

export const casesApi = {
  list: ({
    q,
    status,
    priority,
    category,
    isStarred,
    includeArchived,
    page = 1,
    pageSize = 20,
  }: ListCasesParams = {}) => {
    const params = new URLSearchParams();
    if (q) params.set('q', q);
    if (status) params.set('status', status);
    if (priority) params.set('priority', priority);
    if (category) params.set('category', category);
    if (isStarred !== undefined) params.set('is_starred', String(isStarred));
    if (includeArchived) params.set('include_archived', 'true');
    params.set('page', String(page));
    params.set('page_size', String(pageSize));
    return apiFetch<CaseListResponse>(`/v1/cases?${params}`);
  },

  get: (id: string) => apiFetch<CaseRead>(`/v1/cases/${id}`),

  create: (data: CaseCreate) =>
    apiFetch<CaseRead>('/v1/cases', { method: 'POST', body: data }),

  importPreview: async (file: File): Promise<CaseImportPreview> => {
    const form = new FormData();
    form.append('file', file);
    const url = `${env.apiBaseUrl}/v1/cases/import/preview`;
    const res = await fetch(url, { method: 'POST', credentials: 'include', body: form });
    if (!res.ok) {
      const payload = await res.json().catch(() => undefined);
      throw new Error(payload?.detail ?? res.statusText);
    }
    return res.json();
  },

  update: (id: string, data: CaseUpdate) =>
    apiFetch<CaseRead>(`/v1/cases/${id}`, { method: 'PUT', body: data }),

  delete: (id: string) => apiFetch<void>(`/v1/cases/${id}`, { method: 'DELETE' }),

  archive: (id: string) =>
    apiFetch<CaseRead>(`/v1/cases/${id}/archive`, { method: 'POST' }),

  restore: (id: string) =>
    apiFetch<CaseRead>(`/v1/cases/${id}/restore`, { method: 'POST' }),

  star: (id: string) => apiFetch<CaseRead>(`/v1/cases/${id}/star`, { method: 'POST' }),

  unstar: (id: string) =>
    apiFetch<CaseRead>(`/v1/cases/${id}/unstar`, { method: 'POST' }),

  assign: (id: string, data: CaseAssignRequest) =>
    apiFetch<CaseRead>(`/v1/cases/${id}/assignments`, { method: 'PUT', body: data }),

  listActivities: (id: string, page = 1, pageSize = 50) => {
    const params = new URLSearchParams({ page: String(page), page_size: String(pageSize) });
    return apiFetch<CaseActivityRead[]>(`/v1/cases/${id}/activities?${params}`);
  },

  // Tasks
  listTasks: (caseId: string) =>
    apiFetch<CaseTaskRead[]>(`/v1/cases/${caseId}/tasks`),

  createTask: (caseId: string, data: CaseTaskCreate) =>
    apiFetch<CaseTaskRead>(`/v1/cases/${caseId}/tasks`, { method: 'POST', body: data }),

  updateTask: (caseId: string, taskId: string, data: CaseTaskUpdate) =>
    apiFetch<CaseTaskRead>(`/v1/cases/${caseId}/tasks/${taskId}`, {
      method: 'PUT',
      body: data,
    }),

  deleteTask: (caseId: string, taskId: string) =>
    apiFetch<void>(`/v1/cases/${caseId}/tasks/${taskId}`, { method: 'DELETE' }),

  // Notes
  listNotes: (caseId: string) =>
    apiFetch<CaseNoteRead[]>(`/v1/cases/${caseId}/notes`),

  createNote: (caseId: string, data: CaseNoteCreate) =>
    apiFetch<CaseNoteRead>(`/v1/cases/${caseId}/notes`, { method: 'POST', body: data }),

  updateNote: (caseId: string, noteId: string, data: CaseNoteUpdate) =>
    apiFetch<CaseNoteRead>(`/v1/cases/${caseId}/notes/${noteId}`, {
      method: 'PUT',
      body: data,
    }),

  deleteNote: (caseId: string, noteId: string) =>
    apiFetch<void>(`/v1/cases/${caseId}/notes/${noteId}`, { method: 'DELETE' }),
};
