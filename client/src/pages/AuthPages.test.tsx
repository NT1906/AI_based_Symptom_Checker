/**
 * @file Tests for the login and register pages.
 * Owner: Nisarg · Task: S2-NIS-21 · Issue: #322 · Requirements: FR-01, NFR-06
 */
import { afterEach, describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { useAuthStore } from "../stores/authStore";
import LoginPage from "./LoginPage";
import RegisterPage from "./RegisterPage";

const initialAuth = useAuthStore.getState();

/** Render a page with a home and login route to observe navigation. */
function renderAt(path: "/login" | "/register") {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route path="/" element={<p>Home page</p>} />
        <Route path="/login" element={<LoginPage />} />
        <Route path="/register" element={<RegisterPage />} />
      </Routes>
    </MemoryRouter>,
  );
}

afterEach(() => useAuthStore.setState(initialAuth, true));

describe("LoginPage", () => {
  it("asks for both fields and a valid email before calling the server", async () => {
    const login = vi.fn();
    useAuthStore.setState({ status: "unauthenticated", login });
    const user = userEvent.setup();
    renderAt("/login");

    await user.click(screen.getByRole("button", { name: "Sign In" }));
    expect(screen.getByRole("alert")).toHaveTextContent("Please enter your email and password.");

    await user.type(screen.getByLabelText("Email address"), "not-an-email");
    await user.type(screen.getByLabelText("Password"), "secret-pass");
    await user.click(screen.getByRole("button", { name: "Sign In" }));
    expect(screen.getByRole("alert")).toHaveTextContent("Please enter a valid email address.");
    expect(login).not.toHaveBeenCalled();
  });

  it("logs in with a normalised email and returns home", async () => {
    const login = vi.fn().mockResolvedValue(undefined);
    useAuthStore.setState({ status: "unauthenticated", login });
    const user = userEvent.setup();
    renderAt("/login");

    await user.type(screen.getByLabelText("Email address"), "  Asha@Example.com ");
    await user.type(screen.getByLabelText("Password"), "secret-pass");
    await user.click(screen.getByRole("button", { name: "Sign In" }));

    expect(login).toHaveBeenCalledWith({ email: "asha@example.com", password: "secret-pass" });
    expect(await screen.findByText("Home page")).toBeInTheDocument();
  });

  it("shows the store's error message", () => {
    useAuthStore.setState({ status: "error", errorMessage: "Invalid email or password." });
    renderAt("/login");
    expect(screen.getByRole("alert")).toHaveTextContent("Invalid email or password.");
  });

  it("reveals and hides the password", async () => {
    useAuthStore.setState({ status: "unauthenticated" });
    const user = userEvent.setup();
    renderAt("/login");
    const field = screen.getByLabelText("Password");
    expect(field).toHaveAttribute("type", "password");
    await user.click(screen.getByRole("button", { name: "Show password" }));
    expect(field).toHaveAttribute("type", "text");
    expect(screen.getByRole("button", { name: "Hide password" })).toHaveAttribute("aria-pressed", "true");
  });

  it("offers guest use and account creation", () => {
    useAuthStore.setState({ status: "unauthenticated" });
    renderAt("/login");
    expect(screen.getByRole("link", { name: /continue as guest/i })).toHaveAttribute("href", "/");
    expect(screen.getByRole("link", { name: "Create account" })).toHaveAttribute("href", "/register");
  });
});

describe("RegisterPage", () => {
  it("rejects mismatched and too-short passwords", async () => {
    const register = vi.fn();
    useAuthStore.setState({ status: "unauthenticated", register });
    const user = userEvent.setup();
    renderAt("/register");

    await user.type(screen.getByLabelText("Email address"), "asha@example.com");
    await user.type(screen.getByLabelText("Password"), "short");
    await user.type(screen.getByLabelText("Confirm password"), "short");
    await user.click(screen.getByRole("button", { name: "Create Account" }));
    expect(screen.getByRole("alert")).toHaveTextContent("between 8 and 128 characters");

    await user.clear(screen.getByLabelText("Password"));
    await user.type(screen.getByLabelText("Password"), "Long-enough-1");
    await user.click(screen.getByRole("button", { name: "Create Account" }));
    expect(screen.getByRole("alert")).toHaveTextContent("Your passwords do not match.");
    expect(register).not.toHaveBeenCalled();
  });

  it("shows password strength", async () => {
    useAuthStore.setState({ status: "unauthenticated" });
    const user = userEvent.setup();
    renderAt("/register");
    await user.type(screen.getByLabelText("Password"), "Abcdef1!x");
    expect(screen.getByText("Password strength: Strong")).toBeInTheDocument();
  });

  it("creates the account and sends the user to log in", async () => {
    const register = vi.fn().mockResolvedValue({});
    useAuthStore.setState({ status: "unauthenticated", register });
    const user = userEvent.setup();
    renderAt("/register");

    await user.type(screen.getByLabelText("Email address"), "asha@example.com");
    await user.type(screen.getByLabelText("Password"), "Long-enough-1");
    await user.type(screen.getByLabelText("Confirm password"), "Long-enough-1");
    await user.click(screen.getByRole("button", { name: "Create Account" }));

    expect(register).toHaveBeenCalledWith({ email: "asha@example.com", password: "Long-enough-1" });
    expect(await screen.findByRole("status")).toHaveTextContent("Account created successfully!");
    await user.click(screen.getByRole("button", { name: "Go to Login" }));
    expect(screen.getByRole("heading", { name: "Welcome back" })).toBeInTheDocument();
  });
});
