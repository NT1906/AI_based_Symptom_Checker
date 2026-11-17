
/**
 * @file Typed API services for retrieving assessment history.
 * Owner: Rutva - Task: S2-RUT-2 - Issue: #181
 * Requirement: FR-02
 */

import type { AssessmentRead, ErrorResponse } from "../types";
import { AssessmentApiError } from "./assessmentApi";

/** Paginated response containing assessment history summaries. */
export interface HistoryListResponse {
  /** Assessments returned for the current page. */
  items: AssessmentRead[];
  /** Offset for the next page, or null when no more pages exist. */
  nextOffset: number | null;
}

/**
 * Check whether an unknown value matches the API error contract.
 *
 * @param value - Value received from the server.
 * @returns Whether the value is a structured API error.
 */
function isErrorResponse(value: unknown): value is ErrorResponse {
  if (typeof value !== "object" || value === null) {
    return false;
  }

  const payload = value as Record<string, unknown>;

  return (
    typeof payload.code === "string" &&
    typeof payload.message === "string" &&
    typeof payload.requestId === "string"
  );
}

/**
 * Send a request and return its typed JSON response.
 *
 * @param path - Relative API path.
 * @returns Parsed JSON response.
 * @throws AssessmentApiError when the server returns an unsuccessful status.
 */
async function requestJson<T>(path: string): Promise<T> {
  const response = await fetch(new URL(path, window.location.origin));

  if (!response.ok) {
    const payload: unknown = await response.json().catch(() => null);

    throw new AssessmentApiError(
      response.status,
      isErrorResponse(payload) ? payload : undefined,
    );
  }

  return (await response.json()) as T;
}

/**
 * Retrieve one page of the authenticated user's assessment history.
 *
 * @param limit - Number of records to request (1–100).
 * @param offset - Zero-based pagination offset.
 * @returns Assessment summaries and the next page offset.
 */
export function getAssessmentHistory(
  limit = 20,
  offset = 0,
): Promise<HistoryListResponse> {
  if (!Number.isInteger(limit) || limit < 1 || limit > 100) {
    return Promise.reject(new RangeError("History limit must be between 1 and 100."));
  }

  if (!Number.isInteger(offset) || offset < 0) {
    return Promise.reject(new RangeError("History offset must be a non-negative integer."));
  }

  const params = new URLSearchParams({
    limit: String(limit),
    offset: String(offset),
  });

  return requestJson<HistoryListResponse>(
    `/api/v1/history?${params.toString()}`,
  );
}

/**
 * Retrieve one assessment from the authenticated user's history.
 *
 * @param assessmentId - Assessment identifier.
 * @returns Assessment summary.
 */
export function getAssessmentHistoryDetail(
  assessmentId: string,
): Promise<AssessmentRead> {
  if (!assessmentId.trim()) {
    return Promise.reject(new RangeError("Assessment ID is required."));
  }

  return requestJson<AssessmentRead>(
    `/api/v1/history/${encodeURIComponent(assessmentId)}`,
  );
}
