/**
 * @file Unit tests for SelfCareGuidanceCard component.
 * Owner: Dimple · Task: S2-DIM-2 · Requirements: idea §8, DR-01, DR-05
 *
 * Verifies:
 * - Happy path: low-risk result displays appropriate self-care and warning cards.
 * - Strict risk gating: CONSULT_DOCTOR and URGENT results return null (never show low-risk cards).
 * - Edge cases: missing or incomplete guidance advice falls back to clinical defaults.
 * - Knowledge service integration: supports generalAdvice, whenToSeekCare, and monitoringTips.
 * - Failure handling: guidance retrieval error displays a safe fallback notice.
 * - Medical-safety: disclaimer present, "low risk != zero risk" reminder, 112 emergency advice.
 * - Accessibility: semantic landmarks, accessible status badges, interactive button triggers.
 */

import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import {
  SelfCareGuidanceCard,
  DEFAULT_SELF_CARE_ADVICE,
  DEFAULT_WARNING_SIGNS,
} from "./SelfCareGuidanceCard";

describe("SelfCareGuidanceCard", () => {
  /* ------------------------------------------------------------------ */
  /*  Risk-Level Gating Tests (Strict Safety Boundary)                   */
  /* ------------------------------------------------------------------ */

  it("does not render when riskLevel is CONSULT_DOCTOR", () => {
    const { container } = render(
      <SelfCareGuidanceCard
        riskLevel="CONSULT_DOCTOR"
        advice={["Rest well."]}
      />,
    );

    expect(container.firstChild).toBeNull();
    expect(
      screen.queryByText(/recommended self-care/i),
    ).not.toBeInTheDocument();
  });

  it("does not render when riskLevel is URGENT", () => {
    const { container } = render(
      <SelfCareGuidanceCard
        riskLevel="URGENT"
        advice={["Rest well."]}
      />,
    );

    expect(container.firstChild).toBeNull();
    expect(
      screen.queryByText(/recommended self-care/i),
    ).not.toBeInTheDocument();
  });

  /* ------------------------------------------------------------------ */
  /*  Happy Path Tests (SELF_CARE risk level)                            */
  /* ------------------------------------------------------------------ */

  it("renders low-risk guidance layout when riskLevel is SELF_CARE", () => {
    const customAdvice = [
      "Drink at least 2 liters of water daily.",
      "Apply a gentle warm compress.",
    ];
    const customWarnings = [
      "Sudden shortness of breath.",
      "High fever lasting over 48 hours.",
    ];

    render(
      <SelfCareGuidanceCard
        riskLevel="SELF_CARE"
        conditionName="Mild Viral Rhinitis"
        summary="Symptoms indicate a mild common viral infection."
        advice={customAdvice}
        warningSigns={customWarnings}
        timeframe="48 hours"
      />,
    );

    // Section title & badges
    expect(
      screen.getByRole("heading", {
        name: /recommended self-care & monitoring/i,
        level: 2,
      }),
    ).toBeInTheDocument();
    expect(screen.getByRole("status")).toHaveTextContent(/low-risk outcome/i);
    expect(screen.getByText(/Context: Mild Viral Rhinitis/i)).toBeInTheDocument();

    // Summary
    expect(
      screen.getByText(/symptoms indicate a mild common viral infection/i),
    ).toBeInTheDocument();

    // Safety reminder (low risk != zero risk)
    expect(
      screen.getByText(/low risk does not mean zero risk/i),
    ).toBeInTheDocument();

    // Custom advice points
    expect(
      screen.getByText("Drink at least 2 liters of water daily."),
    ).toBeInTheDocument();
    expect(
      screen.getByText("Apply a gentle warm compress."),
    ).toBeInTheDocument();

    // Custom warning points
    expect(
      screen.getByText("Sudden shortness of breath."),
    ).toBeInTheDocument();
    expect(
      screen.getByText("High fever lasting over 48 hours."),
    ).toBeInTheDocument();

    // Timeframe
    expect(
      screen.getByText(/re-evaluate if symptoms persist past 48 hours/i),
    ).toBeInTheDocument();

    // Mandatory disclaimer
    expect(
      screen.getByText(/this is not a medical diagnosis/i),
    ).toBeInTheDocument();
  });

  it("supports generalAdvice, whenToSeekCare, and monitoringTips from knowledge service", () => {
    render(
      <SelfCareGuidanceCard
        riskLevel="SELF_CARE"
        generalAdvice={["Sip warm ginger tea.", "Use a humidifier."]}
        whenToSeekCare={["Persistent high fever above 102°F."]}
        monitoringTips={["Record peak temperature twice daily."]}
      />,
    );

    expect(screen.getByText("Sip warm ginger tea.")).toBeInTheDocument();
    expect(screen.getByText("Use a humidifier.")).toBeInTheDocument();
    expect(
      screen.getByText("Persistent high fever above 102°F."),
    ).toBeInTheDocument();
    expect(
      screen.getByText("Record peak temperature twice daily."),
    ).toBeInTheDocument();
    expect(screen.getByText(/monitoring tips/i)).toBeInTheDocument();
  });

  /* ------------------------------------------------------------------ */
  /*  Edge Case Tests (Missing / Incomplete Guidance)                    */
  /* ------------------------------------------------------------------ */

  it("falls back to clinical default advice when advice array is empty or undefined", () => {
    render(
      <SelfCareGuidanceCard
        riskLevel="SELF_CARE"
        advice={[]}
      />,
    );

    expect(
      screen.getByText(DEFAULT_SELF_CARE_ADVICE[0]),
    ).toBeInTheDocument();
    expect(
      screen.getByText(DEFAULT_SELF_CARE_ADVICE[1]),
    ).toBeInTheDocument();
  });

  it("falls back to clinical default warning signs when warningSigns is missing", () => {
    render(
      <SelfCareGuidanceCard
        riskLevel="SELF_CARE"
        warningSigns={undefined}
      />,
    );

    expect(
      screen.getByText(DEFAULT_WARNING_SIGNS[0]),
    ).toBeInTheDocument();
    expect(
      screen.getByText(DEFAULT_WARNING_SIGNS[1]),
    ).toBeInTheDocument();
  });

  it("provides safe default summary text when summary is omitted", () => {
    render(<SelfCareGuidanceCard riskLevel="SELF_CARE" />);

    expect(
      screen.getByText(
        /your reported symptoms match mild, low-risk conditions that typically resolve with supportive home care/i,
      ),
    ).toBeInTheDocument();
  });

  /* ------------------------------------------------------------------ */
  /*  Failure Case Tests (Guidance Retrieval Error)                      */
  /* ------------------------------------------------------------------ */

  it("renders safe error notice banner when error is true", () => {
    render(
      <SelfCareGuidanceCard
        riskLevel="SELF_CARE"
        error={true}
      />,
    );

    expect(
      screen.getByRole("heading", {
        name: /self-care information notice/i,
        level: 2,
      }),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/guidance information is temporarily unavailable/i),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/rest and stay hydrated with water or oral fluids/i),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/this is not a medical diagnosis/i),
    ).toBeInTheDocument();
  });

  it("renders custom error message string when passed", () => {
    render(
      <SelfCareGuidanceCard
        riskLevel="SELF_CARE"
        error="Unable to connect to the clinical knowledge service."
      />,
    );

    expect(
      screen.getByText(
        /unable to connect to the clinical knowledge service/i,
      ),
    ).toBeInTheDocument();
  });

  /* ------------------------------------------------------------------ */
  /*  Interaction & Medical Safety Tests                                 */
  /* ------------------------------------------------------------------ */

  it("fires onConsultDoctorClick when user clicks the find clinic button", async () => {
    const user = userEvent.setup();
    const handleConsult = vi.fn();

    render(
      <SelfCareGuidanceCard
        riskLevel="SELF_CARE"
        onConsultDoctorClick={handleConsult}
      />,
    );

    const button = screen.getByRole("button", {
      name: /find nearby clinic \/ doctor/i,
    });
    expect(button).toBeInTheDocument();

    await user.click(button);
    expect(handleConsult).toHaveBeenCalledTimes(1);
  });

  it("mentions emergency phone number 112 in escalation instructions", () => {
    render(
      <SelfCareGuidanceCard
        riskLevel="SELF_CARE"
        emergencyNumber="112"
      />,
    );

    expect(
      screen.getByText(/112/i),
    ).toBeInTheDocument();
  });
});
