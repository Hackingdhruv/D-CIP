/** Standard error envelope returned by every backend error handler. */
export interface ApiError {
  error: {
    code: string;
    message: string;
    /** Present for 422 validation errors. */
    details?: Array<{ field: string; message: string }>;
    /** Correlates the response with backend logs. */
    request_id: string;
  };
}

/** Cursor/offset pagination envelope used by list endpoints. */
export interface Paginated<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}

/** Response shape of GET /api/v1/health. */
export interface HealthStatus {
  status: 'ok' | 'degraded' | 'error';
  checks: Record<string, { status: 'ok' | 'error'; detail?: string }>;
}

/** Response shape of GET /api/v1/version. */
export interface VersionInfo {
  name: string;
  version: string;
  environment: string;
  commit?: string;
}
