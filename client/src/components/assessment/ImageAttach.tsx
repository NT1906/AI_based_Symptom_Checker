/**
 * @file Situational image attachment component with mobile camera capture and in-memory validation.
 * Owner: Mann (Frontend + Deployment · Testing) · Task: S2-MAN-1 · Requirements: idea §3
 */

import {
  type ChangeEvent,
  useEffect,
  useRef,
  useState,
} from "react";
import type { ImageAttachProps } from "./types";
import { hasVisualSymptoms } from "./visualSymptoms";

/** Maximum allowed upload payload size in bytes (5 MB per server upload policy). */
export const MAX_IMAGE_SIZE_BYTES: number = 5 * 1024 * 1024;

/** Permitted image MIME types matching backend validator policy. */
export const ALLOWED_IMAGE_TYPES: readonly string[] = Object.freeze([
  "image/jpeg",
  "image/png",
  "image/webp",
]);

/** Mandatory privacy and non-retention disclaimer for image uploads (DR-06, AI_RULES.md §2.10). */
export const IMAGE_PRIVACY_DISCLAIMER: string =
  "Photos are processed in-memory for visual triage analysis and are never stored, logged, or shared.";

/**
 * Formats byte counts into friendly, human-readable strings (e.g. "2.4 MB").
 *
 * @param bytes The raw file size in bytes.
 * @returns Formatted size string.
 */
