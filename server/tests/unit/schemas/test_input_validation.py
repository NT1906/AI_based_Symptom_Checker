"""Unit tests for input validation hardening on all API request schemas.

Responsibilities:
    - Verify RequestSchemaBase enforces extra='forbid' and str_strip_whitespace.
    - Verify null byte rejection on MessageCreate, SymptomCreate, SymptomUpdate,
      ProfileCreate, ProfileUpdate, and Condition schemas.
    - Verify length limits and enum validation across all request schemas.
    - Verify Duration bounds (NaN/Inf forbidden, le=36500).
    - Verify UpdateSymptomsRequest batch size limits (1-50 items).
    - Verify ClaimAssessmentRequest extra field rejection.

Owner: Darshil (orchestration) · Task: S2-DAR-7 · Requirements: NFR-03
"""

import math
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.schemas.assessment import AssessmentCreate, ClaimAssessmentRequest
from app.schemas.base import RequestSchemaBase
from app.schemas.condition import Condition
from app.schemas.enums import DurationUnit, Severity
from app.schemas.message import MessageCreate
from app.schemas.profile import AgeBand, ProfileCreate, ProfileUpdate
from app.schemas.symptom import (
    Duration,
    SymptomCreate,
    SymptomUpdate,
    UpdateSymptomsRequest,
)


# =============================================================================
# 1. RequestSchemaBase
# =============================================================================


class TestRequestSchemaBase:
    """Tests for the RequestSchemaBase mixin."""

    def _make_concrete(self) -> type:
        """Return a minimal concrete subclass for testing."""
        from pydantic import Field

        class _Req(RequestSchemaBase):
            value: str = Field(default="hello")

        return _Req

    def test_extra_field_rejected(self) -> None:
        """Extra/unknown fields must raise ValidationError (mass-assignment guard)."""
        Req = self._make_concrete()
        with pytest.raises(ValidationError):
            Req(value="ok", unknown_field="injection")

    def test_whitespace_stripped_from_string_fields(self) -> None:
        """Leading/trailing whitespace is stripped automatically."""
        Req = self._make_concrete()
        instance = Req(value="  hello  ")
        assert instance.value == "hello"

    def test_valid_instance_created(self) -> None:
        """Happy path: valid fields produce a valid instance."""
        Req = self._make_concrete()
        instance = Req(value="test")
        assert instance.value == "test"


# =============================================================================
# 2. MessageCreate
# =============================================================================


class TestMessageCreate:
    """Tests for MessageCreate request schema input validation."""

    def test_happy_path(self) -> None:
        """Valid content creates MessageCreate successfully."""
        msg = MessageCreate(content="I have a headache")
        assert msg.content == "I have a headache"

    def test_null_byte_in_content_rejected(self) -> None:
        """Null byte in content must raise ValidationError."""
        with pytest.raises(ValidationError, match="null"):
            MessageCreate(content="bad\x00content")

    def test_null_byte_in_idempotency_key_rejected(self) -> None:
        """Null byte in idempotency_key must raise ValidationError."""
        with pytest.raises(ValidationError, match="null"):
            MessageCreate(content="valid", idempotency_key="key\x00value")

    def test_blank_content_rejected(self) -> None:
        """Blank/whitespace-only content must raise ValidationError."""
        with pytest.raises(ValidationError):
            MessageCreate(content="   ")

    def test_content_too_long_rejected(self) -> None:
        """Content exceeding 4000 characters must be rejected."""
        with pytest.raises(ValidationError):
            MessageCreate(content="a" * 4001)

    def test_extra_field_rejected(self) -> None:
        """Extra fields must be rejected (mass-assignment protection)."""
        with pytest.raises(ValidationError):
            MessageCreate(content="hi", injected="evil")

    def test_whitespace_stripped_from_content(self) -> None:
        """Leading/trailing whitespace is stripped from content."""
        msg = MessageCreate(content="  headache  ")
        assert msg.content == "headache"

    def test_max_length_content_accepted(self) -> None:
        """Content at exactly 4000 characters is accepted."""
        msg = MessageCreate(content="a" * 4000)
        assert len(msg.content) == 4000


