/**
 * @file Unit tests for SymptomConfirmationCard component.
 *
 * Verifies:
 * - Happy path: Renders initial extracted symptoms with attributes and confirms them.
 * - Editing case: Modifies severity and duration and updates source to USER_CORRECTED.
 * - Removal case: Removes a symptom and handles empty list by disabling confirmation.
 * - Addition case: Searches and adds a new symptom from canonical selectable suggestions.
 * - Safety case: Validates presence of mandatory medical disclaimer (DR-01).
 *
 * Owner: Mann (Frontend + Deployment · Testing) · Task: S1-MAN-1 · Requirements: FR-16, FR-21, FR-03, DR-01
 */

import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import {
  SymptomConfirmationCard,
} from "./SymptomConfirmationCard";
import type { ConfirmedSymptom } from "./types";

const mockInitialSymptoms: ConfirmedSymptom[] = [
  {
    id: "sym-1",
    name: "Headache",
    severity: "MODERATE",
    duration: { value: 2, unit: "DAY" },
    bodyLocation: "Temples",
    source: "AI_EXTRACTED",
  },
  {
    id: "sym-2",
    name: "Fever",
    severity: "MILD",
    duration: { value: 1, unit: "DAY" },
    bodyLocation: null,
    source: "AI_EXTRACTED",
  },
];

describe("SymptomConfirmationCard", () => {
  it("renders initial extracted symptoms and allows confirming (happy path)", () => {
    const handleConfirm = vi.fn();
    render(
      <SymptomConfirmationCard
        initialSymptoms={mockInitialSymptoms}
        onConfirm={handleConfirm}
      />,
    );

    // Verify header and symptom names
    expect(screen.getByText(/Review & Confirm Symptoms/i)).toBeInTheDocument();
    expect(screen.getByText(/1\. Headache/i)).toBeInTheDocument();
    expect(screen.getByText(/2\. Fever/i)).toBeInTheDocument();

    // Verify badges and duration
    expect(screen.getByText("MODERATE")).toBeInTheDocument();
    expect(screen.getByText("MILD")).toBeInTheDocument();
    expect(screen.getByText(/⏳ Duration: 2 days/i)).toBeInTheDocument();
    expect(screen.getByText(/📍 Location: Temples/i)).toBeInTheDocument();

    // Click confirm button
    const confirmButton = screen.getByRole("button", {
      name: /Confirm & Analyze Symptoms/i,
    });
    fireEvent.click(confirmButton);

    expect(handleConfirm).toHaveBeenCalledTimes(1);
    expect(handleConfirm).toHaveBeenCalledWith(mockInitialSymptoms);
  });

  it("allows editing symptom severity and duration attributes (edge case)", () => {
    const handleConfirm = vi.fn();
    render(
      <SymptomConfirmationCard
        initialSymptoms={mockInitialSymptoms}
        onConfirm={handleConfirm}
      />,
    );

    // Click edit for Headache
    const editButtons = screen.getAllByRole("button", { name: /Edit/i });
    fireEvent.click(editButtons[0]);

    // Severity select is displayed
    const severitySelect = screen.getByLabelText(/Severity Level/i);
    fireEvent.change(severitySelect, { target: { value: "SEVERE" } });

    // Duration input is updated
    const durationInput = screen.getByLabelText(/Duration Length/i);
    fireEvent.change(durationInput, { target: { value: "5" } });

    // Click Done to finish editing
    fireEvent.click(screen.getByRole("button", { name: /Done/i }));

    // Confirm updated list
    const confirmButton = screen.getByRole("button", {
      name: /Confirm & Analyze Symptoms/i,
    });
    fireEvent.click(confirmButton);

    expect(handleConfirm).toHaveBeenCalledWith([
      expect.objectContaining({
        id: "sym-1",
        name: "Headache",
        severity: "SEVERE",
        duration: { value: 5, unit: "DAY" },
        source: "USER_CORRECTED",
      }),
      mockInitialSymptoms[1],
    ]);
  });

  it("allows removing symptoms and disables confirmation when list is empty (edge case)", () => {
    const handleConfirm = vi.fn();
    render(
      <SymptomConfirmationCard
        initialSymptoms={[{ ...mockInitialSymptoms[0] }]}
        onConfirm={handleConfirm}
      />,
    );

    expect(screen.getByText(/1\. Headache/i)).toBeInTheDocument();

    // Remove the only symptom
    const removeButton = screen.getByRole("button", { name: /Remove Headache/i });
    fireEvent.click(removeButton);

    // Symptom is removed and empty message displayed
    expect(screen.queryByText(/1\. Headache/i)).not.toBeInTheDocument();
    expect(screen.getByText(/No symptoms listed/i)).toBeInTheDocument();

    // Confirm button is disabled
    const confirmButton = screen.getByRole("button", {
      name: /Confirm & Analyze Symptoms/i,
    });
    expect(confirmButton).toBeDisabled();
  });

  it("allows searching and adding a symptom from the selectable list (FR-03, FR-16)", () => {
    const handleConfirm = vi.fn();
    render(
      <SymptomConfirmationCard
        initialSymptoms={mockInitialSymptoms}
        onConfirm={handleConfirm}
      />,
    );

    // Open Add Symptom section
    const openAddButton = screen.getByRole("button", { name: /Add Symptom/i });
    fireEvent.click(openAddButton);

    // Search for nausea
    const searchInput = screen.getByRole("textbox", {
      name: /Search or enter symptom name/i,
    });
    fireEvent.change(searchInput, { target: { value: "nausea" } });

    // Select suggested symptom
    const suggestionButton = screen.getByRole("button", {
      name: /Nausea or feeling sick/i,
    });
    fireEvent.click(suggestionButton);

    // Verify added to symptoms list
    expect(screen.getByText(/3\. Nausea or feeling sick/i)).toBeInTheDocument();

    // Confirm includes the new symptom
    const confirmButton = screen.getByRole("button", {
      name: /Confirm & Analyze Symptoms/i,
    });
    fireEvent.click(confirmButton);

    expect(handleConfirm).toHaveBeenCalledWith(
      expect.arrayContaining([
        mockInitialSymptoms[0],
        mockInitialSymptoms[1],
        expect.objectContaining({
          name: "Nausea or feeling sick",
          source: "USER_CONFIRMED",
        }),
      ]),
    );
  });

  it("displays mandatory medical disclaimer text (DR-01 compliance)", () => {
    render(
      <SymptomConfirmationCard
        initialSymptoms={mockInitialSymptoms}
        onConfirm={vi.fn()}
      />,
    );

    expect(
      screen.getByText((content) =>
        content.includes(
          "This is not a medical diagnosis. Confirmation is used to organize informational suggestions only.",
        ),
      ),
    ).toBeInTheDocument();
  });

  it("renders back to chat button when onCancel prop is provided", () => {
    const handleCancel = vi.fn();
    render(
      <SymptomConfirmationCard
        initialSymptoms={mockInitialSymptoms}
        onConfirm={vi.fn()}
        onCancel={handleCancel}
      />,
    );

    const backButton = screen.getByRole("button", { name: /← Back to Chat/i });
    fireEvent.click(backButton);
    expect(handleCancel).toHaveBeenCalledTimes(1);
  });
});
