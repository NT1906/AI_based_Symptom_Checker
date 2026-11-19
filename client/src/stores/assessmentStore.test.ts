/**
 * @file Assessment store tests.
 * Owner: Rutva · Task: S1-RUT-2 · Issue: #56
 */
import { beforeEach, describe, expect, it, vi } from "vitest";
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

  it("persists only the active assessment ID in session storage", () => {
    useAssessmentStore.getState().setAssessment({
      id: "assessment-456",
      consentId: "consent-123",
      state: "START",
    });

    expect(sessionStorage.getItem("active-assessment-id")).toBe(
      "assessment-456",
    );

    useAssessmentStore.getState().addMessage(exampleMessage);

    expect(sessionStorage.length).toBe(1);
    expect(sessionStorage.getItem("active-assessment-id")).toBe(
      "assessment-456",
    );
    expect(sessionStorage.getItem("messages")).toBeNull();
  });

  it("restores an assessment ID into memory", () => {
    useAssessmentStore.getState().restoreAssessmentId("assessment-789");

    expect(useAssessmentStore.getState().assessmentId).toBe(
      "assessment-789",
    );
    expect(sessionStorage.getItem("active-assessment-id")).toBe(
      "assessment-789",
    );
  });

  it("ignores an empty restored assessment ID", () => {
    useAssessmentStore.getState().restoreAssessmentId("   ");

    expect(useAssessmentStore.getState().assessmentId).toBeNull();
    expect(sessionStorage.getItem("active-assessment-id")).toBeNull();
  });

  it("removes the saved ID when an assessment is cleared", () => {
    useAssessmentStore.getState().restoreAssessmentId("assessment-789");
    useAssessmentStore.getState().clearAssessment();

    expect(sessionStorage.getItem("active-assessment-id")).toBeNull();
    expect(useAssessmentStore.getState().assessmentId).toBeNull();
  });

  it("removes the saved ID when an assessment is completed", () => {
    useAssessmentStore.getState().setAssessment({
      id: "assessment-456",
      consentId: "consent-123",
      state: "COMPLETED",
    });

    expect(sessionStorage.getItem("active-assessment-id")).toBeNull();
    expect(useAssessmentStore.getState().assessmentId).toBeNull();
  });

  it("continues working when session storage writes fail", () => {
    const setItemSpy = vi
      .spyOn(Storage.prototype, "setItem")
      .mockImplementation(() => {
        throw new Error("Storage unavailable");
      });

    try {
      useAssessmentStore.getState().restoreAssessmentId("assessment-789");

      expect(useAssessmentStore.getState().assessmentId).toBe(
        "assessment-789",
      );
    } finally {
      setItemSpy.mockRestore();
    }
  });
});