# =============================================================================
# 3. AssessmentCreate
# =============================================================================


class TestAssessmentCreate:
    """Tests for AssessmentCreate request schema."""

    def test_happy_path(self) -> None:
        """AssessmentCreate with required consent_id succeeds."""
        a = AssessmentCreate(consent_id=uuid4())
        assert a.consent_id is not None

    def test_extra_field_rejected(self) -> None:
        """Extra fields on AssessmentCreate must be rejected."""
        with pytest.raises(ValidationError):
            AssessmentCreate(consent_id=uuid4(), hacked_field="value")

    def test_optional_user_id_accepted(self) -> None:
        """Optional user_id field is accepted."""
        uid = uuid4()
        a = AssessmentCreate(consent_id=uuid4(), user_id=uid)
        assert a.user_id == uid


# =============================================================================
# 4. SymptomCreate
# =============================================================================


class TestSymptomCreate:
    """Tests for SymptomCreate request schema."""

    def test_happy_path(self) -> None:
        """Valid SymptomCreate with all fields."""
        s = SymptomCreate(
            name="Headache",
            severity=Severity.MILD,
            body_location="head",
        )
        assert s.name == "headache"
        assert s.body_location == "head"

    def test_name_normalized_lowercase(self) -> None:
        """Name is stripped and lowercased."""
        s = SymptomCreate(name="  FEVER  ")
        assert s.name == "fever"

    def test_null_byte_in_name_rejected(self) -> None:
        """Null byte in name must raise ValidationError."""
        with pytest.raises(ValidationError, match="null"):
            SymptomCreate(name="fever\x00")

    def test_null_byte_in_body_location_rejected(self) -> None:
        """Null byte in body_location must raise ValidationError."""
        with pytest.raises(ValidationError, match="null"):
            SymptomCreate(name="fever", body_location="chest\x00")

    def test_blank_name_rejected(self) -> None:
        """Blank name after strip must raise ValidationError."""
        with pytest.raises(ValidationError):
            SymptomCreate(name="   ")

    def test_name_too_long_rejected(self) -> None:
        """Name over 128 characters must be rejected."""
        with pytest.raises(ValidationError):
            SymptomCreate(name="a" * 129)

    def test_extra_field_rejected(self) -> None:
        """Extra fields must be rejected."""
        with pytest.raises(ValidationError):
            SymptomCreate(name="fever", malicious="injection")

    def test_body_location_whitespace_only_becomes_none(self) -> None:
        """Whitespace-only body_location is normalized to None."""
        s = SymptomCreate(name="fever", body_location="   ")
        assert s.body_location is None


# =============================================================================
# 5. SymptomUpdate
# =============================================================================


class TestSymptomUpdate:
    """Tests for SymptomUpdate request schema."""

    def test_happy_path_name_only(self) -> None:
        """Update with just a name is valid."""
        u = SymptomUpdate(name="Cough")
        assert u.name == "cough"

    def test_happy_path_severity_only(self) -> None:
        """Update with just severity is valid."""
        u = SymptomUpdate(severity=Severity.SEVERE)
        assert u.severity == Severity.SEVERE

    def test_happy_path_id_only(self) -> None:
        """Update with just an id is valid (confirms symptom by id)."""
        uid = uuid4()
        u = SymptomUpdate(id=uid)
        assert u.id == uid

    def test_empty_update_rejected(self) -> None:
        """SymptomUpdate with no fields must raise ValidationError."""
        with pytest.raises(ValidationError, match="at least one"):
            SymptomUpdate()

    def test_null_byte_in_name_rejected(self) -> None:
        """Null byte in name must raise ValidationError."""
        with pytest.raises(ValidationError, match="null"):
            SymptomUpdate(name="fever\x00")

    def test_null_byte_in_body_location_rejected(self) -> None:
        """Null byte in body_location must raise ValidationError."""
        with pytest.raises(ValidationError, match="null"):
            SymptomUpdate(name="fever", body_location="chest\x00")

    def test_extra_field_rejected(self) -> None:
        """Extra fields must be rejected."""
        with pytest.raises(ValidationError):
            SymptomUpdate(name="fever", extra="bad")

    def test_name_normalized(self) -> None:
        """Name is stripped and lowercased."""
        u = SymptomUpdate(name="  Headache  ")
        assert u.name == "headache"


