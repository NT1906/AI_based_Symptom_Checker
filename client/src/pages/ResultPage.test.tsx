/**
 * @file Unit test suite for ResultPage component.
 *
 * Covers:
 * - Happy path rendering across all 3 triage tiers (SELF_CARE, CONSULT_DOCTOR, URGENT).
 * - High-priority emergency callout and tel:112 dialing on URGENT risk tier (DR-02, FR-06).
 * - Qualitative confidence labels (Likely, Possible, Less likely; no raw scores, FR-23).
 * - Guidance slot with self-care advice and emergency warning signs.
 * - Specialist referral with external map query link (FR-08).
 * - Persistent medical disclaimer compliance (DR-01).
 * - Edge case handling for empty condition lists and missing optional fields.
 * - Interaction with "Start New Assessment" and condition selection callbacks.
 *
 * Owner: Mann (Frontend + Deployment · Testing) · Task: S1-MAN-3 · Requirements: DR-01, DR-02, FR-06, FR-15, FR-22, FR-23, FR-24, FR-08, NFR-06
 */

import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { ResultPage, DEFAULT_RESULT_DATA } from "./ResultPage";
import type { AssessmentResultData } from "../components/result/types";

describe("ResultPage", () => {
  it("renders with default result data showing Consult Doctor tier, conditions, and guidance", () => {
    render(<ResultPage />);

    // Header title and subtitle
    expect(screen.getByRole("heading", { name: "Assessment Result", level: 1 })).toBeInTheDocument();
    expect(screen.getByText(/Clinical Triage & Candidate Conditions Summary/)).toBeInTheDocument();

    // Triage banner
    expect(screen.getByText("Medical Consultation Recommended")).toBeInTheDocument();
    expect(screen.getByRole("status")).toHaveTextContent("Consult a Doctor");

    // Conditions
    expect(screen.getByText("Migraine with Photophobia")).toBeInTheDocument();
    expect(screen.getByText("Likely")).toBeInTheDocument();
    expect(screen.getByText("Tension-type Headache")).toBeInTheDocument();
    expect(screen.getByText("Possible")).toBeInTheDocument();

    // Guidance slot
    expect(screen.getByText("General Self-Care Steps")).toBeInTheDocument();
    expect(screen.getByText("When to Seek Emergency Care")).toBeInTheDocument();

    // Referral slot
    expect(screen.getAllByText(/General Physician/).length).toBeGreaterThanOrEqual(1);
    expect(screen.getByRole("link", { name: /Find a General Physician near you/i })).toBeInTheDocument();

    // Persistent disclaimer (DR-01)
    expect(screen.getByRole("note", { name: /medical disclaimer/i })).toBeInTheDocument();
    expect(screen.getAllByText(/not a medical diagnosis/i).length).toBeGreaterThanOrEqual(1);
  });

  it("renders SELF_CARE triage tier with green status and home management guidance", () => {
    const selfCareData: AssessmentResultData = {
      riskLevel: "SELF_CARE",
      conditions: [
        {
          id: "c-sc-1",
          name: "Mild Tension Headache",
          confidence: "LIKELY",
          rank: 1,
          why: "Short duration and mild bilateral pressure.",
          specialty: "General Physician",
        },
      ],
      guidance: {
        selfCareAdvice: ["Stay hydrated with water.", "Rest in a quiet room."],
        warningSigns: ["Sudden severe worsening."],
      },
    };

    render(<ResultPage result={selfCareData} />);

    expect(screen.getByText("Self-Care Management Recommended")).toBeInTheDocument();
    expect(screen.getByRole("status")).toHaveTextContent("Self-Care");
    expect(screen.getByText("Stay hydrated with water.")).toBeInTheDocument();
    // Urgent emergency alert should NOT be rendered
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });

  it("prioritizes emergency 112 callout when risk level is URGENT (DR-02, FR-06)", () => {
    const urgentData: AssessmentResultData = {
      riskLevel: "URGENT",
      conditions: [
        {
          id: "c-urg-1",
          name: "Suspected Acute Coronary Syndrome",
          confidence: "LIKELY",
          rank: 1,
          why: "Reported crushing chest pain with radiation to arm.",
          specialty: "Emergency Medicine / Cardiologist",
        },
      ],
      guidance: {
        warningSigns: ["Crushing chest pain", "Shortness of breath"],
      },
    };

    render(<ResultPage result={urgentData} emergencyNumber="112" />);

    // Urgent banner & alert
    expect(screen.getByText("Urgent Medical Care Required")).toBeInTheDocument();
    const alert = screen.getByRole("alert");
    expect(alert).toBeInTheDocument();
    expect(alert).toHaveTextContent(/Immediate Action Required/i);
    expect(alert).toHaveTextContent(/Do not attempt to drive yourself/i);

    // Call 112 button inside alert
    const call112Links = screen.getAllByRole("link", { name: /call.*112/i });
    expect(call112Links.length).toBeGreaterThanOrEqual(1);
    expect(call112Links.some((link) => link.getAttribute("href") === "tel:112")).toBe(true);
  });

  it("calls onSelectCondition when a candidate condition item is clicked", async () => {
    const user = userEvent.setup();
    const onSelectCondition = vi.fn();

    render(<ResultPage result={DEFAULT_RESULT_DATA} onSelectCondition={onSelectCondition} />);

    const selectButtons = screen.getAllByRole("button", {
      name: /Select for follow-up/i,
    });
    expect(selectButtons.length).toBeGreaterThanOrEqual(1);
    await user.click(selectButtons[0]);

    expect(onSelectCondition).toHaveBeenCalledTimes(1);
    expect(onSelectCondition).toHaveBeenCalledWith(
      expect.objectContaining({ name: "Migraine with Photophobia" }),
    );
  });

  it("handles empty conditions gracefully with accessible fallback message (edge case)", () => {
    const emptyResult: AssessmentResultData = {
      riskLevel: "CONSULT_DOCTOR",
      conditions: [],
    };

    render(<ResultPage result={emptyResult} />);

    expect(
      screen.getByText(/No matching conditions identified for the provided symptoms/i),
    ).toBeInTheDocument();
  });

  it("handles missing guidance and referral gracefully without crashing (edge case)", () => {
    const minimalResult: AssessmentResultData = {
      riskLevel: "SELF_CARE",
      conditions: [
        {
          id: "c-min-1",
          name: "Mild Fatigue",
          confidence: "POSSIBLE",
        },
      ],
    };

    render(<ResultPage result={minimalResult} />);

    expect(screen.getByText("Mild Fatigue")).toBeInTheDocument();
    expect(screen.queryByText("General Self-Care Steps")).not.toBeInTheDocument();
    expect(screen.queryByText("Recommended Specialist Evaluation")).not.toBeInTheDocument();
  });

  it("triggers onStartNewAssessment callback when clicking start buttons", async () => {
    const user = userEvent.setup();
    const onStartNewAssessment = vi.fn();

    render(
      <ResultPage
        result={DEFAULT_RESULT_DATA}
        onStartNewAssessment={onStartNewAssessment}
      />,
    );

    // Primary action button in the content area
    const startNewBtn = screen.getByRole("button", { name: /Start New Assessment/i });
    await user.click(startNewBtn);
    expect(onStartNewAssessment).toHaveBeenCalledTimes(1);

    // Header "Start Over" button (accessible name comes from aria-label) opens confirmation dialog
    const headerStartOver = screen.getByRole("button", {
      name: /Start a new assessment from scratch/i,
    });
    await user.click(headerStartOver);
    const confirmBtn = screen.getByRole("button", { name: /Yes, Start Over/i });
    await user.click(confirmBtn);
    expect(onStartNewAssessment).toHaveBeenCalledTimes(2);
  });

  it("verifies external map link points to secure URL with noopener noreferrer (FR-08)", () => {
    render(<ResultPage result={DEFAULT_RESULT_DATA} />);

    const mapLink = screen.getByRole("link", { name: /Find a General Physician near you/i });
    expect(mapLink).toHaveAttribute("target", "_blank");
    expect(mapLink).toHaveAttribute("rel", "noopener noreferrer");
    expect(mapLink.getAttribute("href")).toContain("https://www.google.com/maps/search/?api=1");
    expect(mapLink.getAttribute("href")).toContain(encodeURIComponent("General Physician near me"));
  });
});
