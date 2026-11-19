/**
 * @file Tests for account settings (change password, export/delete panel).
 * Owner: Nisarg · Task: S2-NIS-18 · Issue: #315 · Requirements: FR-01, DR-06
 */
import { afterEach, describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { AuthApiError, changePassword } from "../../services/authApi";
import { useAuthStore } from "../../stores/authStore";
import { AccountSettings, validatePasswordChange } from "./AccountSettings";

vi.mock("../../services/authApi", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../../services/authApi")>();
  return { ...actual, changePassword: vi.fn() };
});

const user1 = { id: "user-1", email: "asha@example.com", createdAt: "2026-01-01T00:00:00Z" };

/** Render the settings inside a router. */
function renderSettings() {
  return render(
    <MemoryRouter>
      <AccountSettings />
    </MemoryRouter>,
  );
}

/** Fill the three password fields. */
async function fill(current: string, next: string, confirm: string) {
  const user = userEvent.setup();
  await user.type(screen.getByLabelText("Current password"), current);
  await user.type(screen.getByLabelText("New password"), next);
  await user.type(screen.getByLabelText("Confirm new password"), confirm);
  await user.click(screen.getByRole("button", { name: "Change password" }));
}

describe("AccountSettings", () => {
  afterEach(() => {
    useAuthStore.setState({ user: null, status: "idle", errorMessage: null });
    vi.mocked(changePassword).mockReset();
  });

  it("renders nothing for guests", () => {
    useAuthStore.setState({ user: null, status: "unauthenticated" });
    const { container } = renderSettings();
    expect(container).toBeEmptyDOMElement();
  });

  it("shows the account email, password form and data controls", () => {
    useAuthStore.setState({ user: user1, status: "authenticated" });
    renderSettings();
    expect(screen.getByRole("heading", { name: "Account settings" })).toBeInTheDocument();
    expect(screen.getByText("asha@example.com")).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /permanently delete all data/i }),
    ).toBeInTheDocument();
  });

  it("changes the password and clears the form", async () => {
    useAuthStore.setState({ user: user1, status: "authenticated" });
    vi.mocked(changePassword).mockResolvedValue(undefined);
    renderSettings();

    await fill("Old-pass-123", "New-pass-456", "New-pass-456");

    expect(changePassword).toHaveBeenCalledWith({
      currentPassword: "Old-pass-123",
      newPassword: "New-pass-456",
    });
    expect(await screen.findByRole("status")).toHaveTextContent("Your password has been changed.");
    expect(screen.getByLabelText("Current password")).toHaveValue("");
  });

  it("shows the server's message for a wrong current password", async () => {
    useAuthStore.setState({ user: user1, status: "authenticated" });
    vi.mocked(changePassword).mockRejectedValue(
      new AuthApiError(422, {
        code: "VALIDATION_ERROR",
        message: "Your current password is incorrect.",
        requestId: "req-1",
      }),
    );
    renderSettings();

    await fill("wrong-pass", "New-pass-456", "New-pass-456");

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Your current password is incorrect.",
    );
  });

  it("stops before calling the server when the new passwords differ", async () => {
    useAuthStore.setState({ user: user1, status: "authenticated" });
    renderSettings();
    await fill("Old-pass-123", "New-pass-456", "New-pass-789");
    expect(screen.getByRole("alert")).toHaveTextContent("The new passwords do not match.");
    expect(changePassword).not.toHaveBeenCalled();
  });

  it("validates the form", () => {
    expect(validatePasswordChange("", "x", "x")).toMatch(/fill in all three/);
    expect(validatePasswordChange("old-pass", "short", "short")).toMatch(/at least 8/);
    expect(validatePasswordChange("same-pass1", "same-pass1", "same-pass1")).toMatch(/differs/);
    expect(validatePasswordChange("old-pass1", "new-pass1", "new-pass1")).toBeNull();
  });
});
