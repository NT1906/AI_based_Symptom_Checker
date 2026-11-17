
import { vi } from "vitest";

export const useRegisterSW = vi.fn(() => ({
  needRefresh: [false, vi.fn()],
  updateServiceWorker: vi.fn(),
}));
