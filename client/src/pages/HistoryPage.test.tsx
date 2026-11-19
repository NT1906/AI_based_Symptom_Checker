
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

    expect(
      await screen.findByText("Assessment assessment-1"),
    ).toBeInTheDocument();

    expect(screen.getByText("Completed")).toBeInTheDocument();
    expect(getAssessmentHistory).toHaveBeenCalledWith(20, 0);
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
