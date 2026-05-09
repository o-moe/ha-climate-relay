"""Climate entity platform for Climate Relay regulation entities."""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import Final

from homeassistant.components.climate import ClimateEntity, ClimateEntityFeature, HVACMode
from homeassistant.components.climate.const import (
    ATTR_MIN_TEMP,
    ATTR_PRESET_MODES,
    SERVICE_SET_HVAC_MODE,
    SERVICE_SET_PRESET_MODE,
    SERVICE_SET_TEMPERATURE,
)
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
from .domain import (
    ClimateCapabilities,
    EffectiveTarget,
    resolve_regulation_state,
    resolve_window_action,
)
from .runtime import GlobalRuntime, RegulationProfileConfig

ATTR_TEMPERATURE: Final = "temperature"
ATTR_CURRENT_TEMPERATURE: Final = "current_temperature"
ATTR_HVAC_MODES: Final = "hvac_modes"
ATTR_HVAC_MODE: Final = "hvac_mode"
ATTR_PRESET_MODE: Final = "preset_mode"
DEGRADATION_OPTIONAL_SENSOR_UNAVAILABLE: Final = "optional_sensor_unavailable"
DEGRADATION_REQUIRED_COMPONENT_FALLBACK: Final = "required_component_fallback"
ACTIVE_CONTEXT_FALLBACK: Final = "fallback"
ACTIVE_CONTEXT_MANUAL_OVERRIDE: Final = "manual_override"
ACTIVE_CONTEXT_SCHEDULE: Final = "schedule"
ACTIVE_CONTEXT_WINDOW_OVERRIDE: Final = "window_override"
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
    _attr_supported_features = ClimateEntityFeature.TARGET_TEMPERATURE

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
        self._last_applied_effective_target: EffectiveTarget | None = None
        self._cancel_scheduled_update = None
        self._cancel_window_open_delay = None
        self._window_override_active = False

    async def async_added_to_hass(self) -> None:
        """Register for upstream runtime and state changes."""
        self.async_on_remove(
            self._runtime.subscribe_for_profile(
                self._room_config.profile_id,
                self._handle_runtime_update,
            )
        )
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
        self.async_on_remove(self._cancel_current_scheduled_update)
        self.async_on_remove(self._cancel_current_window_open_delay)
        self._schedule_next_update()
        await self._async_apply_effective_target(source="entity_added")

    @property
    def hvac_mode(self) -> HVACMode:
        """Return the current HVAC mode."""
        if not self._primary_available:
            return HVACMode.HEAT

        primary_state = self._primary_state
        state = str(primary_state.state)
        try:
            return HVACMode(state)
        except ValueError:
            return HVACMode.HEAT

    @property
    def hvac_modes(self) -> list[HVACMode]:
        """Return supported HVAC modes."""
        if not self._primary_available:
            return [HVACMode.HEAT]

        primary_state = self._primary_state
        modes = []
        for value in primary_state.attributes.get(ATTR_HVAC_MODES, [HVACMode.HEAT]):
            try:
                modes.append(HVACMode(value))
            except ValueError:
                continue
        return modes or [HVACMode.HEAT]

    @property
    def target_temperature(self) -> float | None:
        """Return the resolved profile target temperature."""
        return self._resolution.target_temperature

    @property
    def current_temperature(self) -> float | None:
        """Return the upstream current temperature when available."""
        if not self._primary_available:
            return None
        primary_state = self._primary_state
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
        resolution = self._resolution
        next_change_at = resolution.next_change_at
        if next_change_at is not None:
            attrs[ATTR_NEXT_CHANGE_AT] = next_change_at.isoformat()
        if resolution.override_ends_at is not None:
            attrs[ATTR_OVERRIDE_ENDS_AT] = resolution.override_ends_at.isoformat()
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
        return self._resolution.active_context

    @property
    def _manual_override(self):  # type: ignore[no-untyped-def]
        return self._runtime.manual_override_for_profile(self._room_config.profile_id)

    @property
    def _resolution(self):  # type: ignore[no-untyped-def]
        return resolve_regulation_state(
            home_target=self._room_config.home_target,
            away_target=self._room_config.away_target,
            schedule=self._room_config.schedule,
            effective_presence=self._runtime.effective_presence,
            manual_override=self._manual_override,
            window_target=self._window_target,
            primary_available=self._primary_available,
            fallback_temperature=self._runtime.config.fallback_temperature,
            last_valid_target_temperature=self._last_applied_target_temperature,
            now=dt_util.now(),
            timezone=dt_util.DEFAULT_TIME_ZONE,
        )

    @property
    def _degradation_status(self) -> str | None:
        if not self._primary_available:
            return DEGRADATION_REQUIRED_COMPONENT_FALLBACK
        if _is_unavailable(self._humidity_state) or _is_unavailable(self._window_state):
            return DEGRADATION_OPTIONAL_SENSOR_UNAVAILABLE
        return None

    @property
    def _primary_available(self) -> bool:
        return self._primary_state is not None and not _is_unavailable(self._primary_state)

    @property
    def _window_target(self) -> EffectiveTarget | None:
        if not self._window_override_active or self._primary_state is None:
            return None
        return resolve_window_action(
            self._room_config.window_action_type,
            self._climate_capabilities,
            custom_temperature=self._room_config.window_custom_temperature,
        )

    @property
    def _climate_capabilities(self) -> ClimateCapabilities:
        primary_state = self._primary_state
        attributes = primary_state.attributes if primary_state is not None else {}
        hvac_modes = {str(mode) for mode in attributes.get(ATTR_HVAC_MODES, [])}
        preset_modes = {str(mode) for mode in attributes.get(ATTR_PRESET_MODES, [])}
        min_temperature = attributes.get(ATTR_MIN_TEMP, 7.0)
        if not isinstance(min_temperature, int | float):
            min_temperature = 7.0
        return ClimateCapabilities(
            supports_off=HVACMode.OFF.value in hvac_modes,
            supports_preset_frost="frost_protection" in preset_modes,
            min_temperature=float(min_temperature),
        )

    @callback
    def _handle_runtime_update(self) -> None:
        self.async_write_ha_state()
        self._schedule_next_update()
        self.hass.async_create_task(self._async_apply_effective_target(source="runtime_update"))

    @callback
    def _handle_source_state_change(self, _event) -> None:  # type: ignore[no-untyped-def]
        if self._is_window_state_change(_event):
            self._handle_window_state_change(_event.data.get("new_state"))
        self.async_write_ha_state()
        self.hass.async_create_task(self._async_apply_effective_target(source="source_update"))

    @callback
    def _handle_schedule_update(self, _now) -> None:  # type: ignore[no-untyped-def]
        self.async_write_ha_state()
        self._schedule_next_update()
        self.hass.async_create_task(self._async_apply_effective_target(source="schedule"))

    @callback
    def _schedule_next_update(self) -> None:
        self._cancel_current_scheduled_update()
        next_update_at = self._next_update_at
        if next_update_at is None:
            return
        self._cancel_scheduled_update = async_track_point_in_utc_time(
            self.hass,
            self._handle_schedule_update,
            dt_util.as_utc(next_update_at),
        )

    @callback
    def _cancel_current_scheduled_update(self) -> None:
        if self._cancel_scheduled_update is not None:
            self._cancel_scheduled_update()
            self._cancel_scheduled_update = None

    @callback
    def _cancel_current_window_open_delay(self) -> None:
        if self._cancel_window_open_delay is not None:
            self._cancel_window_open_delay()
            self._cancel_window_open_delay = None

    @callback
    def _is_window_state_change(self, event) -> bool:  # type: ignore[no-untyped-def]
        return (
            self._room_config.window_entity_id is not None
            and getattr(event, "data", {}).get("entity_id") == self._room_config.window_entity_id
        )

    @callback
    def _handle_window_state_change(self, new_state) -> None:  # type: ignore[no-untyped-def]
        if _is_open_window_state(new_state):
            self._schedule_window_open_activation()
            return

        self._cancel_current_window_open_delay()
        if self._window_override_active:
            self._window_override_active = False

    @callback
    def _schedule_window_open_activation(self) -> None:
        self._cancel_current_window_open_delay()
        delay_seconds = self._room_config.window_open_delay_seconds
        if delay_seconds <= 0:
            self._activate_window_override(None)
            return
        self._cancel_window_open_delay = async_track_point_in_utc_time(
            self.hass,
            self._activate_window_override,
            dt_util.as_utc(dt_util.now() + timedelta(seconds=delay_seconds)),
        )

    @callback
    def _activate_window_override(self, _now) -> None:  # type: ignore[no-untyped-def]
        self._cancel_window_open_delay = None
        if not _is_open_window_state(self._window_state):
            return
        self._window_override_active = True
        self.async_write_ha_state()
        self.hass.async_create_task(self._async_apply_effective_target(source="window_open"))

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
        return self._resolution.next_change_at

    async def _async_apply_effective_target(self, *, source: str) -> None:
        if not self._primary_available:
            _LOGGER.warning(
                "Required climate component unavailable for %s; "
                "resolved fallback target %.1f via %s and skipped device write",
                self._room_config.primary_climate_entity_id,
                self._resolution.target_temperature,
                source,
            )
            return

        effective_target = self._resolution.effective_target
        if self._last_applied_effective_target == effective_target:
            return
        if self._runtime.config.simulation_mode:
            _LOGGER.info(
                "Simulation mode suppressed climate write for %s to %s via %s",
                self._room_config.primary_climate_entity_id,
                effective_target,
                source,
            )
            return

        try:
            await self._async_call_climate_services(effective_target)
        except Exception:
            _LOGGER.exception(
                "Failed to apply climate target for %s to %s via %s",
                self._room_config.primary_climate_entity_id,
                effective_target,
                source,
            )
            raise
        self._last_applied_effective_target = effective_target
        self._last_applied_target_temperature = effective_target.target_temperature

    async def _async_call_climate_services(self, target: EffectiveTarget) -> None:
        """Apply a resolved target using HA-native climate services."""
        entity_id = self._room_config.primary_climate_entity_id
        if target.hvac_mode is not None and target.hvac_mode != self.hvac_mode.value:
            await self.hass.services.async_call(
                "climate",
                SERVICE_SET_HVAC_MODE,
                {"entity_id": entity_id, ATTR_HVAC_MODE: target.hvac_mode},
                blocking=True,
            )
        if target.preset_mode is not None:
            await self.hass.services.async_call(
                "climate",
                SERVICE_SET_PRESET_MODE,
                {"entity_id": entity_id, ATTR_PRESET_MODE: target.preset_mode},
                blocking=True,
            )
        if target.target_temperature is not None:
            await self.hass.services.async_call(
                "climate",
                SERVICE_SET_TEMPERATURE,
                {"entity_id": entity_id, ATTR_TEMPERATURE: target.target_temperature},
                blocking=True,
            )


def _is_unavailable(state) -> bool:  # type: ignore[no-untyped-def]
    """Return whether an optional source state should be treated as unavailable."""
    if state is None:
        return False
    return str(state.state) in {"unknown", "unavailable"}


def _is_open_window_state(state) -> bool:  # type: ignore[no-untyped-def]
    """Return whether a window contact state represents open."""
    if state is None:
        return False
    return str(state.state).lower() in {"on", "open"}
