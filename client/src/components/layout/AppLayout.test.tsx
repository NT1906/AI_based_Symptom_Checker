/**
 * @file Unit tests for AppLayout component and medical safety disclaimer compliance.
 *
 * Verifies the happy path, edge cases, and safety compliance:
 * - Happy path: Renders children, landmark elements, emergency phone button, and persistent disclaimer.
 * - Edge cases: Custom title, custom emergency number, offline status banner, and start-over actions.
 * - Safety case: Confirms mandatory non-diagnostic disclaimer text (DR-01) is strictly present.
 *
 * Owner: Mann (Frontend + Deployment · Testing) · Task: S0-MAN-1 · Requirements: DR-01, NFR-06
 */

import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { AppLayout, MANDATORY_DISCLAIMER_TEXT } from "./AppLayout";

describe("AppLayout", () => {
  it("renders main children and core landmark regions (happy path)", () => {
    render(
      <AppLayout>
        <div data-testid="test-content">Assessment in progress</div>
      </AppLayout>,
    );

    // Verify main content is rendered
    expect(screen.getByTestId("test-content")).toBeInTheDocument();
    expect(screen.getByText("Assessment in progress")).toBeInTheDocument();

    // Verify semantic landmarks exist
    expect(screen.getByRole("banner")).toBeInTheDocument();
    expect(screen.getByRole("main")).toBeInTheDocument();
    expect(screen.getByRole("contentinfo")).toBeInTheDocument();

    // Verify default title
    expect(
      screen.getByRole("heading", { level: 1, name: /AI-Based Symptom Checker/i }),
    ).toBeInTheDocument();

    // Verify default emergency phone link
    const emergencyLinks = screen.getAllByRole("link", { name: /112/i });
    expect(emergencyLinks.length).toBeGreaterThan(0);
    expect(emergencyLinks[0]).toHaveAttribute("href", "tel:112");
  });

  it("strictly renders the mandatory medical disclaimer text (DR-01 safety rule)", () => {
    render(
      <AppLayout>
        <p>Symptom details</p>
      </AppLayout>,
    );

    // The mandatory non-diagnostic disclaimer must be present on every screen
    expect(screen.getByText(MANDATORY_DISCLAIMER_TEXT)).toBeInTheDocument();

    // Must clearly state it is not a medical diagnosis
    expect(screen.getByText(/not provide a medical diagnosis/i)).toBeInTheDocument();
  });

  it("handles custom titles and subtitles (edge case)", () => {
    render(
      <AppLayout
        title="Emergency Triage Review"
        subtitle="Reviewing reported cardiovascular red flags"
      >
        <p>Content</p>
      </AppLayout>,
    );

    expect(
      screen.getByRole("heading", { level: 1, name: "Emergency Triage Review" }),
    ).toBeInTheDocument();
    expect(screen.getByText("Reviewing reported cardiovascular red flags")).toBeInTheDocument();
  });

  it("supports custom emergency phone numbers (edge case)", () => {
    render(
      <AppLayout emergencyNumber="911">
        <p>Content</p>
      </AppLayout>,
    );

    const emergencyButton = screen.getByRole("link", {
      name: /Call emergency services at 911/i,
    });
    expect(emergencyButton).toHaveAttribute("href", "tel:911");
  });

  it("renders offline banner when isOffline is true (edge case)", () => {
    const { rerender } = render(
      <AppLayout isOffline={false}>
        <p>Content</p>
      </AppLayout>,
    );

    expect(screen.queryByRole("status")).not.toBeInTheDocument();

    rerender(
      <AppLayout isOffline={true}>
        <p>Content</p>
      </AppLayout>,
    );

    const alert = screen.getByRole("status");
    expect(alert).toBeInTheDocument();
    expect(alert).toHaveTextContent(/You are currently offline/i);
  });

  it("renders and triggers the Start Over button when enabled", () => {
    const handleStartOver = vi.fn();

    render(
      <AppLayout showStartOver={true} onStartOver={handleStartOver}>
        <p>Content</p>
      </AppLayout>,
    );

    const startOverBtn = screen.getByRole("button", {
      name: /Start a new assessment from scratch/i,
    });
    expect(startOverBtn).toBeInTheDocument();

    fireEvent.click(startOverBtn);
    expect(handleStartOver).toHaveBeenCalledTimes(1);
  });

  it("provides an accessible skip-to-content link (NFR-06 accessibility)", () => {
    render(
      <AppLayout>
        <p>Content</p>
      </AppLayout>,
    );

    const skipLink = screen.getByRole("link", { name: /Skip to main content/i });
    expect(skipLink).toBeInTheDocument();
    expect(skipLink).toHaveAttribute("href", "#main-content");
  });
});
