/**
 * @file Unit tests for PrivacyPolicyPage.
 * Owner: Dimple · Task: S2-DIM-3 · Requirements: DR-06, DR-08
 *
 * Verifies:
 * - Rendering of statutory policy sections and DPDP Act 2023 disclosures.
 * - Active policy version display (CURRENT_POLICY_VERSION).
 * - Embedding of interactive DataExportDelete privacy controls.
 * - Mandatory medical disclaimer compliance (AI_RULES.md §2 rule 8).
 * - Navigation link back to home.
 */

import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";

import { CURRENT_POLICY_VERSION } from "../services/consentApi";
import PrivacyPolicyPage from "./PrivacyPolicyPage";

describe("PrivacyPolicyPage", () => {
  it("renders page title, active version, and statutory notice", () => {
    render(
      <MemoryRouter>
        <PrivacyPolicyPage />
      </MemoryRouter>,
    );

    expect(
      screen.getByRole("heading", { name: /privacy policy & data rights/i, level: 1 }),
    ).toBeInTheDocument();
    expect(screen.getByRole("status")).toHaveTextContent(
      `Policy Version ${CURRENT_POLICY_VERSION}`,
    );
    expect(
      screen.getAllByText(/Digital Personal Data Protection Act, 2023/i).length,
    ).toBeGreaterThanOrEqual(1);
  });

  it("renders mandatory medical disclaimer notices", () => {
    render(
      <MemoryRouter>
        <PrivacyPolicyPage />
      </MemoryRouter>,
    );

    const disclaimers = screen.getAllByText(/this is not a medical diagnosis/i);
    expect(disclaimers.length).toBeGreaterThanOrEqual(1);
  });

  it("renders interactive data export and deletion controls", () => {
    render(
      <MemoryRouter>
        <PrivacyPolicyPage />
      </MemoryRouter>,
    );

    expect(
      screen.getByRole("heading", { name: /exercise your statutory rights/i }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /download data export/i }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /permanently delete all data/i }),
    ).toBeInTheDocument();
  });

  it("renders back to home navigation link", () => {
    render(
      <MemoryRouter>
        <PrivacyPolicyPage />
      </MemoryRouter>,
    );

    const backLink = screen.getByRole("link", { name: /back to home/i });
    expect(backLink).toBeInTheDocument();
    expect(backLink).toHaveAttribute("href", "/");
  });
});
