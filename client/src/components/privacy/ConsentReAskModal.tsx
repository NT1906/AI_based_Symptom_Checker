/**
 * @file ConsentReAskModal — re-consent modal when privacy policy version changes.
 * Owner: Dimple · Task: S2-DIM-3 · Requirements: DR-06, DR-08
 *
 * Implements DPDP Act 2023 Section 5 and DR-08:
 * - Automatically prompts users to re-consent whenever the active policy version
 * differs from their stored consent record.
 * - Explains key statutory policy updates clearly.
 * - Allows affirmative re-consent or graceful withdrawal with data clearing.
 */

import React, { useState } from "react";
import { postConsent, CURRENT_POLICY_VERSION } from "../../services/consentApi";
import { isConsentOutdated } from "../../services/privacyApi";
import { useConsentStore } from "../../stores/consentStore";
import {
  COLOR_TOKENS,
  SHADOW_TOKENS,
  ACCESSIBILITY_TOKENS,
} from "../../theme/tokens";

/** Props for the ConsentReAskModal component. */
export interface ConsentReAskModalProps {
  /** Optional override to force open the modal regardless of store version. */
  forceOpen?: boolean;
  /** Callback fired after successful affirmative re-consent. */
  onReConsented?: (consentId: string) => void;
  /** Callback fired if the user declines the updated policy. */
  onDeclined?: () => void;
}

/**
 * Modal dialog that prompts the user for affirmative re-consent when the
 * privacy policy version has been updated (DR-08).
 *
 * @param props - Component properties.
 * @returns Rendered modal element or null if consent is already current.
 */
export function ConsentReAskModal({
  forceOpen = false,
  onReConsented,
  onDeclined,
}: ConsentReAskModalProps): React.ReactElement | null {
  const { policyVersion, recordConsent, clearConsent } = useConsentStore();
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const isOutdated = isConsentOutdated(policyVersion);
  const shouldShow = forceOpen || isOutdated;

  if (!shouldShow) {
    return null;
  }

  /* ------------------------------------------------------------------ */
  /*  Handlers                                                          */
  /* ------------------------------------------------------------------ */
  const handleAcceptUpdatedPolicy = async (): Promise<void> => {
    setIsSubmitting(true);
    setErrorMessage(null);

    try {
      const response = await postConsent(CURRENT_POLICY_VERSION);
      recordConsent(response.consentId, CURRENT_POLICY_VERSION);

      if (onReConsented) {
        onReConsented(response.consentId);
      }
    } catch {
      setErrorMessage(
        "Unable to record your updated consent. Please check your connection and try again.",
      );
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleDecline = (): void => {
    clearConsent();
    if (onDeclined) {
      onDeclined();
    }
  };

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="reask-modal-title"
      aria-describedby="reask-modal-desc"
      className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/80 p-4 backdrop-blur-xs animate-in fade-in duration-200"
    >
      <div
        className="w-full max-w-lg rounded-3xl bg-white p-6 shadow-2xl space-y-5 sm:p-8"
        style={{
          boxShadow: SHADOW_TOKENS.lg,
          background: COLOR_TOKENS.neutral.surface,
        }}
      >
        {/* Header */}
        <div className="space-y-1.5 border-b border-slate-100 pb-4">
          <div className="flex items-center gap-2">
            <span
              className="inline-flex items-center gap-1.5 rounded-full border border-teal-300 bg-teal-50 px-2.5 py-0.5 text-xs font-bold text-teal-800"
              role="status"
            >
              <span>Version {CURRENT_POLICY_VERSION}</span>
            </span>
            <span className="text-xs font-semibold uppercase tracking-wider text-slate-500">
              Policy Update (DR-08)
            </span>
          </div>

          <h2
            id="reask-modal-title"
            className="text-xl font-bold tracking-tight text-slate-900 sm:text-2xl"
          >
            Updated Privacy &amp; Data Notice
          </h2>
          <p id="reask-modal-desc" className="text-xs text-slate-600 sm:text-sm">
            We have updated our Privacy Policy to enhance protections under the{" "}
            <strong>Digital Personal Data Protection Act, 2023</strong>. Because
            this affects how health information is handled, we require your
            renewed consent before continuing.
          </p>
        </div>

        {/* Key Highlights */}
        <div className="space-y-2 rounded-2xl border border-slate-200 bg-slate-50 p-4 text-xs sm:text-sm text-slate-700">
          <h3 className="font-bold text-slate-900">
            Summary of Key Policy Terms:
          </h3>
          <ul className="space-y-1.5 list-disc pl-5 leading-relaxed">
            <li>
              <strong>Statutory Rights:</strong> Instant self-service data export
              and permanent erasure controls are now accessible at any time.
            </li>
            <li>
              <strong>Automatic 24-Hour TTL:</strong> Unregistered guest
              assessment data is automatically purged after 24 hours.
            </li>
            <li>
              <strong>Zero Biometric Storage:</strong> Uploaded symptom images
              are processed strictly in volatile memory and never persisted.
            </li>
          </ul>
        </div>

        {/* Error notice */}
        {errorMessage && (
          <div
            role="alert"
            className="rounded-xl border border-rose-300 bg-rose-50 p-3 text-xs font-medium text-rose-900 sm:text-sm"
          >
            ⚠️ {errorMessage}
          </div>
        )}

        {/* Actions */}
        <div className="flex flex-col-reverse sm:flex-row sm:justify-end gap-3 pt-2">
          <button
            type="button"
            onClick={handleDecline}
            disabled={isSubmitting}
            className="inline-flex min-h-[44px] items-center justify-center rounded-xl border border-slate-300 bg-white px-4 py-2.5 text-xs font-semibold text-slate-700 transition hover:bg-slate-100 sm:text-sm"
            style={{ minHeight: ACCESSIBILITY_TOKENS.minTouchTarget }}
          >
            Decline &amp; Clear Session
          </button>
          <button
            type="button"
            onClick={() => void handleAcceptUpdatedPolicy()}
            disabled={isSubmitting}
            aria-busy={isSubmitting}
            className="inline-flex min-h-[44px] items-center justify-center gap-2 rounded-xl bg-teal-700 px-5 py-2.5 text-xs font-semibold text-white shadow-xs transition hover:bg-teal-800 disabled:opacity-60 sm:text-sm"
            style={{ minHeight: ACCESSIBILITY_TOKENS.minTouchTarget }}
          >
            <span>{isSubmitting ? "Recording Consent…" : "I Agree & Continue"}</span>
          </button>
        </div>
      </div>
    </div>
  );
}

export default ConsentReAskModal;
