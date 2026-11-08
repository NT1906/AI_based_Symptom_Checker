/**
 * @file Unit tests for ImageAttach component.
 * Owner: Mann (Frontend + Deployment · Testing) · Task: S2-MAN-1 · Requirements: idea §3, DR-06
 */

import { fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
  ImageAttach,
  IMAGE_PRIVACY_DISCLAIMER,
  MAX_IMAGE_SIZE_BYTES,
  formatFileSize,
} from "./ImageAttach";
import type { ConfirmedSymptom } from "./types";

describe("ImageAttach Component", () => {
  const createMockFile = (
    name = "rash-photo.jpg",
    size = 1024 * 1024,
    type = "image/jpeg",
  ): File => {
    const buffer = new ArrayBuffer(size);
    return new File([buffer], name, { type });
  };

  beforeEach(() => {
    // Mock URL.createObjectURL and URL.revokeObjectURL in jsdom
    globalThis.URL.createObjectURL = vi.fn(
      () => "blob:http://localhost:3000/mock-preview-id",
    );
    globalThis.URL.revokeObjectURL = vi.fn();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe("Situational Rendering (idea §3)", () => {
    it("renders nothing when no visual symptoms are present", () => {
      const { container } = render(
        <ImageAttach
          symptoms="I have a high fever and headache"
          onImageSelect={vi.fn()}
        />,
      );
      expect(container.firstChild).toBeNull();
    });

    it("renders nothing for non-visual ConfirmedSymptom items", () => {
      const nonVisualSymptoms: ConfirmedSymptom[] = [
        { id: "1", name: "Fever", severity: "MODERATE" },
        { id: "2", name: "Fatigue", severity: "MILD" },
      ];
      const { container } = render(
        <ImageAttach symptoms={nonVisualSymptoms} onImageSelect={vi.fn()} />,
      );
      expect(container.firstChild).toBeNull();
    });

    it("renders when visual symptoms are detected in user text", () => {
      render(
        <ImageAttach
          symptoms="I have an itchy red rash on my arm"
          onImageSelect={vi.fn()}
        />,
      );
      expect(
        screen.getByRole("region", { name: "Visual symptom photo attachment" }),
      ).toBeInTheDocument();
      expect(screen.getByText("Visual Symptom Detected")).toBeInTheDocument();
      expect(screen.getByText("Optional")).toBeInTheDocument();
    });

    it("renders when visual symptoms are present in structured symptom list", () => {
      const visualSymptoms: ConfirmedSymptom[] = [
        {
          id: "rash-1",
          name: "Skin rash or redness",
          severity: "MODERATE",
          bodyLocation: "forearm",
        },
      ];
      render(
        <ImageAttach symptoms={visualSymptoms} onImageSelect={vi.fn()} />,
      );
      expect(
        screen.getByRole("region", { name: "Visual symptom photo attachment" }),
      ).toBeInTheDocument();
    });

    it("renders when forceShow is true even without visual symptoms", () => {
      render(
        <ImageAttach
          forceShow={true}
          symptoms="Just feeling tired"
          onImageSelect={vi.fn()}
        />,
      );
      expect(
        screen.getByRole("region", { name: "Visual symptom photo attachment" }),
      ).toBeInTheDocument();
    });
  });

  describe("Mobile Camera Capture and File Picker", () => {
    it("configures camera input with capture='environment' for mobile devices", () => {
      render(
        <ImageAttach forceShow={true} onImageSelect={vi.fn()} />,
      );
      const cameraInput = screen.getByLabelText("Take photo with camera");
      expect(cameraInput).toBeInTheDocument();
      expect(cameraInput).toHaveAttribute("capture", "environment");
      expect(cameraInput).toHaveAttribute("accept", "image/jpeg,image/png,image/webp");
    });

    it("configures choose photo input for gallery/file selection without capture attribute", () => {
      render(
        <ImageAttach forceShow={true} onImageSelect={vi.fn()} />,
      );
      const fileInput = screen.getByLabelText("Choose photo from device");
      expect(fileInput).toBeInTheDocument();
      expect(fileInput).not.toHaveAttribute("capture");
      expect(fileInput).toHaveAttribute("accept", "image/jpeg,image/png,image/webp");
    });

    it("triggers camera file input when 'Take photo' button is clicked", async () => {
      render(
        <ImageAttach forceShow={true} onImageSelect={vi.fn()} />,
      );
      const cameraInput = screen.getByLabelText("Take photo with camera");
      const clickSpy = vi.spyOn(cameraInput, "click");

      const takePhotoBtn = screen.getByRole("button", { name: /Take photo/i });
      await userEvent.click(takePhotoBtn);

      expect(clickSpy).toHaveBeenCalledTimes(1);
    });

    it("triggers file picker when 'Choose photo' button is clicked", async () => {
      render(
        <ImageAttach forceShow={true} onImageSelect={vi.fn()} />,
      );
      const fileInput = screen.getByLabelText("Choose photo from device");
      const clickSpy = vi.spyOn(fileInput, "click");

      const choosePhotoBtn = screen.getByRole("button", { name: /Choose photo/i });
      await userEvent.click(choosePhotoBtn);

      expect(clickSpy).toHaveBeenCalledTimes(1);
    });
  });

  describe("Happy Path - Image selection and in-memory preview", () => {
    it("selects valid JPEG photo, displays thumbnail, and invokes onImageSelect", () => {
      const onImageSelect = vi.fn();
      render(
        <ImageAttach forceShow={true} onImageSelect={onImageSelect} />,
      );

      const file = createMockFile("rash.jpg", 1.5 * 1024 * 1024, "image/jpeg");
      const fileInput = screen.getByLabelText("Choose photo from device");

      fireEvent.change(fileInput, { target: { files: [file] } });

      expect(onImageSelect).toHaveBeenCalledWith(file);
      expect(screen.getByText("rash.jpg")).toBeInTheDocument();
      expect(screen.getByText(/1.5 MB/)).toBeInTheDocument();

      const previewImage = screen.getByAltText("Attached visual symptom preview");
      expect(previewImage).toBeInTheDocument();
      expect(previewImage).toHaveAttribute(
        "src",
        "blob:http://localhost:3000/mock-preview-id",
      );
    });

    it("displays mandatory privacy notice stating photos are never stored (DR-06)", () => {
      render(
        <ImageAttach forceShow={true} onImageSelect={vi.fn()} />,
      );
      expect(screen.getByText(IMAGE_PRIVACY_DISCLAIMER)).toBeInTheDocument();
    });

    it("allows removing the selected photo and revokes preview URL", async () => {
      const onImageSelect = vi.fn();
      render(
        <ImageAttach forceShow={true} onImageSelect={onImageSelect} />,
      );

      const file = createMockFile("swelling.png", 500 * 1024, "image/png");
      const fileInput = screen.getByLabelText("Choose photo from device");

      fireEvent.change(fileInput, { target: { files: [file] } });
      expect(screen.getByText("swelling.png")).toBeInTheDocument();

      const removeBtn = screen.getByRole("button", { name: "Remove attached photo" });
      await userEvent.click(removeBtn);

      expect(onImageSelect).toHaveBeenLastCalledWith(null);
      expect(screen.queryByText("swelling.png")).not.toBeInTheDocument();
      expect(globalThis.URL.revokeObjectURL).toHaveBeenCalled();
    });
  });

  describe("Edge cases and Validation failures", () => {
    it("rejects images larger than 5 MB limit and presents an alert", () => {
      const onImageSelect = vi.fn();
      const onError = vi.fn();

      render(
        <ImageAttach
          forceShow={true}
          onImageSelect={onImageSelect}
          onError={onError}
        />,
      );

      const oversizedFile = createMockFile(
        "large-photo.jpg",
        MAX_IMAGE_SIZE_BYTES + 1024,
        "image/jpeg",
      );
      const fileInput = screen.getByLabelText("Choose photo from device");

      fireEvent.change(fileInput, { target: { files: [oversizedFile] } });

      expect(onImageSelect).not.toHaveBeenCalled();
      expect(onError).toHaveBeenCalledWith(
        expect.stringContaining("Image file exceeds the 5 MB limit"),
      );
      const alert = screen.getByRole("alert");
      expect(alert).toHaveTextContent(/exceeds the 5 MB limit/);
    });

    it("rejects unsupported MIME types (e.g. GIF, PDF)", () => {
      const onImageSelect = vi.fn();
      const onError = vi.fn();

      render(
        <ImageAttach
          forceShow={true}
          onImageSelect={onImageSelect}
          onError={onError}
        />,
      );

      const gifFile = createMockFile("animation.gif", 200 * 1024, "image/gif");
      const fileInput = screen.getByLabelText("Choose photo from device");

      fireEvent.change(fileInput, { target: { files: [gifFile] } });

      expect(onImageSelect).not.toHaveBeenCalled();
      expect(onError).toHaveBeenCalledWith(
        "Unsupported image format. Please select a JPEG, PNG, or WebP photo.",
      );
      expect(screen.getByRole("alert")).toHaveTextContent(/Unsupported image format/);
    });

    it("honors selectedFile prop when controlled externally", () => {
      const file = createMockFile("external-eczema.webp", 800 * 1024, "image/webp");
      render(
        <ImageAttach
          forceShow={true}
          selectedFile={file}
          onImageSelect={vi.fn()}
        />,
      );

      expect(screen.getByText("external-eczema.webp")).toBeInTheDocument();
      expect(screen.getByText(/800\.0 KB/)).toBeInTheDocument();
    });

    it("disables buttons and inputs when disabled prop is true", () => {
      render(
        <ImageAttach forceShow={true} disabled={true} onImageSelect={vi.fn()} />,
      );

      expect(screen.getByRole("button", { name: /Take photo/i })).toBeDisabled();
      expect(screen.getByRole("button", { name: /Choose photo/i })).toBeDisabled();
      expect(screen.getByLabelText("Take photo with camera")).toBeDisabled();
      expect(screen.getByLabelText("Choose photo from device")).toBeDisabled();
    });
  });

  describe("formatFileSize helper", () => {
    it("formats bytes, kilobytes, and megabytes correctly", () => {
      expect(formatFileSize(500)).toBe("500 B");
      expect(formatFileSize(1536)).toBe("1.5 KB");
      expect(formatFileSize(2.5 * 1024 * 1024)).toBe("2.5 MB");
    });
  });
});
