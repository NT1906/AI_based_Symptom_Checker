/**
 * @file TanStack Query client configuration.
 * Owner: Rutva · Task: S0-RUT-1 · Requirements: NFR-08, NFR-09
 */
import { QueryClient } from "@tanstack/react-query";

/**
 * Shared query client for server-state caching and request lifecycle.
 * Retries failed queries once and disables focus-triggered refetching.
 */
export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      refetchOnWindowFocus: false,
      staleTime: 30_000,
    },
  },
});
