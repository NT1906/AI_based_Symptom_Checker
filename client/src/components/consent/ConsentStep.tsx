/**
 * @file Consent step modal shown before any assessment data is saved.
 * Restyle: Nisarg · Task: S2-NIS-20 · Issue: #321
 * Owner: Dimple · Task: S1-DIM-1, S2-DIM-5 · Requirements: DR-08, NFR-06
 *
 * Displays the consent agreement copy and records acceptance via POST /consents
 * before the user can proceed. If the user declines or the call fails they
 * cannot continue — no data is saved without consent (DR-08).
 *
 * Implements WCAG 2.1 Level AA modal dialog standards (NFR-06):
 * - Traps Tab focus inside the dialog container.
 * - Closes and declines on Escape key press.
 * - Meets 44px touch targets and high-contrast text requirements.
 */

import { useMutation } from "@tanstack/react-query";
import { useRef, useState } from "react";
import { useFocusTrap } from "../../lib/useFocusTrap";
import {
  CURRENT_POLICY_VERSION,
  getCurrentPolicyVersion,
  postConsent,
} from "../../services/consentApi";
import { useConsentStore } from "../../stores/consentStore";
import { ShieldCheck } from "lucide-react";

/** Props for the ConsentStep component. */
export type ConsentStepProps = {
  /** Called after consent is successfully recorded on the server. */
  onConsented: () => void;
  /** Called when the user explicitly declines consent. */
  onDeclined: () => void;
};

/** Verbatim consent agreement text shown to the user (DR-08). */
const CONSENT_TEXT = `By using this symptom checker you agree that:

• This tool provides general health information only. It is NOT a medical diagnosis, prescription, or professional medical advice.
• Your symptom information will be processed to generate a triage suggestion. No data is shared with third parties without your consent.
• We collect and process your data in accordance with the DPDP Act 2023. You may withdraw consent and request deletion at any time.
• In a medical emergency, call 112 (Unified Emergency) or go to the nearest emergency department immediately.

Always consult a qualified healthcare professional for any medical concern.`;

/**
 * Full-screen consent step that must be completed before any assessment data
 * is stored. Uses TanStack Query's useMutation to call POST /consents.
 *
 * @param props - Component props.
 * @returns A modal dialog requesting the user's informed consent.
 */
export function ConsentStep({ onConsented, onDeclined }: ConsentStepProps) {
  const dialogRef = useRef<HTMLDivElement>(null);
  const [hasChecked, setHasChecked] = useState(false);
  const recordConsent = useConsentStore((s) => s.recordConsent);

  // WAI-ARIA Modal focus trap and Escape key dismissal (WCAG 2.1 AA, NFR-06)
  useFocusTrap(dialogRef, {
    onEscape: onDeclined,
  });

  const mutation = useMutation({
    mutationFn: async () => {
      const activeVersion = await getCurrentPolicyVersion();
      if (activeVersion !== CURRENT_POLICY_VERSION) {
        throw new Error("The privacy notice has changed. Refresh to see the latest version.");
      }
      return postConsent(CURRENT_POLICY_VERSION);
    },
    onSuccess: (data) => {
      recordConsent(data.consentId, CURRENT_POLICY_VERSION);
      onConsented();
    },
  });

  const handleAgree = () => {
    if (hasChecked) {
      mutation.mutate();
    }
  };

  return (
    <div
      ref={dialogRef}
      role="dialog"
      aria-modal="true"
      aria-labelledby="consent-title"
      aria-describedby="consent-body"
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4 backdrop-blur-sm animate-in fade-in-0"
    >
      <div className="w-full max-w-lg overflow-hidden rounded-xl border border-border bg-card text-card-foreground shadow-2xl animate-in fade-in-0 zoom-in-95">
        {/* Header */}
        <div className="border-b border-border bg-muted/40 px-6 py-5">
          <div className="flex items-center gap-2">
            <span
              className="flex size-8 items-center justify-center rounded-lg bg-primary/10 text-primary"
              aria-hidden="true"
            >
              <ShieldCheck className="size-4" />
            </span>
            <span className="rounded-full border border-primary/20 bg-primary/10 px-2.5 py-0.5 text-[11px] font-medium text-primary">
              DPDP Act 2023
            </span>
          </div>
          <h2
            id="consent-title"
            className="mt-3 text-xl font-semibold tracking-tight"
          >
            Your Consent Is Required
          </h2>
          <p className="mt-1 text-sm text-muted-foreground">
            Please read and agree to our clinical safety terms before continuing.
          </p>
        </div>

        {/* Body */}
        <div className="px-6 py-5">
          <pre
            id="consent-body"
            className="max-h-56 overflow-y-auto whitespace-pre-wrap rounded-lg border border-border bg-muted/50 p-4 font-sans text-xs leading-relaxed text-muted-foreground"
          >
            {CONSENT_TEXT}
          </pre>

          {/* Checkbox */}
          <label className="mt-4 flex min-h-[44px] cursor-pointer items-start gap-3 rounded-lg border border-border p-3 transition hover:bg-accent/50">
            <input
              type="checkbox"
              checked={hasChecked}
              onChange={(e) => setHasChecked(e.target.checked)}
              aria-label="I have read and agree to the terms above"
              className="mt-0.5 size-4 shrink-0 rounded border-input accent-primary focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-hidden"
            />
            <span className="text-sm font-medium">
              I have read and agree to the terms above.
            </span>
          </label>

          {/* API error */}
          {mutation.isError && (
            <p role="alert" className="mt-3 text-sm font-medium text-destructive">
              {mutation.error instanceof Error
                ? mutation.error.message
                : "Unable to record consent. Please try again."}
            </p>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-end gap-3 border-t border-border bg-muted/30 px-6 py-4">
          <button
            type="button"
            onClick={onDeclined}
            disabled={mutation.isPending}
            className="inline-flex h-10 items-center justify-center rounded-md border border-border bg-background px-4 text-sm font-medium shadow-xs transition hover:bg-accent focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-hidden disabled:opacity-50"
          >
            Decline
          </button>
          <button
            type="button"
            onClick={handleAgree}
            disabled={!hasChecked || mutation.isPending}
            aria-disabled={!hasChecked || mutation.isPending}
            className="inline-flex h-10 items-center justify-center rounded-md bg-primary px-5 text-sm font-semibold text-primary-foreground shadow-sm transition hover:bg-primary/90 focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background focus-visible:outline-hidden disabled:cursor-not-allowed disabled:opacity-40"
          >
            {mutation.isPending ? "Recording…" : "I Agree"}
          </button>
        </div>
      </div>
    </div>
  );
}
