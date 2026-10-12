import { QueryClient } from "@tanstack/react-query";

/** Shared query client for server-state caching and request lifecycle. */
export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      refetchOnWindowFocus: false,
      staleTime: 30_000,
    },
  },
});
