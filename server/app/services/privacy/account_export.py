"""Build an account-scoped download from the persisted privacy data inventory.

Owner: Harsh · Task: S2-HAR-2 · Issue: #173 · Requirements: DR-06, NFR-04
"""

from uuid import UUID

from pydantic import JsonValue
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload, sessionmaker

from app.core.errors import NotFoundError
from app.models import Assessment, Symptom, User


class AccountExport:
    """Read only one account and serialize an explicit allowlist of fields."""

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        """Save the factory used to read one export."""
        self._session_factory = session_factory

    def export(self, user_id: UUID) -> dict[str, JsonValue]:
        """Return persisted account data or raise if the account was deleted."""
        with self._session_factory() as session:
            user = session.scalar(
                select(User)
                .where(User.id == user_id)
                .options(
                    selectinload(User.profile),
                    selectinload(User.assessments).selectinload(Assessment.consent),
                    selectinload(User.assessments).selectinload(Assessment.messages),
                    selectinload(User.assessments).selectinload(Assessment.symptoms),
                )
            )
            if user is None:
                raise NotFoundError("Account not found")
            profile = user.profile
            return {
                "account": {
                    "id": str(user.id),
                    "email": user.email,
                    "createdAt": user.created_at.isoformat(),
                },
                "profile": {
                    "ageBand": profile.age_band,
                    "biologicalSex": profile.biological_sex,
                    "chronicConditions": list(profile.chronic_conditions),
                    "updatedAt": profile.updated_at.isoformat(),
                }
                if profile is not None
                else None,
                "assessments": [
                    _export_assessment(row)
                    for row in sorted(
                        user.assessments, key=lambda row: (row.created_at, row.id)
                    )
                ],
            }


def _export_assessment(row: Assessment) -> JsonValue:
    """Export assessment content without guest, token, or internal metadata."""
    return {
        "id": str(row.id),
        "state": row.state,
        "createdAt": row.created_at.isoformat(),
        "result": row.result,
        "consent": {
            "policyVersion": row.consent.policy_version,
            "createdAt": row.consent.created_at.isoformat(),
        },
        "messages": [
            {
                "role": message.role,
                "position": message.position,
                "content": message.content,
                "createdAt": message.created_at.isoformat(),
            }
            for message in row.messages
        ],
        "symptoms": [
            _export_symptom(symptom)
            for symptom in sorted(row.symptoms, key=lambda symptom: symptom.name)
        ],
    }


def _export_symptom(symptom: Symptom) -> JsonValue:
    """Limit stored symptom details to fields intended for the export."""
    duration = symptom.duration or {}
    value, unit = duration.get("value"), duration.get("unit")
    return {
        "name": symptom.name,
        "severity": symptom.severity,
        "duration": (
            {"value": value, "unit": unit}
            if type(value) in (int, float) and isinstance(unit, str)
            else None
        ),
        "bodySite": symptom.body_site,
    }
