/**
 * @file Client-side route definitions.
 * Owner: Rutva - Task: S2-RUT-1 - Issue: #180
 * Requirements: NFR-08, NFR-09
 */
import { createBrowserRouter } from "react-router-dom";
import App from "../App";
import LandingPage from "../pages/LandingPage";
import ProfilePage from "../pages/ProfilePage";
import LoginPage from "../pages/LoginPage";
import RegisterPage from "../pages/RegisterPage";

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
]);
