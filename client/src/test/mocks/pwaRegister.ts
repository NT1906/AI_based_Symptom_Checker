/**
 * @file Vitest mock for the virtual PWA service-worker registration module.
 */
import { vi } from "vitest";

export const useRegisterSW = vi.fn(() => ({
  needRefresh: [false, vi.fn()],
  updateServiceWorker: vi.fn(),
}));
