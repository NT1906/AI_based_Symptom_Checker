/**
 * @file Symptom confirmation and editing card component.
 *
 * Provides a structured, accessible interface allowing users to review symptoms
 * extracted by the AI, edit severity and duration attributes, remove false-positive
 * detections, and add missing symptoms from a canonical selectable list before analysis.
 *
 * Owner: Mann (Frontend + Deployment · Testing) · Task: S1-MAN-1 · Requirements: FR-16, FR-21, FR-03, DR-01
 */

import React, { useState } from "react";
import { CANONICAL_SYMPTOMS } from "./canonicalSymptoms";
import type {
  ConfirmedSymptom,
  DurationUnitType,
  SeverityLevel,
  SymptomConfirmationCardProps,
} from "./types";

/** Mandatory medical disclaimer text required on informational screens (DR-01). */
export const CONFIRMATION_DISCLAIMER_TEXT =
  "This is not a medical diagnosis. Confirmation is used to organize informational suggestions only. Always consult a qualified healthcare professional.";

/**
 * Returns accessible styling classes for severity badges.
 *
 * @param severity - Clinical severity level.
 * @returns Tailwind CSS class string.
 */
function getSeverityBadgeClass(severity: SeverityLevel): string {
  switch (severity) {
    case "SEVERE":
      return "bg-rose-100 text-rose-800 border-rose-300 dark:bg-rose-950 dark:text-rose-200 dark:border-rose-800";
    case "MODERATE":
      return "bg-amber-100 text-amber-800 border-amber-300 dark:bg-amber-950 dark:text-amber-200 dark:border-amber-800";
    case "MILD":
      return "bg-emerald-100 text-emerald-800 border-emerald-300 dark:bg-emerald-950 dark:text-emerald-200 dark:border-emerald-800";
    default:
      return "bg-slate-100 text-slate-700 border-slate-300 dark:bg-slate-800 dark:text-slate-300 dark:border-slate-700";
  }
}

/**
 * Symptom confirmation card for verifying, editing, removing, and adding symptoms.
 *
 * @param props - Component configuration props.
 * @returns Rendered confirmation card.
 */
