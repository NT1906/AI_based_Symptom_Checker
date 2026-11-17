/**
 * @file Application-level providers.
 * Owner: Rutva, Dimple · Tasks: S0-RUT-1, S2-DIM-7 · Requirements: NFR-03, NFR-05, NFR-08, NFR-09
 */
import { QueryClientProvider } from "@tanstack/react-query";
import { RouterProvider } from "react-router-dom";
import { ErrorBoundary } from "../components/layout/ErrorBoundary";
import { queryClient } from "../lib/queryClient";
import { router } from "./router";

/**
 * Wraps the application with its query, routing, and error boundary providers.
 *
 * @returns The application provider tree.
 */
export function AppProviders() {
  return (
    <ErrorBoundary>
      <QueryClientProvider client={queryClient}>
        <RouterProvider router={router} />
      </QueryClientProvider>
    </ErrorBoundary>
  );
}
