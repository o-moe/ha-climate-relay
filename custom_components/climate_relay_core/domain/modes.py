"""Domain logic for global mode resolution."""

from __future__ import annotations

from collections.abc import Iterable
from enum import StrEnum


class GlobalMode(StrEnum):
    """Global operating mode."""

    AUTO = "auto"
    HOME = "home"
    AWAY = "away"


class EffectivePresence(StrEnum):
    """Presence result used by the rule engine."""

    HOME = "home"
    AWAY = "away"


def resolve_presence_mode(
    person_states: Iterable[str], global_mode: GlobalMode
) -> EffectivePresence:
    """Resolve the effective presence state."""
    if global_mode is GlobalMode.HOME:
        return EffectivePresence.HOME
    if global_mode is GlobalMode.AWAY:
        return EffectivePresence.AWAY
    return (
        EffectivePresence.HOME
        if any(state == "home" for state in person_states)
        else EffectivePresence.AWAY
    )
