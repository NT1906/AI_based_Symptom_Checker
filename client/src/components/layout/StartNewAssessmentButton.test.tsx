/**
 * @file Unit tests for StartNewAssessmentButton component and confirmation dialog.
 *
 * Covers:
 * - Happy path: Clicking button opens confirmation alertdialog; confirming resets state and calls onConfirm.
 * - Cancellation: Clicking cancel or pressing Escape preserves state and closes dialog.
 * - Backdrop dismissal: Clicking overlay backdrop dismisses dialog.
 * - Direct execution: skipConfirm skips dialog and runs callback directly.
 * - Customization: Custom labels, dialog titles, and descriptions.
 * - Edge case: Graceful execution when onConfirm is not provided.
 *
 * Owner: Mann (Frontend + Deployment · Testing) · Task: S1-MAN-4 · Requirements: FR-25, NFR-06
 */

import { render, screen, fireEvent } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi, beforeEach } from "vitest";
import { StartNewAssessmentButton } from "./StartNewAssessmentButton";
import { useAssessmentStore } from "../../stores/assessmentStore";

describe("StartNewAssessmentButton", () => {
  beforeEach(() => {
    useAssessmentStore.setState({
      messages: [
        { id: "msg-1", role: "user", content: "I have a headache" },
        { id: "msg-2", role: "assistant", content: "How long has it lasted?" },
      ],
    });
  });

  it("renders trigger button and opens accessible confirm dialog on click (happy path)", async () => {
    const user = userEvent.setup();
    const handleConfirm = vi.fn();

    render(<StartNewAssessmentButton onConfirm={handleConfirm} />);

    const trigger = screen.getByRole("button", {
      name: /Start a new assessment from scratch/i,
    });
    expect(trigger).toBeInTheDocument();
    expect(trigger).toHaveAttribute("aria-haspopup", "dialog");
    expect(trigger).toHaveAttribute("aria-expanded", "false");

    // Click trigger to open dialog
    await user.click(trigger);

    expect(trigger).toHaveAttribute("aria-expanded", "true");
    const dialog = screen.getByRole("alertdialog");
    expect(dialog).toBeInTheDocument();
    expect(dialog).toHaveAttribute("aria-modal", "true");
    expect(screen.getByText("Start New Assessment?")).toBeInTheDocument();
    expect(screen.getByText(/Starting a new assessment will reset your current conversation/i)).toBeInTheDocument();

    // Confirm action
    const confirmBtn = screen.getByRole("button", { name: /Yes, Start Over/i });
    await user.click(confirmBtn);

    expect(handleConfirm).toHaveBeenCalledTimes(1);
    expect(screen.queryByRole("alertdialog")).not.toBeInTheDocument();
    expect(useAssessmentStore.getState().messages).toHaveLength(0);
  });

  it("cancels confirmation dialog without clearing assessment or calling callback", async () => {
    const user = userEvent.setup();
    const handleConfirm = vi.fn();

    render(<StartNewAssessmentButton onConfirm={handleConfirm} />);

    await user.click(screen.getByRole("button", { name: /Start a new assessment from scratch/i }));
    expect(screen.getByRole("alertdialog")).toBeInTheDocument();

    const cancelBtn = screen.getByRole("button", { name: /Cancel & Keep Progress/i });
    await user.click(cancelBtn);

    expect(handleConfirm).not.toHaveBeenCalled();
    expect(screen.queryByRole("alertdialog")).not.toBeInTheDocument();
    // Messages must remain intact
    expect(useAssessmentStore.getState().messages).toHaveLength(2);
  });

  it("dismisses confirmation dialog on Escape key press (keyboard accessibility)", async () => {
    const user = userEvent.setup();
    const handleConfirm = vi.fn();

    render(<StartNewAssessmentButton onConfirm={handleConfirm} />);

    await user.click(screen.getByRole("button", { name: /Start a new assessment from scratch/i }));
    expect(screen.getByRole("alertdialog")).toBeInTheDocument();

    fireEvent.keyDown(window, { key: "Escape" });

    expect(screen.queryByRole("alertdialog")).not.toBeInTheDocument();
    expect(handleConfirm).not.toHaveBeenCalled();
    expect(useAssessmentStore.getState().messages).toHaveLength(2);
  });

  it("dismisses confirmation dialog when clicking the backdrop overlay", async () => {
    const user = userEvent.setup();
    const handleConfirm = vi.fn();

    const { container } = render(<StartNewAssessmentButton onConfirm={handleConfirm} />);

    await user.click(screen.getByRole("button", { name: /Start a new assessment from scratch/i }));
    expect(screen.getByRole("alertdialog")).toBeInTheDocument();

    // Click backdrop
    const backdrop = container.querySelector(".bg-slate-900\\/60");
    expect(backdrop).not.toBeNull();
    if (backdrop) {
      fireEvent.click(backdrop);
    }

    expect(screen.queryByRole("alertdialog")).not.toBeInTheDocument();
    expect(handleConfirm).not.toHaveBeenCalled();
  });

  it("bypasses confirm dialog and executes immediately when skipConfirm is true (edge case)", async () => {
    const user = userEvent.setup();
    const handleConfirm = vi.fn();

    render(<StartNewAssessmentButton onConfirm={handleConfirm} skipConfirm={true} />);

    await user.click(screen.getByRole("button", { name: /Start a new assessment from scratch/i }));

    expect(screen.queryByRole("alertdialog")).not.toBeInTheDocument();
    expect(handleConfirm).toHaveBeenCalledTimes(1);
    expect(useAssessmentStore.getState().messages).toHaveLength(0);
  });

  it("supports custom button label, dialog title, and dialog description (customization)", async () => {
    const user = userEvent.setup();

    render(
      <StartNewAssessmentButton
        label="Reset Chat"
        dialogTitle="Clear Conversation?"
        dialogDescription="All progress will be permanently erased."
        variant="primary"
      />,
    );

    expect(screen.getByText("Reset Chat")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /Start a new assessment from scratch/i }));

    expect(screen.getByText("Clear Conversation?")).toBeInTheDocument();
    expect(screen.getByText("All progress will be permanently erased.")).toBeInTheDocument();
  });

  it("safely resets state when onConfirm is omitted (edge case)", async () => {
    const user = userEvent.setup();

    render(<StartNewAssessmentButton />);

    await user.click(screen.getByRole("button", { name: /Start a new assessment from scratch/i }));
    await user.click(screen.getByRole("button", { name: /Yes, Start Over/i }));

    expect(useAssessmentStore.getState().messages).toHaveLength(0);
  });
});
