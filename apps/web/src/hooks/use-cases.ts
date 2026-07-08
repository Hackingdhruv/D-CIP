import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { casesApi } from '@/lib/api/cases';
import type {
  CaseAssignRequest,
  CaseCreate,
  CaseNoteCreate,
  CaseNoteUpdate,
  CaseTaskCreate,
  CaseTaskUpdate,
  CaseUpdate,
} from '@/types/case';

export function useImportCasePreview() {
  return useMutation({
    mutationFn: (file: File) => casesApi.importPreview(file),
  });
}

interface ListCasesParams {
  q?: string;
  status?: string;
  priority?: string;
  category?: string;
  isStarred?: boolean;
  includeArchived?: boolean;
  page?: number;
  pageSize?: number;
  enabled?: boolean;
}

export function useCases(params: ListCasesParams = {}) {
  const { enabled = true, ...rest } = params;
  return useQuery({
    queryKey: ['cases', rest],
    queryFn: () => casesApi.list(rest),
    enabled,
  });
}

export function useCase(id: string) {
  return useQuery({
    queryKey: ['cases', id],
    queryFn: () => casesApi.get(id),
    enabled: !!id,
  });
}

export function useCaseActivities(caseId: string) {
  return useQuery({
    queryKey: ['cases', caseId, 'activities'],
    queryFn: () => casesApi.listActivities(caseId),
    enabled: !!caseId,
  });
}

export function useCreateCase() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: CaseCreate) => casesApi.create(data),
    onSuccess: (c) => {
      queryClient.invalidateQueries({ queryKey: ['cases'] });
      toast.success(`Case ${c.referenceNumber} created.`);
    },
  });
}

export function useUpdateCase(id: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: CaseUpdate) => casesApi.update(id, data),
    onSuccess: (c) => {
      queryClient.setQueryData(['cases', id], c);
      queryClient.invalidateQueries({ queryKey: ['cases'] });
      toast.success('Case updated.');
    },
  });
}

export function useDeleteCase() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => casesApi.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['cases'] });
      toast.success('Case deleted.');
    },
  });
}

export function useArchiveCase() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => casesApi.archive(id),
    onSuccess: (c) => {
      queryClient.setQueryData(['cases', c.id], c);
      queryClient.invalidateQueries({ queryKey: ['cases'] });
      toast.success('Case archived.');
    },
  });
}

export function useRestoreCase() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => casesApi.restore(id),
    onSuccess: (c) => {
      queryClient.setQueryData(['cases', c.id], c);
      queryClient.invalidateQueries({ queryKey: ['cases'] });
      toast.success('Case restored.');
    },
  });
}

export function useStarCase() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => casesApi.star(id),
    onSuccess: (c) => {
      queryClient.setQueryData(['cases', c.id], c);
      queryClient.invalidateQueries({ queryKey: ['cases'] });
    },
  });
}

export function useUnstarCase() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => casesApi.unstar(id),
    onSuccess: (c) => {
      queryClient.setQueryData(['cases', c.id], c);
      queryClient.invalidateQueries({ queryKey: ['cases'] });
    },
  });
}

export function useAssignCase(caseId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: CaseAssignRequest) => casesApi.assign(caseId, data),
    onSuccess: (c) => {
      queryClient.setQueryData(['cases', caseId], c);
      toast.success('Team assignments updated.');
    },
  });
}

// ── Tasks ──────────────────────────────────────────────────────────────────────

export function useCreateTask(caseId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: CaseTaskCreate) => casesApi.createTask(caseId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['cases', caseId] });
      toast.success('Task created.');
    },
  });
}

export function useUpdateTask(caseId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ taskId, data }: { taskId: string; data: CaseTaskUpdate }) =>
      casesApi.updateTask(caseId, taskId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['cases', caseId] });
    },
  });
}

export function useDeleteTask(caseId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (taskId: string) => casesApi.deleteTask(caseId, taskId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['cases', caseId] });
      toast.success('Task deleted.');
    },
  });
}

// ── Notes ──────────────────────────────────────────────────────────────────────

export function useCreateNote(caseId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: CaseNoteCreate) => casesApi.createNote(caseId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['cases', caseId] });
      toast.success('Note saved.');
    },
  });
}

export function useUpdateNote(caseId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ noteId, data }: { noteId: string; data: CaseNoteUpdate }) =>
      casesApi.updateNote(caseId, noteId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['cases', caseId] });
      toast.success('Note updated.');
    },
  });
}

export function useDeleteNote(caseId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (noteId: string) => casesApi.deleteNote(caseId, noteId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['cases', caseId] });
      toast.success('Note deleted.');
    },
  });
}
