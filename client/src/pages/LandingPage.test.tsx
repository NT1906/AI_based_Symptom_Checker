/**
 * @file Tests for LandingPage — disclaimer display and start flow.
 * Owner: Dimple · Task: S1-DIM-2 · Requirements: DR-01
 *
 * Covers:
 * - Disclaimer is visible on first render (DR-01).
 * - "Start Symptom Check" button renders initially.
 * - Clicking Start shows the consent modal.
 * - Declining consent shows the "declined" state and a go-back button.
 * - Emergency number 112 is present in the disclaimer.
 */

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { describe, expect, it } from "vitest";
import LandingPage from "./LandingPage";

/** Renders LandingPage inside MemoryRouter + QueryClientProvider. */
function renderLanding() {
  const qc = new QueryClient({
    defaultOptions: { mutations: { retry: false } },
  });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={["/"]}>
        <Routes>
          <Route path="/" element={<LandingPage />} />
          <Route path="/chat" element={<div>Chat page</div>} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>
  );
}

describe("LandingPage", () => {
  it("shows the medical disclaimer on first render (DR-01)", () => {
    renderLanding();
    expect(screen.getByRole("note", { name: /medical disclaimer/i })).toBeInTheDocument();
    // Disclaimer text appears in both the card and the persistent footer (DR-01 requires both).
    expect(screen.getAllByText(/not a medical diagnosis/i).length).toBeGreaterThanOrEqual(2);
  });

  it("shows emergency number 112 in the disclaimer", () => {
    renderLanding();
    const disclaimer = screen.getByRole("note", { name: /medical disclaimer/i });
    expect(within(disclaimer).getByText(/112/)).toBeInTheDocument();
  });

  it("shows the Start button initially", () => {
    renderLanding();
    expect(
      screen.getByRole("button", { name: /start symptom check/i })
    ).toBeInTheDocument();
  });

  it("clicking Start opens the consent modal", async () => {
    const user = userEvent.setup();
    renderLanding();
    await user.click(screen.getByRole("button", { name: /start symptom check/i }));
    expect(
      screen.getByRole("dialog", { name: /your consent is required/i })
    ).toBeInTheDocument();
  });

  it("declining consent shows the declined state and go-back option", async () => {
    const user = userEvent.setup();
    renderLanding();
    await user.click(screen.getByRole("button", { name: /start symptom check/i }));
    await user.click(screen.getByRole("button", { name: /decline/i }));

    expect(screen.getByRole("alert")).toBeInTheDocument();
    expect(screen.getByRole("alert")).toHaveTextContent(/need to agree/i);
    expect(screen.getByRole("button", { name: /go back/i })).toBeInTheDocument();
  });

  it("go-back after decline returns to the disclaimer step", async () => {
    const user = userEvent.setup();
    renderLanding();
    await user.click(screen.getByRole("button", { name: /start symptom check/i }));
    await user.click(screen.getByRole("button", { name: /decline/i }));
    await user.click(screen.getByRole("button", { name: /go back/i }));

    expect(
      screen.getByRole("button", { name: /start symptom check/i })
    ).toBeInTheDocument();
  });
});
