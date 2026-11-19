/**
 * @file Doctor referral component opening external map searches for relevant specialties.
 * Owner: Mann (Frontend + Deployment · Testing) · Task: S2-MAN-2 · Requirements: FR-08, idea §9
 * Restyle (design tokens, lucide icons, dark mode): Nisarg · S2-NIS-22 (#323)
 */

import { ArrowUpRight, Lock, Map as MapIcon, Stethoscope } from "lucide-react";
import { useState } from "react";
import type { DoctorReferralProps, MapProvider } from "./types";

/** Mandatory privacy notice emphasizing that no doctor or personal data is stored (FR-08, idea §9). */
export const DOCTOR_REFERRAL_DATA_NOTICE: string =
  "Opens external map search. No doctor or personal data is collected, stored, or tracked by this application.";

/** Default fallback specialty when none is provided. */
export const DEFAULT_REFERRAL_SPECIALTY: string = "General Physician";

/**
 * Builds a secure external map search URL targeting the requested specialty.
 *
 * @param specialty Name of medical specialty (e.g. "General Physician", "Dermatologist").
 * @param options Configuration for map search provider, query override, or location.
 * @returns Fully constructed and URL-encoded external search destination URL.
 */
export function buildMapSearchUrl(
  specialty: string,
  options?: {
    provider?: MapProvider;
    location?: string | null;
    query?: string | null;
  },
): string {
  const provider = options?.provider || "google";
  const cleanSpecialty = specialty.trim() || DEFAULT_REFERRAL_SPECIALTY;

  let query: string;
  if (options?.query && options.query.trim().length > 0) {
    query = options.query.trim();
  } else if (options?.location && options.location.trim().length > 0) {
    query = `${cleanSpecialty} in ${options.location.trim()}`;
  } else if (cleanSpecialty.toLowerCase().includes("near me")) {
    query = cleanSpecialty;
  } else {
    query = `${cleanSpecialty} near me`;
  }

  const encodedQuery = encodeURIComponent(query);

  switch (provider) {
    case "osm":
      return `https://www.openstreetmap.org/search?query=${encodedQuery}`;
    case "apple":
      return `https://maps.apple.com/?q=${encodedQuery}`;
    case "google":
    default:
      return `https://www.google.com/maps/search/?api=1&query=${encodedQuery}`;
  }
}

/**
 * Specialist referral component providing external map search pointers.
 *
 * Directs users to nearby qualified medical specialists via external map queries
 * (Google Maps, OpenStreetMap, Apple Maps). Emphasizes data privacy and module
 * boundaries: strictly no doctor profiles, availability tracking, ratings, or
 * booking data are stored or processed locally (FR-08, idea §9).
 *
 * @param props Configuration properties including specialty, secondary specialties, and query.
 * @returns Accessible specialist referral section.
 */
