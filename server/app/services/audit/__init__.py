"""Audit log service package.

Responsibilities:
    - Structured audit logging for clinical analyses and recommendations (NFR-10).
    - Zero-PII compliance and privacy-preserving telemetry (DR-06, S2-HAR-7).

Owner: Vivek (services/audit) · Task: S2-VIV-4 · Requirements: NFR-10
"""

from app.services.audit.schemas import (
    AuditEventType,
    AuditLogCreate,
    AuditLogRead,
)
from app.services.audit.service import AuditService

__all__ = [
    "AuditEventType",
    "AuditLogCreate",
    "AuditLogRead",
    "AuditService",
]
