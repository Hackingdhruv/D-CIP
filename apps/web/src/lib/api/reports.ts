import { apiFetch } from '@/lib/api-client'
import type {
  CreateReportRequest,
  GenerateReportRequest,
  ReportListItem,
  ReportRead,
  ReportTypeDescriptor,
  TemplateDescriptor,
} from '@/types/report'

const BASE = '/v1'

export const reportsApi = {
  // Metadata
  getTemplates: (): Promise<TemplateDescriptor[]> =>
    apiFetch<TemplateDescriptor[]>(`${BASE}/report-templates`),

  getReportTypes: (): Promise<ReportTypeDescriptor[]> =>
    apiFetch<ReportTypeDescriptor[]>(`${BASE}/report-types`),

  // Case-scoped CRUD
  create: (caseId: string, body: CreateReportRequest): Promise<ReportRead> =>
    apiFetch<ReportRead>(`${BASE}/cases/${caseId}/reports`, {
      method: 'POST',
      body,
    }),

  list: (caseId: string): Promise<ReportListItem[]> =>
    apiFetch<ReportListItem[]>(`${BASE}/cases/${caseId}/reports`),

  get: (caseId: string, reportId: string): Promise<ReportRead> =>
    apiFetch<ReportRead>(`${BASE}/cases/${caseId}/reports/${reportId}`),

  delete: (caseId: string, reportId: string): Promise<void> =>
    apiFetch<void>(`${BASE}/cases/${caseId}/reports/${reportId}`, {
      method: 'DELETE',
    }),

  // Generation & lifecycle
  generate: (
    caseId: string,
    reportId: string,
    body?: GenerateReportRequest
  ): Promise<ReportRead> =>
    apiFetch<ReportRead>(
      `${BASE}/cases/${caseId}/reports/${reportId}/generate`,
      { method: 'POST', body }
    ),

  publish: (caseId: string, reportId: string): Promise<ReportRead> =>
    apiFetch<ReportRead>(
      `${BASE}/cases/${caseId}/reports/${reportId}/publish`,
      { method: 'POST' }
    ),

  newVersion: (
    caseId: string,
    reportId: string,
    body?: GenerateReportRequest
  ): Promise<ReportRead> =>
    apiFetch<ReportRead>(
      `${BASE}/cases/${caseId}/reports/${reportId}/version`,
      { method: 'POST', body }
    ),

  // Export URLs (download links — open in new tab or fetch)
  exportUrl: (
    caseId: string,
    reportId: string,
    format: 'pdf' | 'docx' | 'html' | 'json'
  ): string => `${BASE}/cases/${caseId}/reports/${reportId}/export/${format}`,

  // Global listing
  listAll: (page = 1, pageSize = 20): Promise<ReportListItem[]> =>
    apiFetch<ReportListItem[]>(
      `${BASE}/reports?page=${page}&page_size=${pageSize}`
    ),
}
