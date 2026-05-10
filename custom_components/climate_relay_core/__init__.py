"""Home Assistant integration scaffold for ClimateRelayCore."""

from __future__ import annotations

import logging

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import config_validation as cv

from .const import (
    DOMAIN,
    SERVICE_CLEAR_AREA_OVERRIDE,
    SERVICE_SET_AREA_OVERRIDE,
    SERVICE_SET_GLOBAL_MODE,
)
from .domain import GlobalMode, OverrideTerminationType
from .frontend_api import async_register_websocket_commands
from .runtime import GlobalRuntime, build_global_config, build_room_configs

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SELECT, Platform.CLIMATE]
CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up the integration domain."""
    hass.data.setdefault(DOMAIN, {})
    async_register_websocket_commands(hass)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up the integration from a config entry."""
    hass.data.setdefault(DOMAIN, {})
    room_configs = build_room_configs(entry.data, entry.options, hass=hass)
    runtime = GlobalRuntime(
        hass,
        build_global_config(entry.data, entry.options),
        room_configs,
    )
    remove_listener = entry.add_update_listener(_async_handle_entry_update)
    hass.data[DOMAIN][entry.entry_id] = {
        "title": entry.title,
        "runtime": runtime,
        "room_configs": room_configs,
        "remove_listener": remove_listener,
    }
    _async_register_services(hass)
    _LOGGER.info(
        "Set up %s with global mode %s (simulation_mode=%s)",
        entry.title,
        runtime.global_mode.value,
        runtime.config.simulation_mode,
    )
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        stored_entry = hass.data.get(DOMAIN, {}).pop(entry.entry_id, None)
        if stored_entry is not None:
            stored_entry["remove_listener"]()
        if not hass.data.get(DOMAIN):
            hass.services.async_remove(DOMAIN, SERVICE_SET_GLOBAL_MODE)
            hass.services.async_remove(DOMAIN, SERVICE_SET_AREA_OVERRIDE)
            hass.services.async_remove(DOMAIN, SERVICE_CLEAR_AREA_OVERRIDE)
    return unload_ok


def _async_register_services(hass: HomeAssistant) -> None:
    """Register integration services once per Home Assistant instance."""
    if hass.services.has_service(DOMAIN, SERVICE_SET_GLOBAL_MODE):
        return

    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_GLOBAL_MODE,
        _async_handle_set_global_mode,
        schema=vol.Schema({vol.Required("mode"): vol.In([mode.value for mode in GlobalMode])}),
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_AREA_OVERRIDE,
        _async_handle_set_area_override,
        schema=vol.Schema(
            {
                vol.Required("area_id"): cv.string,
                vol.Required("target_temperature"): vol.Coerce(float),
                vol.Required("termination_type"): vol.In(
                    ["duration", "until_time", "next_timeblock", "never"]
                ),
                vol.Optional("duration_minutes"): vol.Coerce(int),
                vol.Optional("until_time"): cv.string,
            }
        ),
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_CLEAR_AREA_OVERRIDE,
        _async_handle_clear_area_override,
        schema=vol.Schema({vol.Required("area_id"): cv.string}),
    )


async def _async_handle_set_global_mode(service_call: ServiceCall) -> None:
    """Handle the public global mode runtime command."""
    hass = service_call.hass
    entries = hass.data.get(DOMAIN, {})
    if not entries:
        return

    entry_data = next(iter(entries.values()))
    runtime: GlobalRuntime = entry_data["runtime"]
    await runtime.async_set_global_mode(
        GlobalMode(service_call.data["mode"]),
        source="service",
    )


async def _async_handle_set_area_override(service_call: ServiceCall) -> None:
    """Handle the public area manual override runtime command."""
    runtime = _first_runtime(service_call.hass)
    if runtime is None:
        return

    termination_type: OverrideTerminationType = service_call.data["termination_type"]
    duration_minutes = service_call.data.get("duration_minutes")
    until_time = service_call.data.get("until_time")
    _validate_override_termination(
        termination_type,
        duration_minutes=duration_minutes,
        until_time=until_time,
    )
    try:
        await runtime.async_set_area_override(
            area_id=service_call.data["area_id"],
            target_temperature=service_call.data["target_temperature"],
            termination_type=termination_type,
            duration_minutes=duration_minutes,
            until_time=until_time,
            source="service",
        )
    except ValueError as err:
        raise HomeAssistantError(str(err)) from err


async def _async_handle_clear_area_override(service_call: ServiceCall) -> None:
    """Handle the public area manual override clear command."""
    runtime = _first_runtime(service_call.hass)
    if runtime is None:
        return

    try:
        await runtime.async_clear_area_override(
            area_id=service_call.data["area_id"],
            source="service",
        )
    except ValueError as err:
        raise HomeAssistantError(str(err)) from err


def _first_runtime(hass: HomeAssistant) -> GlobalRuntime | None:
    entries = hass.data.get(DOMAIN, {})
    if not entries:
        return None
    entry_data = next(iter(entries.values()))
    return entry_data["runtime"]


def _validate_override_termination(
    termination_type: OverrideTerminationType,
    *,
    duration_minutes: int | None,
    until_time: str | None,
) -> None:
    """Validate service-level manual-override termination payloads."""
    if termination_type == "duration":
        if duration_minutes is None or duration_minutes <= 0:
            raise HomeAssistantError("duration termination requires positive duration_minutes.")
        if until_time is not None:
            raise HomeAssistantError("duration termination does not accept until_time.")
        return
    if termination_type == "until_time":
        if until_time is None:
            raise HomeAssistantError("until_time termination requires until_time.")
        if duration_minutes is not None:
            raise HomeAssistantError("until_time termination does not accept duration_minutes.")
        return
    if termination_type in {"next_timeblock", "never"} and (
        duration_minutes is not None or until_time is not None
    ):
        raise HomeAssistantError(
            f"{termination_type} termination does not accept duration_minutes or until_time."
        )


async def _async_handle_entry_update(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload the config entry after an options update."""
    await hass.config_entries.async_reload(entry.entry_id)
