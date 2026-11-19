/**
 * @file Tests for reading the CSRF cookie.
 * Owner: Nisarg · Task: S2-NIS-18 · Issue: #315 · Requirements: NFR-03
 */
import { describe, expect, it } from "vitest";
import { readCsrfToken } from "./csrf";

describe("readCsrfToken", () => {
  it("finds the token among other cookies", () => {
    expect(readCsrfToken("theme=dark; csrf_token=abc%3D123; other=1")).toBe("abc=123");
  });

  it("returns null when the cookie is missing or empty", () => {
    expect(readCsrfToken("theme=dark")).toBeNull();
    expect(readCsrfToken("csrf_token=")).toBeNull();
    expect(readCsrfToken("")).toBeNull();
  });
});
