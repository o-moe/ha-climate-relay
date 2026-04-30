"""Climate entity platform for Climate Relay regulation entities."""

from __future__ import annotations

import logging
from typing import Final

from homeassistant.components.climate import ClimateEntity, HVACMode
from homeassistant.components.climate.const import SERVICE_SET_TEMPERATURE
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTemperature
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.event import (
    async_track_point_in_utc_time,
    async_track_state_change_event,
)
from homeassistant.util import dt as dt_util

from .const import (
    ATTR_ACTIVE_CONTROL_CONTEXT,
    ATTR_DEGRADATION_STATUS,
    ATTR_HUMIDITY_ENTITY_ID,
    ATTR_NEXT_CHANGE_AT,
    ATTR_OVERRIDE_ENDS_AT,
    ATTR_PRIMARY_CLIMATE_ENTITY_ID,
    ATTR_WINDOW_ENTITY_ID,
    DOMAIN,
)
from .domain import EffectivePresence, evaluate_schedule, resolve_room_target
from .runtime import GlobalRuntime, RegulationProfileConfig

ATTR_TEMPERATURE: Final = "temperature"
ATTR_CURRENT_TEMPERATURE: Final = "current_temperature"
ATTR_HVAC_MODES: Final = "hvac_modes"
DEGRADATION_OPTIONAL_SENSOR_UNAVAILABLE: Final = "optional_sensor_unavailable"
DEGRADATION_REQUIRED_COMPONENT_FALLBACK: Final = "required_component_fallback"
ACTIVE_CONTEXT_FALLBACK: Final = "fallback"
ACTIVE_CONTEXT_MANUAL_OVERRIDE: Final = "manual_override"
ACTIVE_CONTEXT_SCHEDULE: Final = "schedule"
_LOGGER: Final = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up configured climate relay entities."""
    stored_entry = hass.data[DOMAIN][entry.entry_id]
    runtime: GlobalRuntime = stored_entry["runtime"]
    room_configs: tuple[RegulationProfileConfig, ...] = stored_entry["room_configs"]
    async_add_entities(
        [
            ClimateRelayCoreRoomClimateEntity(entry.entry_id, hass, runtime, room)
            for room in room_configs
        ]
    )


class ClimateRelayCoreRoomClimateEntity(ClimateEntity):
    """Primary-climate-anchored climate surface exposed by the integration."""

    _attr_has_entity_name = True
    _attr_should_poll = False
    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_target_temperature_step = 0.5

    def __init__(
        self,
        entry_id: str,
        hass: HomeAssistant,
        runtime: GlobalRuntime,
        room_config: RegulationProfileConfig,
    ) -> None:
        self.hass = hass
        self._runtime = runtime
        self._room_config = room_config
        self._attr_name = room_config.display_name
        self._attr_unique_id = f"{entry_id}_profile_{room_config.profile_id}"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, f"{entry_id}_{room_config.profile_id}")},
            "name": room_config.display_name,
        }
        if room_config.area_name:
            self._attr_device_info["suggested_area"] = room_config.area_name
        self._last_applied_target_temperature: float | None = None
        self._cancel_scheduled_update = None

    async def async_added_to_hass(self) -> None:
        """Register for upstream runtime and state changes."""
        self.async_on_remove(self._runtime.subscribe(self._handle_runtime_update))
        tracked_entities = [self._room_config.primary_climate_entity_id]
        if self._room_config.humidity_entity_id:
            tracked_entities.append(self._room_config.humidity_entity_id)
        if self._room_config.window_entity_id:
            tracked_entities.append(self._room_config.window_entity_id)
        self.async_on_remove(
            async_track_state_change_event(
                self.hass,
                tracked_entities,
                self._handle_source_state_change,
            )
        )
        self._schedule_next_update()
        await self._async_apply_effective_target(source="entity_added")

    @property
    def hvac_mode(self) -> HVACMode:
        """Return the current HVAC mode."""
        primary_state = self._primary_state
        if primary_state is None:
            return HVACMode.HEAT

        state = str(primary_state.state)
        try:
            return HVACMode(state)
        except ValueError:
            return HVACMode.HEAT

    @property
    def hvac_modes(self) -> list[HVACMode]:
        """Return supported HVAC modes."""
        primary_state = self._primary_state
        if primary_state is None:
            return [HVACMode.HEAT]

        modes = []
        for value in primary_state.attributes.get(ATTR_HVAC_MODES, [HVACMode.HEAT]):
            try:
                modes.append(HVACMode(value))
            except ValueError:
                continue
        return modes or [HVACMode.HEAT]

    @property
    def target_temperature(self) -> float:
        """Return the resolved profile target temperature."""
        manual_override = self._manual_override
        if manual_override is not None:
            return manual_override.target_temperature

        if self._primary_state is None:
            return self._runtime.config.fallback_temperature

        schedule_target = self._schedule_target
        if schedule_target is not None:
            return resolve_room_target(
                EffectivePresence.HOME if schedule_target == "home" else EffectivePresence.AWAY,
                home_target=self._room_config.home_target,
                away_target=self._room_config.away_target,
            )

        return resolve_room_target(
            self._runtime.effective_presence,
            home_target=self._room_config.home_target,
            away_target=self._room_config.away_target,
        )

    @property
    def current_temperature(self) -> float | None:
        """Return the upstream current temperature when available."""
        primary_state = self._primary_state
        if primary_state is None:
            return None
        value = primary_state.attributes.get(ATTR_CURRENT_TEMPERATURE)
        return float(value) if isinstance(value, int | float) else None

    @property
    def current_humidity(self) -> float | None:
        """Return humidity from the optional source sensor."""
        humidity_state = self._humidity_state
        if humidity_state is None:
            return None
        try:
            return float(humidity_state.state)
        except TypeError, ValueError:
            return None

    @property
    def extra_state_attributes(self) -> dict[str, str]:
        """Expose sparse explanatory profile context."""
        attrs = {
            ATTR_ACTIVE_CONTROL_CONTEXT: self._active_control_context,
            ATTR_PRIMARY_CLIMATE_ENTITY_ID: self._room_config.primary_climate_entity_id,
        }
        if self._room_config.humidity_entity_id:
            attrs[ATTR_HUMIDITY_ENTITY_ID] = self._room_config.humidity_entity_id
        if self._room_config.window_entity_id:
            attrs[ATTR_WINDOW_ENTITY_ID] = self._room_config.window_entity_id
        next_change_at = self._next_change_at
        if next_change_at is not None:
            attrs[ATTR_NEXT_CHANGE_AT] = next_change_at.isoformat()
        manual_override = self._manual_override
        if manual_override is not None and manual_override.ends_at is not None:
            attrs[ATTR_OVERRIDE_ENDS_AT] = manual_override.ends_at.isoformat()
        if self._degradation_status is not None:
            attrs[ATTR_DEGRADATION_STATUS] = self._degradation_status
        return attrs

    @property
    def _primary_state(self):  # type: ignore[no-untyped-def]
        return self.hass.states.get(self._room_config.primary_climate_entity_id)

    @property
    def _humidity_state(self):  # type: ignore[no-untyped-def]
        if not self._room_config.humidity_entity_id:
            return None
        return self.hass.states.get(self._room_config.humidity_entity_id)

    @property
    def _window_state(self):  # type: ignore[no-untyped-def]
        if not self._room_config.window_entity_id:
            return None
        return self.hass.states.get(self._room_config.window_entity_id)

    @property
    def _active_control_context(self) -> str:
        if self._manual_override is not None:
            return ACTIVE_CONTEXT_MANUAL_OVERRIDE
        if self._primary_state is None:
            return ACTIVE_CONTEXT_FALLBACK
        return ACTIVE_CONTEXT_SCHEDULE

    @property
    def _manual_override(self):  # type: ignore[no-untyped-def]
        return self._runtime.manual_override_for_profile(self._room_config.profile_id)

    @property
    def _schedule_evaluation(self):  # type: ignore[no-untyped-def]
        if self._primary_state is None:
            return None
        return evaluate_schedule(
            self._room_config.schedule,
            dt_util.now(),
            dt_util.DEFAULT_TIME_ZONE,
        )

    @property
    def _schedule_target(self) -> str | None:
        if self._runtime.effective_presence is EffectivePresence.AWAY:
            return "away"
        evaluation = self._schedule_evaluation
        return None if evaluation is None else evaluation.target

    @property
    def _next_change_at(self):  # type: ignore[no-untyped-def]
        if self._manual_override is not None:
            return None
        if self._runtime.effective_presence is EffectivePresence.AWAY:
            return None
        evaluation = self._schedule_evaluation
        return None if evaluation is None else evaluation.next_change_at

    @property
    def _degradation_status(self) -> str | None:
        if self._primary_state is None:
            return DEGRADATION_REQUIRED_COMPONENT_FALLBACK
        if _is_unavailable(self._humidity_state) or _is_unavailable(self._window_state):
            return DEGRADATION_OPTIONAL_SENSOR_UNAVAILABLE
        return None

    @callback
    def _handle_runtime_update(self) -> None:
        self.async_write_ha_state()
        self._schedule_next_update()
        self.hass.async_create_task(self._async_apply_effective_target(source="runtime_update"))

    @callback
    def _handle_source_state_change(self, _event) -> None:  # type: ignore[no-untyped-def]
        self.async_write_ha_state()
        self.hass.async_create_task(self._async_apply_effective_target(source="source_update"))

    @callback
    def _handle_schedule_update(self, _now) -> None:  # type: ignore[no-untyped-def]
        self.async_write_ha_state()
        self._schedule_next_update()
        self.hass.async_create_task(self._async_apply_effective_target(source="schedule"))

    @callback
    def _schedule_next_update(self) -> None:
        if self._cancel_scheduled_update is not None:
            self._cancel_scheduled_update()
            self._cancel_scheduled_update = None
        next_update_at = self._next_update_at
        if next_update_at is None:
            return
        self._cancel_scheduled_update = async_track_point_in_utc_time(
            self.hass,
            self._handle_schedule_update,
            dt_util.as_utc(next_update_at),
        )
        self.async_on_remove(self._cancel_scheduled_update)

    @property
    def _next_update_at(self):  # type: ignore[no-untyped-def]
        manual_override = self._manual_override
        if manual_override is not None:
            candidates = [
                candidate
                for candidate in (
                    manual_override.ends_at,
                    self._runtime.next_manual_override_reset_at(manual_override),
                )
                if candidate is not None
            ]
            return min(candidates) if candidates else None
        return self._next_change_at

    async def _async_apply_effective_target(self, *, source: str) -> None:
        if self._primary_state is None:
            return

        target_temperature = self.target_temperature
        if self._last_applied_target_temperature == target_temperature:
            return
        self._last_applied_target_temperature = target_temperature

        payload = {
            "entity_id": self._room_config.primary_climate_entity_id,
            ATTR_TEMPERATURE: target_temperature,
        }
        if self._runtime.config.simulation_mode:
            _LOGGER.info(
                "Simulation mode suppressed climate.set_temperature for %s to %.1f via %s",
                self._room_config.primary_climate_entity_id,
                target_temperature,
                source,
            )
            return

        await self.hass.services.async_call(
            "climate",
            SERVICE_SET_TEMPERATURE,
            payload,
            blocking=False,
        )


def _is_unavailable(state) -> bool:  # type: ignore[no-untyped-def]
    """Return whether an optional source state should be treated as unavailable."""
    if state is None:
        return False
    return str(state.state) in {"unknown", "unavailable"}
