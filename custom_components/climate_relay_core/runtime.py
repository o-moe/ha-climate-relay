"""Runtime state and global configuration handling."""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from types import MappingProxyType
from typing import Final

from homeassistant.core import HomeAssistant, callback
from homeassistant.util import slugify

from .const import (
    CONF_AWAY_TARGET_TEMPERATURE,
    CONF_AWAY_TARGET_TYPE,
    CONF_HOME_TARGET_TEMPERATURE,
    CONF_HUMIDITY_ENTITY_ID,
    CONF_PRIMARY_CLIMATE_ENTITY_ID,
    CONF_ROOM_NAME,
    CONF_ROOMS,
    CONF_WINDOW_ENTITY_ID,
    DEFAULT_AWAY_TARGET_TYPE,
    DEFAULT_FALLBACK_TEMPERATURE,
    DEFAULT_UNKNOWN_STATE_HANDLING,
)
from .domain import (
    EffectivePresence,
    GlobalMode,
    RoomTarget,
    UnknownStateHandling,
    resolve_presence_mode,
)

_LOGGER: Final = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class GlobalConfig:
    """Global integration configuration for iteration 1.1."""

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
class RoomConfig:
    """Single-room configuration for iteration 1.2."""

    room_id: str
    name: str
    primary_climate_entity_id: str
    humidity_entity_id: str | None
    window_entity_id: str | None
    home_target: RoomTarget
    away_target: RoomTarget


class GlobalRuntime:
    """In-memory runtime model for the integration-wide global state."""

    def __init__(self, hass: HomeAssistant, config: GlobalConfig) -> None:
        self._hass = hass
        self._config = config
        self._global_mode = GlobalMode.AUTO
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


def build_room_configs(data: dict | None, options: dict | None) -> tuple[RoomConfig, ...]:
    """Build configured rooms from entry data and options."""
    merged = {**(data or {}), **(options or {})}
    raw_rooms = merged.get(CONF_ROOMS) or []
    room_configs: list[RoomConfig] = []

    for raw_room in raw_rooms:
        room = _normalize_room_config(raw_room)
        room_configs.append(
            RoomConfig(
                room_id=slugify(room[CONF_ROOM_NAME]),
                name=room[CONF_ROOM_NAME],
                primary_climate_entity_id=room[CONF_PRIMARY_CLIMATE_ENTITY_ID],
                humidity_entity_id=room[CONF_HUMIDITY_ENTITY_ID],
                window_entity_id=room[CONF_WINDOW_ENTITY_ID],
                home_target=RoomTarget(
                    mode="absolute",
                    temperature=room[CONF_HOME_TARGET_TEMPERATURE],
                ),
                away_target=RoomTarget(
                    mode=room[CONF_AWAY_TARGET_TYPE],
                    temperature=room[CONF_AWAY_TARGET_TEMPERATURE],
                ),
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

    name = str(_normalize_optional_value(raw_value.get(CONF_ROOM_NAME)) or "").strip()
    primary_climate_entity_id = _normalize_entity_id(
        raw_value.get(CONF_PRIMARY_CLIMATE_ENTITY_ID),
        required=True,
    )

    normalized = {
        CONF_ROOM_NAME: name,
        CONF_PRIMARY_CLIMATE_ENTITY_ID: primary_climate_entity_id,
        CONF_HUMIDITY_ENTITY_ID: _normalize_entity_id(
            raw_value.get(CONF_HUMIDITY_ENTITY_ID),
            required=False,
        ),
        CONF_WINDOW_ENTITY_ID: _normalize_entity_id(
            raw_value.get(CONF_WINDOW_ENTITY_ID),
            required=False,
        ),
        CONF_HOME_TARGET_TEMPERATURE: float(raw_value.get(CONF_HOME_TARGET_TEMPERATURE)),
        CONF_AWAY_TARGET_TYPE: _normalize_target_type(raw_value.get(CONF_AWAY_TARGET_TYPE)),
        CONF_AWAY_TARGET_TEMPERATURE: float(raw_value.get(CONF_AWAY_TARGET_TEMPERATURE)),
    }
    return MappingProxyType(normalized)


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


def _normalize_optional_value(raw_value: object) -> object:
    """Unwrap common selector wrappers from persisted options."""
    if isinstance(raw_value, dict) and "value" in raw_value:
        return raw_value["value"]
    return raw_value
