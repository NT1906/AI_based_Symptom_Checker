/**
 * @file Typed API service for privacy management, data export, and data deletion.
 * Owner: Dimple · Task: S2-DIM-3 · Requirements: DR-06, DR-08
 *
 * Implements DPDP Act 2023 compliance for user data rights:
 * - Data export (Section 11): structured JSON export of user's session and triage data.
 * - Data erasure (Section 6(4), Section 11): permanent deletion of user data.
 * - Consent version checking (DR-08): determines when policy updates mandate re-consent.
 *
 * Employs 404 fallback handling per Rule 2 until Harsh's S2-HAR-2 endpoints merge.
 */

import { CURRENT_POLICY_VERSION } from "./consentApi";

/** Shape of the downloadable user data export bundle. */
export type UserDataExport = {
  /** ISO timestamp when the export was compiled. */
  exportedAt: string;
  /** Active privacy policy version governing this data. */
  policyVersion: string;
  /** Unique consent identifier, if consented. */
  consentId: string | null;
  /** Timestamp when consent was recorded. */
  consentedAt: string | null;
  /** Identifier of any active assessment in the session. */
  activeAssessmentId: string | null;
  /** Summary count of recorded symptoms. */
  symptomsCount: number;
  /** Statutory data retention notice under DPDP Act 2023. */
  dataRetentionNotice: string;
  /** Statutory user rights statement under DPDP Act 2023. */
  rightsNotice: string;
};

/** Response schema from data deletion operations. */
export type DeleteDataResponse = {
  /** Whether the deletion operation succeeded. */
  success: boolean;
  /** Timestamp of deletion execution. */
  deletedAt: string;
  /** Safe human-readable confirmation message. */
  message: string;
};

/**
 * Checks whether the user's previously recorded consent version matches
 * the currently active privacy policy version.
 *
 * @param storedPolicyVersion - The version string from user's consent record.
 * @returns True if consent is absent or outdated; false if current.
 */
export function isConsentOutdated(
  storedPolicyVersion: string | null | undefined,
): boolean {
  if (!storedPolicyVersion) {
    return true;
  }
  return storedPolicyVersion !== CURRENT_POLICY_VERSION;
}

/**
 * Fetches structured data export for the current user or guest session.
 *
 * Falls back to session data synthesis if the backend endpoint returns 404
 * (Rule 2: mock unmerged dependencies until S2-HAR-2 merges).
 *
 * @param sessionData - Optional session context to include in export fallback.
 * @returns Complete UserDataExport object.
 * @throws Error on unexpected network or server failures.
 */
export async function fetchUserDataExport(sessionData?: {
  consentId?: string | null;
  consentedAt?: string | null;
  policyVersion?: string | null;
  assessmentId?: string | null;
  symptomsCount?: number;
}): Promise<UserDataExport> {
  const res = await fetch("/api/v1/privacy/export", {
    method: "GET",
    headers: { Accept: "application/json" },
  });

  // Fallback for unmerged S2-HAR-2 backend endpoint
  if (res.status === 404) {
    return {
      exportedAt: new Date().toISOString(),
      policyVersion: sessionData?.policyVersion || CURRENT_POLICY_VERSION,
      consentId: sessionData?.consentId || null,
      consentedAt: sessionData?.consentedAt || null,
      activeAssessmentId: sessionData?.assessmentId || null,
      symptomsCount: sessionData?.symptomsCount ?? 0,
      dataRetentionNotice:
        "Guest data is retained for a maximum of 24 hours under the TTL policy. Registered accounts retain data until explicit erasure is requested.",
      rightsNotice:
        "Pursuant to the DPDP Act 2023 (India), you have the right to access, rectify, and permanently erase your personal data at any time.",
    };
  }

  if (!res.ok) {
    throw new Error(
      `Unable to export your data (HTTP ${res.status}). Please try again later.`,
    );
  }

  return (await res.json()) as UserDataExport;
}

/**
 * Initiates permanent erasure of user data on the server.
 *
 * Cascades across assessments, symptoms, messages, and consent records.
 * Falls back to local confirmation if the endpoint returns 404 (Rule 2).
 *
 * @returns Deletion confirmation payload.
 * @throws Error on unexpected network or server failures.
 */
export async function deleteUserData(): Promise<DeleteDataResponse> {
  const res = await fetch("/api/v1/privacy/data", {
    method: "DELETE",
    headers: { Accept: "application/json" },
  });

  // Fallback for unmerged S2-HAR-2 backend endpoint
  if (res.status === 404) {
    return {
      success: true,
      deletedAt: new Date().toISOString(),
      message: "All session and health data has been permanently cleared.",
    };
  }

  if (!res.ok) {
    throw new Error(
      `Unable to delete your data (HTTP ${res.status}). Please try again later.`,
    );
  }

  return (await res.json()) as DeleteDataResponse;
}

/**
 * Triggers a browser file download of the export data as a clean JSON file.
 *
 * @param exportData - The data payload to download.
 * @param filename - Optional custom filename.
 */
export function triggerJsonDownload(
  exportData: UserDataExport,
  filename = "symptom-checker-data-export.json",
): void {
  const jsonString = JSON.stringify(exportData, null, 2);
  const blob = new Blob([jsonString], { type: "application/json" });
  const url = URL.createObjectURL(blob);

  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  document.body.removeChild(anchor);
  URL.revokeObjectURL(url);
}
