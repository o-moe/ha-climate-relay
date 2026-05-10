"""Frontend-facing WebSocket commands for Climate Relay."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import voluptuous as vol
from homeassistant.components import websocket_api
from homeassistant.components.climate import DOMAIN as CLIMATE_DOMAIN
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import entity_registry as er

from . import room_management
from .const import CONF_PRIMARY_CLIMATE_ENTITY_ID, CONF_ROOMS, DOMAIN
from .room_config import default_room_data, normalize_rooms
from .runtime import _resolve_area_reference

COMMAND_ROOM_CANDIDATES = f"{DOMAIN}/room_candidates"
COMMAND_ACTIVATE_ROOM = f"{DOMAIN}/activate_room"

ERROR_NO_CONFIG_ENTRY = "no_config_entry"
ERROR_MULTIPLE_CONFIG_ENTRIES = "multiple_config_entries"
ERROR_UNKNOWN_CANDIDATE = "unknown_candidate"
ERROR_PRIMARY_CLIMATE_AREA_REQUIRED = "primary_climate_area_required"
ERROR_PRIMARY_CLIMATE_ALREADY_ACTIVE = "primary_climate_already_active"
ERROR_AREA_ALREADY_ACTIVE = "area_already_active"
ERROR_INVALID_ENTITY_DOMAIN = "invalid_entity_domain"
ERROR_CONFIG_ENTRY_UPDATE_FAILED = "config_entry_update_failed"


@dataclass(frozen=True, slots=True)
class RoomCandidate:
    """One frontend-renderable room activation candidate."""

    candidate_id: str
    area_id: str | None
    area_name: str | None
    primary_climate_entity_id: str
    primary_climate_display_name: str | None
    already_active: bool
    unavailable_reason: str | None

    def as_dict(self) -> dict[str, Any]:
        """Return the WebSocket payload shape."""
        return {
            "candidate_id": self.candidate_id,
            "area_id": self.area_id,
            "area_name": self.area_name,
            "primary_climate_entity_id": self.primary_climate_entity_id,
            "primary_climate_display_name": self.primary_climate_display_name,
            "already_active": self.already_active,
            "unavailable_reason": self.unavailable_reason,
        }


def async_register_websocket_commands(hass: HomeAssistant) -> None:
    """Register frontend-facing WebSocket commands."""
    websocket_api.async_register_command(hass, websocket_room_candidates)
    websocket_api.async_register_command(hass, websocket_activate_room)


@callback
@websocket_api.websocket_command({vol.Required("type"): COMMAND_ROOM_CANDIDATES})
@websocket_api.async_response
async def websocket_room_candidates(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Handle candidate discovery requests from the custom card."""
    try:
        entry = _require_single_loaded_entry(hass)
    except FrontendApiError as err:
        connection.send_error(msg["id"], err.code, err.message)
        return

    candidates = discover_room_candidates(hass, entry).values()
    connection.send_result(
        msg["id"],
        {"candidates": [candidate.as_dict() for candidate in candidates]},
    )


