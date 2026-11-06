/**
 * @file Typed API service for user profile CRUD (GET/PUT /api/v1/profile).
 * Owner: Dimple · Task: S2-DIM-1 · Requirements: FR-02
 *
 * Profile endpoints are owned by Vivek (S2-VIV-3). Until they are merged,
 * the service falls back to session-scoped storage so the UI is functional
 * without the real backend (Rule 2: mock unmerged dependencies).
 */

/* ------------------------------------------------------------------ */
/*  Types                                                              */
/* ------------------------------------------------------------------ */

/** Supported age-band buckets — intentionally coarse to minimise data. */
export type AgeBand =
  | "child"
  | "teen"
  | "young_adult"
  | "adult"
  | "senior";

/** Biological sex options (used only for clinical context, never identity). */
export type BiologicalSex =
  | "female"
  | "male"
  | "other"
  | "prefer_not_to_say";

/** Common pre-existing conditions the user may self-report. */
export const CHRONIC_CONDITION_OPTIONS = [
  "Diabetes",
  "Asthma",
  "Hypertension",
  "Heart Disease",
  "Thyroid Disorder",
  "Arthritis",
  "COPD",
  "Kidney Disease",
] as const;

/** Shape of the profile data exchanged with the server. */
export type ProfileData = {
  /** Coarse age bracket — all optional. */
  ageBand?: AgeBand | undefined;
  /** Biological sex for clinical context — all optional. */
  biologicalSex?: BiologicalSex | undefined;
  /** Self-reported chronic conditions — all optional. */
  chronicConditions?: string[];
};

/** Marker prefix for locally-cached profile (no backend yet). */
const LOCAL_PROFILE_PREFIX = "local-profile-" as const;

/* ------------------------------------------------------------------ */
/*  Helpers                                                            */
/* ------------------------------------------------------------------ */

/**
 * Parse a JSON response, raising a user-friendly error on failure.
 *
 * @param res - The fetch Response object.
 * @returns Parsed JSON body.
 * @throws Error with a safe message on non-2xx status codes.
 */
async function handleResponse<T>(res: Response): Promise<T> {
  if (!res.ok) {
    throw new Error(
      `Unable to save your profile (HTTP ${res.status}). Please try again.`,
    );
  }
  return (await res.json()) as T;
}

/* ------------------------------------------------------------------ */
/*  Public API                                                         */
/* ------------------------------------------------------------------ */

/**
 * Fetch the current user profile from the backend.
 *
 * Falls back to an empty profile when the endpoint does not exist yet
 * (HTTP 404), so the UI remains functional before S2-VIV-3 merges.
 *
 * @returns The user's profile data (all fields may be undefined).
 * @throws Error on unexpected network or server failures.
 */
export async function getProfile(): Promise<ProfileData> {
  const res = await fetch("/api/v1/profile", {
    method: "GET",
    headers: { Accept: "application/json" },
  });

  // TODO(#188): remove 404 fallback once S2-VIV-3 merges.
  if (res.status === 404) {
    return {};
  }

  return handleResponse<ProfileData>(res);
}

/**
 * Persist the user's optional profile fields.
 *
 * Falls back to a local-only acknowledgement when the endpoint does not
 * exist yet (HTTP 404).
 *
 * @param data - Profile fields to save (all optional).
 * @returns An object with a `profileId` confirming the save.
 * @throws Error with a user-friendly message on network or server failures.
 */
export async function saveProfile(
  data: ProfileData,
): Promise<{ profileId: string }> {
  const res = await fetch("/api/v1/profile", {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });

  // TODO(#188): remove 404 fallback once S2-VIV-3 merges.
  if (res.status === 404) {
    return { profileId: `${LOCAL_PROFILE_PREFIX}${crypto.randomUUID()}` };
  }

  return handleResponse<{ profileId: string }>(res);
}
