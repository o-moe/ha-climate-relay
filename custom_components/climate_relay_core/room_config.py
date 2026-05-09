"""Room/profile configuration normalization helpers."""

from __future__ import annotations

from typing import Any

from .const import (
    CONF_AWAY_TARGET_TEMPERATURE,
    CONF_AWAY_TARGET_TYPE,
    CONF_HOME_TARGET_TEMPERATURE,
    CONF_HUMIDITY_ENTITY_ID,
    CONF_PRIMARY_CLIMATE_ENTITY_ID,
    CONF_ROOMS,
    CONF_SCHEDULE,
    CONF_SCHEDULE_HOME_END,
    CONF_SCHEDULE_HOME_START,
    CONF_WINDOW_ACTION_TYPE,
    CONF_WINDOW_CUSTOM_TEMPERATURE,
    CONF_WINDOW_ENTITY_ID,
    CONF_WINDOW_OPEN_DELAY_SECONDS,
    DEFAULT_AWAY_TARGET_TYPE,
    DEFAULT_FALLBACK_TEMPERATURE,
    DEFAULT_SCHEDULE_HOME_END,
    DEFAULT_SCHEDULE_HOME_START,
    DEFAULT_WINDOW_ACTION_TYPE,
    DEFAULT_WINDOW_OPEN_DELAY_SECONDS,
)

VALID_AWAY_TARGET_TYPES = {"absolute", "relative"}
VALID_WINDOW_ACTION_TYPES = {
    "off",
    "frost_protection",
    "minimum_temperature",
    "custom_temperature",
}


def default_room_data() -> dict[str, Any]:
    """Return the default regulation-profile configuration values."""
    return {
        CONF_PRIMARY_CLIMATE_ENTITY_ID: None,
        CONF_HUMIDITY_ENTITY_ID: None,
        CONF_WINDOW_ENTITY_ID: None,
        CONF_WINDOW_ACTION_TYPE: DEFAULT_WINDOW_ACTION_TYPE,
        CONF_WINDOW_CUSTOM_TEMPERATURE: None,
        CONF_WINDOW_OPEN_DELAY_SECONDS: DEFAULT_WINDOW_OPEN_DELAY_SECONDS,
        CONF_HOME_TARGET_TEMPERATURE: DEFAULT_FALLBACK_TEMPERATURE,
        CONF_AWAY_TARGET_TYPE: DEFAULT_AWAY_TARGET_TYPE,
        CONF_AWAY_TARGET_TEMPERATURE: DEFAULT_FALLBACK_TEMPERATURE - 3.0,
        CONF_SCHEDULE_HOME_START: DEFAULT_SCHEDULE_HOME_START,
        CONF_SCHEDULE_HOME_END: DEFAULT_SCHEDULE_HOME_END,
    }


def normalize_room_options(values: dict[str, Any]) -> dict[str, Any]:
    """Normalize one regulation-profile configuration for rendering and persistence."""
    return {
        CONF_PRIMARY_CLIMATE_ENTITY_ID: normalize_optional_entity_id(
            values.get(CONF_PRIMARY_CLIMATE_ENTITY_ID)
        ),
        CONF_HUMIDITY_ENTITY_ID: normalize_optional_entity_id(values.get(CONF_HUMIDITY_ENTITY_ID)),
        CONF_WINDOW_ENTITY_ID: normalize_optional_entity_id(values.get(CONF_WINDOW_ENTITY_ID)),
        CONF_WINDOW_ACTION_TYPE: normalize_window_action_type(
            values.get(CONF_WINDOW_ACTION_TYPE, DEFAULT_WINDOW_ACTION_TYPE)
        ),
        CONF_WINDOW_CUSTOM_TEMPERATURE: normalize_optional_float(
            values.get(CONF_WINDOW_CUSTOM_TEMPERATURE)
        ),
        CONF_WINDOW_OPEN_DELAY_SECONDS: normalize_non_negative_int(
            values.get(CONF_WINDOW_OPEN_DELAY_SECONDS, DEFAULT_WINDOW_OPEN_DELAY_SECONDS),
            default=DEFAULT_WINDOW_OPEN_DELAY_SECONDS,
        ),
        CONF_HOME_TARGET_TEMPERATURE: float(
            values.get(CONF_HOME_TARGET_TEMPERATURE, DEFAULT_FALLBACK_TEMPERATURE)
        ),
        CONF_AWAY_TARGET_TYPE: normalize_target_type(
            values.get(CONF_AWAY_TARGET_TYPE, DEFAULT_AWAY_TARGET_TYPE)
        ),
        CONF_AWAY_TARGET_TEMPERATURE: float(
            values.get(CONF_AWAY_TARGET_TEMPERATURE, DEFAULT_FALLBACK_TEMPERATURE - 3.0)
        ),
        CONF_SCHEDULE_HOME_START: normalize_time_field_value(
            schedule_value(values, CONF_SCHEDULE_HOME_START, DEFAULT_SCHEDULE_HOME_START)
        ),
        CONF_SCHEDULE_HOME_END: normalize_time_field_value(
            schedule_value(values, CONF_SCHEDULE_HOME_END, DEFAULT_SCHEDULE_HOME_END)
        ),
    }


def normalize_rooms(values: dict[str, Any]) -> list[dict[str, Any]]:
    """Normalize stored regulation-profile list data."""
    raw_rooms = values.get(CONF_ROOMS) or []
    return [normalize_room_options(room) for room in raw_rooms if isinstance(room, dict)]


def normalize_optional_entity_id(raw_value: Any) -> str | None:
    """Normalize an optional entity ID value."""
    if raw_value in (None, ""):
        return None
    if not isinstance(raw_value, str):
        raise ValueError(f"Unsupported entity value: {raw_value!r}")
    return raw_value


def normalize_target_type(raw_value: Any) -> str:
    """Normalize the away target type."""
    if not isinstance(raw_value, str) or raw_value not in VALID_AWAY_TARGET_TYPES:
        raise ValueError(f"Unsupported away target type: {raw_value!r}")
    return raw_value


def normalize_window_action_type(raw_value: Any) -> str:
    """Normalize the window action type."""
    if not isinstance(raw_value, str) or raw_value not in VALID_WINDOW_ACTION_TYPES:
        raise ValueError(f"Unsupported window action type: {raw_value!r}")
    return raw_value


def normalize_optional_float(raw_value: Any) -> float | None:
    """Normalize an optional float value."""
    if raw_value in (None, ""):
        return None
    if isinstance(raw_value, str):
        raw_value = raw_value.strip().replace(",", ".")
    return float(raw_value)


def normalize_non_negative_int(raw_value: Any, *, default: int) -> int:
    """Normalize a non-negative integer value."""
    if raw_value in (None, ""):
        return default
    value = int(raw_value)
    return value if value >= 0 else default


def normalize_time_field_value(raw_value: Any) -> str | None:
    """Normalize a time field value to a string or None."""
    if raw_value in (None, ""):
        return None
    return str(raw_value)


def schedule_value(values: dict[str, Any], key: str, default: str) -> Any:
    """Return a schedule value from either flat or nested persistence."""
    raw_schedule = values.get(CONF_SCHEDULE)
    if isinstance(raw_schedule, dict) and key in raw_schedule:
        return raw_schedule[key]
    return values.get(key, default)


def validate_room_schedule_window(start: str | None, end: str | None) -> bool:
    """Preserve the Options Flow invariant that schedule endpoints differ."""
    return start != end
