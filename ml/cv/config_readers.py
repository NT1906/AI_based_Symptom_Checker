"""Small typed readers shared by the CV config loader.

Each reader takes one key from a parsed-YAML mapping, checks its type and
range, and raises ``ConfigError`` with the full key path when it is wrong, so
a bad config fails before a GPU session starts.

Every reader takes ``section`` (the mapping that holds the key), ``key`` and
``where`` (the dotted path of ``section``, used in error messages). Callers
check that ``key`` exists first with :func:`require_exact_keys`.

Owner: Nisarg (cv) · Task: S0-NIS-2 · Requirements: NFR-07
"""

import re
from collections.abc import Mapping
from typing import Any

NAME_PATTERN = re.compile(r"^[a-z][a-z0-9_]*$")

Raw = Mapping[str, Any]  # Any: parsed YAML; every value is type-checked before use.


class ConfigError(ValueError):
    """Raised when a config file is missing, malformed or breaks a rule."""


def read_mapping(raw: Any, where: str) -> Raw:  # Any: parsed YAML
    """Check that a parsed YAML value is a mapping.

    Args:
        raw: The parsed value.
        where: Dotted path of the value, for the error message.

    Returns:
        ``raw`` itself, typed as a mapping.

    Raises:
        ConfigError: If ``raw`` is not a mapping.
    """
    if not isinstance(raw, Mapping):
        raise ConfigError(f"{where}: expected a mapping")
    return raw


def require_exact_keys(section: Raw, expected: set[str], where: str) -> None:
    """Check that a section has exactly the expected keys.

    Unknown keys are rejected too, because they are usually typos that would
    otherwise be ignored silently.

    Args:
        section: The mapping to check.
        expected: The keys it must have.
        where: Dotted path of ``section``, for the error message.

    Raises:
        ConfigError: If a key is missing or an unknown key is present.
    """
    missing = expected - set(section)
    unknown = set(section) - expected
    if missing:
        raise ConfigError(f"{where}: missing key(s) {sorted(missing)}")
    if unknown:
        raise ConfigError(f"{where}: unknown key(s) {sorted(map(str, unknown))}")


def read_integer(
    section: Raw, key: str, where: str, *, minimum: int, maximum: int | None = None
) -> int:
    """Read an integer within ``[minimum, maximum]``.

    Args:
        section: Mapping that holds the key.
        key: Key to read.
        where: Dotted path of ``section``.
        minimum: Smallest allowed value.
        maximum: Largest allowed value, or ``None`` for no upper limit.

    Returns:
        The integer.

    Raises:
        ConfigError: If the value is not an integer (``true`` does not count)
            or is out of range.
    """
    value = section[key]
    if not isinstance(value, int) or isinstance(value, bool):
        raise ConfigError(f"{where}.{key}: expected an integer")
    if value < minimum or (maximum is not None and value > maximum):
        upper = "" if maximum is None else f" and <= {maximum}"
        raise ConfigError(f"{where}.{key}: must be >= {minimum}{upper}")
    return value


def read_number(
    section: Raw,
    key: str,
    where: str,
    low: float,
    high: float,
    inclusive: bool = True,
) -> float:
    """Read a number within ``[low, high]``, or ``(low, high)`` if not inclusive.

    Args:
        section: Mapping that holds the key.
        key: Key to read.
        where: Dotted path of ``section``.
        low: Lower bound.
        high: Upper bound.
        inclusive: Whether the bounds themselves are allowed.

    Returns:
        The value as a float.

    Raises:
        ConfigError: If the value is not a number or is out of range
            (NaN is always out of range).
    """
    value = section[key]
    if not isinstance(value, int | float) or isinstance(value, bool):
        raise ConfigError(f"{where}.{key}: expected a number")
    inside = low <= value <= high if inclusive else low < value < high
    if not inside:
        bounds = f"[{low}, {high}]" if inclusive else f"({low}, {high})"
        raise ConfigError(f"{where}.{key}: must be in {bounds}")
    return float(value)


def read_boolean(section: Raw, key: str, where: str) -> bool:
    """Read a ``true`` / ``false`` value.

    Args:
        section: Mapping that holds the key.
        key: Key to read.
        where: Dotted path of ``section``.

    Returns:
        The boolean.

    Raises:
        ConfigError: If the value is not a boolean.
    """
    value = section[key]
    if not isinstance(value, bool):
        raise ConfigError(f"{where}.{key}: expected true or false")
    return value


def read_name(section: Raw, key: str, where: str, pattern: str | None = None) -> str:
    """Read an identifier-like string.

    Args:
        section: Mapping that holds the key.
        key: Key to read.
        where: Dotted path of ``section``.
        pattern: Regular expression the string must match. Defaults to
            snake_case (``NAME_PATTERN``).

    Returns:
        The string.

    Raises:
        ConfigError: If the value is not a string or does not match.
    """
    value = section[key]
    regex = re.compile(pattern) if pattern else NAME_PATTERN
    if not isinstance(value, str) or not regex.match(value):
        raise ConfigError(f"{where}.{key}: expected a name matching {regex.pattern}")
    return value


def read_string_list(section: Raw, key: str, where: str) -> list[str]:
    """Read a list of strings.

    Args:
        section: Mapping that holds the key.
        key: Key to read.
        where: Dotted path of ``section``.

    Returns:
        The list (may be empty; callers decide whether that is allowed).

    Raises:
        ConfigError: If the value is not a list of strings.
    """
    value = section[key]
    if not isinstance(value, list) or not all(isinstance(v, str) for v in value):
        raise ConfigError(f"{where}.{key}: expected a list of strings")
    return value


def read_channel_triple(
    section: Raw, key: str, positive: bool = False
) -> tuple[float, float, float]:
    """Read a per-channel (R, G, B) triple from the ``data`` section.

    Args:
        section: The ``data`` mapping.
        key: ``mean`` or ``std``.
        positive: Require every value to be above 0 (needed for ``std``,
            which preprocessing divides by).

    Returns:
        The three values as floats.

    Raises:
        ConfigError: If the value is not exactly 3 numbers, or a value is not
            positive when ``positive`` is set.
    """
    value = section[key]
    if (
        not isinstance(value, list)
        or len(value) != 3
        or not all(
            isinstance(v, int | float) and not isinstance(v, bool) for v in value
        )
    ):
        raise ConfigError(f"data.{key}: expected 3 numbers (R, G, B)")
    if positive and min(value) <= 0:
        raise ConfigError(f"data.{key}: every value must be above 0")
    return (float(value[0]), float(value[1]), float(value[2]))
