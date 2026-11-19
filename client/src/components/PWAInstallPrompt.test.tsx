/**
 * @file Unit tests for the PWA installation prompt, including install,
 * dismissal, and browser event handling.
 */
import { act, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { PWAInstallPrompt } from "./PWAInstallPrompt";

describe("PWAInstallPrompt", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("does not show the prompt when installation is unavailable", () => {
    render(<PWAInstallPrompt />);

    expect(screen.queryByText("Install this app for a better experience."))
      .not.toBeInTheDocument();
  });

  it("shows the prompt when the browser supports installation", () => {
    render(<PWAInstallPrompt />);

    const event = new Event("beforeinstallprompt", { cancelable: true });

    Object.assign(event, {
      platforms: ["web"],
      prompt: vi.fn().mockResolvedValue(undefined),
      userChoice: Promise.resolve({
        outcome: "accepted",
        platform: "web",
      }),
    });

    act(() => {
      window.dispatchEvent(event);
    });

    expect(event.defaultPrevented).toBe(true);
    expect(screen.getByText("Install this app for a better experience."))
      .toBeInTheDocument();
  });

  it("calls the browser installation prompt when Install is clicked", async () => {
    render(<PWAInstallPrompt />);

    const prompt = vi.fn().mockResolvedValue(undefined);
    const event = new Event("beforeinstallprompt", { cancelable: true });

    Object.assign(event, {
      platforms: ["web"],
      prompt,
      userChoice: Promise.resolve({
        outcome: "accepted",
        platform: "web",
      }),
    });

    act(() => {
      window.dispatchEvent(event);
    });

    await act(async () => {
      fireEvent.click(screen.getByRole("button", { name: "Install" }));
    });

    expect(prompt).toHaveBeenCalledTimes(1);
    expect(screen.queryByText("Install this app for a better experience."))
      .not.toBeInTheDocument();
  });

  it("hides the prompt when Later is clicked", () => {
    render(<PWAInstallPrompt />);

    const event = new Event("beforeinstallprompt", { cancelable: true });

    Object.assign(event, {
      platforms: ["web"],
      prompt: vi.fn(),
      userChoice: Promise.resolve({
        outcome: "dismissed",
        platform: "web",
      }),
    });

    act(() => {
      window.dispatchEvent(event);
    });

    fireEvent.click(screen.getByRole("button", { name: "Later" }));

    expect(screen.queryByText("Install this app for a better experience."))
      .not.toBeInTheDocument();
  });

  it("hides the prompt after the app is installed", () => {
    render(<PWAInstallPrompt />);

    const event = new Event("beforeinstallprompt", { cancelable: true });

    Object.assign(event, {
      platforms: ["web"],
      prompt: vi.fn(),
      userChoice: Promise.resolve({
        outcome: "accepted",
        platform: "web",
      }),
    });

    act(() => {
      window.dispatchEvent(event);
    });

    act(() => {
      window.dispatchEvent(new Event("appinstalled"));
    });

    expect(screen.queryByText("Install this app for a better experience."))
      .not.toBeInTheDocument();
  });
});
