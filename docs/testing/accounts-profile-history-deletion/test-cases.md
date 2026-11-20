# Accounts, Profile, History and Deletion API – Test Cases and Evidence (Automated)

> **Task:** S2-KAV-8 (Accounts, profile, history and deletion API tests: automated, with evidence)  
> **Author:** Kavya Nakrani (`202401125@dau.ac.in` / `@KAVY-OP`)  
> **Issue:** [#334 – Accounts, profile, history and deletion API tests (automated, with evidence)](https://github.com/NT1906/AI_based_Symptom_Checker/issues/334)  
> **Branch:** `kavya/334-accounts-profile-history-tests`  
> **Requirements covered:** FR-01, FR-02, NFR-03, NFR-04, DR-02, DR-06, idea § 10  

---

## Metrics Summary

| Metric | Value |
|---|---|
| **Total test cases (TC)** | 18 (Automated Integration / API Suite) |
| **Passed** | 18 |
| **Failed** | 0 |
| **Blocked / not run** | 0 |
| **Pass rate (%)** | 100 % |
| **Acceptance criteria (AC) met** | 6 / 6 (100 %) |
| **Requirements covered** | FR-01, FR-02, NFR-03, NFR-04, DR-02, DR-06, idea § 10 |
| **Defects found** | 0 (None) |
| **Execution time** | 22.71 s (Pytest integration suite, dual-loop asyncio & trio) |
| **Environment** | Windows 11 (win32), Python 3.13.15, Pytest 9.1.1, commit `develop` + S2-KAV-8, 2026-11-20, Tester: Kavya Nakrani (@KAVY-OP) |

---

## Automated Test Cases (S2-KAV-8 · TC-ACC-A)

| TC ID | Requirement | Scenario | Technique | Preconditions | Steps | Test data | Expected result | Actual result | Status | Evidence |
|---|---|---|---|---|---|---|---|---|---|---|
| TC-ACC-A-01 | FR-01, NFR-03 | User Registration with Argon2id & Conflict Rejection | Equivalence Partitioning & Boundary Testing | Fresh database session | 1. POST `/api/v1/auth/register` with new email and valid password<br>2. Verify 201 Created and response attributes<br>3. Submit duplicate email<br>4. Submit blank password | Email: `fresh_patient@example.com`, Password: `ValidPassword123!` | HTTP 201 Created on first attempt; HTTP 409 Conflict with code `CONFLICT` on duplicate; HTTP 422 on blank password | HTTP 201 Created with sanitized UserRead; duplicate rejected with 409; blank password rejected with 422 | Pass | [TC-ACC-A-01.png](screenshots/TC-ACC-A-01.png) |
| TC-ACC-A-02 | FR-01, NFR-03 | User Login Issuing HttpOnly Cookies & CSRF Protection | Authentication & Session Verification | User registered in database | 1. POST `/api/v1/auth/login` with valid credentials<br>2. Inspect Set-Cookie headers<br>3. Verify `X-CSRF-Token` header<br>4. Attempt login with wrong password and nonexistent email | Credentials: `patient_alpha@example.com` / `PasswordAlpha123!` | HTTP 200 OK; sets `access_token` and `refresh_token` HttpOnly cookies; issues `csrf_token`; 401 on bad credentials | HTTP 200 OK; cookies set; CSRF token issued; HTTP 401 returned on invalid login | Pass | [TC-ACC-A-02.png](screenshots/TC-ACC-A-02.png) |
| TC-ACC-A-03 | FR-01, NFR-03 | Token Refresh Rotating Access & Refresh Tokens | Token Rotation & Session Lifecycle | User authenticated with active refresh cookie | 1. Log in to establish session with refresh cookie<br>2. POST `/api/v1/auth/refresh`<br>3. Verify rotated cookies issued<br>4. Submit refresh with omitted cookie | Valid refresh JWT with unique `jti` | HTTP 200 OK; rotates refresh token and issues fresh access token; HTTP 401 when cookie omitted | HTTP 200 OK; tokens rotated; unauthenticated refresh returns HTTP 401 | Pass | [TC-ACC-A-03.png](screenshots/TC-ACC-A-03.png) |
| TC-ACC-A-04 | FR-01, NFR-03 | Current User Profile (`/auth/me`) Session Verification | Session Authorization Testing | User authenticated via session cookie | 1. GET `/api/v1/auth/me` with access token cookie<br>2. Verify returned UserRead payload<br>3. Submit request without cookies | Valid user access token cookie | HTTP 200 OK returning sanitized user account; HTTP 401 Unauthorized when unauthenticated | HTTP 200 OK with accurate user id and email; HTTP 401 returned when cookies cleared | Pass | [TC-ACC-A-04.png](screenshots/TC-ACC-A-04.png) |
| TC-ACC-A-05 | FR-01, NFR-03 | Authenticated Password Change Lifecycle | State Transition & CSRF Defense | User authenticated with session and CSRF token | 1. Submit wrong current password -> verify 422<br>2. Omit CSRF header -> verify 401<br>3. Submit valid current and new password with CSRF<br>4. Verify old password fails (401)<br>5. Verify new password succeeds (200) | `CurrentPassword123!` -> `NewStrongPassword456!` | HTTP 204 No Content; old password invalidated immediately; new password functional | HTTP 204 returned; credentials rotated; login with new credentials succeeds cleanly | Pass | [TC-ACC-A-05.png](screenshots/TC-ACC-A-05.png) |
| TC-ACC-A-06 | FR-01, NFR-03 | User Logout Clearing Cookies & Revoking Tokens | Session Invalidation Testing | Active authenticated session | 1. Log in to obtain active session cookies<br>2. POST `/api/v1/auth/logout`<br>3. Inspect response and cookie deletion headers | Active session cookies | HTTP 200 OK; access, refresh, and CSRF cookies cleared with `max_age=0`; refresh token revoked | HTTP 200 OK returned; body `{"status": "ok"}`; session cookies cleared | Pass | [TC-ACC-A-06.png](screenshots/TC-ACC-A-06.png) |
| TC-ACC-A-07 | FR-02, idea § 10 | Profile Retrieval Default Empty State & No-Store Header | State Verification & Privacy Headers | Registered user with no saved profile | 1. Authenticate as user with no profile record<br>2. GET `/api/v1/profile`<br>3. Inspect payload and Cache-Control header<br>4. Send unauthenticated request | Empty profile state | HTTP 200 OK with `userId`, `ageBand=None`, `conditions=[]`; `Cache-Control: no-store`; 401 on unauth | HTTP 200 OK with default empty structure; no-store verified; HTTP 401 returned without credentials | Pass | [TC-ACC-A-07.png](screenshots/TC-ACC-A-07.png) |
| TC-ACC-A-08 | FR-02, idea § 10, NFR-03 | Profile Creation/Replacement & Condition Deduplication | Input Sanitization & Data Normalization | Authenticated user session | 1. PUT `/api/v1/profile` with age band, sex, and duplicate condition strings<br>2. Inspect saved response attributes<br>3. Verify condition deduplication and whitespace trimming | `ageBand: adult`, `biologicalSex: female`, `conditions: ["Asthma", "  Asthma  ", "Hypertension"]` | HTTP 200 OK; conditions deduplicated to `["Asthma", "Hypertension"]`; `Cache-Control: no-store` | HTTP 200 OK; deduplication verified; demographic fields saved; no-store confirmed | Pass | [TC-ACC-A-08.png](screenshots/TC-ACC-A-08.png) |
| TC-ACC-A-09 | FR-02, idea § 10 | Partial Profile Updates (PATCH) Preserving Attributes | Partial State Update Testing | Existing profile in database | 1. Seed profile with age, sex, and conditions<br>2. PATCH `/api/v1/profile` with `{"ageBand": "senior"}`<br>3. Verify ageBand updated while sex and conditions remain unchanged | `ageBand: senior` | HTTP 200 OK; ageBand updated to senior; biological sex and chronic conditions preserved | HTTP 200 OK; selective modification applied without clobbering unaffected fields | Pass | [TC-ACC-A-09.png](screenshots/TC-ACC-A-09.png) |
| TC-ACC-A-10 | FR-02, NFR-03 | Profile Validation Rejecting Invalid Demographic Inputs | Boundary Value Analysis & Fuzzing | Authenticated user session | 1. PUT `/api/v1/profile` with invalid age band<br>2. PUT with invalid biological sex<br>3. PUT with condition containing null bytes | `toddler_invalid`, `unknown_spec`, `Bad\x00Condition` | HTTP 422 Unprocessable Content on all boundary violations; descriptive validation errors | HTTP 422 returned across all three cases; invalid demographic data rejected safely | Pass | [TC-ACC-A-10.png](screenshots/TC-ACC-A-10.png) |
| TC-ACC-A-11 | FR-02, DR-06 | Profile Deletion Resetting Clinical Context | State Reset & Privacy Compliance | Profile configured for user | 1. DELETE `/api/v1/profile`<br>2. Verify 204 No Content and no-store header<br>3. GET `/api/v1/profile` to verify reset state | Existing user profile | HTTP 204 No Content; profile deleted; subsequent GET returns default empty context | HTTP 204 returned; subsequent GET returns empty profile with `ageBand=None`, `conditions=[]` | Pass | [TC-ACC-A-11.png](screenshots/TC-ACC-A-11.png) |
| TC-ACC-A-12 | FR-02, NFR-03 | Paginated Assessment History Listing with Next Offset | Pagination & Query Verification | 3 completed assessments in database | 1. GET `/api/v1/history?limit=2&offset=0`<br>2. Verify items count and `nextOffset=2`<br>3. GET `/api/v1/history?limit=2&offset=2`<br>4. Verify items count and `nextOffset=None` | Limit: 2, Offsets: 0, 2 | HTTP 200 OK; accurate forward pagination cursor; `Cache-Control: no-store` header present | HTTP 200 OK; page 1 returns 2 items and `nextOffset=2`; page 2 returns 1 item and `nextOffset=None` | Pass | [TC-ACC-A-12.png](screenshots/TC-ACC-A-12.png) |
| TC-ACC-A-13 | FR-02, NFR-03 | History Pagination Boundary & Unauthenticated Rejection | Boundary Value Analysis & Auth Guard | Authenticated user session | 1. GET `/api/v1/history?limit=0` -> verify 422<br>2. GET `/api/v1/history?limit=101` -> verify 422<br>3. GET `/api/v1/history?offset=-1` -> verify 422<br>4. Submit without auth -> verify 401 | Limits: 0, 101; Offset: -1 | HTTP 422 on pagination boundary violations; HTTP 401 on unauthenticated access | HTTP 422 returned on out-of-bounds parameters; HTTP 401 returned when unauthenticated | Pass | [TC-ACC-A-13.png](screenshots/TC-ACC-A-13.png) |
| TC-ACC-A-14 | FR-02, S2-NIS-16, #313 | History Detail Retrieval with Saved Triage Result | End-to-End Retrieval & Schema Validation | Completed assessment with saved result JSON in DB | 1. Store assessment with completed `AssessmentResult` JSON payload<br>2. GET `/api/v1/history/{assessment_id}`<br>3. Verify returned risk level, condition details, and recommendations | Completed assessment result (CONSULT_DOCTOR, Migraine Headache) | HTTP 200 OK; returns complete stored result object with riskLevel and conditions; no-store header | HTTP 200 OK; result parsed accurately; riskLevel == 'CONSULT_DOCTOR'; conditions present | Pass | [TC-ACC-A-14.png](screenshots/TC-ACC-A-14.png) |
| TC-ACC-A-15 | FR-02, NFR-03, DR-02 | Cross-Tenant IDOR Assessment Detail Access Denied | Access Control & Tenant Boundary | User A owns assessment; User B authenticated | 1. Authenticate as User B<br>2. GET `/api/v1/history/{user_a_assessment_id}`<br>3. Inspect response code and body | User A UUID, User B UUID, Assessment UUID | HTTP 404 NOT_FOUND with generic error code; prevents object enumeration | HTTP 404 returned; body `code == 'NOT_FOUND'`; cross-tenant access denied | Pass | [TC-ACC-A-15.png](screenshots/TC-ACC-A-15.png) |
| TC-ACC-A-16 | DR-06, NFR-04, DPDP Act 2023 | Account Data Export Returning Structured Portable JSON | Data Portability & Privacy Rights | User with profile, assessments, messages, symptoms | 1. GET `/api/v1/privacy/export` with valid session<br>2. Verify Content-Disposition attachment header<br>3. Verify payload includes account, profile, assessments, symptoms<br>4. Verify unauthenticated request returns 401 | Full personal data inventory | HTTP 200 OK; downloadable JSON attachment; comprehensive personal data inventory; 401 when unauth | HTTP 200 OK; Content-Disposition attachment header set; portable JSON exported; 401 verified | Pass | [TC-ACC-A-16.png](screenshots/TC-ACC-A-16.png) |
| TC-ACC-A-17 | DR-06, NFR-04, DPDP Act 2023 | Atomic Account Erasure Cascading Deletions & Log Anonymization | Cascading Erasure & Relational Integrity | User with profile, assessments, messages, symptoms, guest session, audit log | 1. Send DELETE `/api/v1/privacy/data` without CSRF -> verify 401<br>2. Send DELETE with valid CSRF header and cookie<br>3. Verify HTTP 204 and cookie clearing<br>4. In DB: verify User, Profile, Assessments, Messages, Symptoms, Consents deleted<br>5. In DB: verify GuestSession unlinked (claimed_by_user_id=NULL)<br>6. In DB: verify AuditLog anonymized (user_id=NULL, assessment_id=NULL) | User account with 7 related tables | HTTP 204 No Content; full relational cascade erasure; audit logs anonymized for telemetry | HTTP 204 returned; user records wiped; guest unlinked; audit logs anonymized successfully | Pass | [TC-ACC-A-17.png](screenshots/TC-ACC-A-17.png) |
| TC-ACC-A-18 | DR-06, NFR-04, NFR-03 | Post-Deletion Login Rejection & Token Invalidation | Expunged Account Security & Idempotency | Account deleted via privacy erasure | 1. POST `/api/v1/auth/login` with deleted credentials -> verify 401<br>2. GET `/api/v1/auth/me` with previous token -> verify 401<br>3. Repeat DELETE `/api/v1/privacy/data` -> verify idempotent handling | Deleted user credentials and stale access token | HTTP 401 Unauthorized on deleted login; HTTP 401 on stale session token | HTTP 401 returned on login; HTTP 401 returned on stale token; account permanently expunged | Pass | [TC-ACC-A-18.png](screenshots/TC-ACC-A-18.png) |

---

## Evidence Gallery – Automated Accounts & Deletion Suite

| TC ID | Description | Evidence Screenshot |
|---|---|---|
| TC-ACC-A-01 | User Registration with Argon2id & Conflict Rejection | ![TC-ACC-A-01](screenshots/TC-ACC-A-01.png) |
| TC-ACC-A-02 | User Login Issuing HttpOnly Cookies & CSRF Protection | ![TC-ACC-A-02](screenshots/TC-ACC-A-02.png) |
| TC-ACC-A-03 | Token Refresh Rotating Access & Refresh Tokens | ![TC-ACC-A-03](screenshots/TC-ACC-A-03.png) |
| TC-ACC-A-04 | Current User Profile (`/auth/me`) Session Verification | ![TC-ACC-A-04](screenshots/TC-ACC-A-04.png) |
| TC-ACC-A-05 | Authenticated Password Change Lifecycle | ![TC-ACC-A-05](screenshots/TC-ACC-A-05.png) |
| TC-ACC-A-06 | User Logout Clearing Cookies & Revoking Tokens | ![TC-ACC-A-06](screenshots/TC-ACC-A-06.png) |
| TC-ACC-A-07 | Profile Retrieval Default Empty State & No-Store Header | ![TC-ACC-A-07](screenshots/TC-ACC-A-07.png) |
| TC-ACC-A-08 | Profile Creation/Replacement & Condition Deduplication | ![TC-ACC-A-08](screenshots/TC-ACC-A-08.png) |
| TC-ACC-A-09 | Partial Profile Updates (PATCH) Preserving Attributes | ![TC-ACC-A-09](screenshots/TC-ACC-A-09.png) |
| TC-ACC-A-10 | Profile Validation Rejecting Invalid Demographic Inputs | ![TC-ACC-A-10](screenshots/TC-ACC-A-10.png) |
| TC-ACC-A-11 | Profile Deletion Resetting Clinical Context | ![TC-ACC-A-11](screenshots/TC-ACC-A-11.png) |
| TC-ACC-A-12 | Paginated Assessment History Listing with Next Offset | ![TC-ACC-A-12](screenshots/TC-ACC-A-12.png) |
| TC-ACC-A-13 | History Pagination Boundary & Unauthenticated Rejection | ![TC-ACC-A-13](screenshots/TC-ACC-A-13.png) |
| TC-ACC-A-14 | History Detail Retrieval with Saved Triage Result | ![TC-ACC-A-14](screenshots/TC-ACC-A-14.png) |
| TC-ACC-A-15 | Cross-Tenant IDOR Assessment Detail Access Denied | ![TC-ACC-A-15](screenshots/TC-ACC-A-15.png) |
| TC-ACC-A-16 | Account Data Export Returning Structured Portable JSON | ![TC-ACC-A-16](screenshots/TC-ACC-A-16.png) |
| TC-ACC-A-17 | Atomic Account Erasure Cascading Deletions & Log Anonymization | ![TC-ACC-A-17](screenshots/TC-ACC-A-17.png) |
| TC-ACC-A-18 | Post-Deletion Login Rejection & Token Invalidation | ![TC-ACC-A-18](screenshots/TC-ACC-A-18.png) |

---

## Terminal Run Screenshot (Automated Suite)

![pytest terminal run – 18 passed in 22.71s](screenshots/terminal-run.png)