# =============================================================================
# 6. UpdateSymptomsRequest
# =============================================================================


class TestUpdateSymptomsRequest:
    """Tests for UpdateSymptomsRequest batch bounds."""

    def _valid_update(self) -> SymptomUpdate:
        return SymptomUpdate(name="fever")

    def test_happy_path_single_item(self) -> None:
        """Single item list is valid."""
        req = UpdateSymptomsRequest(symptoms=[self._valid_update()])
        assert len(req.symptoms) == 1

    def test_happy_path_fifty_items(self) -> None:
        """Exactly 50 items is at the limit and valid."""
        items = [SymptomUpdate(name=f"symptom{i}") for i in range(50)]
        req = UpdateSymptomsRequest(symptoms=items)
        assert len(req.symptoms) == 50

    def test_empty_list_rejected(self) -> None:
        """Empty symptoms list must be rejected (min_length=1)."""
        with pytest.raises(ValidationError):
            UpdateSymptomsRequest(symptoms=[])

    def test_over_fifty_items_rejected(self) -> None:
        """More than 50 symptoms must be rejected (max_length=50)."""
        items = [SymptomUpdate(name=f"symptom{i}") for i in range(51)]
        with pytest.raises(ValidationError):
            UpdateSymptomsRequest(symptoms=items)

    def test_extra_field_rejected(self) -> None:
        """Extra fields must be rejected."""
        with pytest.raises(ValidationError):
            UpdateSymptomsRequest(symptoms=[self._valid_update()], extra="bad")


# =============================================================================
# 7. Duration
# =============================================================================


class TestDuration:
    """Tests for Duration schema bounds and NaN/Inf rejection."""

    def test_happy_path(self) -> None:
        """Valid duration created successfully."""
        d = Duration(value=5.0, unit=DurationUnit.DAY)
        assert d.value == 5.0

    def test_zero_value_allowed(self) -> None:
        """Zero is a valid duration value (ge=0.0)."""
        d = Duration(value=0.0)
        assert d.value == 0.0

    def test_max_value_allowed(self) -> None:
        """36500 is at the upper limit and allowed."""
        d = Duration(value=36500.0)
        assert d.value == 36500.0

    def test_value_above_max_rejected(self) -> None:
        """Value above 36500 must be rejected."""
        with pytest.raises(ValidationError):
            Duration(value=36501.0)

    def test_negative_value_rejected(self) -> None:
        """Negative value must be rejected (ge=0.0)."""
        with pytest.raises(ValidationError):
            Duration(value=-1.0)

    def test_nan_rejected(self) -> None:
        """NaN must be rejected (allow_inf_nan=False)."""
        with pytest.raises(ValidationError):
            Duration(value=math.nan)

    def test_inf_rejected(self) -> None:
        """Positive infinity must be rejected."""
        with pytest.raises(ValidationError):
            Duration(value=math.inf)

    def test_negative_inf_rejected(self) -> None:
        """Negative infinity must be rejected."""
        with pytest.raises(ValidationError):
            Duration(value=-math.inf)

    def test_extra_field_rejected(self) -> None:
        """Extra fields must be rejected."""
        with pytest.raises(ValidationError):
            Duration(value=1.0, extra="bad")


# =============================================================================
# 8. ProfileCreate / ProfileUpdate
# =============================================================================


