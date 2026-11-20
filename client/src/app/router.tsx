/**
 * @file Client-side route definitions.
 * Owner: Rutva - Task: S2-RUT-2 - Issue: #181
 * Requirements: FR-02, NFR-08, NFR-09
 * Root layout, scroll reset, not-found and error routes: Nisarg · S2-NIS-25 (#338)
 */
import { useEffect, useRef } from "react";
import {
  createBrowserRouter,
  Outlet,
  useLocation,
  useNavigationType,
  type RouteObject,
} from "react-router-dom";
import App from "../App";
import LandingPage from "../pages/LandingPage";
import ProfilePage from "../pages/ProfilePage";
import LoginPage from "../pages/LoginPage";
import RegisterPage from "../pages/RegisterPage";
import HistoryPage from "../pages/HistoryPage";
import PrivacyPolicyPage from "../pages/PrivacyPolicyPage";
import { NotFoundPage, RouteErrorPage } from "../pages/NotFoundPage";

/**
 * Opens each newly visited page at the top instead of at the previous page's
 * scroll offset. Only a change of path counts: in-page `#` links (e.g. "How it
 * works") keep their native jump, and browser back/forward ("POP") is left to
 * the browser's own scroll restoration.
 *
 * @returns Nothing; it only manages scrolling.
 */
export function ScrollToTop(): null {
  const { pathname } = useLocation();
  const navigationType = useNavigationType();
  const lastPathname = useRef(pathname);

  useEffect(() => {
    if (pathname === lastPathname.current) return;
    lastPathname.current = pathname;
    if (navigationType !== "POP") window.scrollTo(0, 0);
  }, [pathname, navigationType]);

  return null;
}

/**
 * Wraps every page with the scroll reset.
 *
 * @returns The current page.
 */
export function RootLayout(): React.JSX.Element {
  return (
    <>
      <ScrollToTop />
      <Outlet />
    </>
  );
}

/** The application's routes; exported so tests can mount them in a memory router. */
export const routes: RouteObject[] = [
  {
    element: <RootLayout />,
    errorElement: <RouteErrorPage />,
    children: [
      { path: "/", element: <LandingPage /> },
      { path: "/chat", element: <App /> },
      { path: "/profile", element: <ProfilePage /> },
      { path: "/login", element: <LoginPage /> },
      { path: "/register", element: <RegisterPage /> },
      { path: "/history", element: <HistoryPage /> },
      { path: "/history/:assessmentId", element: <HistoryPage /> },
      { path: "/privacy", element: <PrivacyPolicyPage /> },
      { path: "*", element: <NotFoundPage /> },
    ],
  },
];

/** Defines the application's browser routes. */
export const router = createBrowserRouter(routes);
