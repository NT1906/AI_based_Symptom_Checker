/**
 * @file Tests for the header account control.
 * Owner: Nisarg · Task: S2-NIS-15 · Issue: #312 · Requirements: FR-02, NFR-06
 *
 * Covers guest links, the logged-in menu, Escape to close, logout (clears
 * session state and returns home), logout failure, and rendering outside a router.
 */
import { afterEach, describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { useAssessmentStore } from "../../stores/assessmentStore";
import { useAuthStore } from "../../stores/authStore";
import { useConsentStore } from "../../stores/consentStore";
import type { UserRead } from "../../types";
import { AccountMenu, avatarInitial } from "./AccountMenu";

const testUser: UserRead = {
  id: "user-1",
  email: "asha@example.com",
  createdAt: "2026-01-01T00:00:00Z",
};

const initialAuth = useAuthStore.getState();

/** Render the menu on /history with a home route to observe navigation. */
function renderMenu() {
  return render(
    <MemoryRouter initialEntries={["/history"]}>
      <AccountMenu />
      <Routes>
        <Route path="/" element={<p>Home page</p>} />
        <Route path="/history" element={<p>History page</p>} />
      </Routes>
    </MemoryRouter>,
  );
}

describe("AccountMenu", () => {
  afterEach(() => {
    useAuthStore.setState(initialAuth, true);
    useConsentStore.setState({ consentId: null, consentedAt: null, policyVersion: null });
  });

  it("renders nothing outside a router", () => {
    useAuthStore.setState({ status: "unauthenticated", user: null });
    const { container } = render(<AccountMenu />);
    expect(container).toBeEmptyDOMElement();
  });

  it("renders nothing while the session is being checked", () => {
    useAuthStore.setState({ status: "idle", user: null });
    renderMenu();
    expect(screen.queryByRole("link", { name: "Log in" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /account menu/i })).not.toBeInTheDocument();
  });

  it("shows log-in and sign-up links to guests", () => {
    useAuthStore.setState({ status: "unauthenticated", user: null });
    renderMenu();
    expect(screen.getByRole("link", { name: "Log in" })).toHaveAttribute("href", "/login");
    expect(screen.getByRole("link", { name: "Sign up" })).toHaveAttribute("href", "/register");
  });

  it("shows the user's email and account links when logged in", async () => {
    useAuthStore.setState({ status: "authenticated", user: testUser });
    const user = userEvent.setup();
    renderMenu();

    const trigger = screen.getByRole("button", { name: "Account menu for asha@example.com" });
    expect(trigger).toHaveAttribute("aria-expanded", "false");
    await user.click(trigger);

    expect(trigger).toHaveAttribute("aria-expanded", "true");
    const menu = screen.getByRole("menu", { name: "Account" });
    expect(menu).toHaveTextContent("Signed in as");
    expect(menu).toHaveTextContent("asha@example.com");
    expect(screen.getByRole("menuitem", { name: /my history/i })).toHaveAttribute(
      "href",
      "/history",
    );
    expect(screen.getByRole("menuitem", { name: /my profile/i })).toHaveAttribute(
      "href",
      "/profile",
    );
    expect(screen.getByRole("menuitem", { name: /privacy & data/i })).toHaveAttribute(
      "href",
      "/privacy",
    );

    await user.keyboard("{Escape}");
    expect(screen.queryByRole("menu")).not.toBeInTheDocument();
  });

  it("logs out, clears session state and returns home", async () => {
    const logout = vi.fn().mockResolvedValue(undefined);
    useAuthStore.setState({ status: "authenticated", user: testUser, logout });
    useConsentStore.setState({ consentId: "consent-1", policyVersion: "1.0.0" });
    const clearAssessment = vi.spyOn(useAssessmentStore.getState(), "clearAssessment");
    const user = userEvent.setup();
    renderMenu();

    await user.click(screen.getByRole("button", { name: /account menu/i }));
    await user.click(screen.getByRole("menuitem", { name: /log out/i }));

    expect(logout).toHaveBeenCalledOnce();
    expect(clearAssessment).toHaveBeenCalledOnce();
    expect(useConsentStore.getState().consentId).toBeNull();
    expect(await screen.findByText("Home page")).toBeInTheDocument();
  });

  it("stays put and explains when logout fails", async () => {
    const logout = vi.fn().mockRejectedValue(new Error("network"));
    useAuthStore.setState({ status: "authenticated", user: testUser, logout });
    const user = userEvent.setup();
    renderMenu();

    await user.click(screen.getByRole("button", { name: /account menu/i }));
    await user.click(screen.getByRole("menuitem", { name: /log out/i }));

    expect(await screen.findByRole("alert")).toHaveTextContent("Could not log out");
    expect(screen.getByText("History page")).toBeInTheDocument();
  });

  it("uses the email's first letter as the avatar", () => {
    expect(avatarInitial("asha@example.com")).toBe("A");
    expect(avatarInitial("  ")).toBe("?");
  });
});
