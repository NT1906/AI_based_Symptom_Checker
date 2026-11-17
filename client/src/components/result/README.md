# Result Components (`client/src/components/result/`)

**Owner:** Mann (Frontend + Deployment · Testing)  
**Sprint 1 Tasks:** S1-MAN-2 (Issue #60), S1-MAN-3 (Issue #61)  
**Sprint 2 Task:** S2-MAN-2 (Issue #185)  
**Requirements:** FR-06, FR-15, FR-22, FR-23, DR-01, DR-02, NFR-06, FR-08, idea §9

---

## Purpose

Provides components for presenting ranked candidate conditions, deterministic clinical triage risk tiers, and external doctor referrals:
* Ranks potential conditions based on reported symptoms (FR-22).
* Displays **qualitative confidence labels only** (`Likely`, `Possible`, `Less likely`) — **never raw percentages or scores** (FR-23, AI_RULES §2.3).
* Presents deterministic risk level (`SELF_CARE`, `CONSULT_DOCTOR`, `URGENT`) via accessible `RiskBadge` with text and icon (NFR-06).
* Accompanies each condition with a plain-language "why" rationale and recommended clinical specialty (FR-24).
* Provides outward doctor referral via external map search (`DoctorReferral`), strictly adhering to module boundaries: **no doctor data, profiles, ratings, or booking stored** (FR-08, idea §9).
* Frames all output as non-diagnostic informational guidance (DR-01).

---

## Public Interface

* **`DoctorReferral`**: Specialist referral component linking to external map searches (FR-08, idea §9).
  * `referral?: ReferralInfo | null`: Structured referral data with specialty, secondary specialties, and query.
  * `specialty?: string | null`: Direct specialty name override.
  * `secondarySpecialties?: string[]`: Related specialties for secondary map queries.
  * `mapQuery?: string | null`: Custom map query override.
  * `provider?: MapProvider`: Map search destination (`"google"` | `"osm"` | `"apple"`).
  * `location?: string | null`: Optional geographical hint.
  * `title?: string`: Custom section header.
  * `onReferralClick?: (specialty: string, url: string) => void`: Optional click tracking callback.
* **`buildMapSearchUrl(specialty, options)`**: URL generator with encoding and query construction.
* **`DOCTOR_REFERRAL_DATA_NOTICE`**: Mandatory non-retention notice for external doctor searches.
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
npm test src/components/result/DoctorReferral.test.tsx
npm test src/components/result/
```
