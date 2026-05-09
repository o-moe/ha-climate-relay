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
    if home_target.mode != "absolute":
        raise ValueError(f"Unsupported home target mode: {home_target.mode!r}")
    home_temperature = home_target.temperature
    if effective_presence is EffectivePresence.HOME:
        return home_temperature

    if away_target.mode == "absolute":
        return away_target.temperature
    if away_target.mode != "relative":
        raise ValueError(f"Unsupported away target mode: {away_target.mode!r}")

    return home_temperature + away_target.temperature
