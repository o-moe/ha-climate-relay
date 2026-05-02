"""Runtime state and global configuration handling."""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, time, timedelta
from types import MappingProxyType
from typing import Final

from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import (
    area_registry as ar,
)
from homeassistant.helpers import (
    device_registry as dr,
)
from homeassistant.helpers import (
    entity_registry as er,
)
from homeassistant.util import dt as dt_util
from homeassistant.util import slugify

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
    DEFAULT_UNKNOWN_STATE_HANDLING,
    DEFAULT_WINDOW_ACTION_TYPE,
    DEFAULT_WINDOW_OPEN_DELAY_SECONDS,
)
from .domain import (
    EffectivePresence,
    GlobalMode,
    ManualOverride,
    OverrideTerminationType,
    RoomSchedule,
    RoomTarget,
    UnknownStateHandling,
    WindowActionType,
    build_daily_home_window_schedule,
    build_manual_override,
    evaluate_schedule,
    resolve_presence_mode,
)

_LOGGER: Final = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class GlobalConfig:
    """Global integration configuration."""

    person_entity_ids: tuple[str, ...]
    unknown_state_handling: str
    fallback_temperature: float
    manual_override_reset_time: str | None
    simulation_mode: bool
    verbose_logging: bool

    @property
    def unknown_state_handling_enum(self) -> UnknownStateHandling:
        """Return the configured unknown-state mapping as a domain enum."""
        return UnknownStateHandling(self.unknown_state_handling)


@dataclass(frozen=True, slots=True)
class AreaReference:
    """Resolved Home Assistant area context for one regulation profile."""

    area_id: str | None
    area_name: str | None


@dataclass(frozen=True, slots=True)
class RegulationProfileConfig:
    """Primary-climate-anchored configuration for one regulation profile."""

    profile_id: str
    display_name: str
    primary_climate_entity_id: str
    area_id: str | None
    area_name: str | None
    humidity_entity_id: str | None
    window_entity_id: str | None
    window_action_type: WindowActionType
    window_custom_temperature: float | None
    window_open_delay_seconds: int
    home_target: RoomTarget
    away_target: RoomTarget
    schedule: RoomSchedule


