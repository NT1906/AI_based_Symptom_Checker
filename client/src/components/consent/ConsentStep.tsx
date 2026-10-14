/**
 * @file Consent step modal shown before any assessment data is saved.
 * Owner: Dimple · Task: S1-DIM-1 · Requirements: DR-08
 *
 * Displays the consent agreement copy and records acceptance via POST /consents
 * before the user can proceed. If the user declines or the call fails they
 * cannot continue — no data is saved without consent (DR-08).
 */

import { useMutation } from "@tanstack/react-query";
import { useState } from "react";
import {
  CURRENT_POLICY_VERSION,
  postConsent,
} from "../../services/consentApi";
import { useConsentStore } from "../../stores/consentStore";

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
 * @param props - {@link ConsentStepProps}
 * @returns A modal dialog requesting the user's informed consent.
 */
export function ConsentStep({ onConsented, onDeclined }: ConsentStepProps) {
  const [hasChecked, setHasChecked] = useState(false);
  const recordConsent = useConsentStore((s) => s.recordConsent);

  const mutation = useMutation({
    mutationFn: () => postConsent(CURRENT_POLICY_VERSION),
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
      role="dialog"
      aria-modal="true"
      aria-labelledby="consent-title"
      aria-describedby="consent-body"
      className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 p-4 backdrop-blur-sm"
    >
      <div className="w-full max-w-lg overflow-hidden rounded-2xl bg-white shadow-2xl ring-1 ring-slate-900/10">
        {/* Header */}
        <div className="border-b border-slate-100 bg-slate-50/60 px-6 py-5">
          <div className="flex items-center gap-2">
            <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-teal-100 text-sm">
              🛡️
            </span>
            <span className="rounded-full bg-teal-50 px-2.5 py-0.5 text-[11px] font-bold text-teal-800">
              DPDP Act 2023
            </span>
          </div>
          <h1
            id="consent-title"
            className="mt-2 text-xl font-bold tracking-tight text-slate-900"
          >
            Your Consent Is Required
          </h1>
          <p className="mt-1 text-xs text-slate-500">
            Please read and agree to our clinical safety terms before continuing.
          </p>
        </div>

        {/* Body */}
        <div className="px-6 py-5">
          <pre
            id="consent-body"
            className="max-h-56 overflow-y-auto whitespace-pre-wrap rounded-xl border border-slate-200 bg-slate-50 p-4 font-sans text-xs leading-relaxed text-slate-700"
          >
            {CONSENT_TEXT}
          </pre>

          {/* Checkbox */}
          <label className="mt-4 flex cursor-pointer items-start gap-3 rounded-lg border border-slate-100 bg-slate-50/50 p-3 transition hover:bg-slate-50">
            <input
              type="checkbox"
              checked={hasChecked}
              onChange={(e) => setHasChecked(e.target.checked)}
              aria-label="I have read and agree to the terms above"
              className="mt-0.5 h-4 w-4 shrink-0 rounded border-slate-300 text-teal-600 focus:ring-teal-500"
            />
            <span className="text-xs font-semibold text-slate-800">
              I have read and agree to the terms above.
            </span>
          </label>

          {/* API error */}
          {mutation.isError && (
            <p role="alert" className="mt-3 text-xs font-semibold text-red-600">
              {mutation.error instanceof Error
                ? mutation.error.message
                : "Unable to record consent. Please try again."}
            </p>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-end gap-3 border-t border-slate-100 bg-slate-50/40 px-6 py-4">
          <button
            type="button"
            onClick={onDeclined}
            disabled={mutation.isPending}
            className="rounded-lg border border-slate-300 bg-white px-4 py-2 text-xs font-bold text-slate-700 shadow-sm transition hover:bg-slate-50 disabled:opacity-50"
          >
            Decline
          </button>
          <button
            type="button"
            onClick={handleAgree}
            disabled={!hasChecked || mutation.isPending}
            aria-disabled={!hasChecked || mutation.isPending}
            className="rounded-lg bg-teal-600 px-5 py-2 text-xs font-bold text-white shadow-sm transition hover:bg-teal-700 disabled:cursor-not-allowed disabled:opacity-40"
          >
            {mutation.isPending ? "Recording…" : "I Agree"}
          </button>
        </div>
      </div>
    </div>
  );
}
