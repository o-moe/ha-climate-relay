"""Backend-owned room management operations for persisted room options."""

from __future__ import annotations

from typing import Any

from .const import CONF_PRIMARY_CLIMATE_ENTITY_ID
from .room_config import (
    normalize_daily_schedule_window,
    normalize_room_options,
)


class RoomManagementError(ValueError):
    """Base error for room-management validation failures."""


class MissingPrimaryClimateError(RoomManagementError):
    """Raised when a submitted room has no primary climate anchor."""


class DuplicatePrimaryClimateError(RoomManagementError):
    """Raised when two rooms use the same primary climate anchor."""


class UnknownRoomReferenceError(RoomManagementError):
    """Raised when a room reference does not match an existing room."""


def activate_room(
    existing_rooms: list[dict[str, Any]],
    submitted_room: dict[str, Any],
) -> list[dict[str, Any]]:
    """Return a new room list with one normalized room appended."""
    room = _normalize_submitted_room(submitted_room)
    primary_climate_entity_id = _primary_climate_entity_id(room)
    if _find_room_index(existing_rooms, primary_climate_entity_id) is not None:
        raise DuplicatePrimaryClimateError(
            f"Duplicate primary climate: {primary_climate_entity_id!r}"
        )
    return [dict(existing_room) for existing_room in existing_rooms] + [room]


def update_room(
    existing_rooms: list[dict[str, Any]],
    room_ref: str,
    submitted_room: dict[str, Any],
) -> list[dict[str, Any]]:
    """Return a new room list with exactly one referenced room replaced."""
    index = _require_room_index(existing_rooms, room_ref)
    room = _normalize_submitted_room(submitted_room)
    primary_climate_entity_id = _primary_climate_entity_id(room)

    duplicate_index = _find_room_index(existing_rooms, primary_climate_entity_id)
    if duplicate_index is not None and duplicate_index != index:
        raise DuplicatePrimaryClimateError(
            f"Duplicate primary climate: {primary_climate_entity_id!r}"
        )

    updated_rooms = [dict(existing_room) for existing_room in existing_rooms]
    updated_rooms[index] = room
    return updated_rooms


def disable_room(
    existing_rooms: list[dict[str, Any]],
    room_ref: str,
) -> list[dict[str, Any]]:
    """Return a new room list with exactly one referenced room removed."""
    index = _require_room_index(existing_rooms, room_ref)
    return [
        dict(existing_room)
        for existing_index, existing_room in enumerate(existing_rooms)
        if existing_index != index
    ]


def update_room_schedule(
    existing_rooms: list[dict[str, Any]],
    room_ref: str,
    *,
    schedule_home_start: Any,
    schedule_home_end: Any,
) -> list[dict[str, Any]]:
    """Return a new room list with only one room's daily schedule fields updated."""
    index = _require_room_index(existing_rooms, room_ref)
    schedule = normalize_daily_schedule_window(schedule_home_start, schedule_home_end)

    updated_rooms = [dict(existing_room) for existing_room in existing_rooms]
    updated_rooms[index] = {
        **updated_rooms[index],
        **schedule,
    }
    return updated_rooms


def _normalize_submitted_room(submitted_room: dict[str, Any]) -> dict[str, Any]:
    room = normalize_room_options(submitted_room)
    _primary_climate_entity_id(room)
    return room


def _primary_climate_entity_id(room: dict[str, Any]) -> str:
    primary_climate_entity_id = room.get(CONF_PRIMARY_CLIMATE_ENTITY_ID)
    if not isinstance(primary_climate_entity_id, str) or not primary_climate_entity_id:
        raise MissingPrimaryClimateError("A primary climate entity is required")
    return primary_climate_entity_id


def _require_room_index(existing_rooms: list[dict[str, Any]], room_ref: str) -> int:
    index = _find_room_index(existing_rooms, room_ref)
    if index is None:
        raise UnknownRoomReferenceError(f"Unknown room reference: {room_ref!r}")
    return index


def _find_room_index(existing_rooms: list[dict[str, Any]], room_ref: str) -> int | None:
    for index, existing_room in enumerate(existing_rooms):
        if existing_room.get(CONF_PRIMARY_CLIMATE_ENTITY_ID) == room_ref:
            return index
    return None