class GlobalRuntime:
    """In-memory runtime model for the integration-wide global state."""

    def __init__(
        self,
        hass: HomeAssistant,
        config: GlobalConfig,
        room_configs: tuple[RegulationProfileConfig, ...] = (),
    ) -> None:
        self._hass = hass
        self._config = config
        self._room_configs = room_configs
        self._global_mode = GlobalMode.AUTO
        self._manual_overrides: dict[str, ManualOverride] = {}
        self._subscribers: set[Callable[[], None]] = set()

    @property
    def config(self) -> GlobalConfig:
        """Return the active runtime configuration."""
        return self._config

    @property
    def global_mode(self) -> GlobalMode:
        """Return the currently selected global mode."""
        return self._global_mode

    @property
    def room_configs(self) -> tuple[RegulationProfileConfig, ...]:
        """Return the active regulation-profile configs."""
        return self._room_configs

    @property
    def effective_presence(self) -> EffectivePresence:
        """Resolve the effective presence from the current mode and person states."""
        person_states = [
            state.state
            for entity_id in self._config.person_entity_ids
            if (state := self._hass.states.get(entity_id)) is not None
        ]
        return resolve_presence_mode(
            person_states,
            self._global_mode,
            unknown_state_handling=self._config.unknown_state_handling_enum,
        )

    async def async_set_global_mode(self, mode: GlobalMode, *, source: str) -> None:
        """Set the active global mode and notify listeners."""
        previous_mode = self._global_mode
        self._global_mode = mode

        _LOGGER.info(
            "Global mode changed from %s to %s via %s",
            previous_mode.value,
            mode.value,
            source,
        )
        if self._config.verbose_logging:
            _LOGGER.info(
                "Effective presence is %s with %d configured person entities; simulation_mode=%s",
                self.effective_presence.value,
                len(self._config.person_entity_ids),
                self._config.simulation_mode,
            )

        self._notify_subscribers()

    async def async_set_area_override(
        self,
        *,
        area_id: str,
        target_temperature: float,
        termination_type: OverrideTerminationType,
        source: str,
        duration_minutes: int | None = None,
        until_time: str | None = None,
    ) -> ManualOverride:
        """Set or replace one area-scoped manual override."""
        room_config = self._find_room_config(area_id)
        now = dt_util.now()
        schedule_evaluation = evaluate_schedule(
            room_config.schedule,
            now,
            dt_util.DEFAULT_TIME_ZONE,
        )
        override = build_manual_override(
            profile_id=room_config.profile_id,
            area_id=room_config.area_id or room_config.profile_id,
            target_temperature=target_temperature,
            termination_type=termination_type,
            duration_minutes=duration_minutes,
            until_time=until_time,
            next_change_at=schedule_evaluation.next_change_at,
            now=now,
            timezone=dt_util.DEFAULT_TIME_ZONE,
        )
        self._manual_overrides[room_config.profile_id] = override
        _LOGGER.info(
            "Manual override for %s set to %.1f via %s; termination=%s ends_at=%s",
            room_config.display_name,
            override.target_temperature,
            source,
            override.termination_type,
            override.ends_at.isoformat() if override.ends_at is not None else "never",
        )
        self._notify_subscribers()
        return override

    async def async_clear_area_override(self, *, area_id: str, source: str) -> None:
        """Clear one area-scoped manual override."""
        room_config = self._find_room_config(area_id)
        removed = self._manual_overrides.pop(room_config.profile_id, None)
        if removed is not None:
            _LOGGER.info("Manual override for %s cleared via %s", room_config.display_name, source)
            self._notify_subscribers()

    @callback
    def manual_override_for_profile(self, profile_id: str) -> ManualOverride | None:
        """Return the active manual override for one regulation profile."""
        override = self._manual_overrides.get(profile_id)
        if override is None:
            return None

        now = dt_util.now()
        if not override.is_active(now) or self._is_after_daily_reset(override, now):
            self._manual_overrides.pop(profile_id, None)
            return None
        return override

    @callback
    def next_manual_override_reset_at(self, override: ManualOverride) -> datetime | None:
        """Return the next configured daily reset time for an override."""
        reset_time_value = self._config.manual_override_reset_time
        if reset_time_value is None:
            return None
        reset_time = time.fromisoformat(reset_time_value)
        local_now = dt_util.now().astimezone(dt_util.DEFAULT_TIME_ZONE)
        reset_at = datetime.combine(local_now.date(), reset_time, tzinfo=dt_util.DEFAULT_TIME_ZONE)
        if reset_at <= local_now:
            reset_at += timedelta(days=1)
        return reset_at

    @callback
    def update_config(self, config: GlobalConfig) -> None:
        """Replace the runtime configuration and notify listeners."""
        self._config = config
        _LOGGER.info(
            "Global configuration updated: "
            "unknown_state_handling=%s fallback_temperature=%.1f "
            "reset_time=%s simulation_mode=%s",
            config.unknown_state_handling,
            config.fallback_temperature,
            config.manual_override_reset_time or "disabled",
            config.simulation_mode,
        )
        self._notify_subscribers()

    @callback
    def update_room_configs(self, room_configs: tuple[RegulationProfileConfig, ...]) -> None:
        """Replace the active room configuration set."""
        self._room_configs = room_configs
        valid_profile_ids = {room.profile_id for room in room_configs}
        for profile_id in tuple(self._manual_overrides):
            if profile_id not in valid_profile_ids:
                self._manual_overrides.pop(profile_id, None)
        self._notify_subscribers()

    @callback
    def subscribe(self, subscriber: Callable[[], None]) -> Callable[[], None]:
        """Register a subscriber for runtime state changes."""
        self._subscribers.add(subscriber)

        @callback
        def unsubscribe() -> None:
            self._subscribers.discard(subscriber)

        return unsubscribe

    @callback
    def _notify_subscribers(self) -> None:
        for subscriber in self._subscribers:
            subscriber()

    def _find_room_config(self, area_id: str) -> RegulationProfileConfig:
        for room_config in self._room_configs:
            if area_id in {
                room_config.area_id,
                room_config.profile_id,
                room_config.primary_climate_entity_id,
            }:
                return room_config
        raise ValueError(f"Unknown Climate Relay area or profile: {area_id!r}")

    def _is_after_daily_reset(self, override: ManualOverride, now: datetime) -> bool:
        reset_time_value = self._config.manual_override_reset_time
        if reset_time_value is None:
            return False
        reset_time = time.fromisoformat(reset_time_value)
        local_now = now.astimezone(dt_util.DEFAULT_TIME_ZONE)
        local_created_at = override.created_at.astimezone(dt_util.DEFAULT_TIME_ZONE)
        reset_at = datetime.combine(local_now.date(), reset_time, tzinfo=dt_util.DEFAULT_TIME_ZONE)
        if reset_at > local_now:
            reset_at -= timedelta(days=1)
        return local_created_at < reset_at <= local_now


