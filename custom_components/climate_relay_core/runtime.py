"""Runtime state and global configuration handling."""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from typing import Final

from homeassistant.core import HomeAssistant, callback

from .const import (
    DEFAULT_FALLBACK_TEMPERATURE,
    DEFAULT_UNKNOWN_STATE_HANDLING,
)
from .domain import EffectivePresence, GlobalMode, UnknownStateHandling, resolve_presence_mode

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
        person_entity_ids=tuple(merged.get("person_entity_ids", ())),
        unknown_state_handling=merged.get(
            "unknown_state_handling",
            DEFAULT_UNKNOWN_STATE_HANDLING,
        ),
        fallback_temperature=float(
            merged.get("fallback_temperature", DEFAULT_FALLBACK_TEMPERATURE)
        ),
        manual_override_reset_time=merged.get("manual_override_reset_time"),
        simulation_mode=bool(merged.get("simulation_mode", False)),
        verbose_logging=bool(merged.get("verbose_logging", False)),
    )
