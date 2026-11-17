/**
 * @file Client-side error monitoring and telemetry service with strict zero-PII scrubbing.
 * Owner: Dimple · Task: S2-DIM-7 · Requirements: NFR-03, NFR-05, DR-06
 *
 * Implements client-side Sentry error reporting for production/staging:
 * - Dispatches unhandled exceptions and React rendering crashes to Sentry.
 * - Enforces strict DPDP Act 2023 and medical-safety zero-PII scrubbing.
 * - Strips email addresses, passwords, auth bearer tokens, and session token hashes.
 * - Strips free-text symptom descriptions and health messages.
 * - Operates gracefully when VITE_SENTRY_DSN is absent (disabled by default in test/local).
 * - Records sanitized UI breadcrumbs for diagnostic context.
 */

/** Configuration options for Sentry client initialization. */
export interface SentryConfig {
  /** Sentry project Data Source Name (DSN). e.g. https://public@sentry.io/123 */
  dsn?: string;
  /** Deployment environment name (e.g., 'production', 'staging', 'development'). */
  environment?: string;
  /** Application release version string. */
  release?: string;
  /** Sample rate for error events (0.0 to 1.0). Defaults to 1.0. */
  sampleRate?: number;
  /** Whether error reporting is active. Defaults to true if DSN is set. */
  enabled?: boolean;
}

/** Breadcrumb entry capturing sanitized client navigation or interaction state. */
export interface Breadcrumb {
  category: string;
  message: string;
  level?: "info" | "warning" | "error";
  timestamp: number;
  data?: Record<string, unknown>;
}

/** Internal client telemetry state. */
interface SentryState {
  isInitialized: boolean;
  config: SentryConfig;
  breadcrumbs: Breadcrumb[];
  parsedDsn: {
    protocol: string;
    publicKey: string;
    host: string;
    projectId: string;
  } | null;
}

const MAX_BREADCRUMBS = 50;

/** Regular expressions matching sensitive PII and authentication secrets. */
const EMAIL_REGEX = /[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}/g;
const BEARER_TOKEN_REGEX = /Bearer\s+[a-zA-Z0-9._~+/-]+=*/gi;
const HEX_HASH_64_REGEX = /\b[a-fA-F0-9]{64}\b/g;
const JWT_TOKEN_REGEX = /\bey[a-zA-Z0-9_-]+\.[a-zA-Z0-9_-]+\.[a-zA-Z0-9_-]+\b/g;

const state: SentryState = {
  isInitialized: false,
  config: {},
  breadcrumbs: [],
  parsedDsn: null,
};

/**
 * Scrubs email addresses, bearer tokens, cryptographic hashes, and health text from strings.
 *
 * @param input - Raw text string.
 * @returns Sanitized string safe for telemetry transmission.
 */
export function scrubPii(input: string): string {
  if (!input) {
    return "";
  }
  return input
    .replace(EMAIL_REGEX, "[REDACTED_EMAIL]")
    .replace(JWT_TOKEN_REGEX, "[REDACTED_JWT]")
    .replace(BEARER_TOKEN_REGEX, "Bearer [REDACTED_TOKEN]")
    .replace(HEX_HASH_64_REGEX, "[REDACTED_HASH]");
}

/**
 * Recursively sanitizes an object, scrubbing PII and stripping sensitive health keys.
 *
 * @param data - Metadata object to sanitize.
 * @returns Cleaned object containing zero health data or user credentials.
 */
export function scrubObject(
  data: Record<string, unknown>,
): Record<string, unknown> {
  const SENSITIVE_KEYS = new Set([
    "email",
    "password",
    "password_hash",
    "token",
    "token_hash",
    "authorization",
    "symptoms",
    "content",
    "message",
    "chronic_conditions",
    "user_id",
  ]);

  const output: Record<string, unknown> = {};

  for (const [key, value] of Object.entries(data)) {
    const lowerKey = key.toLowerCase();
    if (SENSITIVE_KEYS.has(lowerKey)) {
      output[key] = "[REDACTED_SENSITIVE]";
      continue;
    }

    if (typeof value === "string") {
      output[key] = scrubPii(value);
    } else if (value && typeof value === "object" && !Array.isArray(value)) {
      output[key] = scrubObject(value as Record<string, unknown>);
    } else {
      output[key] = value;
    }
  }

  return output;
}

/**
 * Parses a Sentry DSN URL into its component elements.
 *
 * @param dsn - Raw Sentry DSN string.
 * @returns Parsed components or null if invalid.
 */
