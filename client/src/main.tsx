/**
 * @file Client application entry point.
 * Owner: Rutva · Task: S0-RUT-1 · Requirements: NFR-08, NFR-09
 */
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { AppProviders } from "./app/providers";
import "./index.css";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <AppProviders />
  </StrictMode>,
);
