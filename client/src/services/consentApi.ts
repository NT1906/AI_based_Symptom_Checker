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

/** Version of the privacy notice bundled with this client. */
export const CURRENT_POLICY_VERSION = "1.0.0" as const;

/** Fetches the active server-side version before reusing or recording consent. */
export async function getCurrentPolicyVersion(): Promise<string> {
  const response = await fetch("/api/v1/consents/current-policy", { cache: "no-store" });
  if (!response.ok) {
    throw new Error("Unable to verify the privacy notice. Please try again.");
  }
  const body = (await response.json()) as { policyVersion?: unknown };
  if (typeof body.policyVersion !== "string" || !body.policyVersion) {
    throw new Error("Unable to verify the privacy notice. Please try again.");
  }
  return body.policyVersion;
}

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

  if (!res.ok) {
    throw new Error(`Unable to record your consent (HTTP ${res.status}). Please try again.`);
  }

  return res.json() as Promise<ConsentResponse>;
}
