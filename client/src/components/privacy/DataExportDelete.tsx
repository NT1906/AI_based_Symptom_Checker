/**
 * @file DataExportDelete — privacy controls for statutory data export and permanent deletion.
 * Owner: Dimple · Task: S2-DIM-3 · Requirements: DR-06, DR-08
 *
 * Implements DPDP Act 2023 user rights:
 * - Export: self-service download of personal and assessment records in JSON.
 * - Deletion: permanent cascading erasure of all stored and session data with
 * explicit affirmative confirmation and irreversibility warnings.
 */

import React, { useState } from "react";
import {
  fetchUserDataExport,
  deleteUserData,
  triggerJsonDownload,
  type UserDataExport,
} from "../../services/privacyApi";
import { useConsentStore } from "../../stores/consentStore";
import { useAssessmentStore } from "../../stores/assessmentStore";
import {
  COLOR_TOKENS,
  SHADOW_TOKENS,
  ACCESSIBILITY_TOKENS,
} from "../../theme/tokens";

/** Props for the DataExportDelete component. */
export interface DataExportDeleteProps {
  /** Optional callback invoked after data deletion completes. */
  onDataDeleted?: () => void;
  /** Optional callback invoked after data export is downloaded. */
  onDataExported?: (data: UserDataExport) => void;
  /** Optional custom CSS classes. */
  className?: string;
}

/**
 * Self-service privacy control panel allowing users to export or permanently
 * delete their personal triage records.
 *
 * @param props - Component properties.
 * @returns Rendered privacy controls element.
 */
