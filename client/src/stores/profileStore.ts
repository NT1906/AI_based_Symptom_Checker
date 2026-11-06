/**
 * @file Zustand store for profile form state (session-scoped, never persisted).
 * Owner: Dimple · Task: S2-DIM-1 · Requirements: FR-02
 *
 * Health data must never be stored in localStorage or IndexedDB
 * (AI_RULES.md §2, DR-06). This store is intentionally NOT persisted.
 */

import { create } from "zustand";

import type { AgeBand, BiologicalSex } from "../services/profileApi";

/** Request status for profile operations. */
export type ProfileStatus = "idle" | "loading" | "success" | "error";

/** Profile store state. */
export type ProfileState = {
  /** Coarse age bracket — optional. */
  ageBand: AgeBand | undefined;
  /** Biological sex for clinical context — optional. */
  biologicalSex: BiologicalSex | undefined;
  /** Self-reported chronic conditions — optional. */
  chronicConditions: string[];
  /** Current operation status. */
  status: ProfileStatus;
  /** User-facing error message, if any. */
  errorMessage: string | null;
  /** Set the age band. */
  setAgeBand: (value: AgeBand | undefined) => void;
  /** Set the biological sex. */
  setBiologicalSex: (value: BiologicalSex | undefined) => void;
  /** Toggle a chronic condition on or off. */
  toggleCondition: (condition: string) => void;
  /** Set the operation status. */
  setStatus: (status: ProfileStatus, errorMessage?: string) => void;
  /** Reset the entire profile to initial state. */
  reset: () => void;
};

/** Initial values for a blank profile. */
const INITIAL_STATE = {
  ageBand: undefined,
  biologicalSex: undefined,
  chronicConditions: [] as string[],
  status: "idle" as ProfileStatus,
  errorMessage: null,
} as const;

/**
 * Holds the profile form state for the current session.
 *
 * Not persisted — health data must stay in memory only (DR-06).
 */
export const useProfileStore = create<ProfileState>((set) => ({
  ...INITIAL_STATE,

  setAgeBand: (value) => set({ ageBand: value }),

  setBiologicalSex: (value) => set({ biologicalSex: value }),

  toggleCondition: (condition) =>
    set((state) => {
      const exists = state.chronicConditions.includes(condition);
      return {
        chronicConditions: exists
          ? state.chronicConditions.filter((c) => c !== condition)
          : [...state.chronicConditions, condition],
      };
    }),

  setStatus: (status, errorMessage) =>
    set({ status, errorMessage: errorMessage ?? null }),

  reset: () => set({ ...INITIAL_STATE }),
}));
