/**
 * @file UrgentCareAlert — full-screen overlay shown for URGENT risk results.
 * Owner: Dimple · Task: S1-DIM-3, S2-DIM-5 · Requirements: FR-06, FR-15, DR-02, NFR-06
 * Restyle (design tokens, lucide icons, dark mode): Nisarg · S2-NIS-22 (#323)
 *
 * Per DR-02 and AI_RULES.md §2 rule 5:
 * - 112 (Unified Emergency) is displayed FIRST and LARGEST.
 * - 108 (Ambulance) is listed as the secondary number.
 * - The mandatory disclaimer is shown (AI_RULES.md §2 rule 8).
 * - No diagnosis language is used.
 *
 * Implements WCAG 2.1 Level AA modal alertdialog standards (NFR-06):
 * - Traps Tab focus inside the dialog container.
 * - Auto-focuses the primary 112 emergency action on mount.
 * - Closes and dismisses on Escape key press.
 * - Meets 44px touch targets and high-contrast text requirements.
 */

import { Siren } from "lucide-react";
import { useRef } from "react";
import { useFocusTrap } from "../../lib/useFocusTrap";

/** Props for the UrgentCareAlert component. */
export type UrgentCareAlertProps = {
  /** Called when the user dismisses the alert to continue viewing the result. */
  onDismiss: () => void;
};

/** Emergency number constants — named so they never appear as magic values. */
const EMERGENCY_UNIFIED = "112" as const;
const EMERGENCY_AMBULANCE = "108" as const;

/**
 * Full-screen urgent-care alert that is displayed whenever the risk engine
 * returns URGENT. Emergency number 112 is shown first and most prominently
 * (DR-02, AI_RULES.md §2 rule 5).
 *
 * @param props - Component props.
 * @returns A full-screen alert dialog element.
 */
export function UrgentCareAlert({ onDismiss }: UrgentCareAlertProps) {
  const dialogRef = useRef<HTMLDivElement>(null);
  const primaryEmergencyRef = useRef<HTMLAnchorElement>(null);

  // WAI-ARIA alertdialog focus trap and Escape key dismissal (WCAG 2.1 AA, NFR-06)
  useFocusTrap(dialogRef, {
    onEscape: onDismiss,
    initialFocusRef: primaryEmergencyRef,
  });

  return (
    <div
      ref={dialogRef}
      role="alertdialog"
      data-testid="urgent-alert"
      aria-modal="true"
      aria-labelledby="urgent-title"
      aria-describedby="urgent-body"
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4 backdrop-blur-md animate-in fade-in duration-200 motion-reduce:animate-none"
    >
      <div className="w-full max-w-md overflow-hidden rounded-xl bg-card shadow-2xl ring-1 ring-danger/40">
        {/* Header with emergency alert tone */}
        <div className="bg-danger px-6 py-6 text-center text-danger-foreground">
          <div
            className="mx-auto flex size-14 items-center justify-center rounded-xl bg-white/15 shadow-inner"
            aria-hidden="true"
          >
            <Siren className="size-7" aria-hidden="true" />
          </div>
          <h1
            id="urgent-title"
            className="mt-3 text-2xl font-black tracking-tight"
          >
            Urgent Care Needed
          </h1>
          <p className="mt-1 text-xs font-semibold text-danger-foreground/90">
            Immediate Clinical Assessment Required
          </p>
        </div>

        {/* Body */}
        <div id="urgent-body" className="px-6 py-6 text-center">
          <p className="text-sm font-medium text-foreground">
            Based on the reported symptoms, you may require{" "}
            <strong className="text-danger-strong">immediate emergency medical attention</strong>.
          </p>

          {/* Emergency numbers — 112 first and largest (DR-02) */}
          <div className="mt-6 space-y-3">
            {/* 112 — primary, largest */}
            <a
              ref={primaryEmergencyRef}
              href={`tel:${EMERGENCY_UNIFIED}`}
              aria-label={`Call ${EMERGENCY_UNIFIED} — Unified Emergency (Police, Fire, Ambulance)`}
              className="group flex min-h-[56px] w-full items-center justify-center gap-4 rounded-xl bg-danger p-4 text-danger-foreground shadow-lg shadow-danger/20 transition-all hover:bg-danger/90 focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-danger/40 focus-visible:ring-offset-2 active:scale-[0.99]"
            >
              <span className="text-3xl font-black tracking-wider">
                {EMERGENCY_UNIFIED}
              </span>
              <span className="text-left">
                <span className="block text-sm font-bold leading-tight">
                  Unified Emergency
                </span>
                <span className="text-xs font-medium text-danger-foreground">
                  Police · Fire · Ambulance
                </span>
              </span>
            </a>

            {/* 108 — secondary, smaller */}
            <a
              href={`tel:${EMERGENCY_AMBULANCE}`}
              aria-label={`Call ${EMERGENCY_AMBULANCE} — Ambulance (Medical Emergencies)`}
              className="flex min-h-[48px] w-full items-center justify-center gap-3 rounded-xl border border-danger/25 bg-danger/5 p-3.5 text-danger-strong transition hover:bg-danger/15 focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-danger/40 focus-visible:ring-offset-2"
            >
              <span className="text-2xl font-extrabold tracking-wide">
                {EMERGENCY_AMBULANCE}
              </span>
              <span className="text-left">
                <span className="block text-xs font-bold leading-tight">
                  Ambulance
                </span>
                <span className="text-[11px] font-semibold text-danger-strong">
                  Medical Emergencies
                </span>
              </span>
            </a>
          </div>

          <p className="mt-4 text-xs font-medium text-muted-foreground">
            Or go directly to the nearest emergency room.
          </p>

          {/* Mandatory disclaimer (AI_RULES.md §2 rule 8) */}
          <div className="mt-5 rounded-xl border border-border bg-muted/60 px-4 py-3 text-left">
            <p className="text-xs leading-relaxed text-muted-foreground">
              <strong>Medical Disclaimer:</strong> This is not a medical diagnosis. Always consult a qualified healthcare professional.
            </p>
          </div>
        </div>

        {/* Dismiss Button */}
        <div className="border-t border-border bg-muted/60 px-6 py-4 text-center">
          <button
            type="button"
            onClick={onDismiss}
            className="inline-flex min-h-[44px] w-full items-center justify-center rounded-xl border border-input bg-card py-2.5 text-xs font-bold text-muted-foreground shadow-xs transition hover:bg-muted/60 focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-ring"
          >
            Continue to Full Result
          </button>
        </div>
      </div>
    </div>
  );
}

export default UrgentCareAlert;
