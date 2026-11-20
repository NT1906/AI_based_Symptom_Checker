/**
 * @file Symptom confirmation and editing card component.
 *
 * Provides a structured, accessible interface allowing users to review symptoms
 * extracted by the AI, edit severity and duration attributes, remove false-positive
 * detections, and add missing symptoms from a canonical selectable list before analysis.
 *
 * Owner: Mann (Frontend + Deployment · Testing) · Task: S1-MAN-1 · Requirements: FR-16, FR-21, FR-03, DR-01
 * Restyle (design tokens, lucide icons, dark mode): Nisarg · S2-NIS-22 (#323)
 */

import { ArrowLeft, ArrowRight, ClipboardList, Clock, MapPin, Pencil, Trash2 } from "lucide-react";
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
      return "bg-danger/15 text-danger-strong border-danger/40";
    case "MODERATE":
      return "bg-warning/15 text-warning-strong border-warning/40";
    case "MILD":
      return "bg-success/15 text-success-strong border-success/40";
    default:
      return "bg-muted text-muted-foreground border-input";
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
      // Why: the user has not said how bad or how long yet; made-up values
      // would reach the risk engine as facts. They can set both in the card.
      severity: "UNKNOWN",
      duration: null,
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
      className="w-full max-w-2xl mx-auto bg-card border border-border rounded-xl shadow-sm overflow-hidden"
    >
      {/* Header Banner */}
      <div className="bg-primary/5 border-b border-primary/25 p-6">
        <h2 className="text-xl font-bold text-foreground flex items-center gap-2">
          <ClipboardList className="size-4 shrink-0" aria-hidden="true" /> Review & Confirm Symptoms
        </h2>
        <p className="text-sm text-muted-foreground mt-1">
          Please verify what we understood from your description. You can adjust details, remove
          inaccurate items, or add symptoms below.
        </p>
      </div>

      {/* Screen Reader & Visual Notification Area */}
      {notification && (
        <div
          role="status"
          aria-live="polite"
          className="px-6 py-2.5 bg-primary/15 text-primary-strong text-xs font-medium flex justify-between items-center"
        >
          <span>{notification}</span>
          <button
            type="button"
            onClick={() => setNotification(null)}
            className="text-primary hover:text-primary-strong underline text-xs ml-3"
            aria-label="Dismiss notification"
          >
            Dismiss
          </button>
        </div>
      )}

      {/* Symptoms List Container */}
      <div className="p-6 space-y-4">
        <div className="flex items-center justify-between pb-2 border-b border-border">
          <span className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
            Reported Symptoms ({symptoms.length})
          </span>
          {!isAddingSymptom && (
            <button
              type="button"
              onClick={() => setIsAddingSymptom(true)}
              className="text-xs font-semibold text-primary hover:text-primary-strong hover:underline flex items-center gap-1 focus:outline-none focus-visible:ring-2 focus-visible:ring-ring rounded px-1 py-0.5"
            >
              <span aria-hidden="true">+</span> Add Symptom
            </button>
          )}
        </div>

        {symptoms.length === 0 ? (
          <div className="text-center py-8 text-muted-foreground">
            <p className="text-sm font-medium">No symptoms listed.</p>
            <p className="text-xs mt-1 text-muted-foreground">
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
                  className="p-4 rounded-xl border border-border bg-muted/60 transition-colors"
                >
                  {isEditing ? (
                    // Inline Edit Form
                    <div className="space-y-3">
                      <div className="flex items-center justify-between">
                        <span className="font-semibold text-foreground text-sm">
                          Editing: {symptom.name}
                        </span>
                        <button
                          type="button"
                          onClick={() => setEditingId(null)}
                          className="text-xs text-muted-foreground hover:text-muted-foreground font-medium"
                        >
                          Done
                        </button>
                      </div>

                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
                        {/* Severity Dropdown */}
                        <div>
                          <label
                            htmlFor={`severity-${symptom.id}`}
                            className="block font-medium text-muted-foreground mb-1"
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
                            className="w-full px-2.5 py-1.5 rounded-lg border border-input bg-card text-foreground focus:ring-2 focus:ring-ring focus:outline-none"
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
                            className="block font-medium text-muted-foreground mb-1"
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
                              className="w-20 px-2.5 py-1.5 rounded-lg border border-input bg-card text-foreground focus:ring-2 focus:ring-ring focus:outline-none"
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
                              className="flex-1 px-2.5 py-1.5 rounded-lg border border-input bg-card text-foreground focus:ring-2 focus:ring-ring focus:outline-none"
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
                            className="block font-medium text-muted-foreground mb-1"
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
                            className="w-full px-2.5 py-1.5 rounded-lg border border-input bg-card text-foreground focus:ring-2 focus:ring-ring focus:outline-none"
                          />
                        </div>
                      </div>
                    </div>
                  ) : (
                    // Display Row
                    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                      <div>
                        <div className="flex items-center gap-2 flex-wrap">
                          <span className="font-semibold text-foreground text-base">
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

                        <div className="flex items-center gap-3 mt-1.5 text-xs text-muted-foreground">
                          {symptom.duration ? (
                            <span>
                              <Clock className="inline size-3.5 align-[-2px]" aria-hidden="true" /> Duration: {symptom.duration.value}{" "}
                              {symptom.duration.unit.toLowerCase()}
                              {symptom.duration.value !== 1 ? "s" : ""}
                            </span>
                          ) : (
                            <span><Clock className="inline size-3.5 align-[-2px]" aria-hidden="true" /> Duration: Not specified</span>
                          )}

                          {symptom.bodyLocation && (
                            <span><MapPin className="inline size-3.5 align-[-2px]" aria-hidden="true" /> Location: {symptom.bodyLocation}</span>
                          )}
                        </div>
                      </div>

                      <div className="flex items-center gap-2 self-end sm:self-center">
                        <button
                          type="button"
                          onClick={() => setEditingId(symptom.id)}
                          className="px-2.5 py-1 text-xs font-medium text-muted-foreground bg-card border border-border rounded-lg hover:bg-muted focus:outline-none focus:ring-2 focus:ring-ring"
                          aria-label={`Edit ${symptom.name} details`}
                        >
                          <Pencil className="inline size-4 align-[-3px]" aria-hidden="true" /> Edit
                        </button>
                        <button
                          type="button"
                          onClick={() => handleRemoveSymptom(symptom.id)}
                          className="px-2.5 py-1 text-xs font-medium text-danger-strong bg-danger/10 border border-danger/25 rounded-lg hover:bg-danger/15 focus:outline-none focus:ring-2 focus:ring-danger/40"
                          aria-label={`Remove ${symptom.name}`}
                        >
                          <Trash2 className="inline size-4 align-[-3px]" aria-hidden="true" /> Remove
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
          <div className="p-4 rounded-xl border border-primary/25 bg-primary/5 space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-primary-strong">
                Search & Add a Symptom (FR-03, FR-16)
              </span>
              <button
                type="button"
                onClick={() => {
                  setIsAddingSymptom(false);
                  setSearchQuery("");
                }}
                className="text-xs text-muted-foreground hover:text-muted-foreground"
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
                className="flex-1 px-3 py-2 text-sm rounded-lg border border-input bg-card text-foreground focus:ring-2 focus:ring-ring focus:outline-none"
                aria-label="Search or enter symptom name"
              />
              <button
                type="button"
                disabled={!searchQuery.trim()}
                onClick={() => handleAddSymptom(searchQuery)}
                className="px-4 py-2 bg-primary hover:bg-primary/90 disabled:opacity-50 text-primary-foreground rounded-lg text-xs font-semibold focus:outline-none focus:ring-2 focus:ring-ring"
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
                <span className="text-[11px] font-medium text-muted-foreground block mb-1">
                  Suggested matching symptoms:
                </span>
                {filteredSuggestions.map((item) => (
                  <button
                    key={item.id}
                    type="button"
                    onClick={() => handleAddSymptom(item.name)}
                    className="w-full text-left px-2.5 py-1.5 rounded text-xs bg-card hover:bg-primary/10 border border-border text-foreground flex justify-between items-center transition-colors"
                  >
                    <span>{item.name}</span>
                    <span className="text-[10px] text-muted-foreground uppercase tracking-wider">
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
      <div className="p-6 bg-muted/60 border-t border-border flex flex-col sm:flex-row items-center justify-between gap-4">
        {onCancel ? (
          <button
            type="button"
            onClick={onCancel}
            disabled={isSubmitting}
            className="w-full sm:w-auto px-4 py-2.5 text-sm font-medium text-muted-foreground hover:text-foreground hover:bg-muted rounded-xl transition-colors focus:outline-none focus:ring-2 focus:ring-ring"
          >
            <ArrowLeft className="inline size-3.5 align-[-2px]" aria-hidden="true" /> Back to Chat
          </button>
        ) : (
          <div />
        )}

        <button
          type="button"
          onClick={handleConfirm}
          disabled={symptoms.length === 0 || isSubmitting}
          className="w-full sm:w-auto px-6 py-2.5 bg-primary hover:bg-primary/90 disabled:opacity-50 disabled:cursor-not-allowed text-primary-foreground font-semibold text-sm rounded-xl shadow-sm transition-colors focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2 flex items-center justify-center gap-2"
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
            <>Confirm & Analyze Symptoms <ArrowRight className="size-4" aria-hidden="true" /></>
          )}
        </button>
      </div>

      {/* Mandatory Medical Disclaimer (DR-01) */}
      <footer className="px-6 py-3 bg-muted border-t border-border text-[11px] leading-relaxed text-muted-foreground text-center">
        {CONFIRMATION_DISCLAIMER_TEXT}
      </footer>
    </section>
  );
}
