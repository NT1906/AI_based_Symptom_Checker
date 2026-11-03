# Result Components (`client/src/components/result/`)

**Owner:** Mann (Frontend + Deployment · Testing)  
**Sprint 1 Task:** S1-MAN-2 (Issue #60)  
**Requirements:** FR-22, FR-23, DR-01

---

## Purpose

Provides components for presenting ranked candidate conditions identified by the triage model. Ensures strict medical-safety compliance (AI_RULES.md §2):
* Ranks potential conditions based on reported symptoms.
* Displays **qualitative confidence labels only** (`Likely`, `Possible`, `Less likely`).
* **Never exposes raw percentages, statistics, or scores** to users.
* Accompanies each condition with a plain-language "why" rationale and recommended clinical specialty.
* Frames all output as non-diagnostic informational guidance.

---

## Public Interface

* **`ConditionList`**: Main presentation component for candidate conditions.
  * `conditions: ConditionItem[]`: Ranked array of candidate conditions.
  * `onSelectCondition?: (condition: ConditionItem) => void`: Optional callback on selection.
  * `emptyMessage?: string`: Fallback text when no conditions are present.
  * `title?: string`: Custom section title.
* **`getConfidenceLabel(confidence: ConfidenceTier): string`**: Helper returning qualitative label.
* **`getConfidenceBadgeClass(confidence: ConfidenceTier): string`**: Helper returning badge styling.

---

## How to Test

Run the Vitest component tests:

```bash
cd client
npm test src/components/result/ConditionList.test.tsx
```

