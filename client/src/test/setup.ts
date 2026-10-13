/**
 * @file Vitest test setup.
 * Owner: Rutva · Task: S0-RUT-1 · Requirements: NFR-08, NFR-09
 */
import "@testing-library/jest-dom/vitest";
import { afterAll, afterEach, beforeAll } from "vitest";
import { server } from "./server";

beforeAll(() => server.listen());
afterEach(() => server.resetHandlers());
afterAll(() => server.close());
