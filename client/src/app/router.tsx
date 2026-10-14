/**
 * @file Client-side route definitions.
 * Owner: Rutva · Task: S0-RUT-1 · Requirements: NFR-08, NFR-09
 */
import { createBrowserRouter } from "react-router-dom";
import LandingPage from "../pages/LandingPage";

/** Defines the application's browser routes. */
export const router = createBrowserRouter([
  {
    path: "/",
    element: <LandingPage />,
  },
]);
