/**
 * @file Client-side route definitions.
 * Owner: Rutva - Task: S2-RUT-2 - Issue: #181
 * Requirements: FR-02, NFR-08, NFR-09
 */
import { createBrowserRouter } from "react-router-dom";
import App from "../App";
import LandingPage from "../pages/LandingPage";
import ProfilePage from "../pages/ProfilePage";
import LoginPage from "../pages/LoginPage";
import RegisterPage from "../pages/RegisterPage";
import HistoryPage from "../pages/HistoryPage";

/** Defines the application's browser routes. */
export const router = createBrowserRouter([
  {
    path: "/",
    element: <LandingPage />,
  },
  {
    path: "/chat",
    element: <App />,
  },
  {
    path: "/profile",
    element: <ProfilePage />,
  },
  {
  path: "/login",
  element: <LoginPage />,
},
{
  path: "/register",
  element: <RegisterPage />,
},
{
  path: "/history",
  element: <HistoryPage />,
},
{
  path: "/history/:assessmentId",
  element: <HistoryPage />,
},
]);
