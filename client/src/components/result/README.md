# Result Components (`client/src/components/result/`)

**Owner:** Mann (Frontend + Deployment · Testing)  
**Sprint 1 Tasks:** S1-MAN-2 (Issue #60), S1-MAN-3 (Issue #61)  
**Sprint 2 Task:** S2-MAN-3 (Issue #186)  
**Requirements:** FR-06, FR-15, FR-22, FR-23, DR-01, DR-02, NFR-06, FR-24

---

## Purpose

Provides components for presenting ranked candidate conditions, deterministic clinical triage risk tiers, and contributing factor explanations:
* Ranks potential conditions based on reported symptoms (FR-22).
* Displays **qualitative confidence labels only** (`Likely`, `Possible`, `Less likely`) — **never raw percentages or scores** (FR-23, AI_RULES §2.3).
* Presents deterministic risk level (`SELF_CARE`, `CONSULT_DOCTOR`, `URGENT`) via accessible `RiskBadge` with text and icon (NFR-06).
* Accompanies each condition with a plain-language "why" rationale and recommended clinical specialty (FR-24).
* Features an expandable `WhyThisResultPanel` detailing contributing factors and symptom patterns (FR-24).
* Frames all output as non-diagnostic informational guidance (DR-01).

---

## Public Interface

* **`WhyThisResultPanel`**: Contributing-factor explanation panel detailing symptom patterns (FR-24).
* **`ConditionList`**: Main presentation component for candidate conditions.
  * `conditions: ConditionItem[]`: Ranked array of candidate conditions.
  * `onSelectCondition?: (condition: ConditionItem) => void`: Optional callback on selection.
  * `emptyMessage?: string`: Fallback text when no conditions are present.
  * `title?: string`: Custom section title.
* **`RiskBadge`**: Visual status badge for clinical triage risk tier.
  * `level: RiskLevel`: Deterministic tier (`SELF_CARE`, `CONSULT_DOCTOR`, `URGENT`).
  * `className?: string`: Optional custom styling.
* **`getConfidenceLabel(confidence: ConfidenceTier): string`**: Qualitative label helper.
* **`getConfidenceBadgeClass(confidence: ConfidenceTier): string`**: Badge style helper.
* **`getRiskConfig(level: RiskLevel): RiskConfig`**: Triage config helper with label, icon, and styling.

---

## How to Test

Run the Vitest component tests:

```bash
cd client
npm test src/components/result/WhyThisResultPanel.test.tsx
npm test src/components/result/
```
