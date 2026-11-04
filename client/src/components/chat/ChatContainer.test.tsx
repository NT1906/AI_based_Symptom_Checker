
/**
 * @file Unit tests for ChatContainer component.
 *
 * Verifies:
 * - Happy path: Displays conversation messages.
 * - Empty state: Displays the initial conversation prompt.
 * - Interaction: Sends a message through the composer.
 * - Disabled case: Disables message submission.
 * - Accessibility: Exposes the conversation as an accessible live log.
 * - Failure case: Handles unavailable browser auto-scroll.
 *
 * Owner: Rutva - Task: S1-RUT-3 - Issue: #57
 */

import { beforeEach, describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ChatContainer } from "./ChatContainer";
import type { AssessmentMessage } from "../../stores/assessmentStore";

const mockMessages: AssessmentMessage[] = [
  {
    id: "message-1",
    role: "assistant",
    content: "What symptoms are you experiencing?",
  },
  {
    id: "message-2",
    role: "user",
    content: "I have a headache.",
  },
];

describe("ChatContainer", () => {
  beforeEach(() => {
    Element.prototype.scrollIntoView = vi.fn();
  });

  it("displays conversation messages (happy path)", () => {
    render(<ChatContainer messages={mockMessages} onSend={vi.fn()} />);

    expect(
      screen.getByText("What symptoms are you experiencing?"),
    ).toBeInTheDocument();
    expect(screen.getByText("I have a headache.")).toBeInTheDocument();
  });

  it("displays an initial prompt when there are no messages", () => {
    render(<ChatContainer messages={[]} onSend={vi.fn()} />);

    expect(
      screen.getByText(/Tell me what you're experiencing/i),
    ).toBeInTheDocument();
  });

  it("sends a new message through the composer", async () => {
    const user = userEvent.setup();
    const handleSend = vi.fn();

    render(<ChatContainer messages={[]} onSend={handleSend} />);

    await user.type(
      screen.getByRole("textbox", { name: /type your message/i }),
      "I feel tired.",
    );
    await user.click(screen.getByRole("button", { name: /send/i }));

    expect(handleSend).toHaveBeenCalledWith("I feel tired.");
  });

  it("disables the composer when disabled", () => {
    render(<ChatContainer messages={[]} onSend={vi.fn()} disabled />);

    expect(
      screen.getByRole("textbox", { name: /type your message/i }),
    ).toBeDisabled();
  });

  it("provides an accessible live conversation log", () => {
    render(<ChatContainer messages={mockMessages} onSend={vi.fn()} />);

    const conversation = screen.getByRole("log", {
      name: "Assessment conversation",
    });

    expect(conversation).toHaveAttribute("aria-live", "polite");
    expect(conversation).toHaveAttribute("aria-relevant", "additions");
  });

  it("still renders when browser auto-scroll is unavailable (failure case)", () => {
    const originalScrollIntoView = Element.prototype.scrollIntoView;

    Object.defineProperty(Element.prototype, "scrollIntoView", {
      configurable: true,
      value: undefined,
    });

    try {
      render(<ChatContainer messages={mockMessages} onSend={vi.fn()} />);

      expect(
        screen.getByText("What symptoms are you experiencing?"),
      ).toBeInTheDocument();
    } finally {
      Object.defineProperty(Element.prototype, "scrollIntoView", {
        configurable: true,
        value: originalScrollIntoView,
      });
    }
  });
  it("shows the assistant typing indicator", () => {
    render(<ChatContainer messages={mockMessages} onSend={vi.fn()} isTyping />);

    expect(screen.getByRole("status")).toHaveTextContent("Assistant is typing...");
  });

  it("shows loading feedback and disables the composer", () => {
    render(<ChatContainer messages={mockMessages} onSend={vi.fn()} isLoading />);

    expect(screen.getByText("Sending your message...")).toBeInTheDocument();
    expect(screen.getByRole("textbox", { name: /type your message/i })).toBeDisabled();
  });

  it("shows an error and invokes retry", async () => {
    const user = userEvent.setup();
    const onRetry = vi.fn();

    render(
      <ChatContainer
        messages={mockMessages}
        onSend={vi.fn()}
        error="Unable to send your message."
        onRetry={onRetry}
      />,
    );

    expect(screen.getByRole("alert")).toHaveTextContent("Unable to send your message.");

    await user.click(screen.getByRole("button", { name: /retry/i }));

    expect(onRetry).toHaveBeenCalledOnce();
  });

  it("shows an error without a retry button when no retry callback exists", () => {
    render(
      <ChatContainer messages={mockMessages} onSend={vi.fn()} error="Something went wrong." />,
    );

    expect(screen.getByRole("alert")).toHaveTextContent("Something went wrong.");
    expect(screen.queryByRole("button", { name: /retry/i })).not.toBeInTheDocument();
  });

  it("shows the emergency message when the browser is offline", () => {
    const originalOnLine = Object.getOwnPropertyDescriptor(Navigator.prototype, "onLine");

    Object.defineProperty(navigator, "onLine", {
      configurable: true,
      value: false,
    });

    try {
      render(<ChatContainer messages={[]} onSend={vi.fn()} />);

      expect(screen.getByRole("alert")).toHaveTextContent(
        "You're offline. If this is an emergency, call 112.",
      );

      expect(screen.getByRole("textbox", { name: /type your message/i })).toBeDisabled();
    } finally {
      if (originalOnLine) {
        Object.defineProperty(navigator, "onLine", originalOnLine);
      } else {
        Reflect.deleteProperty(navigator, "onLine");
      }
    }
  });
});
