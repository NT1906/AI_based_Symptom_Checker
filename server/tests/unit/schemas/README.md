# Schema Unit Tests (`server/tests/unit/schemas/`)

## Purpose
This test suite validates the Pydantic v2 schemas defined in `server/app/schemas/`. It tests model instantiations, boundary conditions, camelCase alias serialization, and strict medical-safety constraints (e.g. non-empty disclaimers, urgent emergency escalations, clarification caps).

## Test Coverage
- **Happy Paths**: Model instantiation, snake_case -> camelCase wire transformations, default disclaimers.
- **Edge Cases**: Zero duration values, whitespace stripping/normalization, maximum clarification loop bounds, URGENT referral defaults.
- **Failure Cases**: Blank names, negative numbers, out-of-range confidence scores, invalid ranks, missing required fields.

## Running Tests
```bash
pytest server/tests/unit/schemas/
```
