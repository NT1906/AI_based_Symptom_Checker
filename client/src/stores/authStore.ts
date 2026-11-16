
/**
 * @file Transient authentication state and actions.
 * Owner: Rutva · Task: S2-RUT-1 · Issue: #180
 *
 * Stores the current user in memory only.
 * Passwords and authentication tokens are never persisted.
 */

import { create } from "zustand";
import type {
  UserLoginRequest,
  UserRead,
  UserRegisterRequest,
} from "../types";
import {
  AuthApiError,
  getCurrentUser,
  loginUser,
  logoutUser,
  registerUser,
} from "../services/authApi";

type AuthStatus =
  | "idle"
  | "loading"
  | "authenticated"
  | "unauthenticated"
  | "error";

/** Client-side authentication state and actions. */
type AuthStoreState = {
  user: UserRead | null;
  status: AuthStatus;
  errorMessage: string | null;
  register: (request: UserRegisterRequest) => Promise<UserRead>;
  login: (request: UserLoginRequest) => Promise<void>;
  logout: () => Promise<void>;
  loadCurrentUser: () => Promise<void>;
  clearAuthError: () => void;
};

/** Return a safe message for an authentication failure. */
function getAuthErrorMessage(error: unknown): string {
  if (error instanceof AuthApiError) {
    if (error.status === 401) {
      return "Your session has expired. Please log in again.";
    }

    if (error.status === 409) {
      return "An account with this email already exists.";
    }

    if (error.status === 422) {
      return "Please check the information you entered.";
    }

    return error.message;
  }

  return "Something went wrong. Please try again.";
}

/** Holds transient authentication state without browser persistence. */
export const useAuthStore = create<AuthStoreState>((set, get) => ({
  user: null,
  status: "idle",
  errorMessage: null,

  register: async (request) => {
    set({ status: "loading", errorMessage: null });

    try {
      const user = await registerUser(request);

      // Registration does not establish a login session.
      set({ user: null, status: "unauthenticated" });

      return user;
    } catch (error) {
      set({
        status: "error",
        errorMessage: getAuthErrorMessage(error),
      });
      throw error;
    }
  },

  login: async (request) => {
    set({ status: "loading", errorMessage: null });

    try {
      const user = await loginUser(request);
      set({
        user,
        status: "authenticated",
        errorMessage: null,
      });
    } catch (error) {
      set({
        user: null,
        status: "error",
        errorMessage: getAuthErrorMessage(error),
      });
      throw error;
    }
  },

  logout: async () => {
    set({ status: "loading", errorMessage: null });

    try {
      await logoutUser();
      set({
        user: null,
        status: "unauthenticated",
        errorMessage: null,
      });
    } catch (error) {
      set({
        status: get().user ? "authenticated" : "error",
        errorMessage: getAuthErrorMessage(error),
      });
      throw error;
    }
  },

  loadCurrentUser: async () => {
    set({ status: "loading", errorMessage: null });

    try {
      const user = await getCurrentUser();
      set({
        user,
        status: "authenticated",
        errorMessage: null,
      });
    } catch (error) {
      if (error instanceof AuthApiError && error.status === 401) {
        set({
          user: null,
          status: "unauthenticated",
          errorMessage: null,
        });
        return;
      }

      set({
        user: null,
        status: "error",
        errorMessage: getAuthErrorMessage(error),
      });
      throw error;
    }
  },

  clearAuthError: () => set({ errorMessage: null }),
}));