def build_global_config(data: dict | None, options: dict | None) -> GlobalConfig:
    """Build the effective runtime configuration from entry data and options."""
    merged = {**(data or {}), **(options or {})}
    return GlobalConfig(
        person_entity_ids=tuple(_normalize_person_entity_ids(merged.get("person_entity_ids"))),
        unknown_state_handling=_normalize_unknown_state_handling(
            merged.get("unknown_state_handling")
        ),
        fallback_temperature=float(
            merged.get("fallback_temperature", DEFAULT_FALLBACK_TEMPERATURE)
        ),
        manual_override_reset_time=_normalize_optional_value(
            merged.get("manual_override_reset_time")
        ),
        simulation_mode=_normalize_bool(merged.get("simulation_mode", False)),
        verbose_logging=_normalize_bool(merged.get("verbose_logging", False)),
    )


def build_room_configs(
    data: dict | None,
    options: dict | None,
    *,
    hass: HomeAssistant | None = None,
) -> tuple[RegulationProfileConfig, ...]:
    """Build configured regulation profiles from entry data and options."""
    merged = {**(data or {}), **(options or {})}
    raw_rooms = merged.get(CONF_ROOMS) or []
    room_configs: list[RegulationProfileConfig] = []

    for raw_room in raw_rooms:
        room = _normalize_room_config(raw_room)
        primary_climate_entity_id = room[CONF_PRIMARY_CLIMATE_ENTITY_ID]
        area_reference = (
            _resolve_area_reference(hass, primary_climate_entity_id)
            if hass is not None
            else AreaReference(area_id=None, area_name=None)
        )
        room_configs.append(
            RegulationProfileConfig(
                profile_id=slugify(primary_climate_entity_id),
                display_name=_resolve_profile_display_name(
                    primary_climate_entity_id,
                    area_reference,
                    legacy_name=room.get("legacy_name"),
                ),
                primary_climate_entity_id=primary_climate_entity_id,
                area_id=area_reference.area_id,
                area_name=area_reference.area_name,
                humidity_entity_id=room[CONF_HUMIDITY_ENTITY_ID],
                window_entity_id=room[CONF_WINDOW_ENTITY_ID],
                window_action_type=WindowActionType(room[CONF_WINDOW_ACTION_TYPE]),
                window_custom_temperature=room[CONF_WINDOW_CUSTOM_TEMPERATURE],
                window_open_delay_seconds=room[CONF_WINDOW_OPEN_DELAY_SECONDS],
                home_target=RoomTarget(
                    mode="absolute",
                    temperature=room[CONF_HOME_TARGET_TEMPERATURE],
                ),
                away_target=RoomTarget(
                    mode=room[CONF_AWAY_TARGET_TYPE],
                    temperature=room[CONF_AWAY_TARGET_TEMPERATURE],
                ),
                schedule=room[CONF_SCHEDULE],
            )
        )

    return tuple(room_configs)


