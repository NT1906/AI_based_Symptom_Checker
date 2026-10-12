import { beforeEach, describe, expect, it } from "vitest";
import {
  useAssessmentStore,
  type AssessmentMessage,
} from "./assessmentStore";

const exampleMessage: AssessmentMessage = {
  id: "test-message-1",
  role: "user",
  content: "I have a headache",
};

describe("assessment store", () => {
  beforeEach(() => {
    useAssessmentStore.getState().clearMessages();
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
