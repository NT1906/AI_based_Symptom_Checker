/**
 * @file MSW test server.
 * Owner: Rutva · Task: S0-RUT-1 · Requirements: NFR-08, NFR-09
 */
import { setupServer } from "msw/node";

/** Shared Mock Service Worker server for API tests. */
export const server = setupServer();
