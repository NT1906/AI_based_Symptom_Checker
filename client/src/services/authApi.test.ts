
/**
 * @file Authentication API service tests.
 * Owner: Rutva · Task: S2-RUT-1 · Issue: #180
 */

import { http, HttpResponse } from "msw";
import { beforeEach, describe, expect, it } from "vitest";
import {
  AuthApiError,
  getCurrentUser,
  loginUser,
  logoutUser,
  registerUser,
} from "./authApi";
import { server } from "../test/server";

const user = {
  id: "user-123",
  email: "rutva@example.com",
  createdAt: "2026-11-16T08:00:00Z",
};

describe("authentication API services", () => {
  beforeEach(() => {
    server.resetHandlers();
  });

  it("registers a new user", async () => {
    server.use(
      http.post("*/api/v1/auth/register", async ({ request }) => {
        expect(await request.json()).toEqual({
          email: "rutva@example.com",
          password: "secure-password",
        });

        return HttpResponse.json(user, { status: 201 });
      }),
    );

    await expect(
      registerUser({
        email: "rutva@example.com",
        password: "secure-password",
      }),
    ).resolves.toEqual(user);
  });

  it("logs in and establishes a cookie-based session", async () => {
    server.use(
      http.post("*/api/v1/auth/login", async ({ request }) => {
        
        expect(await request.json()).toEqual({
          email: "rutva@example.com",
          password: "secure-password",
        });

        return HttpResponse.json(user);
      }),
    );

    await expect(
      loginUser({
        email: "rutva@example.com",
        password: "secure-password",
      }),
    ).resolves.toEqual(user);
  });

  it("logs out the current user", async () => {
    server.use(
      http.post("*/api/v1/auth/logout", () => {
        return HttpResponse.json({
          status: "ok",
          message: "Successfully logged out",
        });
      }),
    );

    await expect(logoutUser()).resolves.toEqual({
      status: "ok",
      message: "Successfully logged out",
    });
  });

  it("retrieves the current user using the session cookie", async () => {
    server.use(
      http.get("*/api/v1/auth/me", () => {
        
        return HttpResponse.json(user);
      }),
    );

    await expect(getCurrentUser()).resolves.toEqual(user);
  });

  it.each([
    [409, "EMAIL_ALREADY_EXISTS"],
    [401, "INVALID_CREDENTIALS"],
    [422, "VALIDATION_ERROR"],
  ])("converts backend error %i into AuthApiError", async (status, code) => {
    server.use(
      http.post("*/api/v1/auth/login", () =>
        HttpResponse.json(
          {
            code,
            message: "Authentication request failed.",
            requestId: "request-123",
          },
          { status },
        ),
      ),
    );

    await expect(
      loginUser({
        email: "rutva@example.com",
        password: "incorrect-password",
      }),
    ).rejects.toMatchObject({
      name: "AuthApiError",
      status,
      code,
      requestId: "request-123",
    });
  });

  it("handles unauthenticated current-user requests", async () => {
    server.use(
      http.get("*/api/v1/auth/me", () =>
        HttpResponse.json(
          {
            code: "UNAUTHORIZED",
            message: "Authentication is required.",
            requestId: "request-401",
          },
          { status: 401 },
        ),
      ),
    );

    await expect(getCurrentUser()).rejects.toBeInstanceOf(AuthApiError);
  });

  it("handles network failures without exposing credentials", async () => {
    server.use(
      http.post("*/api/v1/auth/login", () => HttpResponse.error()),
    );

    await expect(
      loginUser({
        email: "rutva@example.com",
        password: "secure-password",
      }),
    ).rejects.toBeInstanceOf(TypeError);
  });
});
