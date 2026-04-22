"""Public domain API for the ClimateRelayCore backend."""

from .models import ClimateCapabilities, EffectiveTarget
from .modes import (
    EffectivePresence,
    GlobalMode,
    UnknownStateHandling,
    resolve_presence_mode,
)
from .window_actions import WindowActionType, resolve_window_action

__all__ = [
    "ClimateCapabilities",
    "EffectivePresence",
    "EffectiveTarget",
    "GlobalMode",
    "UnknownStateHandling",
    "WindowActionType",
    "resolve_presence_mode",
    "resolve_window_action",
]
