/**
 * @file Unit tests for WhyThisResultPanel component.
 * Owner: Mann (Frontend + Deployment · Testing) · Task: S2-MAN-3 · Requirements: FR-24
 */

import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import { WhyThisResultPanel } from "./WhyThisResultPanel";
import type { ConditionItem } from "./types";

describe("WhyThisResultPanel Component", () => {
  const mockConditions: ConditionItem[] = [
    {
      id: "c-1",
      name: "Migraine",
      confidence: "LIKELY",
      rank: 1,
      why: "Matches unilateral throbbing pain, nausea, and photophobia.",
      specialty: "Neurologist",
    },
    {
      id: "c-2",
      name: "Tension Headache",
      confidence: "POSSIBLE",
      rank: 2,
      why: "Common cause of diffuse head pressure and fatigue.",
      specialty: "General Physician",
    },
  ];

  it("renders heading, conditions list, and contributing why factors (FR-24)", () => {
    render(
      <WhyThisResultPanel
        conditions={mockConditions}
        reportedSymptoms={["Severe headache", "Nausea", "Sensitivity to light"]}
      />,
    );

    expect(
      screen.getByRole("heading", { name: "Why Was This Result Suggested?" }),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/Symptoms evaluated from your input:/i),
    ).toBeInTheDocument();
    expect(screen.getByText("Migraine")).toBeInTheDocument();
    expect(
      screen.getByText("Matches unilateral throbbing pain, nausea, and photophobia."),
    ).toBeInTheDocument();
    expect(screen.getByText("Tension Headache")).toBeInTheDocument();
  });

  it("toggles collapse and expand on button click", async () => {
    render(
      <WhyThisResultPanel
        conditions={mockConditions}
        defaultExpanded={true}
      />,
    );

    const toggleBtn = screen.getByRole("button", { name: /Collapse/i });
    expect(toggleBtn).toHaveAttribute("aria-expanded", "true");

    await userEvent.click(toggleBtn);

    expect(screen.getByRole("button", { name: /Expand/i })).toHaveAttribute(
      "aria-expanded",
      "false",
    );
    expect(screen.queryByText("Migraine")).not.toBeInTheDocument();
  });

  it("renders nothing when conditions array is empty", () => {
    const { container } = render(<WhyThisResultPanel conditions={[]} />);
    expect(container.firstChild).toBeNull();
  });
});
