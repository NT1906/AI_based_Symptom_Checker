
/**
 * @file Unit tests for MessageInput component.
 *
 * Verifies:
 * - Happy path: Sends a typed message.
 * - Edge case: Prevents empty and whitespace-only messages.
 * - Keyboard case: Enter sends and Shift+Enter preserves a newline.
 * - Disabled case: Prevents submission when disabled.
 *
 * Owner: Rutva · Task: S1-RUT-1 · Requirements: idea §1, §2
 */

import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MessageInput } from "./MessageInput";

describe("MessageInput", () => {
  it("sends a typed message (happy path)", async () => {
    const user = userEvent.setup();
    const handleSend = vi.fn();

    render(<MessageInput onSend={handleSend} />);

    await user.type(
      screen.getByRole("textbox", { name: /type your message/i }),
      "I have a headache.",
    );
    await user.click(screen.getByRole("button", { name: /send/i }));

    expect(handleSend).toHaveBeenCalledOnce();
    expect(handleSend).toHaveBeenCalledWith("I have a headache.");
    expect(
      screen.getByRole("textbox", { name: /type your message/i }),
    ).toHaveValue("");
  });

  it("does not send an empty or whitespace-only message (edge case)", async () => {
    const user = userEvent.setup();
    const handleSend = vi.fn();

    render(<MessageInput onSend={handleSend} />);

    const input = screen.getByRole("textbox", {
      name: /type your message/i,
    });

    expect(screen.getByRole("button", { name: /send/i })).toBeDisabled();

    await user.type(input, "   ");

    expect(screen.getByRole("button", { name: /send/i })).toBeDisabled();
    expect(handleSend).not.toHaveBeenCalled();
  });

  it("sends with Enter and preserves a newline with Shift+Enter", () => {
    const handleSend = vi.fn();

    render(<MessageInput onSend={handleSend} />);

    const input = screen.getByRole("textbox", {
      name: /type your message/i,
    });

    fireEvent.change(input, { target: { value: "First line" } });
    fireEvent.keyDown(input, { key: "Enter", shiftKey: true });

    expect(input).toHaveValue("First line");

    fireEvent.change(input, {
      target: { value: "First line\nSecond line" },
    });
    fireEvent.keyDown(input, { key: "Enter", shiftKey: false });

    expect(handleSend).toHaveBeenCalledWith("First line\nSecond line");
  });

  it("prevents submission when disabled", () => {
  const handleSend = vi.fn();
    render(<MessageInput onSend={handleSend} disabled />);

    expect(
      screen.getByRole("textbox", { name: /type your message/i }),
    ).toBeDisabled();

    expect(screen.getByRole("button", { name: /send/i })).toBeDisabled();
    expect(handleSend).not.toHaveBeenCalled();
  });
});