export function formatFileSize(bytes: number): string {
  if (bytes < 1024) {
    return `${bytes} B`;
  }
  if (bytes < 1024 * 1024) {
    return `${(bytes / 1024).toFixed(1)} KB`;
  }
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

/**
 * Situational image attachment component for guided chat conversations.
 *
 * Appears only when visual symptoms (rashes, skin discoloration, swelling, bumps)
 * are detected or when explicitly forced. Provides direct mobile camera capture
 * via `capture="environment"` as well as gallery file selection, client-side
 * MIME and 5 MB size validation, in-memory preview with removal, and non-retention
 * privacy notices.
 *
 * @param props Configuration and callbacks for image attachment.
 * @returns The rendered attachment widget, or null if no visual symptoms detected.
 */
export function ImageAttach({
  symptoms,
  forceShow = false,
  selectedFile: externalFile,
  onImageSelect,
  onError,
  disabled = false,
  className = "",
}: ImageAttachProps) {
  const [internalFile, setInternalFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const fileInputRef = useRef<HTMLInputElement>(null);
  const cameraInputRef = useRef<HTMLInputElement>(null);

  const currentFile = externalFile !== undefined ? externalFile : internalFile;

  // Evaluate whether visual symptoms are present
  const isVisual = forceShow || hasVisualSymptoms(symptoms);

  // Manage in-memory preview URL lifecycle
  useEffect(() => {
    if (!currentFile) {
      setPreviewUrl(null);
      return;
    }

    const objectUrl = URL.createObjectURL(currentFile);
    setPreviewUrl(objectUrl);

    return () => {
      URL.revokeObjectURL(objectUrl);
    };
  }, [currentFile]);

  // Clean up on component unmount
  useEffect(() => {
    return () => {
      if (previewUrl) {
        URL.revokeObjectURL(previewUrl);
      }
    };
  }, [previewUrl]);

  // If no visual symptoms are detected and not forced, situational upload is not offered (idea §3)
  if (!isVisual) {
    return null;
  }

  /**
   * Validates and sets an incoming File candidate.
   *
   * @param file Candidate file selected by the user.
   */
  const processSelectedFile = (file: File) => {
    // Validate MIME type
    if (!ALLOWED_IMAGE_TYPES.includes(file.type)) {
      const err = "Unsupported image format. Please select a JPEG, PNG, or WebP photo.";
      setErrorMessage(err);
      onError?.(err);
      return;
    }

    // Validate size limit (5 MB)
    if (file.size > MAX_IMAGE_SIZE_BYTES) {
      const err = `Image file exceeds the 5 MB limit (${formatFileSize(file.size)}). Please select a smaller photo.`;
      setErrorMessage(err);
      onError?.(err);
      return;
    }

    // Clear previous error
    setErrorMessage(null);
    onError?.(null);

    setInternalFile(file);
    onImageSelect(file);
  };

  const handleInputChange = (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (file) {
      processSelectedFile(file);
    }
    // Reset input value so the same file can be selected again if removed
    event.target.value = "";
  };

  const handleRemovePhoto = () => {
    setInternalFile(null);
    setErrorMessage(null);
    onError?.(null);
    onImageSelect(null);

    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
    if (cameraInputRef.current) {
      cameraInputRef.current.value = "";
    }
  };

  const triggerCameraInput = () => {
    if (!disabled && cameraInputRef.current) {
      cameraInputRef.current.click();
    }
  };

  const triggerFileInput = () => {
    if (!disabled && fileInputRef.current) {
      fileInputRef.current.click();
    }
  };

  return (
    <div
      role="region"
      aria-label="Visual symptom photo attachment"
      className={`rounded-xl border border-teal-200 bg-teal-50/60 p-4 transition ${className}`}
    >
      {/* Situational prompt banner */}
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-start gap-2.5">
          <span className="text-xl" aria-hidden="true">
            📷
          </span>
          <div>
            <div className="flex items-center gap-2">
              <h3 className="text-sm font-semibold text-teal-900">
                Visual Symptom Detected
              </h3>
              <span className="rounded-full bg-teal-200/70 px-2 py-0.5 text-[11px] font-medium text-teal-800">
                Optional
              </span>
            </div>
            <p className="mt-1 text-xs text-teal-800/90 leading-relaxed">
              Since your symptoms include a visible skin condition or rash, you may attach a
              photo to assist in triage.
            </p>
          </div>
        </div>
      </div>

      {/* Error alert */}
      {errorMessage && (
        <div
          role="alert"
          className="mt-3 flex items-start gap-2 rounded-lg border border-red-200 bg-red-50 p-2.5 text-xs text-red-800"
        >
          <span className="font-bold" aria-hidden="true">
            ⚠️
          </span>
          <span>{errorMessage}</span>
        </div>
      )}

      {/* Selected photo preview & actions */}
      {currentFile && previewUrl ? (
        <div className="mt-3 flex items-center justify-between rounded-lg border border-teal-200 bg-white p-3 shadow-xs">
          <div className="flex items-center gap-3 overflow-hidden">
            <img
              src={previewUrl}
              alt="Attached visual symptom preview"
              className="h-14 w-14 rounded-md object-cover border border-slate-200"
            />
            <div className="min-w-0">
              <p className="truncate text-xs font-semibold text-slate-800">
                {currentFile.name}
              </p>
              <p className="text-[11px] text-slate-500">
                {formatFileSize(currentFile.size)} · In-memory
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={handleRemovePhoto}
              disabled={disabled}
              aria-label="Remove attached photo"
              className="rounded-md border border-slate-300 bg-white px-2.5 py-1.5 text-xs font-medium text-red-700 hover:bg-red-50 focus:outline-none focus:ring-2 focus:ring-red-400 disabled:cursor-not-allowed disabled:opacity-50"
            >
              Remove
            </button>
          </div>
        </div>
      ) : (
        /* Action buttons for mobile camera & file upload */
        <div className="mt-3 flex flex-wrap items-center gap-2.5">
          {/* Mobile Camera Input (capture="environment") */}
          <input
            ref={cameraInputRef}
            type="file"
            accept="image/jpeg,image/png,image/webp"
            capture="environment"
            onChange={handleInputChange}
            disabled={disabled}
            className="hidden"
            aria-label="Take photo with camera"
            tabIndex={-1}
          />

          {/* File Picker Input */}
          <input
            ref={fileInputRef}
            type="file"
            accept="image/jpeg,image/png,image/webp"
            onChange={handleInputChange}
            disabled={disabled}
            className="hidden"
            aria-label="Choose photo from device"
            tabIndex={-1}
          />

          <button
            type="button"
            onClick={triggerCameraInput}
            disabled={disabled}
            className="flex items-center gap-1.5 rounded-lg bg-teal-700 px-3 py-2 text-xs font-semibold text-white transition hover:bg-teal-800 focus:outline-none focus:ring-2 focus:ring-teal-500 focus:ring-offset-1 disabled:cursor-not-allowed disabled:opacity-50"
          >
            <span aria-hidden="true">📸</span>
            <span>Take photo</span>
          </button>

          <button
            type="button"
            onClick={triggerFileInput}
            disabled={disabled}
            className="flex items-center gap-1.5 rounded-lg border border-teal-600 bg-white px-3 py-2 text-xs font-semibold text-teal-800 transition hover:bg-teal-50 focus:outline-none focus:ring-2 focus:ring-teal-500 focus:ring-offset-1 disabled:cursor-not-allowed disabled:opacity-50"
          >
            <span aria-hidden="true">📁</span>
            <span>Choose photo</span>
          </button>

          <span className="text-[11px] text-teal-700/80">
            JPG, PNG, WebP up to 5 MB
          </span>
        </div>
      )}

      {/* Mandatory medical safety and privacy notice (DR-06, AI_RULES.md §2.10) */}
      <div className="mt-3 border-t border-teal-200/80 pt-2 text-[11px] text-teal-900/80 leading-snug">
        <p>
          <strong className="font-semibold">Privacy notice: </strong>
          {IMAGE_PRIVACY_DISCLAIMER}
        </p>
      </div>
    </div>
  );
}
