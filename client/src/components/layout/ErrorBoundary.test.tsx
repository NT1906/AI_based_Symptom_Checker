/**
 * @file Tests for the ErrorBoundary component.
 * Owner: Dimple · Task: S2-DIM-7 · Requirements: NFR-03, NFR-05, DR-01, DR-02
 */

import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import * as sentry from "../../services/sentry";
import { ErrorBoundary } from "./ErrorBoundary";

/** Component that intentionally throws an error for testing boundaries. */
function ProblemChild({ shouldThrow = false }: { shouldThrow?: boolean }) {
  if (shouldThrow) {
    throw new Error("Simulated rendering explosion in user@test.com session");
  }
  return <div>Safe Child Content</div>;
}

describe("ErrorBoundary", () => {
  beforeEach(() => {
    vi.spyOn(console, "error").mockImplementation(() => {});
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("renders children normally when no exception occurs", () => {
    render(
      <ErrorBoundary>
        <ProblemChild shouldThrow={false} />
      </ErrorBoundary>,
    );

    expect(screen.getByText("Safe Child Content")).toBeInTheDocument();
  });

  it("catches rendering errors, renders fallback alert, and notifies Sentry", () => {
    const captureSpy = vi.spyOn(sentry, "captureException");
    const onError = vi.fn();

    render(
      <ErrorBoundary onError={onError}>
        <ProblemChild shouldThrow={true} />
      </ErrorBoundary>,
    );

    // Fallback UI is displayed
    expect(screen.getByRole("alert")).toBeInTheDocument();
    expect(screen.getByText(/something went wrong/i)).toBeInTheDocument();

    // Sentry capture was called
    expect(captureSpy).toHaveBeenCalledOnce();
    expect(onError).toHaveBeenCalledOnce();

    // Emergency 112 guidance is present (DR-02)
    expect(screen.getByText(/112 \(unified emergency\)/i)).toBeInTheDocument();

    // Mandatory non-diagnostic disclaimer is present (DR-01)
    expect(
      screen.getByText(/not provide a medical diagnosis/i),
    ).toBeInTheDocument();
  });

  it("resets error state when clicking Try Again", async () => {
    const user = userEvent.setup();

    function FlakyComponent({ attempts }: { attempts: number }) {
      if (attempts === 0) {
        throw new Error("Transient error");
      }
      return <div>Recovered Successfully</div>;
    }

    const { rerender } = render(
      <ErrorBoundary>
        <FlakyComponent attempts={0} />
      </ErrorBoundary>,
    );

    expect(screen.getByRole("alert")).toBeInTheDocument();

    // Rerender with recovered state, then click Try Again
    rerender(
      <ErrorBoundary>
        <FlakyComponent attempts={1} />
      </ErrorBoundary>,
    );

    await user.click(screen.getByRole("button", { name: /try again/i }));

    expect(screen.getByText("Recovered Successfully")).toBeInTheDocument();
  });
});