@callback
@websocket_api.websocket_command(
    {
        vol.Required("type"): COMMAND_ACTIVATE_ROOM,
        vol.Optional("candidate_id"): str,
        vol.Optional("primary_climate_entity_id"): str,
    }
)
@websocket_api.async_response
async def websocket_activate_room(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Handle one-room activation requests from the custom card."""
    try:
        result = await async_activate_room_from_frontend(
            hass,
            candidate_id=msg.get("candidate_id"),
            primary_climate_entity_id=msg.get("primary_climate_entity_id"),
        )
    except FrontendApiError as err:
        connection.send_error(msg["id"], err.code, err.message)
        return

    connection.send_result(msg["id"], result)


async def async_activate_room_from_frontend(
    hass: HomeAssistant,
    *,
    candidate_id: str | None = None,
    primary_climate_entity_id: str | None = None,
) -> dict[str, Any]:
    """Activate exactly one room through the existing room options format."""
    entry = _require_single_loaded_entry(hass)

    lookup_id = primary_climate_entity_id or candidate_id
    if not lookup_id:
        raise FrontendApiError(ERROR_UNKNOWN_CANDIDATE, "Unknown room candidate.")
    if primary_climate_entity_id is not None and primary_climate_entity_id.split(".", 1)[0] != (
        CLIMATE_DOMAIN
    ):
        raise FrontendApiError(
            ERROR_INVALID_ENTITY_DOMAIN,
            "Room activation requires a climate entity.",
        )

    candidates = discover_room_candidates(hass, entry)
    candidate = candidates.get(lookup_id)
    if candidate is None:
        raise FrontendApiError(ERROR_UNKNOWN_CANDIDATE, "Unknown room candidate.")
    if candidate.unavailable_reason == "missing_area":
        raise FrontendApiError(
            ERROR_PRIMARY_CLIMATE_AREA_REQUIRED,
            "Primary climate entity must belong to a Home Assistant area.",
        )
    if candidate.already_active or candidate.unavailable_reason == "duplicate_primary_climate":
        raise FrontendApiError(
            ERROR_PRIMARY_CLIMATE_ALREADY_ACTIVE,
            "Primary climate entity is already activated.",
        )
    if candidate.unavailable_reason == "duplicate_area":
        raise FrontendApiError(
            ERROR_AREA_ALREADY_ACTIVE,
            "Home Assistant area is already activated by another room.",
        )
    if candidate.unavailable_reason is not None:
        raise FrontendApiError(candidate.unavailable_reason, "Room candidate is not activatable.")

    rooms = normalize_rooms({**entry.data, **entry.options})
    submitted_room = {
        **default_room_data(),
        CONF_PRIMARY_CLIMATE_ENTITY_ID: candidate.primary_climate_entity_id,
    }
    try:
        updated_rooms = room_management.activate_room(rooms, submitted_room)
    except room_management.DuplicatePrimaryClimateError as err:
        raise FrontendApiError(ERROR_PRIMARY_CLIMATE_ALREADY_ACTIVE, str(err)) from err
    except room_management.RoomManagementError as err:
        raise FrontendApiError(ERROR_UNKNOWN_CANDIDATE, str(err)) from err

    options = {**entry.options, CONF_ROOMS: updated_rooms}
    try:
        hass.config_entries.async_update_entry(entry, options=options)
        await hass.config_entries.async_reload(entry.entry_id)
    except Exception as err:
        raise FrontendApiError(
            ERROR_CONFIG_ENTRY_UPDATE_FAILED,
            "Failed to persist activated room.",
        ) from err

    return {
        "activated": True,
        "candidate": candidate.as_dict(),
        "primary_climate_entity_id": candidate.primary_climate_entity_id,
        "rooms_count": len(updated_rooms),
    }


def discover_room_candidates(
    hass: HomeAssistant,
    entry: Any,
) -> dict[str, RoomCandidate]:
    """Return frontend-renderable climate candidates keyed by entity and candidate ID."""
    existing_rooms = normalize_rooms({**entry.data, **entry.options})
    active_primary_climates = {
        room[CONF_PRIMARY_CLIMATE_ENTITY_ID]
        for room in existing_rooms
        if isinstance(room.get(CONF_PRIMARY_CLIMATE_ENTITY_ID), str)
    }
    active_area_ids = _active_area_ids(hass, active_primary_climates)

    candidates: dict[str, RoomCandidate] = {}
    for entity_id in sorted(_climate_entity_ids(hass)):
        area_reference = _resolve_area_reference(hass, entity_id)
        already_active = entity_id in active_primary_climates
        unavailable_reason = _unavailable_reason(
            area_reference.area_id,
            already_active=already_active,
            active_area_ids=active_area_ids,
        )
        candidate = RoomCandidate(
            candidate_id=entity_id,
            area_id=area_reference.area_id,
            area_name=area_reference.area_name,
            primary_climate_entity_id=entity_id,
            primary_climate_display_name=_entity_display_name(hass, entity_id),
            already_active=already_active,
            unavailable_reason=unavailable_reason,
        )
        candidates[entity_id] = candidate
    return candidates


def _require_single_loaded_entry(hass: HomeAssistant) -> Any:
    entries = hass.data.get(DOMAIN, {})
    if not entries:
        raise FrontendApiError(ERROR_NO_CONFIG_ENTRY, "No loaded Climate Relay config entry.")
    if len(entries) > 1:
        raise FrontendApiError(
            ERROR_MULTIPLE_CONFIG_ENTRIES,
            "Room activation requires exactly one loaded Climate Relay config entry.",
        )

    entry_id = next(iter(entries))
    for entry in hass.config_entries.async_entries(DOMAIN):
        if entry.entry_id == entry_id:
            return entry
    raise FrontendApiError(ERROR_NO_CONFIG_ENTRY, "No loaded Climate Relay config entry.")


def _climate_entity_ids(hass: HomeAssistant) -> set[str]:
    entity_ids = {
        entity_id for entity_id in hass.states.async_entity_ids(CLIMATE_DOMAIN) if "." in entity_id
    }
    entity_registry = er.async_get(hass)
    for entity_entry in entity_registry.entities.values():
        if entity_entry.domain == CLIMATE_DOMAIN:
            entity_ids.add(entity_entry.entity_id)
    return entity_ids


def _active_area_ids(hass: HomeAssistant, active_primary_climates: set[str]) -> set[str]:
    area_ids: set[str] = set()
    for primary_climate_entity_id in active_primary_climates:
        area_id = _resolve_area_reference(hass, primary_climate_entity_id).area_id
        if area_id is not None:
            area_ids.add(area_id)
    return area_ids


def _unavailable_reason(
    area_id: str | None,
    *,
    already_active: bool,
    active_area_ids: set[str],
) -> str | None:
    if already_active:
        return "duplicate_primary_climate"
    if area_id is None:
        return "missing_area"
    if area_id in active_area_ids:
        return "duplicate_area"
    return None


def _entity_display_name(hass: HomeAssistant, entity_id: str) -> str | None:
    state = hass.states.get(entity_id)
    if state is not None:
        friendly_name = state.attributes.get("friendly_name")
        if isinstance(friendly_name, str) and friendly_name:
            return friendly_name

    entity_entry = er.async_get(hass).async_get(entity_id)
    if entity_entry is None:
        return None
    return entity_entry.name or entity_entry.original_name


class FrontendApiError(ValueError):
    """Structured frontend API error."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
