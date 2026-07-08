import { apiFetch } from '@/lib/api-client'
import type {
  ExecutiveDashboard,
  IntelligenceDashboard,
  InvestigatorDashboard,
  OperationsDashboard,
} from '@/types/dashboard'

const BASE = '/v1/dashboard'

export const dashboardApi = {
  executive: (): Promise<ExecutiveDashboard> =>
    apiFetch<ExecutiveDashboard>(`${BASE}/executive`),

  intelligence: (): Promise<IntelligenceDashboard> =>
    apiFetch<IntelligenceDashboard>(`${BASE}/intelligence`),

  operations: (): Promise<OperationsDashboard> =>
    apiFetch<OperationsDashboard>(`${BASE}/operations`),

  investigator: (): Promise<InvestigatorDashboard> =>
    apiFetch<InvestigatorDashboard>(`${BASE}/investigator`),
}
