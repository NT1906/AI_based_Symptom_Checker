/**
 * @file UrgentCareAlert — full-screen overlay shown for URGENT risk results.
 * Owner: Dimple · Task: S1-DIM-3 · Requirements: FR-06, FR-15, DR-02
 *
 * Per DR-02 and AI_RULES.md §2 rule 5:
 * - 112 (Unified Emergency) is displayed FIRST and LARGEST.
 * - 108 (Ambulance) is listed as the secondary number.
 * - The mandatory disclaimer is shown (AI_RULES.md §2 rule 8).
 * - No diagnosis language is used.
 */

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
 * @param props - {@link UrgentCareAlertProps}
 * @returns A full-screen alert dialog element.
 */
export function UrgentCareAlert({ onDismiss }: UrgentCareAlertProps) {
  return (
    <div
      role="alertdialog"
      aria-modal="true"
      aria-labelledby="urgent-title"
      aria-describedby="urgent-body"
      className="fixed inset-0 z-50 flex items-center justify-center bg-red-950/85 p-4 backdrop-blur-md"
    >
      <div className="w-full max-w-md overflow-hidden rounded-3xl bg-white shadow-2xl ring-1 ring-red-500/20">
        {/* Header with emergency alert tone */}
        <div className="bg-gradient-to-b from-red-600 to-red-700 px-6 py-6 text-center text-white">
          <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-2xl bg-white/10 text-3xl shadow-inner">
            🚨
          </div>
          <h1
            id="urgent-title"
            className="mt-3 text-2xl font-black tracking-tight"
          >
            Urgent Care Needed
          </h1>
          <p className="mt-1 text-xs font-medium text-red-100">
            Immediate Clinical Assessment Required
          </p>
        </div>

        {/* Body */}
        <div id="urgent-body" className="px-6 py-6 text-center">
          <p className="text-sm font-medium text-slate-700">
            Based on the reported symptoms, you may require{" "}
            <strong className="text-red-700">immediate emergency medical attention</strong>.
          </p>

          {/* Emergency numbers — 112 first and largest (DR-02) */}
          <div className="mt-6 space-y-3">
            {/* 112 — primary, largest */}
            <a
              href={`tel:${EMERGENCY_UNIFIED}`}
              aria-label={`Call ${EMERGENCY_UNIFIED} — Unified Emergency (Police, Fire, Ambulance)`}
              className="group flex w-full items-center justify-center gap-4 rounded-2xl bg-red-600 p-4 text-white shadow-lg shadow-red-600/30 transition-all hover:bg-red-700 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-red-600 active:scale-[0.99]"
            >
              <span className="text-3xl font-black tracking-wider">
                {EMERGENCY_UNIFIED}
              </span>
              <span className="text-left">
                <span className="block text-sm font-bold leading-tight">
                  Unified Emergency
                </span>
                <span className="text-[11px] font-medium text-red-100">
                  Police · Fire · Ambulance
                </span>
              </span>
            </a>

            {/* 108 — secondary, smaller */}
            <a
              href={`tel:${EMERGENCY_AMBULANCE}`}
              aria-label={`Call ${EMERGENCY_AMBULANCE} — Ambulance (Medical Emergencies)`}
              className="flex w-full items-center justify-center gap-3 rounded-2xl border border-red-200 bg-red-50/80 p-3.5 text-red-800 transition hover:bg-red-100 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-red-400"
            >
              <span className="text-2xl font-extrabold tracking-wide">
                {EMERGENCY_AMBULANCE}
              </span>
              <span className="text-left">
                <span className="block text-xs font-bold leading-tight">
                  Ambulance
                </span>
                <span className="text-[10px] text-red-600">
                  Medical Emergencies
                </span>
              </span>
            </a>
          </div>

          <p className="mt-4 text-xs font-medium text-slate-500">
            Or go directly to the nearest emergency room.
          </p>

          {/* Mandatory disclaimer (AI_RULES.md §2 rule 8) */}
          <div className="mt-5 rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-left">
            <p className="text-[11px] leading-relaxed text-slate-500">
              <strong>Medical Disclaimer:</strong> This is not a medical diagnosis. Always consult a qualified healthcare professional.
            </p>
          </div>
        </div>

        {/* Dismiss Button */}
        <div className="border-t border-slate-100 bg-slate-50/60 px-6 py-4 text-center">
          <button
            type="button"
            onClick={onDismiss}
            className="w-full rounded-xl border border-slate-300 bg-white py-2.5 text-xs font-bold text-slate-700 shadow-sm transition hover:bg-slate-50"
          >
            Continue to Full Result
          </button>
        </div>
      </div>
    </div>
  );
}
