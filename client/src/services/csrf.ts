/**
 * @file CSRF header for state-changing requests that need it.
 * Owner: Nisarg · Task: S2-NIS-18 · Issue: #315 · Requirements: NFR-03, NFR-04
 *
 * The server sets a readable `csrf_token` cookie at login (double-submit
 * pattern). Requests that change account data echo it in `X-CSRF-Token`.
 */

/** Name of the readable CSRF cookie set by the server at login. */
export const CSRF_COOKIE_NAME = "csrf_token";

/**
 * Read the CSRF token from the browser cookies.
 *
 * @param cookieString - Cookie string to read; defaults to `document.cookie`.
 * @returns The token, or null when there is none.
 */
export function readCsrfToken(cookieString: string = document.cookie): string | null {
  for (const part of cookieString.split(";")) {
    const [name, ...rest] = part.trim().split("=");
    if (name === CSRF_COOKIE_NAME) {
      const value = decodeURIComponent(rest.join("="));
      return value || null;
    }
  }
  return null;
}

/**
 * Headers carrying the CSRF token, or no headers when there is no token.
 *
 * @returns An object to spread into `fetch` headers.
 */
export function csrfHeaders(): Record<string, string> {
  const token = readCsrfToken();
  return token ? { "X-CSRF-Token": token } : {};
}