def _normalize_bool(raw_value: object) -> bool:
    """Normalize persisted or wrapped booleans from Home Assistant options."""
    raw_value = _normalize_optional_value(raw_value)
    if isinstance(raw_value, bool):
        return raw_value
    if isinstance(raw_value, str):
        normalized = raw_value.strip().lower()
        if normalized in {"true", "on", "yes", "1"}:
            return True
        if normalized in {"false", "off", "no", "0", ""}:
            return False
    return bool(raw_value)


def _normalize_person_entity_ids(raw_value: object) -> list[str]:
    """Normalize persisted person-entity selectors to plain entity IDs."""
    raw_value = _normalize_optional_value(raw_value)
    if raw_value is None:
        return []
    if isinstance(raw_value, str):
        return [raw_value]
    if isinstance(raw_value, dict):
        entity_id = raw_value.get("entity_id") or raw_value.get("value")
        if isinstance(entity_id, str):
            return [entity_id]
        raw_value = entity_id

    normalized: list[str] = []
    for item in raw_value:
        item = _normalize_optional_value(item)
        if isinstance(item, str):
            normalized.append(item)
            continue
        if isinstance(item, dict):
            entity_id = item.get("entity_id") or item.get("value")
            if isinstance(entity_id, str):
                normalized.append(entity_id)
                continue
        raise ValueError(f"Unsupported person entity selector value: {item!r}")
    return normalized


def _normalize_unknown_state_handling(raw_value: object) -> str:
    """Normalize persisted unknown-state handling values."""
    normalized = _normalize_optional_value(raw_value)
    if isinstance(normalized, str) and normalized:
        return normalized
    return DEFAULT_UNKNOWN_STATE_HANDLING


def _normalize_room_config(raw_value: object) -> MappingProxyType[str, object]:
    """Normalize one persisted room configuration payload."""
    if not isinstance(raw_value, dict):
        raise ValueError(f"Unsupported room configuration: {raw_value!r}")

    primary_climate_entity_id = _normalize_entity_id(
        raw_value.get(CONF_PRIMARY_CLIMATE_ENTITY_ID),
        required=True,
    )
    legacy_name = str(_normalize_optional_value(raw_value.get("name")) or "").strip() or None

    normalized = {
        CONF_PRIMARY_CLIMATE_ENTITY_ID: primary_climate_entity_id,
        CONF_HUMIDITY_ENTITY_ID: _normalize_entity_id(
            raw_value.get(CONF_HUMIDITY_ENTITY_ID),
            required=False,
        ),
        CONF_WINDOW_ENTITY_ID: _normalize_entity_id(
            raw_value.get(CONF_WINDOW_ENTITY_ID),
            required=False,
        ),
        CONF_WINDOW_ACTION_TYPE: _normalize_window_action_type(
            raw_value.get(CONF_WINDOW_ACTION_TYPE)
        ),
        CONF_WINDOW_CUSTOM_TEMPERATURE: _normalize_optional_float(
            raw_value.get(CONF_WINDOW_CUSTOM_TEMPERATURE)
        ),
        CONF_WINDOW_OPEN_DELAY_SECONDS: _normalize_non_negative_int(
            raw_value.get(CONF_WINDOW_OPEN_DELAY_SECONDS),
            default=DEFAULT_WINDOW_OPEN_DELAY_SECONDS,
        ),
        CONF_HOME_TARGET_TEMPERATURE: float(raw_value.get(CONF_HOME_TARGET_TEMPERATURE)),
        CONF_AWAY_TARGET_TYPE: _normalize_target_type(raw_value.get(CONF_AWAY_TARGET_TYPE)),
        CONF_AWAY_TARGET_TEMPERATURE: float(raw_value.get(CONF_AWAY_TARGET_TEMPERATURE)),
        CONF_SCHEDULE: _normalize_schedule(raw_value),
        "legacy_name": legacy_name,
    }
    return MappingProxyType(normalized)


