
/**
 * @file Application-level providers.
 * Owner: Rutva · Task: S2-RUT-3 · Issue: #182
 */
import { QueryClientProvider } from "@tanstack/react-query";
import { RouterProvider } from "react-router-dom";
import { queryClient } from "../lib/queryClient";
import { router } from "./router";
import { PWAUpdatePrompt } from "../components/PWAUpdatePrompt";
import { PWAInstallPrompt } from "../components/PWAInstallPrompt";

/**
 * Wraps the application with its query, routing, and PWA providers.
 *
 * @returns The application provider tree.
 */
export function AppProviders() {
 return (
  <QueryClientProvider client={queryClient}>
    <RouterProvider router={router} />
    <PWAUpdatePrompt />
    <PWAInstallPrompt />
  </QueryClientProvider>
);
}
