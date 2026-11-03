/**
 * @file "Start new assessment" button with accessible confirmation dialog.
 *
 * Implements requirement FR-25: "Start new assessment" button, always visible,
 * with confirmation dialog to prevent accidental loss of triage progress.
 *
 * Owner: Mann (Frontend + Deployment · Testing) · Task: S1-MAN-4 · Requirements: FR-25, NFR-06
 */

import React, { useState, useEffect, useRef } from "react";
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
      "inline-flex min-h-[44px] min-w-[44px] items-center justify-center gap-1.5 rounded-lg border border-slate-300 bg-white px-3 py-2 text-xs font-medium text-slate-700 transition hover:bg-slate-50 hover:text-slate-900 focus:outline-none focus:ring-2 focus:ring-teal-700 focus:ring-offset-2 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200 dark:hover:bg-slate-700",
    primary:
      "inline-flex min-h-[44px] items-center justify-center gap-2 rounded-xl bg-teal-600 px-5 py-2.5 text-sm font-semibold text-white shadow-xs transition hover:bg-teal-700 focus:outline-none focus:ring-4 focus:ring-teal-500/40",
    secondary:
      "inline-flex min-h-[44px] items-center justify-center gap-2 rounded-xl border border-slate-300 bg-white px-5 py-2.5 text-sm font-semibold text-slate-800 shadow-xs transition hover:bg-slate-50 focus:outline-none focus:ring-4 focus:ring-slate-300 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200 dark:hover:bg-slate-700",
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
        <span aria-hidden="true">🔄</span>
        <span>{label}</span>
      </button>

      {/* Confirmation Modal Dialog (FR-25) */}
      {isOpen && (
        <div
          role="presentation"
          className="fixed inset-0 z-50 flex items-center justify-center p-4 sm:p-6"
        >
          {/* Backdrop Overlay */}
          <div
            className="fixed inset-0 bg-slate-900/60 backdrop-blur-xs transition-opacity"
            onClick={handleCancel}
            aria-hidden="true"
          />

          {/* Dialog Container */}
          <div
            role="alertdialog"
            aria-modal="true"
            aria-labelledby="confirm-dialog-title"
            aria-describedby="confirm-dialog-desc"
            className="relative w-full max-w-md rounded-2xl border border-slate-200 bg-white p-6 shadow-2xl transition-all sm:p-7 dark:border-slate-800 dark:bg-slate-900"
          >
            {/* Header Icon & Title */}
            <div className="flex items-start gap-4">
              <div
                className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-amber-100 text-xl text-amber-700 dark:bg-amber-950/60 dark:text-amber-300"
                aria-hidden="true"
              >
                ⚠️
              </div>
              <div className="space-y-1">
                <h2
                  id="confirm-dialog-title"
                  className="text-lg font-bold text-slate-900 sm:text-xl dark:text-slate-100"
                >
                  {dialogTitle}
                </h2>
                <p
                  id="confirm-dialog-desc"
                  className="text-xs leading-relaxed text-slate-600 sm:text-sm dark:text-slate-400"
                >
                  {dialogDescription}
                </p>
              </div>
            </div>

            {/* Informational Safe-Handling Note */}
            <div className="mt-4 rounded-lg bg-slate-50 p-3 text-[11px] text-slate-500 dark:bg-slate-800/60 dark:text-slate-400">
              Session data is maintained in-memory only and is never stored permanently.
            </div>

            {/* Action Buttons */}
            <div className="mt-6 flex flex-col-reverse gap-2 sm:flex-row sm:justify-end sm:gap-3">
              <button
                ref={cancelButtonRef}
                type="button"
                onClick={handleCancel}
                className="inline-flex min-h-[44px] items-center justify-center rounded-xl border border-slate-300 bg-white px-4 py-2.5 text-xs font-semibold text-slate-700 transition hover:bg-slate-50 focus:outline-none focus:ring-2 focus:ring-teal-700 focus:ring-offset-2 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200 dark:hover:bg-slate-700"
              >
                Cancel &amp; Keep Progress
              </button>
              <button
                type="button"
                onClick={handleConfirm}
                className="inline-flex min-h-[44px] items-center justify-center rounded-xl bg-rose-600 px-4 py-2.5 text-xs font-semibold text-white shadow-xs transition hover:bg-rose-700 focus:outline-none focus:ring-2 focus:ring-rose-600 focus:ring-offset-2"
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
