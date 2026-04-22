"""Pure room-target resolution logic."""

from __future__ import annotations

from .models import RoomTarget
from .modes import EffectivePresence


def resolve_room_target(
    effective_presence: EffectivePresence,
    *,
    home_target: RoomTarget,
    away_target: RoomTarget,
) -> float:
    """Resolve the effective room target temperature for the current presence."""
    home_temperature = _resolve_target(home_target)
    if effective_presence is EffectivePresence.HOME:
        return home_temperature

    if away_target.mode == "absolute":
        return away_target.temperature

    return home_temperature + away_target.temperature


def _resolve_target(target: RoomTarget) -> float:
    """Resolve a standalone room target."""
    return target.temperature
