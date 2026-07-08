import type { ApiError } from '@dcip/types';
import { env } from '@/config/env';

/** Thrown for any non-2xx API response; carries the parsed error envelope. */
export class ApiRequestError extends Error {
  readonly status: number;
  readonly code: string;
  readonly requestId?: string;

  constructor(status: number, body: ApiError | undefined, fallback: string) {
    super(body?.error?.message ?? fallback);
    this.name = 'ApiRequestError';
    this.status = status;
    this.code = body?.error?.code ?? 'unknown_error';
    this.requestId = body?.error?.request_id;
  }
}

type RequestOptions = Omit<RequestInit, 'body'> & { body?: unknown };

/**
 * Thin fetch wrapper that:
 *  - prefixes the configured API base URL,
 *  - sends cookies (httpOnly auth cookies arrive in a later milestone),
 *  - serializes/deserializes JSON,
 *  - normalizes errors into `ApiRequestError`.
 */
export async function apiFetch<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { body, headers, ...rest } = options;
  const url = path.startsWith('http') ? path : `${env.apiBaseUrl}${path}`;

  const response = await fetch(url, {
    credentials: 'include',
    headers: {
      Accept: 'application/json',
      ...(body !== undefined ? { 'Content-Type': 'application/json' } : {}),
      ...headers,
    },
    ...(body !== undefined ? { body: JSON.stringify(body) } : {}),
    ...rest,
  });

  if (response.status === 204) {
    return undefined as T;
  }

  const payload = await response.json().catch(() => undefined);

  if (!response.ok) {
    throw new ApiRequestError(response.status, payload as ApiError, response.statusText);
  }

  return payload as T;
}
