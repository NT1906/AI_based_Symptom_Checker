
/**
 * @file Unit tests for MessageBubble component.
 *
 * Verifies:
 * - Happy path: Renders an assistant message.
 * - User case: Renders a user message with the correct accessible label.
 * - Edge case: Handles empty message content.
 * - Safety case: Renders message text as text, not executable HTML.
 *
 * Owner: Rutva · Task: S1-RUT-1 · Requirements: idea §1, §2
 */

import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { MessageBubble } from "./MessageBubble";
import type { AssessmentMessage } from "../../stores/assessmentStore";

describe("MessageBubble", () => {
  it("renders an assistant message (happy path)", () => {
    const message: AssessmentMessage = {
      id: "message-1",
      role: "assistant",
      content: "Can you describe your symptoms?",
    };

    render(<MessageBubble message={message} />);

    expect(screen.getByText("AI Assistant")).toBeInTheDocument();
    expect(
      screen.getByText("Can you describe your symptoms?"),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("article", { name: "Assistant message" }),
    ).toBeInTheDocument();
  });

  it("renders a user message with the correct label", () => {
    const message: AssessmentMessage = {
      id: "message-2",
      role: "user",
      content: "I have a headache.",
    };

    render(<MessageBubble message={message} />);

    expect(screen.getByText("You")).toBeInTheDocument();
    expect(screen.getByText("I have a headache.")).toBeInTheDocument();
    expect(
      screen.getByRole("article", { name: "Your message" }),
    ).toBeInTheDocument();
  });

  it("handles empty message content (edge case)", () => {
    const message: AssessmentMessage = {
      id: "message-3",
      role: "assistant",
      content: "",
    };

    render(<MessageBubble message={message} />);

    expect(
      screen.getByRole("article", { name: "Assistant message" }),
    ).toBeInTheDocument();
  });

  it("renders HTML-like input as plain text (safety case)", () => {
    const message: AssessmentMessage = {
      id: "message-4",
      role: "user",
      content: "<script>alert('test')</script>",
    };

    render(<MessageBubble message={message} />);

    expect(
      screen.getByText("<script>alert('test')</script>"),
    ).toBeInTheDocument();
    expect(document.querySelector("script")).toBeNull();
  });
});
