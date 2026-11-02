/**
 * @file Unit tests for ConditionList component.
 *
 * Verifies:
 * - Happy path: Renders ranked conditions with names, confidence badges, and "why" lines.
 * - Confidence safety case: Strictly displays qualitative labels (Likely, Possible, Less likely)
 *   and never raw numerical probabilities or percentages (FR-23, AI_RULES §2.3).
 * - Empty state edge case: Handles empty conditions array with appropriate guidance.
 * - Detail accordion edge case: Toggles additional metadata (ICD-10 code, overview).
 * - Selection callback case: Dispatches onSelectCondition handler.
 * - Safety case: Displays non-diagnostic informational footer.
 *
 * Owner: Mann (Frontend + Deployment · Testing) · Task: S1-MAN-2 · Requirements: FR-22, FR-23, DR-01
 */

import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import {
  ConditionList,
  getConfidenceLabel,
  getConfidenceBadgeClass,
} from "./ConditionList";
import type { ConditionItem } from "./types";

const mockConditions: ConditionItem[] = [
  {
    id: "c-1",
    name: "Migraine with Photophobia",
    confidence: "LIKELY",
    rank: 1,
    why: "Matching unilateral throbbing headache and light sensitivity.",
    specialty: "Neurology / General Medicine",
    icd10Code: "G43.9",
    description: "A neurological condition characterized by recurrent moderate to severe headaches.",
  },
  {
    id: "c-2",
    name: "Tension-type Headache",
    confidence: "POSSIBLE",
    rank: 2,
    why: "Common cause of persistent head discomfort without systemic signs.",
    specialty: "General Medicine",
    icd10Code: "G44.2",
    description: "Common type of primary headache presenting as a dull band-like sensation.",
  },
  {
    id: "c-3",
    name: "Sinusitis",
    confidence: "LESS_LIKELY",
    rank: 3,
    why: "Potential overlap, though primary nasal symptoms were not reported.",
    specialty: "Otolaryngology (ENT)",
  },
];

describe("ConditionList", () => {
  it("renders ranked conditions with titles, confidence badges, and why lines (happy path)", () => {
    render(<ConditionList conditions={mockConditions} />);

    // Check main title
    expect(screen.getByRole("heading", { name: /Possible Conditions/i })).toBeInTheDocument();

    // Check condition titles and ranks
    expect(screen.getByText("Migraine with Photophobia")).toBeInTheDocument();
    expect(screen.getByText("#1")).toBeInTheDocument();
    expect(screen.getByText("Tension-type Headache")).toBeInTheDocument();
    expect(screen.getByText("#2")).toBeInTheDocument();
    expect(screen.getByText("Sinusitis")).toBeInTheDocument();
    expect(screen.getByText("#3")).toBeInTheDocument();

    // Check qualitative confidence badges
    expect(screen.getByLabelText("Likelihood: Likely")).toBeInTheDocument();
    expect(screen.getByLabelText("Likelihood: Possible")).toBeInTheDocument();
    expect(screen.getByLabelText("Likelihood: Less likely")).toBeInTheDocument();

    // Check "Why" rationale lines
    expect(
      screen.getByText(/Matching unilateral throbbing headache and light sensitivity/i),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/Common cause of persistent head discomfort without systemic signs/i),
    ).toBeInTheDocument();

    // Check recommended specialties
    expect(screen.getByText("Neurology / General Medicine")).toBeInTheDocument();
    expect(screen.getByText("General Medicine")).toBeInTheDocument();
  });

  it("strictly renders qualitative confidence labels and never raw percentages (FR-23, AI_RULES §2.3)", () => {
    render(<ConditionList conditions={mockConditions} />);

    // Verify qualitative badges exist
    expect(screen.getByText("Likely")).toBeInTheDocument();
    expect(screen.getByText("Possible")).toBeInTheDocument();
    expect(screen.getByText("Less likely")).toBeInTheDocument();

    // Verify that NO percentage signs or probability decimal formats appear anywhere
    const rawPercentageRegex = /\b\d+(\.\d+)?%\b/;
    const allText = document.body.textContent || "";
    expect(allText).not.toMatch(rawPercentageRegex);

    // Verify helper mappings
    expect(getConfidenceLabel("LIKELY")).toBe("Likely");
    expect(getConfidenceLabel("POSSIBLE")).toBe("Possible");
    expect(getConfidenceLabel("LESS_LIKELY")).toBe("Less likely");
    expect(getConfidenceBadgeClass("LIKELY")).toContain("bg-teal-100");
  });

  it("renders empty state fallback when no conditions are present (edge case)", () => {
    render(
      <ConditionList
        conditions={[]}
        emptyMessage="No matching conditions found."
      />,
    );

    expect(screen.getByText("No matching conditions found.")).toBeInTheDocument();
    expect(
      screen.getByText(/A general physician can help evaluate non-specific or evolving symptoms/i),
    ).toBeInTheDocument();
  });

  it("toggles condition details accordion to show ICD-10 and description (edge case)", () => {
    render(<ConditionList conditions={mockConditions} />);

    // Initially details are hidden
    expect(screen.queryByText("G43.9")).not.toBeInTheDocument();

    // Click show details on first item
    const showDetailsButtons = screen.getAllByRole("button", { name: /Show details/i });
    fireEvent.click(showDetailsButtons[0]);

    // ICD-10 and description now visible
    expect(screen.getByText("G43.9")).toBeInTheDocument();
    expect(
      screen.getByText(
        /A neurological condition characterized by recurrent moderate to severe headaches/i,
      ),
    ).toBeInTheDocument();

    // Click hide details to collapse
    const hideDetailsButton = screen.getByRole("button", { name: /Hide details/i });
    fireEvent.click(hideDetailsButton);
    expect(screen.queryByText("G43.9")).not.toBeInTheDocument();
  });

  it("calls onSelectCondition callback when selection button is clicked", () => {
    const handleSelect = vi.fn();
    render(
      <ConditionList
        conditions={mockConditions}
        onSelectCondition={handleSelect}
      />,
    );

    const selectButtons = screen.getAllByRole("button", {
      name: /Select for follow-up/i,
    });
    fireEvent.click(selectButtons[0]);

    expect(handleSelect).toHaveBeenCalledTimes(1);
    expect(handleSelect).toHaveBeenCalledWith(mockConditions[0]);
  });

  it("displays non-diagnostic informational footer note (DR-01 compliance)", () => {
    render(<ConditionList conditions={mockConditions} />);

    expect(
      screen.getByText((content) =>
        content.includes("Conditions are ranked suggestions for informational discussion"),
      ),
    ).toBeInTheDocument();
  });
});
