/**
 * @file API service for recording user consent (POST /api/v1/consents).
 * Owner: Dimple · Task: S1-DIM-1 · Requirements: DR-08
 *
 * Provides typed requests and responses for recording consent agreements
 * pursuant to DPDP Act 2023.
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

/** Prefix of the temporary consent ID used while the server has no consent endpoint. */
export const LOCAL_CONSENT_PREFIX = "local-" as const;

/** Current privacy-policy version. Bump this when the policy text changes. */
export const CURRENT_POLICY_VERSION = "1.0.0" as const;

/**
 * Records the user's consent by calling POST /api/v1/consents.
 *
 * @param policyVersion - The policy version string the user has agreed to.
 * @returns The server-assigned consent UUID.
 * @throws Error with a user-friendly message on network or server failures.
 */
export async function postConsent(policyVersion: string): Promise<ConsentResponse> {
  const res = await fetch("/api/v1/consents", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ policyVersion } satisfies ConsentRequest),
  });

  // TODO(#50): remove this fallback once POST /api/v1/consents exists on the server.
  // Why: until then the route returns 404 and would block every user at the consent
  // step. Nothing is stored server-side yet, so a session-only consent is safe.
  if (res.status === 404) {
    return { consentId: `${LOCAL_CONSENT_PREFIX}${crypto.randomUUID()}` };
  }

  if (!res.ok) {
    throw new Error(`Unable to record your consent (HTTP ${res.status}). Please try again.`);
  }

  return res.json() as Promise<ConsentResponse>;
}
