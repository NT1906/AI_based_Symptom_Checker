
/**
 * @file Typed authentication API services.
 * Owner: Rutva · Task: S2-RUT-1 · Issue: #180
 *
 * Uses HttpOnly session cookies and generated OpenAPI contracts.
 * Credentials and authentication tokens are never persisted in browser storage.
 */

import type {
  ErrorResponse,
  LogoutResponse,
  UserLoginRequest,
  UserRead,
  UserRegisterRequest,
} from "../types";

/** Structured error returned by an authentication API request. */
export class AuthApiError extends Error {
  /** HTTP status returned by the server. */
  readonly status: number;

  /** Machine-readable error code, when supplied by the API. */
  readonly code?: string;

  /** Request identifier supplied by the API, when available. */
  readonly requestId?: string;

  /**
   * Create a typed authentication API error.
   *
   * @param status - HTTP response status.
   * @param payload - Parsed API error payload, if available.
   */
  constructor(status: number, payload?: ErrorResponse) {
    super(payload?.message ?? "The authentication service could not complete the request.");
    this.name = "AuthApiError";
    this.status = status;
    this.code = payload?.code;
    this.requestId = payload?.requestId;
  }
}

/**
 * Check whether an unknown value matches the generated API error contract.
 *
 * @param value - Value received from the server.
 * @returns Whether the value is an API error response.
 */
function isErrorResponse(value: unknown): value is ErrorResponse {
  if (typeof value !== "object" || value === null) {
    return false;
  }

  const payload = value as Record<string, unknown>;

  return (
    typeof payload.code === "string" &&
    typeof payload.message === "string" &&
    typeof payload.requestId === "string"
  );
}

/**
 * Send an authentication request and return its typed JSON response.
 *
 * @param path - Relative API path.
 * @param init - Fetch configuration.
 * @returns Parsed response matching the generated OpenAPI type.
 * @throws AuthApiError when the server returns an unsuccessful status.
 */
async function requestJson<T>(
  path: string,
  init: RequestInit = {},
): Promise<T> {
  const response = await fetch(new URL(path, window.location.origin), {
    ...init,
    credentials: "include",
    headers: {
      ...(init.body ? { "Content-Type": "application/json" } : {}),
      ...init.headers,
    },
  });

  if (!response.ok) {
    const payload: unknown = await response.json().catch(() => null);

    throw new AuthApiError(
      response.status,
      isErrorResponse(payload) ? payload : undefined,
    );
  }

  return (await response.json()) as T;
}

/**
 * Register a new user account.
 *
 * @param request - Registration credentials.
 * @returns Newly created user account.
 */
export function registerUser(
  request: UserRegisterRequest,
): Promise<UserRead> {
  return requestJson<UserRead>("/api/v1/auth/register", {
    method: "POST",
    body: JSON.stringify(request),
  });
}

/**
 * Authenticate an existing user and establish a session cookie.
 *
 * @param request - Login credentials.
 * @returns Authenticated user account.
 */
export function loginUser(
  request: UserLoginRequest,
): Promise<UserRead> {
  return requestJson<UserRead>("/api/v1/auth/login", {
    method: "POST",
    body: JSON.stringify(request),
  });
}

/**
 * Terminate the current authenticated session.
 *
 * @returns Logout confirmation.
 */
export function logoutUser(): Promise<LogoutResponse> {
  return requestJson<LogoutResponse>("/api/v1/auth/logout", {
    method: "POST",
  });
}

/**
 * Retrieve the currently authenticated user using the session cookie.
 *
 * @returns Current user account.
 */
export function getCurrentUser(): Promise<UserRead> {
  return requestJson<UserRead>("/api/v1/auth/me");
}
