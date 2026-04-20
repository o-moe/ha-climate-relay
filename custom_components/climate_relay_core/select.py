"""Select entity platform for ClimateRelayCore."""

from __future__ import annotations

from typing import Final

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import (
    ATTR_EFFECTIVE_PRESENCE,
    ATTR_FALLBACK_TEMPERATURE,
    ATTR_MANUAL_OVERRIDE_RESET_TIME,
    ATTR_SIMULATION_MODE,
    ATTR_UNKNOWN_STATE_HANDLING,
    DOMAIN,
)
from .domain import GlobalMode
from .runtime import GlobalRuntime

ENTITY_OPTIONS: Final = [mode.value for mode in GlobalMode]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the global mode select entity."""
    runtime: GlobalRuntime = hass.data[DOMAIN][entry.entry_id]["runtime"]
    async_add_entities([ClimateRelayCoreGlobalModeSelect(entry.entry_id, entry.title, runtime)])


class ClimateRelayCoreGlobalModeSelect(SelectEntity):
    """Global mode control surface exposed to Home Assistant."""

    _attr_has_entity_name = True
    _attr_name = "Global Mode"
    _attr_options = ENTITY_OPTIONS
    _attr_should_poll = False

    def __init__(self, entry_id: str, title: str, runtime: GlobalRuntime) -> None:
        self._attr_unique_id = f"{entry_id}_global_mode"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry_id)},
            "name": title,
        }
        self._runtime = runtime

    @property
    def current_option(self) -> str:
        """Return the current selected option."""
        return self._runtime.global_mode.value

    @property
    def extra_state_attributes(self) -> dict[str, str | float | None]:
        """Expose sparse diagnostics relevant to global mode handling."""
        return {
            ATTR_EFFECTIVE_PRESENCE: self._runtime.effective_presence.value,
            ATTR_UNKNOWN_STATE_HANDLING: self._runtime.config.unknown_state_handling,
            ATTR_FALLBACK_TEMPERATURE: self._runtime.config.fallback_temperature,
            ATTR_MANUAL_OVERRIDE_RESET_TIME: self._runtime.config.manual_override_reset_time,
            ATTR_SIMULATION_MODE: "on" if self._runtime.config.simulation_mode else "off",
        }

    async def async_added_to_hass(self) -> None:
        """Register for runtime updates after entity creation."""
        self.async_on_remove(self._runtime.subscribe(self._handle_runtime_update))

    async def async_select_option(self, option: str) -> None:
        """Apply a new global mode selected by the user."""
        await self._runtime.async_set_global_mode(GlobalMode(option), source="select")

    @callback
    def _handle_runtime_update(self) -> None:
        self.async_write_ha_state()
