/**
 * @file App component tests.
 * Owner: Rutva · Tasks: S0-RUT-1, S2-HAR-3 · Requirements: NFR-08, NFR-09, DR-08
 */
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, describe, expect, it } from "vitest";
import App from "./App";
import { useConsentStore } from "./stores/consentStore";
import { server } from "./test/server";

/** Render a direct chat visit with an isolated policy query. */
function renderChat() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={["/chat"]}>
        <Routes>
          <Route path="/chat" element={<App />} />
          <Route path="/" element={<div>Review privacy notice</div>} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("App", () => {
  afterEach(() => useConsentStore.getState().clearConsent());

  it("renders the symptom assessment introduction with current consent", async () => {
    useConsentStore.getState().recordConsent("example-id", "1.0.0");
    server.use(
      http.get("/api/v1/consents/current-policy", () =>
        HttpResponse.json({ policyVersion: "1.0.0" }),
      ),
    );
    renderChat();

    expect(await screen.findByRole("heading", { name: "Symptom assessment" })).toBeInTheDocument();
    expect(screen.getByText(/does not provide a medical diagnosis/i)).toBeInTheDocument();
  });

  it("redirects a direct chat visit with outdated consent", async () => {
    useConsentStore.getState().recordConsent("example-id", "1.0.0");
    server.use(
      http.get("/api/v1/consents/current-policy", () =>
        HttpResponse.json({ policyVersion: "2.0.0" }),
      ),
    );
    renderChat();

    expect(await screen.findByText("Review privacy notice")).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Symptom assessment" })).not.toBeInTheDocument();
  });

  it("redirects a direct chat visit without consent", async () => {
    renderChat();
    expect(await screen.findByText("Review privacy notice")).toBeInTheDocument();
  });
});
