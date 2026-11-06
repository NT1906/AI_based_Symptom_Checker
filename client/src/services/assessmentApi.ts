
/**
 * @file Typed assessment API services.
 * Owner: Rutva · Task: S1-RUT-2 · Issue: #56
 *
 * Uses generated OpenAPI contracts and keeps assessment data in memory only.
 */

import type {
  AnalyzeResponse,
  AssessmentCreate,
  AssessmentRead,
  AssessmentResult,
  AssessmentStateResponse,
  ErrorResponse,
  MessageCreate,
  MessageRead,
  SendMessageResponse,
  SymptomRead,
  UpdateSymptomsRequest,
} from "../types";

/** Structured error returned by an assessment API request. */
export class AssessmentApiError extends Error {
  /** HTTP status returned by the server. */
  readonly status: number;

  /** Machine-readable error code, when supplied by the API. */
  readonly code?: string;

  /** Request identifier supplied by the API, when available. */
  readonly requestId?: string;

  /**
   * Create a typed assessment API error.
   *
   * @param status - HTTP response status.
   * @param payload - Parsed API error payload, if available.
   */
  constructor(status: number, payload?: ErrorResponse) {
    super(payload?.message ?? "The assessment service could not complete the request.");
    this.name = "AssessmentApiError";
    this.status = status;
    this.code = payload?.code;
    this.requestId = payload?.requestId;
  }
}

/**
 * Check whether an unknown value matches the generated API error contract.
 *
 * @param value - Value received from the server.
 * @returns Whether the value is an API error response.
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
 * @param init - Optional fetch configuration.
 * @returns Parsed response matching the generated OpenAPI type.
 * @throws AssessmentApiError when the server returns an unsuccessful status.
 */
async function requestJson<T>(
  path: string,
  init: RequestInit = {},
): Promise<T> {
  const response = await fetch(new URL(path, window.location.origin), {
    ...init,
    headers: {
      ...(init.body ? { "Content-Type": "application/json" } : {}),
      ...init.headers,
    },
  });

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
 * Create a new assessment linked to an existing consent record.
 *
 * @param request - Assessment creation payload.
 * @returns Created assessment.
 */
export function createAssessment(
  request: AssessmentCreate,
): Promise<AssessmentRead> {
  return requestJson<AssessmentRead>("/api/v1/assessments", {
    method: "POST",
    body: JSON.stringify(request),
  });
}

/**
 * Retrieve an assessment by its identifier.
 *
 * @param id - Assessment identifier.
 * @returns Assessment metadata and lifecycle state.
 */
export function getAssessment(id: string): Promise<AssessmentRead> {
  return requestJson<AssessmentRead>(
    `/api/v1/assessments/${encodeURIComponent(id)}`,
  );
}

/**
 * Retrieve conversation history for an assessment.
 *
 * @param id - Assessment identifier.
 * @returns Ordered conversation messages.
 */
export function getAssessmentMessages(id: string): Promise<MessageRead[]> {
  return requestJson<MessageRead[]>(
    `/api/v1/assessments/${encodeURIComponent(id)}/messages`,
  );
}

/**
 * Send a user message to an assessment conversation.
 *
 * @param id - Assessment identifier.
 * @param request - Message content.
 * @returns Recorded user message, assistant reply, and next state.
 */
export function sendAssessmentMessage(
  id: string,
  request: MessageCreate,
): Promise<SendMessageResponse> {
  return requestJson<SendMessageResponse>(
    `/api/v1/assessments/${encodeURIComponent(id)}/messages`,
    {
      method: "POST",
      body: JSON.stringify(request),
    },
  );
}

/**
 * Retrieve the current assessment lifecycle state.
 *
 * @param id - Assessment identifier.
 * @returns Assessment state snapshot.
 */
export function getAssessmentState(
  id: string,
): Promise<AssessmentStateResponse> {
  return requestJson<AssessmentStateResponse>(
    `/api/v1/assessments/${encodeURIComponent(id)}/state`,
  );
}

/**
 * Retrieve recognized symptoms for an assessment.
 *
 * @param id - Assessment identifier.
 * @returns Recognized symptoms.
 */
export function getAssessmentSymptoms(id: string): Promise<SymptomRead[]> {
  return requestJson<SymptomRead[]>(
    `/api/v1/assessments/${encodeURIComponent(id)}/symptoms`,
  );
}

/**
 * Confirm or update the symptoms recorded for an assessment.
 *
 * @param id - Assessment identifier.
 * @param request - Updated symptom list.
 * @returns Updated symptoms.
 */
export function updateAssessmentSymptoms(
  id: string,
  request: UpdateSymptomsRequest,
): Promise<SymptomRead[]> {
  return requestJson<SymptomRead[]>(
    `/api/v1/assessments/${encodeURIComponent(id)}/symptoms`,
    {
      method: "PATCH",
      body: JSON.stringify(request),
    },
  );
}

/**
 * Trigger clinical triage analysis for an assessment.
 *
 * @param id - Assessment identifier.
 * @returns Analysis status and resulting lifecycle state.
 */
export function analyzeAssessment(id: string): Promise<AnalyzeResponse> {
  return requestJson<AnalyzeResponse>(
    `/api/v1/assessments/${encodeURIComponent(id)}/analyze`,
    { method: "POST" },
  );
}

/**
 * Retrieve the completed assessment result.
 *
 * @param id - Assessment identifier.
 * @returns Categorical triage result and safety guidance.
 */
export function getAssessmentResult(id: string): Promise<AssessmentResult> {
  return requestJson<AssessmentResult>(
    `/api/v1/assessments/${encodeURIComponent(id)}/result`,
  );
}
