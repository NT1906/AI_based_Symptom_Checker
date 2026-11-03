/**
 * @file Unit test suite for RiskBadge component.
 *
 * Covers:
 * - Happy path rendering for SELF_CARE, CONSULT_DOCTOR, and URGENT.
 * - Accessible landmarks and ARIA status attributes (NFR-06, WCAG 2.1 AA).
 * - Fallback behavior for invalid or edge case risk levels.
 * - Custom className propagation.
 *
 * Owner: Mann (Frontend + Deployment · Testing) · Task: S1-MAN-3 · Requirements: FR-06, FR-15, DR-02, NFR-06
 */

import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { RiskBadge, getRiskConfig } from "./RiskBadge";
import type { RiskLevel } from "./types";

describe("RiskBadge", () => {
  it("renders SELF_CARE tier badge with accessible status and icon", () => {
    render(<RiskBadge level="SELF_CARE" />);

    const badge = screen.getByRole("status");
    expect(badge).toBeInTheDocument();
    expect(badge).toHaveAttribute("aria-label", "Risk level: Self-Care");
    expect(badge).toHaveTextContent("Self-Care");
    expect(badge).toHaveTextContent("🏠");
  });

  it("renders CONSULT_DOCTOR tier badge with accessible status and icon", () => {
    render(<RiskBadge level="CONSULT_DOCTOR" />);

    const badge = screen.getByRole("status");
    expect(badge).toBeInTheDocument();
    expect(badge).toHaveAttribute("aria-label", "Risk level: Consult a Doctor");
    expect(badge).toHaveTextContent("Consult a Doctor");
    expect(badge).toHaveTextContent("🩺");
  });

  it("renders URGENT tier badge with accessible status and icon", () => {
    render(<RiskBadge level="URGENT" />);

    const badge = screen.getByRole("status");
    expect(badge).toBeInTheDocument();
    expect(badge).toHaveAttribute("aria-label", "Risk level: Urgent Care Needed");
    expect(badge).toHaveTextContent("Urgent Care Needed");
    expect(badge).toHaveTextContent("🚨");
  });

  it("applies custom CSS class names to the badge container", () => {
    render(<RiskBadge level="SELF_CARE" className="custom-test-class" />);

    const badge = screen.getByRole("status");
    expect(badge.className).toContain("custom-test-class");
  });

  it("safely falls back to CONSULT_DOCTOR configuration on unexpected level", () => {
    // Edge case: unexpected level at runtime
    const fallbackConfig = getRiskConfig("UNKNOWN_TIER" as unknown as RiskLevel);
    expect(fallbackConfig.label).toBe("Consult a Doctor");

    render(<RiskBadge level={"UNKNOWN_TIER" as unknown as RiskLevel} />);
    const badge = screen.getByRole("status");
    expect(badge).toHaveTextContent("Consult a Doctor");
  });
});