def _normalize_schedule(raw_value: dict[str, object]) -> RoomSchedule:
    """Normalize the persisted schedule payload for one room."""
    raw_schedule = _normalize_optional_value(raw_value.get(CONF_SCHEDULE))
    if isinstance(raw_schedule, dict):
        raw_home_start = raw_schedule.get(CONF_SCHEDULE_HOME_START)
        raw_home_end = raw_schedule.get(CONF_SCHEDULE_HOME_END)
    else:
        raw_home_start = raw_value.get(CONF_SCHEDULE_HOME_START)
        raw_home_end = raw_value.get(CONF_SCHEDULE_HOME_END)

    return build_daily_home_window_schedule(
        _normalize_time(raw_home_start, default=DEFAULT_SCHEDULE_HOME_START),
        _normalize_time(raw_home_end, default=DEFAULT_SCHEDULE_HOME_END),
    )


def _normalize_time(raw_value: object, *, default: str) -> time:
    """Normalize a time selector value."""
    normalized = _normalize_optional_value(raw_value)
    value = str(normalized or default).strip()
    return time.fromisoformat(value)


def _normalize_entity_id(raw_value: object, *, required: bool) -> str | None:
    """Normalize entity selectors to plain entity IDs."""
    normalized = _normalize_optional_value(raw_value)
    if isinstance(normalized, dict):
        normalized = normalized.get("entity_id") or normalized.get("value")
    if normalized in (None, ""):
        if required:
            raise ValueError("Required entity_id is missing")
        return None
    if not isinstance(normalized, str):
        raise ValueError(f"Unsupported entity selector value: {raw_value!r}")
    return normalized


def _normalize_target_type(raw_value: object) -> str:
    """Normalize the away-target mode."""
    normalized = _normalize_optional_value(raw_value)
    if isinstance(normalized, str) and normalized in {"absolute", "relative"}:
        return normalized
    return DEFAULT_AWAY_TARGET_TYPE


def _normalize_window_action_type(raw_value: object) -> str:
    """Normalize the configured window action type."""
    normalized = _normalize_optional_value(raw_value)
    if isinstance(normalized, str) and normalized in {action.value for action in WindowActionType}:
        return normalized
    return DEFAULT_WINDOW_ACTION_TYPE


def _normalize_optional_float(raw_value: object) -> float | None:
    """Normalize an optional float selector value."""
    normalized = _normalize_optional_value(raw_value)
    if normalized in (None, ""):
        return None
    return float(normalized)


def _normalize_non_negative_int(raw_value: object, *, default: int) -> int:
    """Normalize a non-negative integer selector value."""
    normalized = _normalize_optional_value(raw_value)
    if normalized in (None, ""):
        return default
    value = int(normalized)
    return value if value >= 0 else default


def _normalize_optional_value(raw_value: object) -> object:
    """Unwrap common selector wrappers from persisted options."""
    if isinstance(raw_value, dict) and "value" in raw_value:
        return raw_value["value"]
    return raw_value


def _resolve_profile_display_name(
    primary_climate_entity_id: str,
    area_reference: AreaReference,
    *,
    legacy_name: object,
) -> str:
    """Resolve a user-facing profile label from HA-native context."""
    if area_reference.area_name:
        return area_reference.area_name
    if isinstance(legacy_name, str) and legacy_name:
        return legacy_name

    object_id = primary_climate_entity_id.partition(".")[2]
    return object_id.replace("_", " ").title() or primary_climate_entity_id


def _resolve_area_reference(
    hass: HomeAssistant,
    primary_climate_entity_id: str,
) -> AreaReference:
    """Resolve the Home Assistant area for a primary climate entity."""
    entity_registry = er.async_get(hass)
    device_registry = dr.async_get(hass)
    area_registry = ar.async_get(hass)

    resolved_entity_id = er.async_resolve_entity_id(entity_registry, primary_climate_entity_id)
    entity_entry = entity_registry.async_get(resolved_entity_id)
    if entity_entry is None:
        return AreaReference(area_id=None, area_name=None)

    area_id = entity_entry.area_id
    if area_id is None and entity_entry.device_id is not None:
        device_entry = device_registry.async_get(entity_entry.device_id)
        if device_entry is not None:
            area_id = device_entry.area_id

    if area_id is None:
        return AreaReference(area_id=None, area_name=None)

    area_entry = area_registry.async_get_area(area_id)
    return AreaReference(
        area_id=area_id,
        area_name=area_entry.name if area_entry is not None else None,
    )
