
/**
 * @file Assessment API service tests.
 * Owner: Rutva · Task: S1-RUT-2 · Issue: #56
 */

import { http, HttpResponse } from "msw";
import { beforeEach, describe, expect, it } from "vitest";
import {
  analyzeAssessment,
  createAssessment,
  getAssessment,
  getAssessmentMessages,
  getAssessmentResult,
  getAssessmentState,
  getAssessmentSymptoms,
  sendAssessmentMessage,
  updateAssessmentSymptoms,
} from "./assessmentApi";
import { server } from "../test/server";

describe("assessment API services", () => {
  beforeEach(() => {
    server.resetHandlers();
  });
  it("retrieves assessment metadata", async () => {
    server.use(
      http.get("*/api/v1/assessments/:id", ({ params }) => {
        expect(params.id).toBe("assessment-123");

        return HttpResponse.json({
          id: "assessment-123",
          consentId: "consent-123",
          state: "START",
        });
      }),
    );

    const result = await getAssessment("assessment-123");

    expect(result.id).toBe("assessment-123");
    expect(result.state).toBe("START");
  });

  it("retrieves assessment lifecycle state", async () => {
    server.use(
      http.get("*/api/v1/assessments/:id/state", () =>
        HttpResponse.json({
          assessmentId: "assessment-123",
          state: "CLARIFYING",
          clarificationCount: 1,
          maxClarifications: 3,
          isLowConfidence: false,
        }),
      ),
    );

    const result = await getAssessmentState("assessment-123");

    expect(result.state).toBe("CLARIFYING");
    expect(result.clarificationCount).toBe(1);
  });

  it("retrieves recognized symptoms", async () => {
    server.use(
      http.get("*/api/v1/assessments/:id/symptoms", () =>
        HttpResponse.json([
          {
            id: "symptom-123",
            assessmentId: "assessment-123",
            name: "headache",
          },
        ]),
      ),
    );

    const result = await getAssessmentSymptoms("assessment-123");

    expect(result).toHaveLength(1);
    expect(result[0].name).toBe("headache");
  });

  it("updates assessment symptoms using PATCH", async () => {
    server.use(
      http.patch(
        "*/api/v1/assessments/:id/symptoms",
        async ({ request, params }) => {
          expect(params.id).toBe("assessment-123");
          expect(request.method).toBe("PATCH");

          const body = await request.json();
          expect(body).toBeDefined();

          return HttpResponse.json([]);
        },
      ),
    );

    const result = await updateAssessmentSymptoms("assessment-123", {
      symptoms: [],
    });

    expect(result).toEqual([]);
  });

  it("triggers assessment analysis", async () => {
    server.use(
      http.post("*/api/v1/assessments/:id/analyze", ({ params }) => {
        expect(params.id).toBe("assessment-123");

        return HttpResponse.json({
          assessmentId: "assessment-123",
          state: "COMPLETED",
        });
      }),
    );

    const result = await analyzeAssessment("assessment-123");

    expect(result.assessmentId).toBe("assessment-123");
  });

  it("retrieves the completed assessment result", async () => {
    server.use(
      http.get("*/api/v1/assessments/:id/result", () =>
        HttpResponse.json({
          assessmentId: "assessment-123",
          riskLevel: "CONSULT_DOCTOR",
        }),
      ),
    );

    const result = await getAssessmentResult("assessment-123");

    expect(result.riskLevel).toBe("CONSULT_DOCTOR");
  });

  it("creates an assessment successfully", async () => {
    server.use(
      http.post("*/api/v1/assessments", async ({ request }) => {
        const body = await request.json();

        expect(body).toEqual({ consentId: "consent-123" });

        return HttpResponse.json(
          {
            id: "assessment-123",
            consentId: "consent-123",
            state: "START",
          },
          { status: 201 },
        );
      }),
    );

    const result = await createAssessment({
      consentId: "consent-123",
    });

    expect(result.id).toBe("assessment-123");
    expect(result.state).toBe("START");
  });

  it("sends a message and receives the assistant response", async () => {
    server.use(
      http.post("*/api/v1/assessments/:id/messages", async ({ params, request }) => {
        const body = await request.json();

        expect(params.id).toBe("assessment-123");
        expect(body).toEqual({ content: "I have a headache" });

        return HttpResponse.json({
          message: {
            assessmentId: "assessment-123",
            content: "I have a headache",
          },
          assistantMessage: {
            assessmentId: "assessment-123",
            content: "When did the headache begin?",
          },
          nextState: "CLARIFYING",
        });
      }),
    );

    const result = await sendAssessmentMessage("assessment-123", {
      content: "I have a headache",
    });

    expect(result.message.content).toBe("I have a headache");
    expect(result.assistantMessage.content).toBe(
      "When did the headache begin?",
    );
    expect(result.nextState).toBe("CLARIFYING");
  });

  it("returns an empty array when message history is empty", async () => {
    server.use(
      http.get("*/api/v1/assessments/:id/messages", () =>
        HttpResponse.json([]),
      ),
    );

    const result = await getAssessmentMessages("assessment-123");

    expect(result).toEqual([]);
  });

  it("converts structured backend errors into AssessmentApiError", async () => {
    server.use(
      http.post("*/api/v1/assessments/:id/messages", () =>
        HttpResponse.json(
          {
            code: "INVALID_STATE",
            message: "Messages cannot be sent in the current state.",
            requestId: "request-123",
          },
          { status: 409 },
        ),
      ),
    );

    await expect(
      sendAssessmentMessage("assessment-123", {
        content: "Hello",
      }),
    ).rejects.toMatchObject({
      name: "AssessmentApiError",
      status: 409,
      code: "INVALID_STATE",
      requestId: "request-123",
      message: "Messages cannot be sent in the current state.",
    });
  });

  it("handles network failures without exposing request content", async () => {
    server.use(
      http.get("*/api/v1/assessments/:id/messages", () =>
        HttpResponse.error(),
      ),
    );

    await expect(
      getAssessmentMessages("assessment-123"),
    ).rejects.toBeInstanceOf(TypeError);
  });
});
