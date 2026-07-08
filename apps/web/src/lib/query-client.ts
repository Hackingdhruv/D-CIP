import { QueryClient } from '@tanstack/react-query';
import { ApiRequestError } from '@/lib/api-client';

/**
 * Shared TanStack Query client. Auth failures (401) are not retried; transient
 * failures get a small bounded retry. Defaults favor fresh-but-not-chatty data.
 */
export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      gcTime: 5 * 60_000,
      refetchOnWindowFocus: false,
      retry: (failureCount, error) => {
        if (error instanceof ApiRequestError && error.status >= 400 && error.status < 500) {
          return false;
        }
        return failureCount < 2;
      },
    },
    mutations: {
      retry: false,
    },
  },
});