export function SymptomConfirmationCard({
  initialSymptoms,
  onConfirm,
  onCancel,
  isSubmitting = false,
}: SymptomConfirmationCardProps): React.ReactElement {
  const [symptoms, setSymptoms] = useState<ConfirmedSymptom[]>(initialSymptoms);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [isAddingSymptom, setIsAddingSymptom] = useState(false);
  const [notification, setNotification] = useState<string | null>(null);

  // Filter canonical symptoms based on live query excluding already selected
  const existingNames = new Set(symptoms.map((s) => s.name.toLowerCase()));
  const filteredSuggestions = searchQuery.trim()
    ? CANONICAL_SYMPTOMS.filter(
        (item) =>
          item.name.toLowerCase().includes(searchQuery.toLowerCase()) &&
          !existingNames.has(item.name.toLowerCase()),
      )
    : [];

  /**
   * Handles removing a symptom from the active confirmation list.
   *
   * @param id - Identifier of the symptom to delete.
   */
  const handleRemoveSymptom = (id: string) => {
    const target = symptoms.find((s) => s.id === id);
    setSymptoms((prev) => prev.filter((s) => s.id !== id));
    if (editingId === id) {
      setEditingId(null);
    }
    if (target) {
      setNotification(`Removed "${target.name}".`);
    }
  };

  /**
   * Handles updating attributes of a single symptom item.
   *
   * @param id - Target symptom identifier.
   * @param updates - Partial symptom properties to merge.
   */
  const handleUpdateSymptom = (id: string, updates: Partial<ConfirmedSymptom>) => {
    setSymptoms((prev) =>
      prev.map((s) => (s.id === id ? { ...s, ...updates, source: "USER_CORRECTED" } : s)),
    );
    setNotification("Symptom details updated.");
  };

  /**
   * Adds a symptom chosen from the selectable suggestions list.
   *
   * @param name - Display label of the added canonical symptom.
   */
  const handleAddSymptom = (name: string) => {
    const trimmed = name.trim();
    if (!trimmed) return;

    const newSymptom: ConfirmedSymptom = {
      id: `symptom-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`,
      name: trimmed,
      severity: "MODERATE",
      duration: { value: 1, unit: "DAY" },
      bodyLocation: null,
      source: "USER_CONFIRMED",
    };

    setSymptoms((prev) => [...prev, newSymptom]);
    setSearchQuery("");
    setIsAddingSymptom(false);
    setNotification(`Added "${trimmed}" to your symptom list.`);
  };

  /** Submits the verified symptoms to the parent orchestrator callback. */
  const handleConfirm = () => {
    onConfirm(symptoms);
  };

  return (
    <section
      aria-label="Symptom Confirmation"
      className="w-full max-w-2xl mx-auto bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl shadow-sm overflow-hidden"
    >
      {/* Header Banner */}
      <div className="bg-teal-50/80 dark:bg-teal-950/40 border-b border-teal-100 dark:border-teal-900/60 p-6">
        <h2 className="text-xl font-bold text-slate-900 dark:text-slate-100 flex items-center gap-2">
          <span aria-hidden="true">📋</span> Review & Confirm Symptoms
        </h2>
        <p className="text-sm text-slate-600 dark:text-slate-300 mt-1">
          Please verify what we understood from your description. You can adjust details, remove
          inaccurate items, or add symptoms below.
        </p>
      </div>

      {/* Screen Reader & Visual Notification Area */}
      {notification && (
        <div
          role="status"
          aria-live="polite"
          className="px-6 py-2.5 bg-teal-100/70 dark:bg-teal-900/40 text-teal-800 dark:text-teal-200 text-xs font-medium flex justify-between items-center"
        >
          <span>{notification}</span>
          <button
            type="button"
            onClick={() => setNotification(null)}
            className="text-teal-700 dark:text-teal-300 hover:text-teal-900 underline text-xs ml-3"
            aria-label="Dismiss notification"
          >
            Dismiss
          </button>
        </div>
      )}

      {/* Symptoms List Container */}
      <div className="p-6 space-y-4">
        <div className="flex items-center justify-between pb-2 border-b border-slate-100 dark:border-slate-800">
          <span className="text-xs font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400">
            Reported Symptoms ({symptoms.length})
          </span>
          {!isAddingSymptom && (
            <button
              type="button"
              onClick={() => setIsAddingSymptom(true)}
              className="text-xs font-semibold text-teal-700 dark:text-teal-400 hover:text-teal-800 dark:hover:text-teal-300 hover:underline flex items-center gap-1 focus:outline-none focus-visible:ring-2 focus-visible:ring-teal-600 rounded px-1 py-0.5"
            >
              <span aria-hidden="true">+</span> Add Symptom
            </button>
          )}
        </div>

        {symptoms.length === 0 ? (
          <div className="text-center py-8 text-slate-500 dark:text-slate-400">
            <p className="text-sm font-medium">No symptoms listed.</p>
            <p className="text-xs mt-1 text-slate-400 dark:text-slate-500">
              Please add at least one symptom below so we can assist with informational triage.
            </p>
          </div>
        ) : (
          <ul className="space-y-3" aria-label="Extracted symptom list">
            {symptoms.map((symptom, index) => {
              const isEditing = editingId === symptom.id;

              return (
                <li
                  key={symptom.id}
                  className="p-4 rounded-xl border border-slate-200 dark:border-slate-800 bg-slate-50/60 dark:bg-slate-800/40 transition-colors"
                >
                  {isEditing ? (
                    // Inline Edit Form
                    <div className="space-y-3">
                      <div className="flex items-center justify-between">
                        <span className="font-semibold text-slate-900 dark:text-slate-100 text-sm">
                          Editing: {symptom.name}
                        </span>
                        <button
                          type="button"
                          onClick={() => setEditingId(null)}
                          className="text-xs text-slate-500 hover:text-slate-700 dark:hover:text-slate-300 font-medium"
                        >
                          Done
                        </button>
                      </div>

                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
                        {/* Severity Dropdown */}
                        <div>
                          <label
                            htmlFor={`severity-${symptom.id}`}
                            className="block font-medium text-slate-700 dark:text-slate-300 mb-1"
                          >
                            Severity Level
                          </label>
                          <select
                            id={`severity-${symptom.id}`}
                            value={symptom.severity}
                            onChange={(e) =>
                              handleUpdateSymptom(symptom.id, {
                                severity: e.target.value as SeverityLevel,
                              })
                            }
                            className="w-full px-2.5 py-1.5 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 text-slate-900 dark:text-slate-100 focus:ring-2 focus:ring-teal-600 focus:outline-none"
                          >
                            <option value="MILD">Mild (noticeable, does not disrupt activities)</option>
                            <option value="MODERATE">Moderate (uncomfortable, somewhat disruptive)</option>
                            <option value="SEVERE">Severe (intense, prevents normal activities)</option>
                            <option value="UNKNOWN">Unsure / Unknown</option>
                          </select>
                        </div>

                        {/* Duration Inputs */}
                        <div>
                          <label
                            htmlFor={`duration-value-${symptom.id}`}
                            className="block font-medium text-slate-700 dark:text-slate-300 mb-1"
                          >
                            Duration Length
                          </label>
                          <div className="flex gap-2">
                            <input
                              id={`duration-value-${symptom.id}`}
                              aria-label="Duration length"
                              type="number"
                              min="0"
                              step="1"
                              value={symptom.duration?.value ?? ""}
                              placeholder="e.g. 2"
                              onChange={(e) => {
                                const val = parseFloat(e.target.value);
                                handleUpdateSymptom(symptom.id, {
                                  duration: {
                                    value: isNaN(val) ? 0 : val,
                                    unit: symptom.duration?.unit ?? "DAY",
                                  },
                                });
                              }}
                              className="w-20 px-2.5 py-1.5 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 text-slate-900 dark:text-slate-100 focus:ring-2 focus:ring-teal-600 focus:outline-none"
                            />
                            <select
                              id={`duration-unit-${symptom.id}`}
                              aria-label="Duration unit"
                              value={symptom.duration?.unit ?? "DAY"}
                              onChange={(e) =>
                                handleUpdateSymptom(symptom.id, {
                                  duration: {
                                    value: symptom.duration?.value ?? 1,
                                    unit: e.target.value as DurationUnitType,
                                  },
                                })
                              }
                              className="flex-1 px-2.5 py-1.5 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 text-slate-900 dark:text-slate-100 focus:ring-2 focus:ring-teal-600 focus:outline-none"
                            >
                              <option value="HOUR">Hours</option>
                              <option value="DAY">Days</option>
                              <option value="WEEK">Weeks</option>
                              <option value="MONTH">Months</option>
                            </select>
                          </div>
                        </div>

                        {/* Body Location */}
                        <div className="sm:col-span-2">
                          <label
                            htmlFor={`location-${symptom.id}`}
                            className="block font-medium text-slate-700 dark:text-slate-300 mb-1"
                          >
                            Body Location (Optional)
                          </label>
                          <input
                            id={`location-${symptom.id}`}
                            type="text"
                            value={symptom.bodyLocation ?? ""}
                            placeholder="e.g. temples, left knee, chest"
                            onChange={(e) =>
                              handleUpdateSymptom(symptom.id, {
                                bodyLocation: e.target.value.trim() ? e.target.value : null,
                              })
                            }
                            className="w-full px-2.5 py-1.5 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 text-slate-900 dark:text-slate-100 focus:ring-2 focus:ring-teal-600 focus:outline-none"
                          />
                        </div>
                      </div>
                    </div>
                  ) : (
                    // Display Row
                    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                      <div>
                        <div className="flex items-center gap-2 flex-wrap">
                          <span className="font-semibold text-slate-900 dark:text-slate-100 text-base">
                            {index + 1}. {symptom.name}
                          </span>
                          <span
                            className={`px-2 py-0.5 rounded-md text-xs font-semibold border ${getSeverityBadgeClass(
                              symptom.severity,
                            )}`}
                          >
                            {symptom.severity}
                          </span>
                        </div>

                        <div className="flex items-center gap-3 mt-1.5 text-xs text-slate-600 dark:text-slate-400">
                          {symptom.duration ? (
                            <span>
                              ⏳ Duration: {symptom.duration.value}{" "}
                              {symptom.duration.unit.toLowerCase()}
                              {symptom.duration.value !== 1 ? "s" : ""}
                            </span>
                          ) : (
                            <span>⏳ Duration: Not specified</span>
                          )}

                          {symptom.bodyLocation && (
                            <span>📍 Location: {symptom.bodyLocation}</span>
                          )}
                        </div>
                      </div>

                      <div className="flex items-center gap-2 self-end sm:self-center">
                        <button
                          type="button"
                          onClick={() => setEditingId(symptom.id)}
                          className="px-2.5 py-1 text-xs font-medium text-slate-700 dark:text-slate-200 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-700 focus:outline-none focus:ring-2 focus:ring-teal-600"
                          aria-label={`Edit ${symptom.name} details`}
                        >
                          ✏️ Edit
                        </button>
                        <button
                          type="button"
                          onClick={() => handleRemoveSymptom(symptom.id)}
                          className="px-2.5 py-1 text-xs font-medium text-rose-700 dark:text-rose-300 bg-rose-50 dark:bg-rose-950/40 border border-rose-200 dark:border-rose-900 rounded-lg hover:bg-rose-100 dark:hover:bg-rose-900 focus:outline-none focus:ring-2 focus:ring-rose-500"
                          aria-label={`Remove ${symptom.name}`}
                        >
                          🗑️ Remove
                        </button>
                      </div>
                    </div>
                  )}
                </li>
              );
            })}
          </ul>
        )}

        {/* Add Symptom Selectable Section */}
        {isAddingSymptom && (
          <div className="p-4 rounded-xl border border-teal-200 dark:border-teal-800/80 bg-teal-50/50 dark:bg-teal-950/30 space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-teal-900 dark:text-teal-200">
                Search & Add a Symptom (FR-03, FR-16)
              </span>
              <button
                type="button"
                onClick={() => {
                  setIsAddingSymptom(false);
                  setSearchQuery("");
                }}
                className="text-xs text-slate-500 hover:text-slate-700 dark:hover:text-slate-300"
              >
                Cancel
              </button>
            </div>

            <div className="flex gap-2">
              <input
                type="text"
                value={searchQuery}
                placeholder="Type a symptom e.g. nausea, cough, headache..."
                onChange={(e) => setSearchQuery(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && searchQuery.trim()) {
                    e.preventDefault();
                    handleAddSymptom(searchQuery);
                  }
                }}
                className="flex-1 px-3 py-2 text-sm rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 text-slate-900 dark:text-slate-100 focus:ring-2 focus:ring-teal-600 focus:outline-none"
                aria-label="Search or enter symptom name"
              />
              <button
                type="button"
                disabled={!searchQuery.trim()}
                onClick={() => handleAddSymptom(searchQuery)}
                className="px-4 py-2 bg-teal-700 hover:bg-teal-800 disabled:opacity-50 text-white rounded-lg text-xs font-semibold focus:outline-none focus:ring-2 focus:ring-teal-600"
              >
                Add
              </button>
            </div>

            {/* Suggestions list */}
            {filteredSuggestions.length > 0 && (
              <div
                className="max-h-40 overflow-y-auto space-y-1 pr-1"
                aria-label="Symptom suggestions"
              >
                <span className="text-[11px] font-medium text-slate-500 dark:text-slate-400 block mb-1">
                  Suggested matching symptoms:
                </span>
                {filteredSuggestions.map((item) => (
                  <button
                    key={item.id}
                    type="button"
                    onClick={() => handleAddSymptom(item.name)}
                    className="w-full text-left px-2.5 py-1.5 rounded text-xs bg-white dark:bg-slate-800 hover:bg-teal-50 dark:hover:bg-teal-900/40 border border-slate-200 dark:border-slate-700 text-slate-800 dark:text-slate-200 flex justify-between items-center transition-colors"
                  >
                    <span>{item.name}</span>
                    <span className="text-[10px] text-slate-400 uppercase tracking-wider">
                      {item.bodySystem}
                    </span>
                  </button>
                ))}
              </div>
            )}
          </div>
        )}
      </div>

      {/* Action Footer */}
      <div className="p-6 bg-slate-50/80 dark:bg-slate-950/60 border-t border-slate-200 dark:border-slate-800 flex flex-col sm:flex-row items-center justify-between gap-4">
        {onCancel ? (
          <button
            type="button"
            onClick={onCancel}
            disabled={isSubmitting}
            className="w-full sm:w-auto px-4 py-2.5 text-sm font-medium text-slate-700 dark:text-slate-300 hover:text-slate-900 dark:hover:text-slate-100 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-xl transition-colors focus:outline-none focus:ring-2 focus:ring-slate-400"
          >
            ← Back to Chat
          </button>
        ) : (
          <div />
        )}

        <button
          type="button"
          onClick={handleConfirm}
          disabled={symptoms.length === 0 || isSubmitting}
          className="w-full sm:w-auto px-6 py-2.5 bg-teal-700 hover:bg-teal-800 disabled:opacity-50 disabled:cursor-not-allowed text-white font-semibold text-sm rounded-xl shadow-sm transition-colors focus:outline-none focus:ring-2 focus:ring-teal-600 focus:ring-offset-2 flex items-center justify-center gap-2"
        >
          {isSubmitting ? (
            <>
              <span
                className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"
                aria-hidden="true"
              />
              Analyzing...
            </>
          ) : (
            <>Confirm & Analyze Symptoms ➤</>
          )}
        </button>
      </div>

      {/* Mandatory Medical Disclaimer (DR-01) */}
      <footer className="px-6 py-3 bg-slate-100 dark:bg-slate-900 border-t border-slate-200 dark:border-slate-800 text-[11px] leading-relaxed text-slate-500 dark:text-slate-400 text-center">
        {CONFIRMATION_DISCLAIMER_TEXT}
      </footer>
    </section>
  );
}
