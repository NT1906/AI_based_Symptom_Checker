/**
 * @file API service for the consent endpoint (POST /consents).
 * Owner: Dimple · Task: S1-DIM-1 · Requirements: DR-08
 *
 * Harsh's consent service (S1-HAR-4) is not yet merged; the MSW handler
 * in ConsentStep.test.tsx mocks this endpoint for tests.
 */

/** Request body for recording a consent. */
export type ConsentRequest = {
  /** Semantic version string of the active privacy policy. */
  policyVersion: string;
};

/** Response body returned by POST /consents. */
export type ConsentResponse = {
  /** UUID of the newly created consent record. */
  consentId: string;
};

/** Current privacy-policy version. Bump this when the policy text changes. */
export const CURRENT_POLICY_VERSION = "1.0.0" as const;

/**
 * Records the user's consent by calling POST /api/v1/consents.
 *
 * @param policyVersion - The policy version string the user has agreed to.
 * @returns The server-assigned consent UUID.
 * @throws Error with a user-friendly message on network or server failures.
 */
export async function postConsent(
  policyVersion: string
): Promise<ConsentResponse> {
  const res = await fetch("/api/v1/consents", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ policyVersion } satisfies ConsentRequest),
  });

  if (!res.ok) {
    throw new Error(
      `Unable to record your consent (HTTP ${res.status}). Please try again.`
    );
  }

  return res.json() as Promise<ConsentResponse>;
}