export function DoctorReferral({
  referral,
  specialty: directSpecialty,
  secondarySpecialties: directSecondary,
  mapQuery: directQuery,
  provider: initialProvider = "google",
  location = null,
  title = "Recommended Specialist Referral",
  onReferralClick,
  className = "",
}: DoctorReferralProps) {
  const [activeProvider, setActiveProvider] = useState<MapProvider>(initialProvider);

  // Extract primary specialty from either referral bundle or direct prop
  const effectiveSpecialty =
    directSpecialty || referral?.specialty || DEFAULT_REFERRAL_SPECIALTY;

  // Extract secondary specialties
  const effectiveSecondary =
    directSecondary || referral?.secondarySpecialties || [];

  // Extract query override
  const effectiveQuery = directQuery || referral?.mapQuery || null;

  const primarySearchUrl = buildMapSearchUrl(effectiveSpecialty, {
    provider: activeProvider,
    location,
    query: effectiveQuery,
  });

  const handleLinkClick = (spec: string, url: string) => {
    onReferralClick?.(spec, url);
  };

  return (
    <section
      aria-labelledby="referral-section-heading"
      className={`rounded-xl border border-border bg-card p-5 shadow-xs sm:p-6 ${className}`}
    >
      <div className="flex flex-col gap-5 sm:flex-row sm:items-start sm:justify-between">
        {/* Referral description */}
        <div className="space-y-2 max-w-xl">
          <div className="flex items-center gap-2">
            <span className="text-xl" aria-hidden="true">
              <Stethoscope className="size-5" aria-hidden="true" />
            </span>
            <h2
              id="referral-section-heading"
              className="text-lg font-bold tracking-tight text-foreground sm:text-xl"
            >
              {title}
            </h2>
          </div>

          <p className="text-xs text-muted-foreground sm:text-sm leading-relaxed">
            Based on what you reported, you may want to see a{" "}
            <strong className="font-semibold text-primary">
              {effectiveSpecialty}
            </strong>
            . This is a suggestion, not a diagnosis.
          </p>

          {/* Secondary specialties, if available */}
          {effectiveSecondary.length > 0 && (
            <div className="pt-2">
              <p className="text-xs font-medium text-muted-foreground">
                Related specialties to consider:
              </p>
              <div className="mt-1.5 flex flex-wrap gap-2">
                {effectiveSecondary.map((secSpecialty) => {
                  const secUrl = buildMapSearchUrl(secSpecialty, {
                    provider: activeProvider,
                    location,
                  });
                  return (
                    <a
                      key={secSpecialty}
                      href={secUrl}
                      target="_blank"
                      rel="noopener noreferrer"
                      onClick={() => handleLinkClick(secSpecialty, secUrl)}
                      aria-label={`Search for a ${secSpecialty} near you on external map`}
                      className="inline-flex items-center gap-1.5 rounded-lg border border-border bg-muted/60 px-2.5 py-1 text-xs font-medium text-muted-foreground transition hover:border-primary/40 hover:bg-primary/5 hover:text-primary-strong focus:outline-none focus:ring-2 focus:ring-ring"
                    >
                      <span>{secSpecialty}</span>
                      <ArrowUpRight className="size-3 text-muted-foreground" aria-hidden="true" />
                    </a>
                  );
                })}
              </div>
            </div>
          )}
        </div>

        {/* Primary map action */}
        <div className="flex flex-col gap-2 sm:items-end sm:shrink-0">
          <a
            href={primarySearchUrl}
            target="_blank"
            rel="noopener noreferrer"
            onClick={() => handleLinkClick(effectiveSpecialty, primarySearchUrl)}
            className="inline-flex min-h-[44px] items-center justify-center gap-2 rounded-xl bg-primary px-4 py-2.5 text-sm font-semibold text-primary-foreground shadow-xs transition hover:bg-primary/90 focus:outline-none focus:ring-4 focus:ring-ring/40"
            aria-label={`Find a ${effectiveSpecialty} near you on external map`}
          >
            <MapIcon className="size-4 shrink-0" aria-hidden="true" />
            <span>Find a {effectiveSpecialty} Near Me</span>
          </a>

          {/* Map provider toggle */}
          <div className="flex items-center gap-1 text-[11px] text-muted-foreground">
            <span>Provider:</span>
            <button
              type="button"
              onClick={() => setActiveProvider("google")}
              className={`px-1.5 py-0.5 rounded transition ${
                activeProvider === "google"
                  ? "bg-muted font-semibold text-foreground"
                  : "text-muted-foreground hover:text-foreground"
              }`}
            >
              Google
            </button>
            <span>·</span>
            <button
              type="button"
              onClick={() => setActiveProvider("osm")}
              className={`px-1.5 py-0.5 rounded transition ${
                activeProvider === "osm"
                  ? "bg-muted font-semibold text-foreground"
                  : "text-muted-foreground hover:text-foreground"
              }`}
            >
              OSM
            </button>
          </div>
        </div>
      </div>

      {/* Mandatory privacy & boundary notice (FR-08, idea §9) */}
      <div className="mt-4 border-t border-border pt-3 text-[11px] text-muted-foreground">
        <p className="flex items-center gap-1.5">
          <Lock className="size-4 shrink-0" aria-hidden="true" />
          <span>{DOCTOR_REFERRAL_DATA_NOTICE}</span>
        </p>
      </div>
    </section>
  );
}
