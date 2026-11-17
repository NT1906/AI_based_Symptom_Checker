/**
 * @file Unit tests for the PWA update prompt, including update activation
 * and dismissal behavior.
 */
import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { useRegisterSW } from "virtual:pwa-register/react";
import { PWAUpdatePrompt } from "./PWAUpdatePrompt";

vi.mock("virtual:pwa-register/react", () => ({
  useRegisterSW: vi.fn(),
}));

describe("PWAUpdatePrompt", () => {
  const setNeedRefresh = vi.fn();
  const updateServiceWorker = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();

    vi.mocked(useRegisterSW).mockReturnValue({
      needRefresh: [true, setNeedRefresh],
      updateServiceWorker,
    } as never);
  });

  it("shows the update notification when an update is available", () => {
    render(<PWAUpdatePrompt />);

    expect(screen.getByText("A new version is available.")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Update" })).toBeInTheDocument();
  });

  it("dismisses the notification when Later is clicked", () => {
    render(<PWAUpdatePrompt />);

    fireEvent.click(screen.getByRole("button", { name: "Later" }));

    expect(setNeedRefresh).toHaveBeenCalledWith(false);
  });

  it("activates the new service worker when Update is clicked", () => {
    render(<PWAUpdatePrompt />);

    fireEvent.click(screen.getByRole("button", { name: "Update" }));

    expect(updateServiceWorker).toHaveBeenCalledWith(true);
  });

  it("does not render when no update is available", () => {
    vi.mocked(useRegisterSW).mockReturnValue({
      needRefresh: [false, setNeedRefresh],
      updateServiceWorker,
    } as never);

    render(<PWAUpdatePrompt />);

    expect(screen.queryByText("A new version is available.")).not.toBeInTheDocument();
  });
});
