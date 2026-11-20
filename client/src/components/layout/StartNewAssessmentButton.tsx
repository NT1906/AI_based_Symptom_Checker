/**
 * @file "Start new assessment" button with accessible confirmation dialog.
 *
 * Implements requirement FR-25: "Start new assessment" button, always visible,
 * with confirmation dialog to prevent accidental loss of triage progress.
 *
 * Owner: Mann (Frontend + Deployment · Testing) · Task: S1-MAN-4, S2-NIS-19 (#320 restyle) · Requirements: FR-25, NFR-06
 */

import React, { useState, useEffect, useRef } from "react";
import { RotateCcw, TriangleAlert } from "lucide-react";
import { useAssessmentStore } from "../../stores/assessmentStore";

/** Props for the StartNewAssessmentButton component. */
export interface StartNewAssessmentButtonProps {
  /** Optional callback invoked when the user confirms starting a new assessment. */
  onConfirm?: () => void;
  /** Visual presentation variant. */
  variant?: "header" | "primary" | "secondary";
  /** Custom button label text. Defaults to "Start Over". */
  label?: string;
  /** Custom title for the confirmation dialog. Defaults to "Start New Assessment?". */
  dialogTitle?: string;
  /** Custom message explanation for the dialog. */
  dialogDescription?: string;
  /** Optional additional CSS class names. */
  className?: string;
  /** Whether to skip the confirmation dialog and trigger immediately. Defaults to false. */
  skipConfirm?: boolean;
}

/**
 * Always-visible "Start new assessment" action button with accessible confirmation dialog.
 *
 * @param props - Component configuration properties.
 * @returns Rendered button and modal dialog element.
 */
export function StartNewAssessmentButton({
  onConfirm,
  variant = "header",
  label = "Start Over",
  dialogTitle = "Start New Assessment?",
  dialogDescription = "Starting a new assessment will reset your current conversation, reported symptoms, and results. Are you sure you want to start over?",
  className = "",
  skipConfirm = false,
}: StartNewAssessmentButtonProps): React.ReactElement {
  const [isOpen, setIsOpen] = useState(false);
  const cancelButtonRef = useRef<HTMLButtonElement>(null);
  const triggerButtonRef = useRef<HTMLButtonElement>(null);
  const clearMessages = useAssessmentStore((state) => state.clearMessages);

  // Focus management: focus cancel button when dialog opens
  useEffect(() => {
    if (isOpen) {
      cancelButtonRef.current?.focus();
    }
  }, [isOpen]);

  // Handle Escape key to close dialog
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (isOpen && e.key === "Escape") {
        e.preventDefault();
        setIsOpen(false);
        triggerButtonRef.current?.focus();
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isOpen]);

  const handleTriggerClick = () => {
    if (skipConfirm) {
      handleConfirm();
    } else {
      setIsOpen(true);
    }
  };

  const handleCancel = () => {
    setIsOpen(false);
    triggerButtonRef.current?.focus();
  };

  const handleConfirm = () => {
    setIsOpen(false);
    // Clear assessment store messages to reset state
    clearMessages();
    if (onConfirm) {
      onConfirm();
    }
  };

  // Variant styling
  const variantClasses = {
    header:
      "inline-flex h-10 min-w-10 items-center justify-center gap-1.5 rounded-md border border-border bg-background px-3 text-sm font-medium text-foreground shadow-xs transition hover:bg-accent hover:text-accent-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
    primary:
      "inline-flex min-h-[44px] items-center justify-center gap-2 rounded-md bg-primary px-5 py-2.5 text-sm font-semibold text-primary-foreground shadow-sm transition hover:bg-primary/90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background",
    secondary:
      "inline-flex min-h-[44px] items-center justify-center gap-2 rounded-md border border-border bg-background px-5 py-2.5 text-sm font-semibold text-foreground shadow-xs transition hover:bg-accent hover:text-accent-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
  };

  return (
    <>
      {/* Trigger Button */}
      <button
        ref={triggerButtonRef}
        type="button"
        onClick={handleTriggerClick}
        aria-haspopup="dialog"
        aria-expanded={isOpen}
        aria-label="Start a new assessment from scratch"
        className={[variantClasses[variant], className].join(" ")}
      >
        <RotateCcw className="size-4" aria-hidden="true" />
        <span className={variant === "header" ? "hidden sm:inline" : undefined}>{label}</span>
      </button>

      {/* Confirmation Modal Dialog (FR-25) */}
      {isOpen && (
        <div
          role="presentation"
          className="fixed inset-0 z-50 flex items-center justify-center p-4 sm:p-6"
        >
          {/* Backdrop Overlay */}
          <div
            data-testid="confirm-backdrop"
            className="fixed inset-0 bg-black/50 backdrop-blur-sm animate-in fade-in-0"
            onClick={handleCancel}
            aria-hidden="true"
          />

          {/* Dialog Container */}
          <div
            role="alertdialog"
            aria-modal="true"
            aria-labelledby="confirm-dialog-title"
            aria-describedby="confirm-dialog-desc"
            className="relative w-full max-w-md rounded-xl border border-border bg-card p-6 text-card-foreground shadow-2xl animate-in fade-in-0 zoom-in-95 sm:p-7"
          >
            {/* Header Icon & Title */}
            <div className="flex items-start gap-4">
              <div
                className="flex size-10 shrink-0 items-center justify-center rounded-lg bg-warning/15 text-warning"
                aria-hidden="true"
              >
                <TriangleAlert className="size-5" />
              </div>
              <div className="space-y-1">
                <h2
                  id="confirm-dialog-title"
                  className="text-lg font-semibold tracking-tight"
                >
                  {dialogTitle}
                </h2>
                <p
                  id="confirm-dialog-desc"
                  className="text-sm leading-relaxed text-muted-foreground"
                >
                  {dialogDescription}
                </p>
              </div>
            </div>

            {/* Informational Safe-Handling Note */}
            <div className="mt-4 rounded-md bg-muted p-3 text-xs text-muted-foreground">
              Your current answers will be cleared. Results already saved to your
              history are not affected.
            </div>

            {/* Action Buttons */}
            <div className="mt-6 flex flex-col-reverse gap-2 sm:flex-row sm:justify-end sm:gap-3">
              <button
                ref={cancelButtonRef}
                type="button"
                onClick={handleCancel}
                className="inline-flex h-10 items-center justify-center rounded-md border border-border bg-background px-4 text-sm font-medium transition hover:bg-accent focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
              >
                Cancel &amp; Keep Progress
              </button>
              <button
                type="button"
                onClick={handleConfirm}
                className="inline-flex h-10 items-center justify-center rounded-md bg-danger px-4 text-sm font-semibold text-danger-foreground shadow-sm transition hover:bg-danger/90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-danger focus-visible:ring-offset-2 focus-visible:ring-offset-background"
              >
                Yes, Start Over
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}

export default StartNewAssessmentButton;
