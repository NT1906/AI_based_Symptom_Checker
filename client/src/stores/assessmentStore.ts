/**
 * @file Assessment conversation state.
 * Owner: Rutva · Task: S0-RUT-1 · Requirements: NFR-08, NFR-09
 */
import { create } from "zustand";

/** A message exchanged during an assessment conversation. */
export type AssessmentMessage = {
  id: string;
  role: "user" | "assistant";
  content: string;
};

type AssessmentState = {
  messages: AssessmentMessage[];
  addMessage: (message: AssessmentMessage) => void;
  clearMessages: () => void;
};

/** Holds transient client-side assessment conversation state. */
export const useAssessmentStore = create<AssessmentState>((set) => ({
  messages: [],
  addMessage: (message) => set((state) => ({ messages: [...state.messages, message] })),
  clearMessages: () => set({ messages: [] }),
}));
