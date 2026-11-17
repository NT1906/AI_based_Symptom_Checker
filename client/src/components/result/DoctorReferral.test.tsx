/**
 * @file Unit tests for DoctorReferral component and map search URL generator.
 * Owner: Mann (Frontend + Deployment · Testing) · Task: S2-MAN-2 · Requirements: FR-08, idea §9
 */

import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import {
  DoctorReferral,
  buildMapSearchUrl,
  DOCTOR_REFERRAL_DATA_NOTICE,
  DEFAULT_REFERRAL_SPECIALTY,
} from "./DoctorReferral";
import type { ReferralInfo } from "./types";

describe("DoctorReferral Component", () => {
  describe("Happy Path - Primary Referral Presentation", () => {
    it("renders recommended specialty and external map search link", () => {
      render(<DoctorReferral specialty="Dermatologist" />);

      expect(
        screen.getByRole("heading", { name: "Recommended Specialist Referral" }),
      ).toBeInTheDocument();
      expect(screen.getByText("Dermatologist")).toBeInTheDocument();

      const mapLink = screen.getByRole("link", {
        name: "Find a Dermatologist near you on external map",
      });
      expect(mapLink).toBeInTheDocument();
      expect(mapLink).toHaveAttribute("target", "_blank");
      expect(mapLink).toHaveAttribute("rel", "noopener noreferrer");
      expect(mapLink).toHaveAttribute(
        "href",
        "https://www.google.com/maps/search/?api=1&query=Dermatologist%20near%20me",
      );
    });

    it("accepts a structured ReferralInfo bundle", () => {
      const referral: ReferralInfo = {
        specialty: "Neurologist",
        secondarySpecialties: ["General Physician"],
        mapQuery: "Neurologist clinic near me",
      };

      render(<DoctorReferral referral={referral} />);

      expect(screen.getByText("Neurologist")).toBeInTheDocument();
      const link = screen.getByRole("link", {
        name: "Find a Neurologist near you on external map",
      });
      expect(link).toHaveAttribute(
        "href",
        "https://www.google.com/maps/search/?api=1&query=Neurologist%20clinic%20near%20me",
      );
    });

    it("displays mandatory data privacy notice (FR-08, idea §9)", () => {
      render(<DoctorReferral specialty="Cardiologist" />);
      expect(screen.getByText(DOCTOR_REFERRAL_DATA_NOTICE)).toBeInTheDocument();
    });
  });

  describe("Secondary Specialties", () => {
    it("renders clickable external map links for secondary specialties", () => {
      render(
        <DoctorReferral
          specialty="Orthopedic Surgeon"
          secondarySpecialties={["Rheumatologist", "General Physician"]}
        />,
      );

      expect(screen.getByText("Related specialties to consider:")).toBeInTheDocument();

      const rheumLink = screen.getByRole("link", {
        name: "Search for a Rheumatologist near you on external map",
      });
      expect(rheumLink).toHaveAttribute("target", "_blank");
      expect(rheumLink).toHaveAttribute("rel", "noopener noreferrer");
      expect(rheumLink).toHaveAttribute(
        "href",
        "https://www.google.com/maps/search/?api=1&query=Rheumatologist%20near%20me",
      );

      const gpLink = screen.getByRole("link", {
        name: "Search for a General Physician near you on external map",
      });
      expect(gpLink).toHaveAttribute(
        "href",
        "https://www.google.com/maps/search/?api=1&query=General%20Physician%20near%20me",
      );
    });
  });

  describe("Provider Switching & Custom Configuration", () => {
    it("switches map destination to OpenStreetMap when OSM provider is selected", async () => {
      render(<DoctorReferral specialty="Pediatrician" />);

      const osmButton = screen.getByRole("button", { name: "OSM" });
      await userEvent.click(osmButton);

      const primaryLink = screen.getByRole("link", {
        name: "Find a Pediatrician near you on external map",
      });
      expect(primaryLink).toHaveAttribute(
        "href",
        "https://www.openstreetmap.org/search?query=Pediatrician%20near%20me",
      );
    });

    it("applies location hint when provided", () => {
      render(
        <DoctorReferral specialty="Allergist" location="South Mumbai" />,
      );

      const link = screen.getByRole("link", {
        name: "Find a Allergist near you on external map",
      });
      expect(link).toHaveAttribute(
        "href",
        "https://www.google.com/maps/search/?api=1&query=Allergist%20in%20South%20Mumbai",
      );
    });

    it("fires onReferralClick callback when the user clicks map link", async () => {
      const onReferralClick = vi.fn();
      render(
        <DoctorReferral
          specialty="Ophthalmologist"
          onReferralClick={onReferralClick}
        />,
      );

      const link = screen.getByRole("link", {
        name: "Find a Ophthalmologist near you on external map",
      });
      await userEvent.click(link);

      expect(onReferralClick).toHaveBeenCalledTimes(1);
      expect(onReferralClick).toHaveBeenCalledWith(
        "Ophthalmologist",
        "https://www.google.com/maps/search/?api=1&query=Ophthalmologist%20near%20me",
      );
    });
  });

  describe("Edge Cases and Fallbacks", () => {
    it("falls back to DEFAULT_REFERRAL_SPECIALTY when no specialty is provided", () => {
      render(<DoctorReferral />);

      expect(
        screen.getByRole("link", {
          name: `Find a ${DEFAULT_REFERRAL_SPECIALTY} near you on external map`,
        }),
      ).toBeInTheDocument();
    });

    it("safely encodes special characters in medical specialties", () => {
      render(<DoctorReferral specialty="ENT / Ear, Nose & Throat" />);

      const link = screen.getByRole("link", {
        name: "Find a ENT / Ear, Nose & Throat near you on external map",
      });
      expect(link.getAttribute("href")).toContain(
        encodeURIComponent("ENT / Ear, Nose & Throat near me"),
      );
    });
  });

  describe("buildMapSearchUrl utility function", () => {
    it("generates valid Google Maps search URLs by default", () => {
      const url = buildMapSearchUrl("Dermatologist");
      expect(url).toBe(
        "https://www.google.com/maps/search/?api=1&query=Dermatologist%20near%20me",
      );
    });

    it("generates valid OpenStreetMap search URLs", () => {
      const url = buildMapSearchUrl("Dentist", { provider: "osm" });
      expect(url).toBe(
        "https://www.openstreetmap.org/search?query=Dentist%20near%20me",
      );
    });

    it("generates valid Apple Maps search URLs", () => {
      const url = buildMapSearchUrl("Cardiologist", { provider: "apple" });
      expect(url).toBe("https://maps.apple.com/?q=Cardiologist%20near%20me");
    });

    it("preserves explicit queries without repeating 'near me'", () => {
      const url = buildMapSearchUrl("General Clinic near me");
      expect(url).toBe(
        "https://www.google.com/maps/search/?api=1&query=General%20Clinic%20near%20me",
      );
    });
  });
});
