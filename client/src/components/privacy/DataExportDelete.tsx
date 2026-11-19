/**
 * @file DataExportDelete — privacy controls for statutory data export and permanent deletion.
 * Owner: Dimple · Task: S2-DIM-3 · Requirements: DR-06, DR-08
 * Real account deletion and guest handling: Nisarg · Task: S2-NIS-18 · Issue: #315
 * Restyle: Nisarg · Task: S2-NIS-21 · Issue: #322
 *
 * Implements DPDP Act 2023 user rights:
 * - Export: self-service download of personal and assessment records in JSON.
 * - Deletion: permanent cascading erasure of all stored and session data with
 * explicit affirmative confirmation and irreversibility warnings.
 */

import React, { useState } from "react";
import { queryClient } from "../../lib/queryClient";
import {
  fetchUserDataExport,
  deleteUserData,
  NotLoggedInError,
  triggerJsonDownload,
  type UserDataExport,
} from "../../services/privacyApi";
import { useConsentStore } from "../../stores/consentStore";
import { useAssessmentStore } from "../../stores/assessmentStore";
import { useAuthStore } from "../../stores/authStore";
import { CheckCircle2, Download, Trash2, TriangleAlert } from "lucide-react";

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
  const accountUser = useAuthStore((s) => s.user);

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
      // Why: guests have no account, so there is nothing to erase on the
      // server yet; say so instead of claiming a deletion (S2-NIS-18).
      if (accountUser) {
        await deleteUserData();
      }

      // Clear all client stores (DR-06 compliance: zero persistence)
      consentStore.clearConsent();
      assessmentStore.clearAssessment();
      queryClient.clear();
      if (accountUser) {
        useAuthStore.setState({ user: null, status: "unauthenticated", errorMessage: null });
      }

      setShowConfirmModal(false);
      setStatusMessage({
        type: "success",
        text: accountUser
          ? "All your data has been permanently deleted: your account, assessments, saved results and profile. You have been logged out."
          : "This browser session has been cleared. You are not logged in, so no account data is stored; guest sessions are purged automatically after 24 hours.",
      });

      if (onDataDeleted) {
        onDataDeleted();
      }
    } catch (error) {
      setShowConfirmModal(false);
      setStatusMessage({
        type: "error",
        text:
          error instanceof NotLoggedInError
            ? "Your session has ended. Please log in again to delete your account."
            : "Unable to complete data deletion. Please try again.",
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
              ? "border border-success/30 bg-success/10 text-foreground"
              : "border border-danger/30 bg-danger/10 text-danger"
          }`}
        >
          <span className="flex items-start gap-2">
            {statusMessage.type === "success" ? (
              <CheckCircle2 className="mt-0.5 size-4 shrink-0 text-success" aria-hidden="true" />
            ) : (
              <TriangleAlert className="mt-0.5 size-4 shrink-0 text-danger" aria-hidden="true" />
            )}
            <span>{statusMessage.text}</span>
          </span>
        </div>
      )}

      {/* Grid of privacy actions */}
      <div className="grid gap-6 md:grid-cols-2">
        {/* Action 1: Export My Data */}
        <section
          aria-labelledby="export-card-heading"
          className="flex flex-col justify-between rounded-xl border border-border bg-card p-5 shadow-xs transition sm:p-6"
        >
          <div className="space-y-2">
            <div className="flex items-center gap-2 text-primary">
              <Download className="size-5" aria-hidden="true" />
              <h3
                id="export-card-heading"
                className="text-base font-bold text-foreground sm:text-lg"
              >
                Export My Data
              </h3>
            </div>
            <p className="text-xs text-muted-foreground leading-relaxed sm:text-sm">
              Download a structured, human-readable JSON file containing all
              assessments, confirmed symptoms, timestamps, and active consent
              records linked to your session.
            </p>
            <p className="text-xs text-muted-foreground font-medium">
              Statutory Right: Section 11, DPDP Act 2023 (Right to Access).
            </p>
          </div>

          <div className="pt-4">
            <button
              type="button"
              onClick={() => void handleExport()}
              disabled={isExporting}
              aria-busy={isExporting}
              className="inline-flex min-h-11 w-full items-center justify-center gap-2 rounded-lg border border-primary/40 bg-primary/10 px-4 py-2.5 text-xs font-semibold text-primary transition hover:bg-primary/15 focus:outline-none focus:ring-4 focus:ring-ring/40 disabled:cursor-not-allowed disabled:opacity-60 sm:text-sm"
            >
              <span>{isExporting ? "Generating Export…" : "Download Data Export (JSON)"}</span>
            </button>
          </div>
        </section>

        {/* Action 2: Delete All My Data */}
        <section
          aria-labelledby="delete-card-heading"
          className="flex flex-col justify-between rounded-xl border border-danger/30 bg-danger/5 p-5 shadow-xs transition sm:p-6"
        >
          <div className="space-y-2">
            <div className="flex items-center gap-2 text-danger">
              <Trash2 className="size-5" aria-hidden="true" />
              <h3
                id="delete-card-heading"
                className="text-base font-bold text-foreground sm:text-lg"
              >
                Delete All My Data
              </h3>
            </div>
            <p className="text-xs text-muted-foreground leading-relaxed sm:text-sm">
              Permanently erase all your health information, messages, and consent
              records. This action is <strong>irreversible</strong> and cannot be
              undone.
            </p>
            <p className="text-xs text-danger font-medium">
              Statutory Right: Section 6(4) &amp; Section 11, DPDP Act 2023 (Right to Erasure).
            </p>
          </div>

          <div className="pt-4">
            <button
              type="button"
              onClick={() => setShowConfirmModal(true)}
              className="inline-flex min-h-11 w-full items-center justify-center gap-2 rounded-lg bg-danger px-4 py-2.5 text-xs font-semibold text-danger-foreground shadow-xs transition hover:bg-danger/90 focus:outline-none focus:ring-4 focus:ring-danger/30 sm:text-sm"
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
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4 backdrop-blur-xs animate-in fade-in duration-200"
        >
          <div
            className="w-full max-w-md space-y-4 rounded-xl border border-border bg-card p-6 text-card-foreground shadow-2xl animate-in fade-in-0 zoom-in-95"
          >
            <div className="flex items-center gap-3 text-danger">
              <TriangleAlert className="size-6" aria-hidden="true" />
              <h4
                id="confirm-delete-title"
                className="text-lg font-bold text-foreground"
              >
                Confirm Permanent Deletion
              </h4>
            </div>

            <div id="confirm-delete-body" className="space-y-2 text-xs text-muted-foreground sm:text-sm leading-relaxed">
              <p>
                Are you sure you want to delete all personal and triage records?
              </p>
              <div className="rounded-xl border border-danger/30 bg-danger/10 p-3 text-foreground font-medium">
                <strong>Warning:</strong> This will immediately delete:
                <ul className="mt-1 list-disc pl-5 space-y-0.5 text-xs">
                  <li>All conversation history and symptom entries.</li>
                  <li>All triage results and condition predictions.</li>
                  <li>Your active consent agreement and session tokens.</li>
                </ul>
              </div>
              <p className="text-muted-foreground">
                This operation is immediate and cannot be recovered.
              </p>
            </div>

            <div className="flex flex-col-reverse sm:flex-row sm:justify-end gap-2 pt-2">
              <button
                type="button"
                onClick={() => setShowConfirmModal(false)}
                disabled={isDeleting}
                className="inline-flex min-h-[44px] items-center justify-center rounded-xl border border-border bg-card px-4 py-2 text-xs font-semibold text-muted-foreground transition hover:bg-accent sm:text-sm"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={() => void handleConfirmDelete()}
                disabled={isDeleting}
                aria-busy={isDeleting}
                className="inline-flex min-h-[44px] items-center justify-center gap-2 rounded-xl bg-danger px-4 py-2 text-xs font-semibold text-danger-foreground transition hover:bg-danger/90 disabled:opacity-60 sm:text-sm"
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
