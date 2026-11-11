/**
 * @file Unit tests for SymptomTooltip component and symptom glossary lookup.
 * Owner: Mann (Frontend + Deployment · Testing) · Task: S2-MAN-3 · Requirements: FR-18
 */

import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import { SymptomTooltip } from "./SymptomTooltip";
import { getSymptomDefinition } from "./symptomGlossary";

describe("SymptomTooltip Component", () => {
  describe("Happy Path - Glossary Lookup and Tooltip Popover", () => {
    it("renders trigger button with symptom name and information indicator", () => {
      render(<SymptomTooltip symptom="fever" />);

      const trigger = screen.getByRole("button", { name: "Definition for Fever" });
      expect(trigger).toBeInTheDocument();
      expect(screen.getByText("Fever")).toBeInTheDocument();
      expect(trigger).toHaveAttribute("aria-expanded", "false");
    });

    it("opens tooltip popover on click and shows plain-language definition", async () => {
      render(<SymptomTooltip symptom="headache" />);

      const trigger = screen.getByRole("button", { name: "Definition for Headache" });
      await userEvent.click(trigger);

      expect(trigger).toHaveAttribute("aria-expanded", "true");
      expect(screen.getByRole("tooltip")).toBeInTheDocument();
      expect(
        screen.getByText(/A pain or aching sensation in any part of the head/i),
      ).toBeInTheDocument();
    });

    it("displays 'when to seek care' emergency guidance in popover", async () => {
      render(<SymptomTooltip symptom="chest_pain" />);

      const trigger = screen.getByRole("button", { name: "Definition for Chest pain or pressure" });
      await userEvent.click(trigger);

      expect(
        screen.getByText(/Treat new, severe, or crushing chest pain as a potential medical emergency/i),
      ).toBeInTheDocument();
    });

    it("closes tooltip when close button is clicked", async () => {
      render(<SymptomTooltip symptom="nausea" />);

      const trigger = screen.getByRole("button", { name: "Definition for Nausea or feeling sick" });
      await userEvent.click(trigger);
      expect(screen.getByRole("tooltip")).toBeInTheDocument();

      const closeBtn = screen.getByRole("button", { name: "Close definition tooltip" });
      await userEvent.click(closeBtn);

      expect(screen.queryByRole("tooltip")).not.toBeInTheDocument();
      expect(trigger).toHaveAttribute("aria-expanded", "false");
    });

    it("closes tooltip when Escape key is pressed", async () => {
      render(<SymptomTooltip symptom="fatigue" />);

      const trigger = screen.getByRole("button", { name: "Definition for Tiredness or weakness" });
      await userEvent.click(trigger);
      expect(screen.getByRole("tooltip")).toBeInTheDocument();

      await userEvent.keyboard("{Escape}");
      expect(screen.queryByRole("tooltip")).not.toBeInTheDocument();
    });
  });

  describe("Custom Overrides and Edge Cases", () => {
    it("renders custom children text over default symptom name", () => {
      render(
        <SymptomTooltip symptom="skin_rash">
          <span>High temperature symptom</span>
        </SymptomTooltip>,
      );

      expect(screen.getByText("High temperature symptom")).toBeInTheDocument();
    });

    it("renders custom definition when provided", async () => {
      render(
        <SymptomTooltip
          symptom="cough"
          customDefinition="A persistent tickle in the throat causing dry coughing."
        />,
      );

      const trigger = screen.getByRole("button", { name: /Definition for/i });
      await userEvent.click(trigger);

      expect(
        screen.getByText("A persistent tickle in the throat causing dry coughing."),
      ).toBeInTheDocument();
    });

    it("falls back to plain text if symptom has no glossary definition", () => {
      render(<SymptomTooltip symptom="unknown_obscure_symptom_xyz" />);

      expect(
        screen.queryByRole("button", { name: /Definition for/i }),
      ).not.toBeInTheDocument();
      expect(screen.getByText("unknown_obscure_symptom_xyz")).toBeInTheDocument();
    });
  });

  describe("getSymptomDefinition helper", () => {
    it("retrieves entries by ID, display name, and case insensitively", () => {
      expect(getSymptomDefinition("fever")?.name).toBe("Fever");
      expect(getSymptomDefinition("FEVER")?.name).toBe("Fever");
      expect(getSymptomDefinition("skin_rash")?.bodySystem).toBe("skin");
      expect(getSymptomDefinition("Headache")?.id).toBe("headache");
      expect(getSymptomDefinition("nonexistent_12345")).toBeNull();
    });
  });
});
