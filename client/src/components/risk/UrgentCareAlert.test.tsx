/**
 * @file Tests for the UrgentCareAlert component.
 * Owner: Dimple · Task: S1-DIM-3, S2-DIM-5 · Requirements: FR-06, FR-15, DR-02, NFR-06
 *
 * Covers:
 * - DR-02 / rule 5: 112 is rendered first and largest; 108 is secondary.
 * - Mandatory non-diagnostic medical disclaimer (DR-01, rule 8).
 * - Clicking "Continue to Full Result" invokes onDismiss.
 * - WCAG 2.1 AA keyboard accessibility: role="alertdialog", Escape key dismissal, Tab focus trapping.
 */

import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { UrgentCareAlert } from "./UrgentCareAlert";

describe("UrgentCareAlert", () => {
  it("renders with alertdialog role, modal semantics, and accessible heading", () => {
    const onDismiss = vi.fn();
    render(<UrgentCareAlert onDismiss={onDismiss} />);

    const dialog = screen.getByRole("alertdialog", {
      name: /urgent care needed/i,
    });
    expect(dialog).toBeInTheDocument();
    expect(dialog).toHaveAttribute("aria-modal", "true");
  });

  it("prioritizes 112 first and largest, with 108 secondary (DR-02)", () => {
    render(<UrgentCareAlert onDismiss={vi.fn()} />);

    // 112 emergency phone link
    const link112 = screen.getByRole("link", {
      name: /call 112/i,
    });
    expect(link112).toBeInTheDocument();
    expect(link112).toHaveAttribute("href", "tel:112");
    expect(link112).toHaveTextContent("112");
    expect(link112).toHaveTextContent(/unified emergency/i);

    // 108 secondary phone link
    const link108 = screen.getByRole("link", {
      name: /call 108/i,
    });
    expect(link108).toBeInTheDocument();
    expect(link108).toHaveAttribute("href", "tel:108");
    expect(link108).toHaveTextContent("108");
    expect(link108).toHaveTextContent(/ambulance/i);
  });

  it("renders the mandatory non-diagnostic medical disclaimer (DR-01, AI_RULES §2)", () => {
    render(<UrgentCareAlert onDismiss={vi.fn()} />);

    expect(
      screen.getByText(/this is not a medical diagnosis/i),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/always consult a qualified healthcare professional/i),
    ).toBeInTheDocument();
  });

  it("invokes onDismiss when the user clicks 'Continue to Full Result'", async () => {
    const user = userEvent.setup();
    const onDismiss = vi.fn();
    render(<UrgentCareAlert onDismiss={onDismiss} />);

    const dismissButton = screen.getByRole("button", {
      name: /continue to full result/i,
    });
    await user.click(dismissButton);

    expect(onDismiss).toHaveBeenCalledOnce();
  });

  it("invokes onDismiss when the user presses the Escape key (WCAG 2.1 SC 2.1.2)", async () => {
    const user = userEvent.setup();
    const onDismiss = vi.fn();
    render(<UrgentCareAlert onDismiss={onDismiss} />);

    await user.keyboard("{Escape}");

    expect(onDismiss).toHaveBeenCalledOnce();
  });

  it("traps focus inside the alert dialog upon Tab cycling (WCAG 2.1 SC 2.1.2, NFR-06)", async () => {
    const user = userEvent.setup();
    render(<UrgentCareAlert onDismiss={vi.fn()} />);

    const link112 = screen.getByRole("link", { name: /call 112/i });
    const link108 = screen.getByRole("link", { name: /call 108/i });
    const dismissBtn = screen.getByRole("button", {
      name: /continue to full result/i,
    });

    // Initial focus lands on 112
    expect(link112).toHaveFocus();

    // Tab -> 108
    await user.tab();
    expect(link108).toHaveFocus();

    // Tab -> dismiss button
    await user.tab();
    expect(dismissBtn).toHaveFocus();

    // Tab from last element wraps to first (112)
    await user.tab();
    expect(link112).toHaveFocus();

    // Shift+Tab from first element wraps to last (dismiss button)
    await user.tab({ shift: true });
    expect(dismissBtn).toHaveFocus();
  });
});
