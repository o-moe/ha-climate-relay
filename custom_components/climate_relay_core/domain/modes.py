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


class UnknownStateHandling(StrEnum):
    """How to interpret unknown or unavailable person states in auto mode."""

    HOME = "home"
    AWAY = "away"


def resolve_presence_mode(
    person_states: Iterable[str],
    global_mode: GlobalMode,
    *,
    unknown_state_handling: UnknownStateHandling = UnknownStateHandling.AWAY,
) -> EffectivePresence:
    """Resolve the effective presence state."""
    if global_mode is GlobalMode.HOME:
        return EffectivePresence.HOME
    if global_mode is GlobalMode.AWAY:
        return EffectivePresence.AWAY
    return (
        EffectivePresence.HOME
        if any(_state_counts_as_home(state, unknown_state_handling) for state in person_states)
        else EffectivePresence.AWAY
    )


def _state_counts_as_home(
    state: str,
    unknown_state_handling: UnknownStateHandling,
) -> bool:
    """Return whether a Home Assistant person state should count as home."""
    if state == "home":
        return True
    if state in {"unknown", "unavailable"}:
        return unknown_state_handling is UnknownStateHandling.HOME
    return False
