/**
 * @file Tests for the home-page welcome panel.
 * Owner: Nisarg · Task: S2-NIS-15 · Issue: #312 · Requirements: FR-02
 *
 * Covers guests (no panel), the greeting, recent assessments, the empty state,
 * the load error and the state labels.
 */
import { afterEach, describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import { getAssessmentHistory } from "../../services/historyApi";
import { useAuthStore } from "../../stores/authStore";
import type { AssessmentRead, UserRead } from "../../types";
import { RECENT_COUNT, WelcomeBackPanel, stateLabel } from "./WelcomeBackPanel";

vi.mock("../../services/historyApi", () => ({
  getAssessmentHistory: vi.fn(),
}));

const testUser: UserRead = {
  id: "user-1",
  email: "asha@example.com",
  createdAt: "2026-01-01T00:00:00Z",
};

const completed: AssessmentRead = {
  id: "assessment-1",
  state: "COMPLETED",
  consentId: "consent-1",
  userId: "user-1",
  createdAt: "2026-11-15T10:00:00Z",
};

const initialAuth = useAuthStore.getState();

/** Render the panel with routing and an isolated query client. */
function renderPanel() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <WelcomeBackPanel />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("WelcomeBackPanel", () => {
  afterEach(() => {
    useAuthStore.setState(initialAuth, true);
    vi.mocked(getAssessmentHistory).mockReset();
  });

  it("renders nothing for guests and does not fetch history", () => {
    useAuthStore.setState({ status: "unauthenticated", user: null });
    const { container } = renderPanel();
    expect(container).toBeEmptyDOMElement();
    expect(getAssessmentHistory).not.toHaveBeenCalled();
  });

  it("greets the user and lists recent assessments", async () => {
    vi.mocked(getAssessmentHistory).mockResolvedValue({
      items: [completed, { ...completed, id: "assessment-2", state: "CLARIFYING" }],
      nextOffset: null,
    });
    useAuthStore.setState({ status: "authenticated", user: testUser });
    renderPanel();

    expect(screen.getByRole("heading", { name: "Welcome back, asha" })).toBeInTheDocument();
    expect(await screen.findByText("Completed")).toBeInTheDocument();
    expect(screen.getByText("In progress")).toBeInTheDocument();
    expect(getAssessmentHistory).toHaveBeenCalledWith(RECENT_COUNT, 0);

    const links = screen.getAllByRole("link");
    expect(links.map((link) => link.getAttribute("href"))).toEqual(
      expect.arrayContaining(["/history", "/profile", "/history/assessment-1"]),
    );
  });

  it("explains the empty state", async () => {
    vi.mocked(getAssessmentHistory).mockResolvedValue({ items: [], nextOffset: null });
    useAuthStore.setState({ status: "authenticated", user: testUser });
    renderPanel();
    expect(await screen.findByText(/no saved assessments yet/i)).toBeInTheDocument();
  });

  it("shows an error when history cannot be loaded", async () => {
    vi.mocked(getAssessmentHistory).mockRejectedValue(new Error("down"));
    useAuthStore.setState({ status: "authenticated", user: testUser });
    renderPanel();
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Could not load your recent assessments.",
    );
  });

  it("labels assessment states in plain language", () => {
    expect(stateLabel("COMPLETED")).toBe("Completed");
    expect(stateLabel("ERROR")).toBe("Did not finish");
    expect(stateLabel("SYMPTOM_COLLECTION")).toBe("In progress");
  });
});
