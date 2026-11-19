
/**
 * @file Tests for the authenticated assessment history page.
 * Owner: Rutva - Task: S2-RUT-2 - Issue: #181
 * Requirement: FR-02
 *
 * Covers list, empty, detail, error, authentication, and loading states.
 */

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen, within } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import HistoryPage from "./HistoryPage";
import { useAuthStore } from "../stores/authStore";
import {
  getAssessmentHistory,
  getAssessmentHistoryDetail,
} from "../services/historyApi";
import type { AssessmentRead, UserRead } from "../types";

vi.mock("../services/historyApi", () => ({
  getAssessmentHistory: vi.fn(),
  getAssessmentHistoryDetail: vi.fn(),
}));

const testUser: UserRead = {
  id: "user-1",
  email: "test@example.com",
  createdAt: "2026-01-01T00:00:00Z",
};

const testAssessment: AssessmentRead = {
  id: "assessment-1",
  state: "COMPLETED",
  consentId: "consent-1",
  userId: "user-1",
  guestSessionId: null,
  createdAt: "2026-11-15T10:00:00Z",
  updatedAt: "2026-11-15T10:30:00Z",
};

/**
 * Render the History page with routing and an isolated query client.
 *
 * @param initialEntry - Initial browser route for the test.
 * @returns Rendered test utilities.
 */
function renderHistoryPage(initialEntry = "/history") {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
    },
  });

  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[initialEntry]}>
        <Routes>
          <Route path="/history" element={<HistoryPage />} />
          <Route
            path="/history/:assessmentId"
            element={<HistoryPage />}
          />
          <Route path="/login" element={<h1>Login page</h1>} />
          <Route path="/chat" element={<h1>Chat page</h1>} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("HistoryPage", () => {
  beforeEach(() => {
    useAuthStore.setState({
      status: "authenticated",
      user: testUser,
    });

    vi.clearAllMocks();
  });

  afterEach(() => {
    cleanup();
  });

  it("renders the assessment history list", async () => {
    vi.mocked(getAssessmentHistory).mockResolvedValue({
      items: [testAssessment],
      nextOffset: null,
    });

    renderHistoryPage();

    expect(await screen.findByText("No saved result")).toBeInTheDocument();
    expect(screen.getByText("Completed")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /view details/i })).toHaveAttribute(
      "href",
      "/history/assessment-1",
    );
    expect(getAssessmentHistory).toHaveBeenCalledWith(20, 0);
  });

  it("shows the saved risk level and top condition (S2-NIS-16)", async () => {
    vi.mocked(getAssessmentHistory).mockResolvedValue({
      items: [
        {
          ...testAssessment,
          riskLevel: "URGENT",
          topCondition: "Heart attack (myocardial infarction)",
        },
      ],
      nextOffset: null,
    });

    renderHistoryPage();

    expect(
      await screen.findByText(
        "Top possible condition: Heart attack (myocardial infarction)",
      ),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("status", { name: "Risk level: Urgent Care Needed" }),
    ).toBeInTheDocument();
    expect(screen.getByText("View result")).toBeInTheDocument();
  });

  it("reopens a saved result from history (S2-NIS-16)", async () => {
    vi.mocked(getAssessmentHistoryDetail).mockResolvedValue({
      ...testAssessment,
      riskLevel: "SELF_CARE",
      topCondition: "Common cold",
      result: {
        assessmentId: "assessment-1",
        riskLevel: "SELF_CARE",
        conditions: [
          {
            name: "Common cold",
            confidence: "LIKELY",
            rank: 1,
            why: "Because you reported runny nose and sneezing.",
          },
        ],
        guidance: ["Rest and drink plenty of fluids."],
        referral: { required: false },
        limitations: [],
        modelVersion: "1.0.0",
        disclaimer: "This is not a medical diagnosis.",
        createdAt: "2026-11-15T10:30:00Z",
      },
    });

    renderHistoryPage("/history/assessment-1");

    expect(
      await screen.findByRole("heading", { name: "Past Assessment Result" }),
    ).toBeInTheDocument();
    expect(screen.getAllByText("Common cold").length).toBeGreaterThan(0);
    expect(screen.getByText("Rest and drink plenty of fluids.")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /back to history/i })).toHaveAttribute(
      "href",
      "/history",
    );
  });

  it("renders an empty state when no assessments exist", async () => {
    vi.mocked(getAssessmentHistory).mockResolvedValue({
      items: [],
      nextOffset: null,
    });

    renderHistoryPage();

    expect(
      await screen.findByText("No assessments yet"),
    ).toBeInTheDocument();

    expect(
      screen.getByRole("link", { name: "Start an assessment" }),
    ).toHaveAttribute("href", "/chat");
  });

  it("renders assessment details", async () => {
    vi.mocked(getAssessmentHistoryDetail).mockResolvedValue(
      testAssessment,
    );

    renderHistoryPage("/history/assessment-1");

    expect(
      await screen.findByText("assessment-1"),
    ).toBeInTheDocument();

    expect(screen.getByText("Completed")).toBeInTheDocument();
    expect(screen.getByText("Assessment information")).toBeInTheDocument();

    expect(getAssessmentHistoryDetail).toHaveBeenCalledWith(
      "assessment-1",
    );
  });

  it("shows an error when the history API fails", async () => {
    vi.mocked(getAssessmentHistory).mockRejectedValue(
      new Error("Network error"),
    );

    renderHistoryPage();

    expect(
      await screen.findByRole("alert"),
    ).toHaveTextContent("Unable to load assessment history");

    expect(
      screen.getByRole("button", { name: "Retry" }),
    ).toBeInTheDocument();
  });

  it("shows an error when assessment details cannot be loaded", async () => {
    vi.mocked(getAssessmentHistoryDetail).mockRejectedValue(
      new Error("Not found"),
    );

    renderHistoryPage("/history/unknown-assessment");

    expect(
      await screen.findByRole("alert"),
    ).toHaveTextContent("Unable to load this assessment");
  });

  it("asks unauthenticated users to log in", () => {
    useAuthStore.setState({
      status: "unauthenticated",
      user: null,
    });

    renderHistoryPage();

    expect(
      screen.getByText("Log in to view your history"),
    ).toBeInTheDocument();

    expect(
      within(screen.getByRole("main")).getByRole("link", { name: "Log in" }),
    ).toHaveAttribute("href", "/login");

    expect(getAssessmentHistory).not.toHaveBeenCalled();
  });

  it("shows a session loading state", () => {
    useAuthStore.setState({
      status: "loading",
      user: null,
    });

    renderHistoryPage();

    expect(
      screen.getByRole("status"),
    ).toHaveTextContent("Checking your session...");
  });

  it("shows a session verification error with retry", () => {
    useAuthStore.setState({
      status: "error",
      user: null,
    });

    renderHistoryPage();

    expect(
      screen.getByText("Unable to verify your session"),
    ).toBeInTheDocument();

    expect(
      screen.getByRole("button", { name: "Retry" }),
    ).toBeInTheDocument();
  });
});
