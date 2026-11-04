/**
 * @file Assessment store tests.
 * Owner: Rutva · Task: S1-RUT-2 · Issue: #56
 */
import { beforeEach, describe, expect, it } from "vitest";
import { useAssessmentStore, type AssessmentMessage } from "./assessmentStore";

const exampleMessage: AssessmentMessage = {
  id: "test-message-1",
  role: "user",
  content: "I have a headache",
};

describe("assessment store", () => {
  beforeEach(() => {
    useAssessmentStore.getState().clearAssessment();
  });
  it("starts without an active assessment", () => {
    expect(useAssessmentStore.getState().assessmentId).toBeNull();
    expect(useAssessmentStore.getState().assessmentState).toBeNull();
  });

  it("stores assessment metadata", () => {
    useAssessmentStore.getState().setAssessment({
      id: "assessment-123",
      consentId: "consent-123",
      state: "START",
    });

    expect(useAssessmentStore.getState().assessmentId).toBe("assessment-123");
    expect(useAssessmentStore.getState().assessmentState).toBe("START");
  });

  it("updates the assessment lifecycle state", () => {
    useAssessmentStore.getState().setAssessmentState("CLARIFYING");

    expect(useAssessmentStore.getState().assessmentState).toBe("CLARIFYING");
  });

  it("clears assessment metadata and conversation together", () => {
    const store = useAssessmentStore.getState();

    store.setAssessment({
      id: "assessment-123",
      consentId: "consent-123",
      state: "START",
    });
    store.addMessage(exampleMessage);

    useAssessmentStore.getState().clearAssessment();

    expect(useAssessmentStore.getState().assessmentId).toBeNull();
    expect(useAssessmentStore.getState().assessmentState).toBeNull();
    expect(useAssessmentStore.getState().messages).toEqual([]);
  });

  it("starts with an empty conversation", () => {
    expect(useAssessmentStore.getState().messages).toEqual([]);
  });

  it("adds a message and clears the conversation", () => {
    useAssessmentStore.getState().addMessage(exampleMessage);

    expect(useAssessmentStore.getState().messages).toEqual([exampleMessage]);

    useAssessmentStore.getState().clearMessages();

    expect(useAssessmentStore.getState().messages).toEqual([]);
  });

  it("does not retain messages after clearing an already empty conversation", () => {
    useAssessmentStore.getState().clearMessages();

    expect(useAssessmentStore.getState().messages).toEqual([]);
  });
});
