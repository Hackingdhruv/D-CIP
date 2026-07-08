import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { evidenceApi, uploadEvidenceFiles, type UploadProgress } from '@/lib/api/evidence';
import type { EvidenceUpdate } from '@/types/evidence';

// ── Query keys ────────────────────────────────────────────────────────────────

export const evidenceKeys = {
  all: (caseId: string) => ['evidence', caseId] as const,
  list: (caseId: string, params?: object) =>
    ['evidence', caseId, 'list', params] as const,
  detail: (caseId: string, evidenceId: string) =>
    ['evidence', caseId, evidenceId] as const,
  preview: (caseId: string, evidenceId: string) =>
    ['evidence', caseId, evidenceId, 'preview'] as const,
  custody: (caseId: string, evidenceId: string) =>
    ['evidence', caseId, evidenceId, 'custody'] as const,
};

// ── List ──────────────────────────────────────────────────────────────────────

export function useEvidence(
  caseId: string,
  params: {
    q?: string;
    mimeCategory?: string;
    fileExtension?: string;
    status?: string;
    page?: number;
    pageSize?: number;
  } = {},
) {
  return useQuery({
    queryKey: evidenceKeys.list(caseId, params),
    queryFn: () => evidenceApi.list(caseId, params),
    enabled: Boolean(caseId),
  });
}

// ── Single ────────────────────────────────────────────────────────────────────

export function useEvidenceItem(caseId: string, evidenceId: string) {
  return useQuery({
    queryKey: evidenceKeys.detail(caseId, evidenceId),
    queryFn: () => evidenceApi.get(caseId, evidenceId),
    enabled: Boolean(caseId) && Boolean(evidenceId),
  });
}

export function useEvidencePreview(caseId: string, evidenceId: string | null) {
  return useQuery({
    queryKey: evidenceKeys.preview(caseId, evidenceId ?? ''),
    queryFn: () => evidenceApi.preview(caseId, evidenceId!),
    enabled: Boolean(caseId) && Boolean(evidenceId),
    staleTime: 5 * 60 * 1000, // previews are stable
  });
}

export function useEvidenceCustody(caseId: string, evidenceId: string | null) {
  return useQuery({
    queryKey: evidenceKeys.custody(caseId, evidenceId ?? ''),
    queryFn: () => evidenceApi.custody(caseId, evidenceId!),
    enabled: Boolean(caseId) && Boolean(evidenceId),
  });
}

// ── Upload ────────────────────────────────────────────────────────────────────

export function useUploadEvidence(caseId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      files,
      onProgress,
    }: {
      files: File[];
      onProgress?: (updates: UploadProgress[]) => void;
    }) => uploadEvidenceFiles(caseId, files, onProgress),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: evidenceKeys.all(caseId) });
    },
  });
}

// ── Update ────────────────────────────────────────────────────────────────────

export function useUpdateEvidence(caseId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      evidenceId,
      data,
    }: {
      evidenceId: string;
      data: EvidenceUpdate;
    }) => evidenceApi.update(caseId, evidenceId, data),
    onSuccess: (_, { evidenceId }) => {
      qc.invalidateQueries({ queryKey: evidenceKeys.all(caseId) });
      qc.invalidateQueries({ queryKey: evidenceKeys.detail(caseId, evidenceId) });
    },
  });
}

// ── Delete ────────────────────────────────────────────────────────────────────

export function useDeleteEvidence(caseId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (evidenceId: string) => evidenceApi.delete(caseId, evidenceId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: evidenceKeys.all(caseId) });
    },
  });
}

// ── Verify hash ───────────────────────────────────────────────────────────────

export function useVerifyEvidence(caseId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (evidenceId: string) => evidenceApi.verify(caseId, evidenceId),
    onSuccess: (_, evidenceId) => {
      qc.invalidateQueries({
        queryKey: evidenceKeys.custody(caseId, evidenceId),
      });
    },
  });
}
