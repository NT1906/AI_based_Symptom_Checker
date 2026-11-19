
/**
 * @file Assessment conversation and session state.
 * Owner: Rutva · Task: S2-RUT-3 · Issue: #182
 *
 * Only the active assessment ID is persisted in sessionStorage.
 * Messages and all medical information remain in memory only.
 */

import { create } from "zustand";
import type {
  AssessmentRead,
  AssessmentState as AssessmentLifecycleState,
} from "../types";

const ACTIVE_ASSESSMENT_KEY = "active-assessment-id";

/** Safely read the active assessment ID from the current browser session. */
function readStoredAssessmentId(): string | null {
  try {
    if (typeof window === "undefined") return null;

    const id = window.sessionStorage.getItem(ACTIVE_ASSESSMENT_KEY);
    return id?.trim() ? id : null;
  } catch {
    return null;
  }
}

/** Safely persist only an assessment identifier. */
function storeAssessmentId(id: string): void {
  try {
    if (typeof window !== "undefined") {
      window.sessionStorage.setItem(ACTIVE_ASSESSMENT_KEY, id);
    }
  } catch {
    // Storage may be unavailable; the in-memory assessment still works.
  }
}

/** Remove the active assessment identifier from this browser session. */
function removeStoredAssessmentId(): void {
  try {
    if (typeof window !== "undefined") {
      window.sessionStorage.removeItem(ACTIVE_ASSESSMENT_KEY);
    }
  } catch {
    // Clearing in-memory state must still succeed.
  }
}

/** A message exchanged during an assessment conversation. */
export type AssessmentMessage = {
  id: string;
  role: "user" | "assistant";
  content: string;
};

/** Client-side assessment session state and actions. */
type AssessmentStoreState = {
  messages: AssessmentMessage[];
  assessmentId: string | null;
  assessmentState: AssessmentLifecycleState | null;
  addMessage: (message: AssessmentMessage) => void;
  clearMessages: () => void;
  setAssessment: (assessment: AssessmentRead) => void;
  restoreAssessmentId: (id: string) => void;
  setAssessmentState: (state: AssessmentLifecycleState) => void;
  clearAssessment: () => void;
};

/** Holds transient conversation data and an ID-only session recovery pointer. */
export const useAssessmentStore = create<AssessmentStoreState>((set) => ({
  messages: [],
  assessmentId: readStoredAssessmentId(),
  assessmentState: null,

  addMessage: (message) =>
    set((state) => ({
      messages: [...state.messages, message],
    })),

  clearMessages: () => set({ messages: [] }),

  setAssessment: (assessment) => {
    if (assessment.state === "COMPLETED" || assessment.state === "ERROR") {
      removeStoredAssessmentId();
    } else {
      storeAssessmentId(assessment.id);
    }

    set({
      assessmentId:
        assessment.state === "COMPLETED" || assessment.state === "ERROR"
          ? null
          : assessment.id,
      assessmentState: assessment.state,
    });
  },

  restoreAssessmentId: (id) => {
    const validId = id.trim();

    if (!validId) {
      removeStoredAssessmentId();
      set({ assessmentId: null, assessmentState: null });
      return;
    }

    storeAssessmentId(validId);
    set({ assessmentId: validId });
  },

  setAssessmentState: (assessmentState) =>
    set({ assessmentState }),

  clearAssessment: () => {
    removeStoredAssessmentId();

    set({
      messages: [],
      assessmentId: null,
      assessmentState: null,
    });
  },
}));
