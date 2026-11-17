# Retention and deletion verification

Owner: Harsh · Task: S2-HAR-6 · Issue: #209 · Requirements: NFR-04, DR-06

Reviewed on 17 November 2026 against `develop` revision `e25e37c`.
This is a source inventory and staging test plan. Staging results are pending.
Do not close #209 or represent this report as compliance certification.

## Current implementation

- Export is registered through `create_privacy_router(get_account_export)`.
  It scopes data to the authenticated account and sets `Cache-Control: no-store`.
- The optional delete route is not registered by the production router.
  `DataRightsRepository.delete_user_data` is a protocol, with no concrete
  implementation in the reviewed repositories. A merged #173 does not prove
  end-to-end erasure.
- #163 is still open. The reviewed repositories contain no production TTL
  purge callback. #175's separately prepared scheduler runner uses injected
  callbacks and has not been deployed. Expiry timestamps alone do not erase rows.
- Audit storage and profiles are now real models, not proposed features.
  Migration head in this source tree is `0006_audit_log`; the staging database
  migration revision has not been observed.

## Source data inventory

Every table also has UUID `id` and `created_at`. This lists all eight tables
registered in `app.models.Base.metadata` at the reviewed revision.

| Store | Stored fields beyond id and created_at | Purpose | Retention and deletion evidence |
| --- | --- | --- | --- |
| `users` | email, password_hash | Account authentication | Account lifetime/request scope needs owner approval. No live erasure evidence. Password hash excluded from export. |
| `profiles` | user_id, age_band, biological_sex, chronic_conditions, updated_at | Optional assessment context | User FK is CASCADE. Full account erasure remains unimplemented. Profile fields are exported. |
| `guest_sessions` | token_hash, expires_at, claimed_at, claimed_by_user_id | Anonymous ownership and claim tracking | Default TTL described as 24 h. Real expiry cleanup pending #163/#175. Token hash is excluded from export. |
| `assessments` | user_id, guest_session_id, consent_id, state | Assessment ownership and workflow | Account data on request, unclaimed guest data at expiry are project targets. User/consent FKs are RESTRICT. Guest FK is SET NULL, so deleting a guest alone leaves assessments. |
| `messages` | assessment_id, position, role, content | Conversation context | Raw user text can contain personal data. Assessment FK is RESTRICT. Delete children before assessments. Export is owner-scoped. |
| `symptoms` | assessment_id, name, details JSON | Structured symptom information | Assessment FK is RESTRICT. Remove with applicable assessment; JSON may contain health data. |
| `consents` | policy_version | Evidence of accepted policy | Assessments link the consent. Retention period and deletion/de-linking decision require privacy-owner sign-off. |
| `audit_logs` | user_id, guest_session_id, assessment_id, action, risk_level, risk_engine_version, condition_model_version, cv_model_version, ai_model, details JSON | Operational/reproducibility trail | All three owner FKs use SET NULL. Audit rows survive parent deletion. Agree duration, access and residual-data handling. |

Additional locations need deployment-owner confirmation.

| Location | Source finding | Evidence still needed |
| --- | --- | --- |
| Auth cookies/JWT | Browser cookies and signed tokens. Refresh revocations are held in an in-process set in `auth/service.py`. | Erasure must invalidate relevant sessions/tokens across all workers and restarts. Never capture tokens as evidence. |
| Images | Project design requires memory-only processing. | Check temporary files, proxy buffering and telemetry on the deployed upload path. |
| Assessment results and caches | Results are composed by services. No separate result table is registered. | Check worker memory, API/proxy caches and any deployed storage beyond these models. |
| Application and platform logs | #210 changes omit personal logging fields. | Capture sink configuration, access controls, redacted samples and retention. |
| External AI processors | Configurable AI provider receives gateway inputs. | Confirm deployed provider, terms, data regions, retention and training settings. Scrubbing is not guaranteed anonymisation. |
| Database backups | Outside ORM/source inventory. | Record retention window, permissions, restore procedure and handling of erased data after a restore. |
| Browser/PWA storage | Policy prohibits caching health API data or storing health data in browser persistence. | Inspect actual Cache API, localStorage and IndexedDB using fictional data. |

