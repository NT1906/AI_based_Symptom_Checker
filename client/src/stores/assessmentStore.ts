
/**
 * @file Assessment conversation and session state.
 * Owner: Rutva · Task: S1-RUT-2 · Issue: #56
 *
 * Keeps assessment information in transient memory only.
 */

import { create } from "zustand";
import type {
  AssessmentRead,
  AssessmentState as AssessmentLifecycleState,
} from "../types";

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
  setAssessmentState: (state: AssessmentLifecycleState) => void;
  clearAssessment: () => void;
};

/** Holds transient client-side assessment conversation and session state. */
export const useAssessmentStore = create<AssessmentStoreState>((set) => ({
  messages: [],
  assessmentId: null,
  assessmentState: null,

  addMessage: (message) =>
    set((state) => ({
      messages: [...state.messages, message],
    })),

  clearMessages: () => set({ messages: [] }),

  setAssessment: (assessment) =>
    set({
      assessmentId: assessment.id,
      assessmentState: assessment.state,
    }),

  setAssessmentState: (assessmentState) =>
    set({ assessmentState }),

  clearAssessment: () =>
    set({
      messages: [],
      assessmentId: null,
      assessmentState: null,
    }),
}));
