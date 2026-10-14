/**
 * @file Zustand store for tracking user consent state across the session.
 * Owner: Dimple · Task: S1-DIM-1 · Requirements: DR-08
 */
import { create } from "zustand";

/** Consent state for the current browser session. */
type ConsentState = {
  /** UUID of the recorded consent returned by POST /consents, or null if not yet consented. */
  consentId: string | null;
  /** ISO-8601 timestamp of when consent was recorded. */
  consentedAt: string | null;
  /** Policy version the user consented to. */
  policyVersion: string | null;
  /** Record a successful consent response from the API. */
  recordConsent: (consentId: string, policyVersion: string) => void;
  /** Reset consent (e.g. on logout or policy version bump). */
  clearConsent: () => void;
};

/**
 * Holds the user's consent status for the current session.
 * Health data must never be stored in localStorage (PWA storage rule DR-06).
 * This store is intentionally NOT persisted.
 */
export const useConsentStore = create<ConsentState>((set) => ({
  consentId: null,
  consentedAt: null,
  policyVersion: null,
  recordConsent: (consentId, policyVersion) =>
    set({ consentId, policyVersion, consentedAt: new Date().toISOString() }),
  clearConsent: () =>
    set({ consentId: null, consentedAt: null, policyVersion: null }),
}));
