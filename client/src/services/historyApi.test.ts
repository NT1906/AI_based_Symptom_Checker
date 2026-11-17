
/**
 * @file Tests for assessment history API services.
 * Owner: Rutva - Task: S2-RUT-2 - Issue: #181
 * Requirement: FR-02
 */

import { http, HttpResponse } from "msw";
import { beforeEach, describe, expect, it } from "vitest";
import {
  getAssessmentHistory,
  getAssessmentHistoryDetail,
} from "./historyApi";
import { server } from "../test/server";

describe("assessment history API services", () => {
  beforeEach(() => {
    server.resetHandlers();
  });

  it("retrieves a page of assessment history", async () => {
    server.use(
      http.get("*/api/v1/history", ({ request }) => {
        const url = new URL(request.url);

        expect(url.searchParams.get("limit")).toBe("20");
        expect(url.searchParams.get("offset")).toBe("0");

        return HttpResponse.json({
          items: [
            {
              id: "assessment-123",
              consentId: "consent-123",
              state: "COMPLETED",
              createdAt: "2026-11-16T08:00:00Z",
            },
          ],
          nextOffset: null,
        });
      }),
    );

    const result = await getAssessmentHistory();

    expect(result.items).toHaveLength(1);
    expect(result.items[0].id).toBe("assessment-123");
    expect(result.nextOffset).toBeNull();
  });

  it("supports requesting the next page", async () => {
    server.use(
      http.get("*/api/v1/history", ({ request }) => {
        const url = new URL(request.url);

        expect(url.searchParams.get("limit")).toBe("10");
        expect(url.searchParams.get("offset")).toBe("10");

        return HttpResponse.json({
          items: [],
          nextOffset: null,
        });
      }),
    );

    const result = await getAssessmentHistory(10, 10);

    expect(result.items).toEqual([]);
    expect(result.nextOffset).toBeNull();
  });

  it("rejects invalid pagination values", async () => {
    await expect(getAssessmentHistory(0, 0)).rejects.toThrow(RangeError);
    await expect(getAssessmentHistory(101, 0)).rejects.toThrow(RangeError);
    await expect(getAssessmentHistory(20, -1)).rejects.toThrow(RangeError);
  });

  it("retrieves an individual assessment from history", async () => {
    server.use(
      http.get("*/api/v1/history/:assessmentId", ({ params }) => {
        expect(params.assessmentId).toBe("assessment-123");

        return HttpResponse.json({
          id: "assessment-123",
          consentId: "consent-123",
          state: "COMPLETED",
          createdAt: "2026-11-16T08:00:00Z",
        });
      }),
    );

    const result = await getAssessmentHistoryDetail("assessment-123");

    expect(result.id).toBe("assessment-123");
    expect(result.state).toBe("COMPLETED");
  });

  it("rejects an empty assessment identifier", async () => {
    await expect(getAssessmentHistoryDetail("")).rejects.toThrow(RangeError);
    await expect(getAssessmentHistoryDetail("   ")).rejects.toThrow(RangeError);
  });

  it("handles an assessment that is not available to the user", async () => {
    server.use(
      http.get("*/api/v1/history/:assessmentId", () =>
        HttpResponse.json(
          {
            code: "NOT_FOUND",
            message: "Assessment not found.",
            requestId: "request-123",
          },
          { status: 404 },
        ),
      ),
    );

    await expect(
      getAssessmentHistoryDetail("unknown-assessment"),
    ).rejects.toMatchObject({
      name: "AssessmentApiError",
      status: 404,
      code: "NOT_FOUND",
    });
  });

  it("handles network failures without exposing assessment content", async () => {
    server.use(
      http.get("*/api/v1/history", () => HttpResponse.error()),
    );

    await expect(getAssessmentHistory()).rejects.toBeInstanceOf(TypeError);
  });
});