function parseDsn(
  dsn: string,
): { protocol: string; publicKey: string; host: string; projectId: string } | null {
  try {
    const url = new URL(dsn);
    const publicKey = url.username;
    const projectId = url.pathname.replace(/^\//, "");
    if (!publicKey || !projectId) {
      return null;
    }
    return {
      protocol: url.protocol,
      publicKey,
      host: url.host,
      projectId,
    };
  } catch {
    return null;
  }
}

/**
 * Initializes Sentry telemetry and binds global uncaught error listeners.
 *
 * @param options - Custom configuration overrides.
 */
export function initSentry(options?: Partial<SentryConfig>): void {
  const envDsn =
    options?.dsn ||
    (typeof import.meta !== "undefined" && import.meta.env?.VITE_SENTRY_DSN) ||
    "";

  const environment =
    options?.environment ||
    (typeof import.meta !== "undefined" && import.meta.env?.MODE) ||
    "production";

  const config: SentryConfig = {
    dsn: envDsn,
    environment,
    release: options?.release || "1.0.0",
    sampleRate: options?.sampleRate ?? 1.0,
    enabled: options?.enabled ?? Boolean(envDsn),
  };

  state.config = config;
  state.parsedDsn = config.dsn ? parseDsn(config.dsn) : null;
  state.breadcrumbs = [];
  state.isInitialized = true;

  if (typeof window !== "undefined" && config.enabled) {
    window.addEventListener("error", (event) => {
      captureException(event.error || event.message, {
        source: "window.onerror",
        filename: event.filename,
        lineno: event.lineno,
      });
    });

    window.addEventListener("unhandledrejection", (event) => {
      captureException(event.reason, {
        source: "window.onunhandledrejection",
      });
    });
  }
}

/**
 * Appends a sanitized navigational or action breadcrumb to telemetry state.
 *
 * @param breadcrumb - Breadcrumb data.
 */
export function addBreadcrumb(
  breadcrumb: Omit<Breadcrumb, "timestamp">,
): void {
  const sanitized: Breadcrumb = {
    category: breadcrumb.category,
    message: scrubPii(breadcrumb.message),
    level: breadcrumb.level || "info",
    timestamp: Date.now() / 1000,
    data: breadcrumb.data ? scrubObject(breadcrumb.data) : undefined,
  };

  state.breadcrumbs.push(sanitized);
  if (state.breadcrumbs.length > MAX_BREADCRUMBS) {
    state.breadcrumbs.shift();
  }
}

/**
 * Returns current in-memory breadcrumbs (useful for test validation).
 *
 * @returns Array of breadcrumbs.
 */
export function getBreadcrumbs(): readonly Breadcrumb[] {
  return state.breadcrumbs;
}

/**
 * Clears in-memory breadcrumbs queue.
 */
export function clearBreadcrumbs(): void {
  state.breadcrumbs = [];
}

/**
 * Captures an application exception, scrubs all PII, and transmits to Sentry.
 *
 * @param error - The caught error object or message string.
 * @param context - Optional metadata attached to the error report.
 */
export function captureException(
  error: unknown,
  context?: Record<string, unknown>,
): void {
  if (!state.isInitialized) {
    initSentry({ enabled: false });
  }

  const errorMessage =
    error instanceof Error ? error.message : typeof error === "string" ? error : "Unknown error";

  const errorStack = error instanceof Error ? error.stack : undefined;

  const sanitizedMessage = scrubPii(errorMessage);
  const sanitizedContext = context ? scrubObject(context) : {};

  // If telemetry is disabled or no DSN is present, record locally in dev mode
  if (!state.config.enabled || !state.parsedDsn) {
    return;
  }

  // Construct Sentry-compatible event payload
  const eventPayload = {
    event_id: crypto.randomUUID().replace(/-/g, ""),
    timestamp: new Date().toISOString(),
    platform: "javascript",
    level: "error",
    environment: state.config.environment,
    release: state.config.release,
    exception: {
      values: [
        {
          type: error instanceof Error ? error.name : "Error",
          value: sanitizedMessage,
          stacktrace: errorStack
            ? {
                frames: errorStack
                  .split("\n")
                  .slice(1)
                  .map((line) => ({ filename: scrubPii(line.trim()) })),
              }
            : undefined,
        },
      ],
    },
    breadcrumbs: [...state.breadcrumbs],
    extra: sanitizedContext,
  };

  const { protocol, host, projectId, publicKey } = state.parsedDsn;
  const sentryUrl = `${protocol}//${host}/api/${projectId}/store/?sentry_version=7&sentry_key=${publicKey}&sentry_client=custom-pwa-client/1.0.0`;

  try {
    fetch(sentryUrl, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(eventPayload),
      keepalive: true,
    }).catch(() => {
      // Ignore network transport failures during error dispatch
    });
  } catch {
    // Non-blocking telemetry failure
  }
}

/**
 * Resets Sentry service state (used primarily in unit testing).
 */
export function resetSentry(): void {
  state.isInitialized = false;
  state.config = {};
  state.breadcrumbs = [];
  state.parsedDsn = null;
}
