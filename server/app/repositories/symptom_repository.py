"""Symptom repository providing typed persistence for structured symptoms (FR-17).

Responsibilities:
    - Persist symptoms with normalized names and structured JSONB clinical details.
    - Support upsert operations to merge newly extracted clinical attributes.
    - Provide bulk replace operations for symptom confirmation and edits.
    - Query symptoms per assessment with typed accessors.

Owner: Nishith · Task: S1-NIT-4 · Requirements: FR-17
"""

from collections.abc import Sequence
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.symptom import Symptom


def _build_details_payload(
    severity: str = "UNKNOWN",
    duration: dict[str, Any] | None = None,
    body_site: str | None = None,
    onset: str | None = None,
    source: str = "user",
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Assemble structured clinical details dictionary for JSONB storage."""
    payload: dict[str, Any] = {
        "severity": severity.upper() if severity else "UNKNOWN",
        "duration": duration,
        "body_site": body_site.strip().lower() if body_site else None,
        "onset": onset.strip() if onset else None,
        "source": source.strip().lower() if source else "user",
    }
    if extra:
        for k, v in extra.items():
            if k not in payload or payload[k] is None:
                payload[k] = v
    return payload


def create_symptom(
    session: Session,
    assessment_id: UUID,
    name: str,
    severity: str = "UNKNOWN",
    duration: dict[str, Any] | None = None,
    body_site: str | None = None,
    onset: str | None = None,
    source: str = "user",
    details: dict[str, Any] | None = None,
) -> Symptom:
    """Create and persist a new symptom with structured clinical details.

    Args:
        session: Active SQLAlchemy database session.
        assessment_id: Target assessment session UUID.
        name: Canonical or reported symptom name.
        severity: Clinical severity ('MILD', 'MODERATE', 'SEVERE', 'UNKNOWN').
        duration: Structured duration dict (e.g. {'value': 2, 'unit': 'DAY'}).
        body_site: Anatomical location or None if systemic.
        onset: Timing phrase or relative onset string.
        source: Symptom origin ('user' or 'ai').
        details: Optional arbitrary details dictionary overriding defaults.

    Returns:
        The newly created Symptom instance.
    """
    clean_name = name.strip().lower()
    full_details = details or _build_details_payload(
        severity=severity,
        duration=duration,
        body_site=body_site,
        onset=onset,
        source=source,
    )

    symptom = Symptom(
        assessment_id=assessment_id,
        name=clean_name,
        details=full_details,
    )
    session.add(symptom)
    session.flush()
    return symptom


def get_symptom(
    session: Session,
    assessment_id: UUID,
    name: str,
) -> Symptom | None:
    """Retrieve a specific symptom by assessment ID and name.

    Args:
        session: Active SQLAlchemy database session.
        assessment_id: Target assessment session UUID.
        name: Symptom name (normalized before query).

    Returns:
        Symptom instance if found, None otherwise.
    """
    clean_name = name.strip().lower()
    stmt = select(Symptom).where(
        Symptom.assessment_id == assessment_id,
        Symptom.name == clean_name,
    )
    return session.scalar(stmt)


def list_symptoms_by_assessment(
    session: Session,
    assessment_id: UUID,
) -> Sequence[Symptom]:
    """Retrieve all symptoms recorded for an assessment.

    Args:
        session: Active SQLAlchemy database session.
        assessment_id: Target assessment session UUID.

    Returns:
        Sequence of Symptom instances ordered by creation time.
    """
    stmt = (
        select(Symptom)
        .where(Symptom.assessment_id == assessment_id)
        .order_by(Symptom.created_at.asc())
    )
    return session.scalars(stmt).all()


def upsert_symptom(
    session: Session,
    assessment_id: UUID,
    name: str,
    severity: str = "UNKNOWN",
    duration: dict[str, Any] | None = None,
    body_site: str | None = None,
    onset: str | None = None,
    source: str = "user",
    details: dict[str, Any] | None = None,
) -> Symptom:
    """Insert or update a symptom, merging structured attributes deterministically.

    If the symptom already exists:
        - Updates severity if the new severity is not 'UNKNOWN'.
        - Updates duration if a new duration is provided.
        - Updates body_site if a new body_site is provided.
        - Retains previous details when new attributes are omitted.

    Args:
        session: Active SQLAlchemy database session.
        assessment_id: Target assessment session UUID.
        name: Symptom name.
        severity: Clinical severity level.
        duration: Structured duration dict.
        body_site: Anatomical site.
        onset: Timing onset.
        source: Provenance string.
        details: Optional custom details dict overriding merge logic.

    Returns:
        The created or updated Symptom instance.
    """
    existing = get_symptom(session, assessment_id, name)
    if existing is None:
        return create_symptom(
            session=session,
            assessment_id=assessment_id,
            name=name,
            severity=severity,
            duration=duration,
            body_site=body_site,
            onset=onset,
            source=source,
            details=details,
        )

    if details is not None:
        merged = {**existing.details, **details}
    else:
        merged = dict(existing.details or {})
        # Update severity if new is specific
        new_sev = severity.upper() if severity else "UNKNOWN"
        if new_sev != "UNKNOWN" or not merged.get("severity"):
            merged["severity"] = new_sev
        # Update duration if specified
        if duration is not None:
            merged["duration"] = duration
        # Update body_site if specified
        if body_site is not None:
            merged["body_site"] = body_site.strip().lower()
        # Update onset if specified
        if onset is not None:
            merged["onset"] = onset.strip()
        merged["source"] = source.strip().lower() if source else "user"

    existing.details = merged
    session.flush()
    return existing


def delete_symptom(
    session: Session,
    assessment_id: UUID,
    name: str,
) -> bool:
    """Delete a specific symptom from an assessment.

    Args:
        session: Active SQLAlchemy database session.
        assessment_id: Target assessment session UUID.
        name: Symptom name.

    Returns:
        True if deleted, False if symptom not found.
    """
    symptom = get_symptom(session, assessment_id, name)
    if symptom is None:
        return False
    session.delete(symptom)
    session.flush()
    return True


def delete_symptoms_by_assessment(
    session: Session,
    assessment_id: UUID,
) -> int:
    """Delete all symptoms associated with an assessment.

    Args:
        session: Active SQLAlchemy database session.
        assessment_id: Target assessment session UUID.

    Returns:
        Number of symptoms deleted.
    """
    symptoms = list_symptoms_by_assessment(session, assessment_id)
    count = len(symptoms)
    for s in symptoms:
        session.delete(s)
    session.flush()
    return count


def replace_symptoms_for_assessment(
    session: Session,
    assessment_id: UUID,
    symptoms_data: list[dict[str, Any]],
) -> list[Symptom]:
    """Atomically replace the full symptom set for an assessment (FR-16, FR-17).

    Preserves existing symptom IDs when names match; removes symptoms not in the
    new list; adds new symptoms.

    Args:
        session: Active SQLAlchemy database session.
        assessment_id: Target assessment session UUID.
        symptoms_data: List of dicts with 'name', 'severity', 'duration', etc.

    Returns:
        List of current active Symptom instances.
    """
    existing_list = list_symptoms_by_assessment(session, assessment_id)
    existing_map = {s.name: s for s in existing_list}
    new_names = {
        item["name"].strip().lower() for item in symptoms_data if item.get("name")
    }

    # Delete symptoms no longer present
    for name, s in existing_map.items():
        if name not in new_names:
            session.delete(s)

    # Upsert symptoms in the new list
    result: list[Symptom] = []
    for item in symptoms_data:
        raw_name = item.get("name")
        if not raw_name or not str(raw_name).strip():
            continue
        item_name = str(raw_name).strip().lower()
        upserted = upsert_symptom(
            session=session,
            assessment_id=assessment_id,
            name=item_name,
            severity=str(item.get("severity", "UNKNOWN")),
            duration=item.get("duration"),
            body_site=item.get("body_site") or item.get("body_location"),
            onset=item.get("onset"),
            source=str(item.get("source", "user")),
            details=item.get("details"),
        )
        result.append(upserted)

    session.flush()
    return result
