/**
 * @file Comprehensive frontend component integration tests for chat, confirmation, and results.
 * Owner: Mann (Frontend + Deployment · Testing) · Task: S2-MAN-4 · Requirements: NFR-06, DR-01, DR-02
 */

import { fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { ChatContainer } from "../chat/ChatContainer";
import { SymptomConfirmationCard } from "./SymptomConfirmationCard";
import { ConditionList } from "../result/ConditionList";
import { RiskBadge } from "../result/RiskBadge";
import type { ConfirmedSymptom } from "./types";
import type { ConditionItem } from "../result/types";

describe("Frontend Component Integration Tests (S2-MAN-4)", () => {
  describe("1. Chat Conversation Component Tests", () => {
    it("renders conversation history and handles message submission", async () => {
      const handleSend = vi.fn();
      render(
        <ChatContainer
          messages={[
            { id: "m-1", role: "assistant", content: "Hello! What symptoms are you experiencing?" },
            { id: "m-2", role: "user", content: "I have had a throbbing headache since morning." },
          ]}
          onSend={handleSend}
        />,
      );

      expect(screen.getByText("Hello! What symptoms are you experiencing?")).toBeInTheDocument();
      expect(screen.getByText("I have had a throbbing headache since morning.")).toBeInTheDocument();

      const textarea = screen.getByPlaceholderText("Describe how you're feeling...");
      await userEvent.type(textarea, "Also feeling a bit dizzy.");

      const sendButton = screen.getByRole("button", { name: "Send" });
      await userEvent.click(sendButton);

      expect(handleSend).toHaveBeenCalledWith("Also feeling a bit dizzy.");
    });

    it("displays offline warning banner when disconnected from network", () => {
      // Temporarily mock navigator.onLine as false
      vi.spyOn(navigator, "onLine", "get").mockReturnValue(false);

      render(
        <ChatContainer
          messages={[]}
          onSend={vi.fn()}
        />,
      );

      const alert = screen.getByRole("alert");
      expect(alert).toHaveTextContent(/You're offline\. If this is an emergency, call 112\./i);

      vi.restoreAllMocks();
    });

    it("displays error banner with retry button on network or service error", async () => {
      const handleRetry = vi.fn();
      render(
        <ChatContainer
          messages={[{ id: "m-1", role: "user", content: "Fever" }]}
          onSend={vi.fn()}
          error="Network timeout connecting to analysis service."
          onRetry={handleRetry}
        />,
      );

      expect(screen.getByText("Network timeout connecting to analysis service.")).toBeInTheDocument();
      const retryBtn = screen.getByRole("button", { name: "Retry" });
      await userEvent.click(retryBtn);

      expect(handleRetry).toHaveBeenCalledTimes(1);
    });

    it("displays typing indicator when assistant is formulating response", () => {
      render(
        <ChatContainer
          messages={[{ id: "m-1", role: "user", content: "Fever" }]}
          onSend={vi.fn()}
          isTyping={true}
        />,
      );

      expect(screen.getByRole("status", { name: "Assistant is typing" })).toBeInTheDocument();
    });
  });

  describe("2. Symptom Confirmation Card Component Tests", () => {
    const mockSymptoms: ConfirmedSymptom[] = [
      {
        id: "s-1",
        name: "Headache",
        severity: "MODERATE",
        duration: { value: 3, unit: "DAY" },
        bodyLocation: "Frontal",
        source: "AI_EXTRACTED",
      },
      {
        id: "s-2",
        name: "Fever",
        severity: "MILD",
        duration: { value: 1, unit: "DAY" },
        source: "AI_EXTRACTED",
      },
    ];

    it("allows editing symptom severity and duration attributes", async () => {
      const handleConfirm = vi.fn();
      render(
        <SymptomConfirmationCard
          initialSymptoms={mockSymptoms}
          onConfirm={handleConfirm}
        />,
      );

      // Click Edit on the first symptom
      const editButtons = screen.getAllByRole("button", { name: /Edit/i });
      await userEvent.click(editButtons[0]);

      // Change severity to SEVERE
      const severitySelect = screen.getByLabelText(/Severity Level/i);
      fireEvent.change(severitySelect, { target: { value: "SEVERE" } });

      // Click Done editing
      const doneButton = screen.getByRole("button", { name: "Done" });
      await userEvent.click(doneButton);

      // Verify updated badge
      expect(screen.getByText("SEVERE")).toBeInTheDocument();

      // Submit confirmation
      const confirmButton = screen.getByRole("button", { name: /Confirm & Analyze Symptoms/i });
      await userEvent.click(confirmButton);

      expect(handleConfirm).toHaveBeenCalledWith(
        expect.arrayContaining([
          expect.objectContaining({
            id: "s-1",
            severity: "SEVERE",
            source: "USER_CORRECTED",
          }),
        ]),
      );
    });

    it("allows removing symptoms and disables confirmation when symptom list becomes empty", async () => {
      const handleConfirm = vi.fn();
      render(
        <SymptomConfirmationCard
          initialSymptoms={[mockSymptoms[0]]}
          onConfirm={handleConfirm}
        />,
      );

      const removeBtn = screen.getByRole("button", { name: /Remove Headache/i });
      await userEvent.click(removeBtn);

      expect(screen.getByText("No symptoms listed.")).toBeInTheDocument();
      const confirmBtn = screen.getByRole("button", { name: /Confirm & Analyze Symptoms/i });
      expect(confirmBtn).toBeDisabled();
    });

    it("displays mandatory non-diagnostic disclaimer text (DR-01)", () => {
      render(
        <SymptomConfirmationCard
          initialSymptoms={mockSymptoms}
          onConfirm={vi.fn()}
        />,
      );

      expect(
        screen.getByText(/This is not a medical diagnosis\. Confirmation is used to organize/i),
      ).toBeInTheDocument();
    });
  });

  describe("3. Results and Condition List Component Tests", () => {
    const mockConditions: ConditionItem[] = [
      {
        id: "c-1",
        name: "Viral Pharyngitis",
        confidence: "LIKELY",
        rank: 1,
        why: "Common cause of acute sore throat accompanied by mild fever.",
        specialty: "General Physician",
      },
      {
        id: "c-2",
        name: "Streptococcal Pharyngitis",
        confidence: "POSSIBLE",
        rank: 2,
        why: "Bacterial infection considered if tonsillar exudates are present.",
        specialty: "ENT Specialist",
      },
    ];

    it("renders ranked conditions with qualitative confidence labels and why rationale", () => {
      render(<ConditionList conditions={mockConditions} />);

      expect(screen.getByText("Viral Pharyngitis")).toBeInTheDocument();
      expect(screen.getByText("Likely")).toBeInTheDocument();
      expect(
        screen.getByText("Common cause of acute sore throat accompanied by mild fever."),
      ).toBeInTheDocument();

      expect(screen.getByText("Streptococcal Pharyngitis")).toBeInTheDocument();
      expect(screen.getByText("Possible")).toBeInTheDocument();
    });

    it("invokes onSelectCondition callback when a condition item is clicked", async () => {
      const onSelect = vi.fn();
      render(
        <ConditionList
          conditions={mockConditions}
          onSelectCondition={onSelect}
        />,
      );

      const selectButtons = screen.getAllByRole("button", {
        name: /Select for follow-up/i,
      });
      await userEvent.click(selectButtons[0]);

      expect(onSelect).toHaveBeenCalledTimes(1);
      expect(onSelect).toHaveBeenCalledWith(mockConditions[0]);
    });

    it("renders fallback message when conditions array is empty (edge case)", () => {
      render(
        <ConditionList
          conditions={[]}
          emptyMessage="No matching conditions found."
        />,
      );

      expect(screen.getByText("No matching conditions found.")).toBeInTheDocument();
    });

    it("renders deterministic risk badge across all tiers (DR-02, FR-06)", () => {
      const { rerender } = render(<RiskBadge level="SELF_CARE" />);
      expect(screen.getByRole("status")).toHaveTextContent("Self-Care");

      rerender(<RiskBadge level="CONSULT_DOCTOR" />);
      expect(screen.getByRole("status")).toHaveTextContent("Consult a Doctor");

      rerender(<RiskBadge level="URGENT" />);
      expect(screen.getByRole("status")).toHaveTextContent("Urgent Care");
    });
  });
});
