
/**
 * @file Authentication store tests.
 * Owner: Rutva · Task: S2-RUT-1 · Issue: #180
 */

import { beforeEach, describe, expect, it, vi } from "vitest";
import {
  AuthApiError,
  getCurrentUser,
  loginUser,
  logoutUser,
  registerUser,
} from "../services/authApi";
import { useAuthStore } from "./authStore";

vi.mock("../services/authApi", async (importOriginal) => {
  const actual =
    await importOriginal<typeof import("../services/authApi")>();

  return {
    ...actual,
    registerUser: vi.fn(),
    loginUser: vi.fn(),
    logoutUser: vi.fn(),
    getCurrentUser: vi.fn(),
  };
});

const exampleUser = {
  id: "user-123",
  email: "test@example.com",
  createdAt: "2026-11-16T10:00:00Z",
};

const exampleLogin = {
  email: "test@example.com",
  password: "password123",
};

const exampleRegister = {
  email: "test@example.com",
  password: "password123",
};

describe("authentication store", () => {
  beforeEach(() => {
    vi.clearAllMocks();

    useAuthStore.setState({
      user: null,
      status: "idle",
      errorMessage: null,
    });
  });

  it("starts without an authenticated user", () => {
    const state = useAuthStore.getState();

    expect(state.user).toBeNull();
    expect(state.status).toBe("idle");
    expect(state.errorMessage).toBeNull();
  });

  it("registers a new user without automatically logging them in", async () => {
    vi.mocked(registerUser).mockResolvedValue(exampleUser);

    const result = await useAuthStore
      .getState()
      .register(exampleRegister);

    expect(result).toEqual(exampleUser);
    expect(useAuthStore.getState().user).toBeNull();
    expect(useAuthStore.getState().status).toBe("unauthenticated");
  });

  it("sets an error when registration fails", async () => {
    vi.mocked(registerUser).mockRejectedValue(
      new AuthApiError(409, {
        code: "EMAIL_EXISTS",
        message: "Email already registered",
        requestId: "request-1",
      }),
    );

    await expect(
      useAuthStore.getState().register(exampleRegister),
    ).rejects.toThrow();

    expect(useAuthStore.getState().status).toBe("error");
    expect(useAuthStore.getState().errorMessage).toBe(
      "An account with this email already exists.",
    );
  });

  it("logs in and stores the authenticated user", async () => {
    vi.mocked(loginUser).mockResolvedValue(exampleUser);

    await useAuthStore.getState().login(exampleLogin);

    expect(loginUser).toHaveBeenCalledWith(exampleLogin);
    expect(useAuthStore.getState().user).toEqual(exampleUser);
    expect(useAuthStore.getState().status).toBe("authenticated");
    expect(useAuthStore.getState().errorMessage).toBeNull();
  });

  it("clears the user when login fails", async () => {
    vi.mocked(loginUser).mockRejectedValue(
      new AuthApiError(401, {
        code: "INVALID_CREDENTIALS",
        message: "Invalid email or password",
        requestId: "request-2",
      }),
    );

    await expect(
      useAuthStore.getState().login(exampleLogin),
    ).rejects.toThrow();

    expect(useAuthStore.getState().user).toBeNull();
    expect(useAuthStore.getState().status).toBe("error");
  });

  it("loads the current authenticated user", async () => {
    vi.mocked(getCurrentUser).mockResolvedValue(exampleUser);

    await useAuthStore.getState().loadCurrentUser();

    expect(useAuthStore.getState().user).toEqual(exampleUser);
    expect(useAuthStore.getState().status).toBe("authenticated");
  });

  it("handles an expired session without treating it as an unexpected error", async () => {
    vi.mocked(getCurrentUser).mockRejectedValue(
      new AuthApiError(401, {
        code: "UNAUTHORIZED",
        message: "Not authenticated",
        requestId: "request-3",
      }),
    );

    await useAuthStore.getState().loadCurrentUser();

    expect(useAuthStore.getState().user).toBeNull();
    expect(useAuthStore.getState().status).toBe("unauthenticated");
    expect(useAuthStore.getState().errorMessage).toBeNull();
  });

  it("sets an error when current-user loading fails unexpectedly", async () => {
    vi.mocked(getCurrentUser).mockRejectedValue(
      new Error("Network unavailable"),
    );

    await expect(
      useAuthStore.getState().loadCurrentUser(),
    ).rejects.toThrow("Network unavailable");

    expect(useAuthStore.getState().status).toBe("error");
    expect(useAuthStore.getState().user).toBeNull();
  });

  it("logs out and clears the authenticated user", async () => {
    useAuthStore.setState({
      user: exampleUser,
      status: "authenticated",
    });

    vi.mocked(logoutUser).mockResolvedValue({
      status: "ok",
      message: "Successfully logged out",
    });

    await useAuthStore.getState().logout();

    expect(useAuthStore.getState().user).toBeNull();
    expect(useAuthStore.getState().status).toBe("unauthenticated");
  });

  it("preserves the user when logout fails", async () => {
    useAuthStore.setState({
      user: exampleUser,
      status: "authenticated",
    });

    vi.mocked(logoutUser).mockRejectedValue(
      new Error("Network unavailable"),
    );

    await expect(
      useAuthStore.getState().logout(),
    ).rejects.toThrow("Network unavailable");

    expect(useAuthStore.getState().user).toEqual(exampleUser);
    expect(useAuthStore.getState().status).toBe("authenticated");
    expect(useAuthStore.getState().errorMessage).toBeTruthy();
  });

  it("clears an authentication error", () => {
    useAuthStore.setState({
      status: "error",
      errorMessage: "Login failed",
    });

    useAuthStore.getState().clearAuthError();

    expect(useAuthStore.getState().errorMessage).toBeNull();
  });
});