Audit review finding for Nishith: the repository rejects a list of top-level
JSON keys. It does not recursively validate arbitrary `details` values or
free-text `action`/version fields. This is not evidence that all audit payloads
are free of personal data. Review an allowlist and caller payloads before
retention sign-off. Database-owner files were not changed in this task.

## DPDP engineering control assessment

The following is an implementation review, not a claim of legal compliance.
The Gazette notification phases commencement. The cited notice, consent,
safeguards and individual-rights provisions are in its eighteen-month group.
Recheck current applicability and any additional obligations before release.

| Reference | Project evidence | Open work |
| --- | --- | --- |
| Act section 5, notice | Consent/privacy UI and policy-version records exist. | Verify deployed notice, purposes, contact details and supported languages. |
| Act section 6, consent/withdrawal | Consent versioning is merged. | Verify withdrawal and downstream processing cessation. |
| Act section 8(5), safeguards | Security and logging controls exist. | #208 staging verification, audit-payload review and operational access review. |
| Act section 8(7), erasure | Expiry metadata and data-rights service boundary exist. | Real purge, account deletion, processor/backup handling and retention decisions. |
| Act section 11, access information | Authenticated JSON export is merged. | Verify deployed response and required information about processing/recipients. Export alone is not a full rights process. |
| Act section 12, correction/erasure | Profile update support and optional delete route exist. | Wire actual erasure, confirm correction scope and test the deployed request flow. |
| Act sections 13/14, grievance/nomination | Not verified by this review. | Record contact, handling process, applicable scope and owner. |

Official sources checked on 17 November 2026

- [DPDP Act, 2023, India Code](https://www.indiacode.nic.in/bitstream/123456789/22037/1/a2023-22.pdf)
- [G.S.R. 843(E), phased commencement](https://www.meity.gov.in/static/uploads/2025/11/c56ceae6c383460ca69577428d36828b.pdf)
- [MeitY DPDP Rules, 2025 publication page](https://www.meity.gov.in/documents/act-and-policies/digital-personal-data-protection-rules-2025-gDOxUjMtQWa)

## Staging verification procedure

Use a dedicated synthetic fixture namespace and approved staging database.
Record environment, deployed SHA, migration head, run time, tester and owners.
Never put real account identifiers, health text, cookies, tokens or database
credentials in the report.

| Case | Action | Required observation | Result |
| --- | --- | --- | --- |
| Export ownership | Export fictional account A with data belonging to A and B. | Only A's permitted data; no credentials/token material; no-store header. | Pending |
| Unauthenticated rights | Request export/delete with no valid account session. | Authentication rejects access; no row changes. | Pending |
| Delete CSRF | Attempt authenticated deletion with missing/invalid CSRF, after real route wiring. | Rejected; all fixture rows unchanged. | Pending |
| Account deletion | Delete A through real route, then inspect tables. | Approved A data removed atomically; B unchanged; session invalidation verified. | Pending |
| Delete retry | Repeat the approved request. | Defined safe behaviour without extra deletion or information disclosure. | Pending |
| Expired guest | Expire synthetic unclaimed G1; run the actual scheduled callback. | G1 children/assessment/session removed; fresh G2 and claimed G3 history retained. | Pending |
| Claim race | Run claim and purge concurrently under DB-owner supervision. | No claimed/registered data loss; consistent winner and rollback. | Pending |
| Failure/retry | Inject an approved database failure before commit, then retry. | No partial deletion, failed scheduler exit, successful safe retry and alert. | Pending |
| Scheduled execution | Observe an actual scheduled run and a failure. | Singleton scheduling, deployed revision, aggregate counts and alert evidence. | Pending |
| Residual stores | Inspect audit, consent, logs, provider settings, browser caches and backup policy. | Approved retention matrix and access controls, with explicit exceptions. | Pending |

The schedule interval adds to effective retention. A 24 h TTL plus a 15 minute
schedule is not a guarantee of deletion within exactly 24 h. Record measured
maximum delay and outage handling, then reconcile the user-facing policy.

## Release decision

#209 remains open until the pending cases have real observations and owners
approve consent/audit/backup retention and the data-rights request process.
The inventory is complete for the reviewed source revision. Deployed stores,
external settings and operational policies are not yet verified.
