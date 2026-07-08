import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { reportsApi } from '@/lib/api/reports'
import type { CreateReportRequest, GenerateReportRequest } from '@/types/report'

const KEY = (caseId: string) => ['reports', caseId]
const REPORT_KEY = (caseId: string, reportId: string) => ['report', caseId, reportId]

export function useReports(caseId: string) {
  return useQuery({
    queryKey: KEY(caseId),
    queryFn: () => reportsApi.list(caseId),
    staleTime: 30_000,
  })
}

export function useReport(caseId: string, reportId: string) {
  return useQuery({
    queryKey: REPORT_KEY(caseId, reportId),
    queryFn: () => reportsApi.get(caseId, reportId),
    enabled: !!reportId,
    staleTime: 30_000,
  })
}

export function useCreateReport(caseId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: CreateReportRequest) => reportsApi.create(caseId, body),
    onSuccess: () => qc.invalidateQueries({ queryKey: KEY(caseId) }),
  })
}

export function useGenerateReport(caseId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ reportId, body }: { reportId: string; body?: GenerateReportRequest }) =>
      reportsApi.generate(caseId, reportId, body),
    onSuccess: (data) => {
      qc.invalidateQueries({ queryKey: KEY(caseId) })
      qc.setQueryData(REPORT_KEY(caseId, data.id), data)
    },
  })
}

export function usePublishReport(caseId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (reportId: string) => reportsApi.publish(caseId, reportId),
    onSuccess: (data) => {
      qc.invalidateQueries({ queryKey: KEY(caseId) })
      qc.setQueryData(REPORT_KEY(caseId, data.id), data)
    },
  })
}

export function useDeleteReport(caseId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (reportId: string) => reportsApi.delete(caseId, reportId),
    onSuccess: () => qc.invalidateQueries({ queryKey: KEY(caseId) }),
  })
}

export function useNewVersion(caseId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ reportId, body }: { reportId: string; body?: GenerateReportRequest }) =>
      reportsApi.newVersion(caseId, reportId, body),
    onSuccess: () => qc.invalidateQueries({ queryKey: KEY(caseId) }),
  })
}

export function useReportTemplates() {
  return useQuery({
    queryKey: ['report-templates'],
    queryFn: () => reportsApi.getTemplates(),
    staleTime: 300_000,
  })
}

export function useReportTypes() {
  return useQuery({
    queryKey: ['report-types'],
    queryFn: () => reportsApi.getReportTypes(),
    staleTime: 300_000,
  })
}

export function useAllReports(page = 1) {
  return useQuery({
    queryKey: ['reports-all', page],
    queryFn: () => reportsApi.listAll(page),
    staleTime: 60_000,
  })
}