class TestProfileCreate:
    """Tests for ProfileCreate request schema validation."""

    def test_happy_path_no_fields(self) -> None:
        """ProfileCreate with no fields uses defaults."""
        p = ProfileCreate()
        assert p.age_band is None
        assert p.chronic_conditions == []

    def test_happy_path_with_age_band(self) -> None:
        """ProfileCreate with age_band succeeds."""
        p = ProfileCreate(age_band=AgeBand.ADULT)
        assert p.age_band == AgeBand.ADULT

    def test_null_byte_in_chronic_condition_rejected(self) -> None:
        """Null byte in a chronic condition must raise ValidationError."""
        with pytest.raises(ValidationError, match="null"):
            ProfileCreate(chronic_conditions=["diabetes\x00"])

    def test_condition_name_too_long_rejected(self) -> None:
        """Condition name over 128 chars must raise ValidationError."""
        with pytest.raises(ValidationError):
            ProfileCreate(chronic_conditions=["a" * 129])

    def test_too_many_conditions_rejected(self) -> None:
        """More than 50 chronic conditions must be rejected."""
        # Use 51 unique conditions to bypass deduplication
        with pytest.raises(ValidationError):
            ProfileCreate(chronic_conditions=[f"condition_{i}" for i in range(51)])

    def test_extra_field_rejected(self) -> None:
        """Extra fields must be rejected."""
        with pytest.raises(ValidationError):
            ProfileCreate(age_band=AgeBand.ADULT, hacked="value")


class TestProfileUpdate:
    """Tests for ProfileUpdate request schema validation."""

    def test_happy_path_no_fields(self) -> None:
        """ProfileUpdate with no fields is valid (partial update)."""
        p = ProfileUpdate()
        assert p.age_band is None

    def test_happy_path_with_age_band(self) -> None:
        """ProfileUpdate with age_band succeeds."""
        p = ProfileUpdate(age_band=AgeBand.SENIOR)
        assert p.age_band == AgeBand.SENIOR

    def test_null_byte_in_chronic_condition_rejected(self) -> None:
        """Null byte in a chronic condition must raise ValidationError."""
        with pytest.raises(ValidationError, match="null"):
            ProfileUpdate(chronic_conditions=["hypertension\x00"])

    def test_condition_name_too_long_rejected(self) -> None:
        """Condition name over 128 chars must raise ValidationError."""
        with pytest.raises(ValidationError):
            ProfileUpdate(chronic_conditions=["b" * 129])

    def test_too_many_conditions_rejected(self) -> None:
        """More than 50 chronic conditions must be rejected."""
        with pytest.raises(ValidationError):
            ProfileUpdate(chronic_conditions=[f"cond_{i}" for i in range(51)])

    def test_extra_field_rejected(self) -> None:
        """Extra fields must be rejected."""
        with pytest.raises(ValidationError):
            ProfileUpdate(age_band=AgeBand.CHILD, injection="bad")


# =============================================================================
# 9. ClaimAssessmentRequest
# =============================================================================


class TestClaimAssessmentRequest:
    """Tests for ClaimAssessmentRequest schema."""

    def test_happy_path(self) -> None:
        """Valid user_id creates ClaimAssessmentRequest successfully."""
        req = ClaimAssessmentRequest(user_id=uuid4())
        assert req.user_id is not None

    def test_with_guest_session_id(self) -> None:
        """Optional guest_session_id is accepted."""
        req = ClaimAssessmentRequest(user_id=uuid4(), guest_session_id=uuid4())
        assert req.guest_session_id is not None

    def test_extra_field_rejected(self) -> None:
        """Extra fields must be rejected (mass-assignment protection)."""
        with pytest.raises(ValidationError):
            ClaimAssessmentRequest(user_id=uuid4(), extra="injected")


# =============================================================================
# 10. Condition
# =============================================================================


class TestCondition:
    """Tests for Condition schema null byte and blank rejection."""

    def test_happy_path(self) -> None:
        """Valid condition name creates Condition successfully."""
        from app.schemas.enums import ConfidenceLabel

        c = Condition(name="Diabetes", confidence=ConfidenceLabel.LIKELY)
        assert c.name == "Diabetes"

    def test_null_byte_in_name_rejected(self) -> None:
        """Null byte in condition name must raise ValidationError."""
        from app.schemas.enums import ConfidenceLabel

        with pytest.raises(ValidationError, match="null"):
            Condition(name="Diabetes\x00", confidence=ConfidenceLabel.LIKELY)

    def test_blank_name_rejected(self) -> None:
        """Blank condition name must raise ValidationError."""
        from app.schemas.enums import ConfidenceLabel

        with pytest.raises(ValidationError):
            Condition(name="   ", confidence=ConfidenceLabel.LIKELY)
