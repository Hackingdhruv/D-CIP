import { apiFetch } from '@/lib/api-client';
import { env } from '@/config/env';
import type {
  EvidenceCustodyEvent,
  EvidenceListResponse,
  EvidencePreviewResponse,
  EvidenceRead,
  EvidenceUpdate,
  EvidenceVerifyResponse,
} from '@/types/evidence';

const base = (caseId: string) => `/v1/cases/${caseId}/evidence`;

// ── Upload (multipart — bypasses JSON-only apiFetch) ──────────────────────────

export interface UploadProgress {
  file: File;
  progress: number; // 0-100
  status: 'pending' | 'uploading' | 'done' | 'duplicate' | 'error';
  error?: string;
  result?: EvidenceRead;
}

export async function uploadEvidenceFiles(
  caseId: string,
  files: File[],
  onProgress?: (updates: UploadProgress[]) => void,
): Promise<EvidenceRead[]> {
  const results: EvidenceRead[] = [];
  const progress: UploadProgress[] = files.map((f) => ({
    file: f,
    progress: 0,
    status: 'pending' as const,
  }));

  onProgress?.(progress);

  for (let i = 0; i < files.length; i++) {
    const file = files[i]!;
    progress[i] = { file, status: 'uploading', progress: 0 };
    onProgress?.([...progress]);

    try {
      const fd = new FormData();
      fd.append('files', file);

      const res = await fetch(
        `${env.apiBaseUrl}${base(caseId)}`,
        { method: 'POST', credentials: 'include', body: fd },
      );

      if (!res.ok) {
        const payload = await res.json().catch(() => ({}));
        throw new Error(payload?.error?.message ?? res.statusText);
      }

      const data: EvidenceRead[] = await res.json();
      const ev = data[0]!;
      progress[i] = { file, status: 'done', progress: 100, result: ev };
      results.push(ev);
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Upload failed';
      const isDup = msg.toLowerCase().includes('already');
      progress[i] = {
        file,
        status: isDup ? 'duplicate' : 'error',
        error: msg,
        progress: 100,
      };
    }

    onProgress?.([...progress]);
  }

  return results;
}

// ── CRUD ──────────────────────────────────────────────────────────────────────

export const evidenceApi = {
  list: (
    caseId: string,
    params: {
      q?: string;
      mimeCategory?: string;
      fileExtension?: string;
      status?: string;
      page?: number;
      pageSize?: number;
    } = {},
  ) => {
    const qs = new URLSearchParams();
    if (params.q) qs.set('q', params.q);
    if (params.mimeCategory) qs.set('mime_category', params.mimeCategory);
    if (params.fileExtension) qs.set('file_extension', params.fileExtension);
    if (params.status) qs.set('status', params.status);
    if (params.page) qs.set('page', String(params.page));
    if (params.pageSize) qs.set('page_size', String(params.pageSize));
    const query = qs.toString();
    return apiFetch<EvidenceListResponse>(
      `${base(caseId)}${query ? `?${query}` : ''}`,
    );
  },

  get: (caseId: string, evidenceId: string) =>
    apiFetch<EvidenceRead>(`${base(caseId)}/${evidenceId}`),

  update: (caseId: string, evidenceId: string, data: EvidenceUpdate) =>
    apiFetch<EvidenceRead>(`${base(caseId)}/${evidenceId}`, {
      method: 'PUT',
      body: data,
    }),

  delete: (caseId: string, evidenceId: string) =>
    apiFetch<void>(`${base(caseId)}/${evidenceId}`, { method: 'DELETE' }),

  preview: (caseId: string, evidenceId: string) =>
    apiFetch<EvidencePreviewResponse>(`${base(caseId)}/${evidenceId}/preview`),

  verify: (caseId: string, evidenceId: string) =>
    apiFetch<EvidenceVerifyResponse>(`${base(caseId)}/${evidenceId}/verify`, {
      method: 'POST',
    }),

  custody: (caseId: string, evidenceId: string, page = 1) =>
    apiFetch<EvidenceCustodyEvent[]>(
      `${base(caseId)}/${evidenceId}/custody?page=${page}`,
    ),

  downloadUrl: (caseId: string, evidenceId: string) =>
    `${env.apiBaseUrl}${base(caseId)}/${evidenceId}/download`,
};
