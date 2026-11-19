/**
 * @file Client application entry point.
 * Owner: Rutva, Dimple · Tasks: S0-RUT-1, S2-DIM-7 · Requirements: NFR-05, NFR-08, NFR-09
 */
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { AppProviders } from "./app/providers";
import { initSentry } from "./services/sentry";
import "./index.css";

// Initialize Sentry error telemetry (disabled automatically if VITE_SENTRY_DSN is absent)
initSentry();

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <AppProviders />
  </StrictMode>,
);
