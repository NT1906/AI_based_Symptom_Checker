/**
 * @file Client-side route definitions with route-level code splitting.
 * Owner: Rutva - Task: S2-RUT-7 - Issue: #216
 * Requirements: NFR-01, NFR-06, NFR-08, NFR-09
 */
import { createBrowserRouter } from "react-router-dom";

/** Defines application routes and loads each page only when it is visited. */
export const router = createBrowserRouter([
  {
    path: "/",
    lazy: async () => {
      const { default: LandingPage } = await import("../pages/LandingPage");
      return { Component: LandingPage };
    },
  },
  {
    path: "/chat",
    lazy: async () => {
      const { default: App } = await import("../App");
      return { Component: App };
    },
  },
  {
    path: "/profile",
    lazy: async () => {
      const { default: ProfilePage } = await import("../pages/ProfilePage");
      return { Component: ProfilePage };
    },
  },
  {
    path: "/login",
    lazy: async () => {
      const { default: LoginPage } = await import("../pages/LoginPage");
      return { Component: LoginPage };
    },
  },
  {
    path: "/register",
    lazy: async () => {
      const { default: RegisterPage } = await import("../pages/RegisterPage");
      return { Component: RegisterPage };
    },
  },
  {
    path: "/history",
    lazy: async () => {
      const { default: HistoryPage } = await import("../pages/HistoryPage");
      return { Component: HistoryPage };
    },
  },
  {
    path: "/history/:assessmentId",
    lazy: async () => {
      const { default: HistoryPage } = await import("../pages/HistoryPage");
      return { Component: HistoryPage };
    },
  },
  {
    path: "/privacy",
    lazy: async () => {
      const { default: PrivacyPolicyPage } = await import("../pages/PrivacyPolicyPage");
      return { Component: PrivacyPolicyPage };
    },
  },
]);
