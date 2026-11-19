
/**
 * @file Application-level providers.
 * Owner: Rutva, Dimple · Tasks: S0-RUT-1, S2-RUT-3, S2-DIM-7, S2-NIS-15 (#312)
 * Requirements: NFR-03, NFR-05, NFR-08, NFR-09
 */
import { useEffect } from "react";
import { QueryClientProvider } from "@tanstack/react-query";
import { RouterProvider } from "react-router-dom";
import { ErrorBoundary } from "../components/layout/ErrorBoundary";
import { PWAInstallPrompt } from "../components/PWAInstallPrompt";
import { PWAUpdatePrompt } from "../components/PWAUpdatePrompt";
import { queryClient } from "../lib/queryClient";
import { useAuthStore } from "../stores/authStore";
import { router } from "./router";

/**
 * Restores a logged-in session from the auth cookie once on start-up, so
 * every page knows who is logged in after a reload (the store is memory only).
 */
function useRestoreSession(): void {
  useEffect(() => {
    const { status, loadCurrentUser } = useAuthStore.getState();
    if (status === "idle") {
      void loadCurrentUser().catch(() => undefined);
    }
  }, []);
}

/**
 * Wraps the application with query, routing, error boundary,
 * and PWA prompt providers.
 *
 * @returns The application provider tree.
 */
export function AppProviders() {
  useRestoreSession();
  return (
    <ErrorBoundary>
      <QueryClientProvider client={queryClient}>
        <RouterProvider router={router} />
        <PWAUpdatePrompt />
        <PWAInstallPrompt />
      </QueryClientProvider>
    </ErrorBoundary>
  );
}
