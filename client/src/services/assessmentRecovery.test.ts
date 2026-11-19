
/**
 * @file Assessment recovery tests.
 * Owner: Rutva · Task: S2-RUT-3 · Issue: #182
 */

import { http, HttpResponse } from "msw";
import { beforeEach, describe, expect, it } from "vitest";
import { restoreUnfinishedAssessment } from "./assessmentRecovery";
import { useAssessmentStore } from "../stores/assessmentStore";
import { server } from "../test/server";

describe("assessment recovery", () => {
  beforeEach(() => {
    useAssessmentStore.getState().clearAssessment();
    server.resetHandlers();
  });

  it("returns false when there is no saved assessment ID", async () => {
    await expect(restoreUnfinishedAssessment()).resolves.toBe(false);
  });

  it("restores an unfinished assessment and its conversation", async () => {
    useAssessmentStore.getState().restoreAssessmentId("assessment-123");

    server.use(
      http.get("*/api/v1/assessments/:id", () =>
        HttpResponse.json({
          id: "assessment-123",
          consentId: "consent-123",
          state: "CLARIFYING",
        }),
      ),
      http.get("*/api/v1/assessments/:id/messages", () =>
        HttpResponse.json([
          {
            id: "message-1",
            assessmentId: "assessment-123",
            role: "user",
            content: "I have a headache.",
          },
          {
            id: "message-2",
            assessmentId: "assessment-123",
            role: "assistant",
            content: "When did it begin?",
          },
          {
            id: "message-3",
            assessmentId: "assessment-123",
            role: "system",
            content: "Internal event",
          },
        ]),
      ),
    );

    await expect(restoreUnfinishedAssessment()).resolves.toBe(true);

    const state = useAssessmentStore.getState();

    expect(state.assessmentId).toBe("assessment-123");
    expect(state.assessmentState).toBe("CLARIFYING");
    expect(state.messages).toEqual([
      {
        id: "message-1",
        role: "user",
        content: "I have a headache.",
      },
      {
        id: "message-2",
        role: "assistant",
        content: "When did it begin?",
      },
    ]);
  });

  it("clears a completed assessment instead of resuming it", async () => {
    useAssessmentStore.getState().restoreAssessmentId("assessment-123");

    server.use(
      http.get("*/api/v1/assessments/:id", () =>
        HttpResponse.json({
          id: "assessment-123",
          consentId: "consent-123",
          state: "COMPLETED",
        }),
      ),
    );

    await expect(restoreUnfinishedAssessment()).resolves.toBe(false);

    expect(useAssessmentStore.getState().assessmentId).toBeNull();
    expect(sessionStorage.getItem("active-assessment-id")).toBeNull();
  });

  it("keeps the saved ID when the backend is temporarily unavailable", async () => {
    useAssessmentStore.getState().restoreAssessmentId("assessment-123");

    server.use(
      http.get("*/api/v1/assessments/:id", () => HttpResponse.error()),
    );

    await expect(restoreUnfinishedAssessment()).resolves.toBe(false);

    expect(useAssessmentStore.getState().assessmentId).toBe("assessment-123");
  });

  it("clears the saved ID if the backend returns a different assessment", async () => {
    useAssessmentStore.getState().restoreAssessmentId("assessment-123");

    server.use(
      http.get("*/api/v1/assessments/:id", () =>
        HttpResponse.json({
          id: "assessment-other",
          consentId: "consent-123",
          state: "START",
        }),
      ),
    );

    await expect(restoreUnfinishedAssessment()).resolves.toBe(false);

    expect(useAssessmentStore.getState().assessmentId).toBeNull();
  });
});
