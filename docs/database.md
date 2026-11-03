# CareGuide AI Database Architecture

## Overview
This document defines the schema, indexing strategy, and seed data architecture for CareGuide AI, ensuring compliance with DPDP Act 2023 and deterministic clinical triage rules.

## Core Tables (Sprint 0: Setup & Contracts)
- `users`: User identity and credentials (optional for guests).
- `consents`: Explicit informed consent records compliant with DPDP Act 2023.
- `assessments`: Triage sessions linked to consents and optional users.
- `messages`: Conversation turns between patient and assistant.
- `symptoms`: Extracted and confirmed clinical symptoms.

## Sprint 1: Database Optimization (Issue #38 · Task: S1-DIM-4)

Owner: Dimple · Requirements: NFR-01

Revision `0002_hot_query_indexes` introduces B-tree indexes for all hot query patterns identified in the assessment lifecycle and data retention flows:

| Table | Index Name | Columns | Query Pattern / Rationale |
|---|---|---|---|
| `assessments` | `ix_assessments_user_id` | `user_id` | Fetching past assessments for registered users (`WHERE user_id = :uid`). |
| `assessments` | `ix_assessments_created_at` | `created_at` | Guest assessment TTL purge job (`WHERE user_id IS NULL AND created_at < :cutoff`). |
| `assessments` | `ix_assessments_state` | `state` | Filtering active assessments by state machine state. |
| `assessments` | `ix_assessments_user_id_created_at` | `user_id, created_at` | Composite covering index for user history ordered by recency. |
| `messages` | `ix_messages_assessment_id` | `assessment_id` | Fast retrieval of conversation turns for an active assessment. |
| `symptoms` | `ix_symptoms_assessment_id` | `assessment_id` | Fast retrieval of extracted/confirmed symptoms for an active assessment. |

### Realistic Demo Seed Data
`server/app/repositories/seed_repository.py` provides `seed_realistic_demo_data(session)` with three realistic, non-diagnostic triage scenarios:
1. **Registered Patient (Completed):** User with multi-turn chat messages, normalized symptoms ("headache", "fatigue"), and `COMPLETED` state.
2. **Anonymous Guest (Active):** Guest session with no user account, in `SYMPTOM_COLLECTION` state with active symptoms ("cough", "runny nose").
3. **Registered Patient (Clarifying):** Assessment in `CLARIFYING` state with targeted follow-up dialogue.

All demo data uses reserved `.invalid` emails, fixed deterministic UUIDs, and explicitly fictional text. Seeding is idempotent and safe to run repeatedly.

### Staging Verification on Neon
To verify migration 0002 on Neon staging:
```powershell
# 1. Generate offline SQL to inspect DDL before applying:
alembic upgrade head --sql

# 2. Apply online migration against Neon staging database:
DATABASE_URL="<neon-staging-connection-string>" alembic upgrade head
```

## Windows Local Setup (Docker Database)

For local development with PostgreSQL 16:
```powershell
# 1. Start local PostgreSQL container
docker-compose up -d db

# 2. Apply migrations
.venv\Scripts\python.exe -m alembic upgrade head

# 3. Seed demo data
.venv\Scripts\python.exe -c "from app.db.session import create_session_factory, get_engine; from app.repositories.seed_repository import seed_realistic_demo_data; factory = create_session_factory(get_engine()); session = factory(); seed_realistic_demo_data(session); session.commit(); print('Demo data seeded successfully!')"
```