export function DataExportDelete({
  onDataDeleted,
  onDataExported,
  className = "",
}: DataExportDeleteProps): React.ReactElement {
  const consentStore = useConsentStore();
  const assessmentStore = useAssessmentStore();

  const [isExporting, setIsExporting] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);
  const [showConfirmModal, setShowConfirmModal] = useState(false);
  const [statusMessage, setStatusMessage] = useState<{
    type: "success" | "error";
    text: string;
  } | null>(null);

  /* ------------------------------------------------------------------ */
  /*  Export Handler                                                    */
  /* ------------------------------------------------------------------ */
  const handleExport = async (): Promise<void> => {
    setIsExporting(true);
    setStatusMessage(null);

    try {
      const exportData = await fetchUserDataExport({
        consentId: consentStore.consentId,
        consentedAt: consentStore.consentedAt,
        policyVersion: consentStore.policyVersion,
        assessmentId: assessmentStore.assessmentId,
        symptomsCount: assessmentStore.messages?.length ?? 0,
      });

      triggerJsonDownload(
        exportData,
        `symptom-checker-data-export-${new Date().toISOString().slice(0, 10)}.json`,
      );

      setStatusMessage({
        type: "success",
        text: "Your data has been successfully exported and downloaded.",
      });

      if (onDataExported) {
        onDataExported(exportData);
      }
    } catch {
      setStatusMessage({
        type: "error",
        text: "Unable to generate your data export. Please try again.",
      });
    } finally {
      setIsExporting(false);
    }
  };

  /* ------------------------------------------------------------------ */
  /*  Deletion Handler                                                  */
  /* ------------------------------------------------------------------ */
  const handleConfirmDelete = async (): Promise<void> => {
    setIsDeleting(true);
    setStatusMessage(null);

    try {
      await deleteUserData();

      // Clear all client stores (DR-06 compliance: zero persistence)
      consentStore.clearConsent();
      assessmentStore.clearAssessment();

      setShowConfirmModal(false);
      setStatusMessage({
        type: "success",
        text: "All your data has been permanently deleted from our servers and this browser session.",
      });

      if (onDataDeleted) {
        onDataDeleted();
      }
    } catch {
      setShowConfirmModal(false);
      setStatusMessage({
        type: "error",
        text: "Unable to complete data deletion. Please try again.",
      });
    } finally {
      setIsDeleting(false);
    }
  };

  return (
    <div className={`space-y-6 ${className}`}>
      {/* Status banner */}
      {statusMessage && (
        <div
          role={statusMessage.type === "error" ? "alert" : "status"}
          aria-live="polite"
          className={`rounded-xl p-4 text-sm font-medium ${
            statusMessage.type === "success"
              ? "border border-emerald-300 bg-emerald-50 text-emerald-900"
              : "border border-rose-300 bg-rose-50 text-rose-900"
          }`}
        >
          {statusMessage.type === "success" ? "✓ " : "⚠️ "}
          {statusMessage.text}
        </div>
      )}

      {/* Grid of privacy actions */}
      <div className="grid gap-6 md:grid-cols-2">
        {/* Action 1: Export My Data */}
        <section
          aria-labelledby="export-card-heading"
          className="flex flex-col justify-between rounded-2xl border border-slate-200 bg-white p-5 shadow-xs transition sm:p-6"
          style={{ boxShadow: SHADOW_TOKENS.sm }}
        >
          <div className="space-y-2">
            <div className="flex items-center gap-2 text-teal-800">
              <span className="text-xl" aria-hidden="true">
                📥
              </span>
              <h3
                id="export-card-heading"
                className="text-base font-bold text-slate-900 sm:text-lg"
              >
                Export My Data
              </h3>
            </div>
            <p className="text-xs text-slate-600 leading-relaxed sm:text-sm">
              Download a structured, human-readable JSON file containing all
              assessments, confirmed symptoms, timestamps, and active consent
              records linked to your session.
            </p>
            <p className="text-xs text-slate-500 font-medium">
              Statutory Right: Section 11, DPDP Act 2023 (Right to Access).
            </p>
          </div>

          <div className="pt-4">
            <button
              type="button"
              onClick={() => void handleExport()}
              disabled={isExporting}
              aria-busy={isExporting}
              className="inline-flex w-full items-center justify-center gap-2 rounded-xl border border-teal-700 bg-teal-50 px-4 py-2.5 text-xs font-semibold text-teal-800 transition hover:bg-teal-100 focus:outline-none focus:ring-4 focus:ring-teal-500/20 disabled:cursor-not-allowed disabled:opacity-60 sm:text-sm"
              style={{ minHeight: ACCESSIBILITY_TOKENS.minTouchTarget }}
            >
              <span>{isExporting ? "Generating Export…" : "Download Data Export (JSON)"}</span>
            </button>
          </div>
        </section>

        {/* Action 2: Delete All My Data */}
        <section
          aria-labelledby="delete-card-heading"
          className="flex flex-col justify-between rounded-2xl border border-rose-200 bg-rose-50/40 p-5 shadow-xs transition sm:p-6"
          style={{ boxShadow: SHADOW_TOKENS.sm }}
        >
          <div className="space-y-2">
            <div className="flex items-center gap-2 text-rose-800">
              <span className="text-xl" aria-hidden="true">
                🗑️
              </span>
              <h3
                id="delete-card-heading"
                className="text-base font-bold text-rose-950 sm:text-lg"
              >
                Delete All My Data
              </h3>
            </div>
            <p className="text-xs text-rose-900/90 leading-relaxed sm:text-sm">
              Permanently erase all your health information, messages, and consent
              records. This action is <strong>irreversible</strong> and cannot be
              undone.
            </p>
            <p className="text-xs text-rose-800 font-medium">
              Statutory Right: Section 6(4) &amp; Section 11, DPDP Act 2023 (Right to Erasure).
            </p>
          </div>

          <div className="pt-4">
            <button
              type="button"
              onClick={() => setShowConfirmModal(true)}
              className="inline-flex w-full items-center justify-center gap-2 rounded-xl bg-rose-700 px-4 py-2.5 text-xs font-semibold text-white shadow-xs transition hover:bg-rose-800 focus:outline-none focus:ring-4 focus:ring-rose-500/30 sm:text-sm"
              style={{ minHeight: ACCESSIBILITY_TOKENS.minTouchTarget }}
            >
              <span>Permanently Delete All Data</span>
            </button>
          </div>
        </section>
      </div>

      {/* Confirmation Modal */}
      {showConfirmModal && (
        <div
          role="dialog"
          aria-modal="true"
          aria-labelledby="confirm-delete-title"
          aria-describedby="confirm-delete-body"
          className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/80 p-4 backdrop-blur-xs animate-in fade-in duration-200"
        >
          <div
            className="w-full max-w-md rounded-3xl bg-white p-6 shadow-2xl space-y-4"
            style={{
              borderRadius: "1.25rem",
              background: COLOR_TOKENS.neutral.surface,
            }}
          >
            <div className="flex items-center gap-3 text-rose-700">
              <span className="text-2xl" aria-hidden="true">
                ⚠️
              </span>
              <h4
                id="confirm-delete-title"
                className="text-lg font-bold text-slate-900"
              >
                Confirm Permanent Deletion
              </h4>
            </div>

            <div id="confirm-delete-body" className="space-y-2 text-xs text-slate-600 sm:text-sm leading-relaxed">
              <p>
                Are you sure you want to delete all personal and triage records?
              </p>
              <div className="rounded-xl border border-rose-200 bg-rose-50 p-3 text-rose-950 font-medium">
                <strong>Warning:</strong> This will immediately delete:
                <ul className="mt-1 list-disc pl-5 space-y-0.5 text-xs">
                  <li>All conversation history and symptom entries.</li>
                  <li>All triage results and condition predictions.</li>
                  <li>Your active consent agreement and session tokens.</li>
                </ul>
              </div>
              <p className="text-slate-500">
                This operation is immediate and cannot be recovered.
              </p>
            </div>

            <div className="flex flex-col-reverse sm:flex-row sm:justify-end gap-2 pt-2">
              <button
                type="button"
                onClick={() => setShowConfirmModal(false)}
                disabled={isDeleting}
                className="inline-flex min-h-[44px] items-center justify-center rounded-xl border border-slate-300 bg-white px-4 py-2 text-xs font-semibold text-slate-700 transition hover:bg-slate-100 sm:text-sm"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={() => void handleConfirmDelete()}
                disabled={isDeleting}
                aria-busy={isDeleting}
                className="inline-flex min-h-[44px] items-center justify-center gap-2 rounded-xl bg-rose-700 px-4 py-2 text-xs font-semibold text-white transition hover:bg-rose-800 disabled:opacity-60 sm:text-sm"
              >
                <span>{isDeleting ? "Erasing Data…" : "Yes, Permanently Delete"}</span>
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default DataExportDelete;
