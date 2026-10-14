
/**
 * @file Tests for RiskBadge and UrgentCareAlert components.
 * Owner: Dimple · Task: S1-DIM-3 · Requirements: FR-06, FR-15, DR-02
 *
 * RiskBadge covers: all three risk levels render with correct label.
 * UrgentCareAlert covers:
 * - 112 is present and displayed before 108 in the DOM (DR-02).
 * - Disclaimer text is present (AI_RULES.md §2 rule 8).
 * - onDismiss callback fires when "Continue" is clicked.
 * - tel: links are correct for both numbers.
 */

import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { RiskBadge, type RiskLevel } from "./RiskBadge";
import { UrgentCareAlert } from "./UrgentCareAlert";

// ---------------------------------------------------------------------------
// RiskBadge
// ---------------------------------------------------------------------------
describe("RiskBadge", () => {
  const levels: RiskLevel[] = ["SELF_CARE", "CONSULT_DOCTOR", "URGENT"];

  it.each(levels)("renders with accessible label for %s", (level) => {
    render(<RiskBadge level={level} />);
    expect(screen.getByRole("status")).toBeInTheDocument();
    expect(screen.getByRole("status").getAttribute("aria-label")).toMatch(
      /risk level/i
    );
  });

  it("SELF_CARE shows 'Self-Care' text", () => {
    render(<RiskBadge level="SELF_CARE" />);
    expect(screen.getByText("Self-Care")).toBeInTheDocument();
  });

  it("CONSULT_DOCTOR shows 'Consult a Doctor' text", () => {
    render(<RiskBadge level="CONSULT_DOCTOR" />);
    expect(screen.getByText("Consult a Doctor")).toBeInTheDocument();
  });

  it("URGENT shows 'Urgent Care Needed' text", () => {
    render(<RiskBadge level="URGENT" />);
    expect(screen.getByText("Urgent Care Needed")).toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// UrgentCareAlert
// ---------------------------------------------------------------------------
describe("UrgentCareAlert", () => {
  it("renders as an alertdialog with a title", () => {
    render(<UrgentCareAlert onDismiss={vi.fn()} />);
    expect(
      screen.getByRole("alertdialog", { name: /urgent care needed/i })
    ).toBeInTheDocument();
  });

  it("112 appears before 108 in the DOM (DR-02 — 112 must be shown first)", () => {
    render(<UrgentCareAlert onDismiss={vi.fn()} />);
    const links = screen.getAllByRole("link");
    const numbers = links.map((l) => l.getAttribute("href") ?? "");
    const idx112 = numbers.findIndex((h) => h === "tel:112");
    const idx108 = numbers.findIndex((h) => h === "tel:108");
    expect(idx112).toBeGreaterThanOrEqual(0);
    expect(idx108).toBeGreaterThanOrEqual(0);
    expect(idx112).toBeLessThan(idx108);
  });

  it("112 link has correct tel: href", () => {
    render(<UrgentCareAlert onDismiss={vi.fn()} />);
    const link112 = screen.getByRole("link", { name: /call 112/i });
    expect(link112).toHaveAttribute("href", "tel:112");
  });

  it("108 link has correct tel: href", () => {
    render(<UrgentCareAlert onDismiss={vi.fn()} />);
    const link108 = screen.getByRole("link", { name: /call 108/i });
    expect(link108).toHaveAttribute("href", "tel:108");
  });

  it("shows mandatory disclaimer text (AI_RULES.md §2 rule 8)", () => {
    render(<UrgentCareAlert onDismiss={vi.fn()} />);
    expect(
      screen.getByText(/not a medical diagnosis/i)
    ).toBeInTheDocument();
  });

  it("calls onDismiss when Continue button is clicked", async () => {
    const user = userEvent.setup();
    const onDismiss = vi.fn();
    render(<UrgentCareAlert onDismiss={onDismiss} />);
    await user.click(screen.getByRole("button", { name: /continue to full result/i }));
    expect(onDismiss).toHaveBeenCalledOnce();
  });
});



