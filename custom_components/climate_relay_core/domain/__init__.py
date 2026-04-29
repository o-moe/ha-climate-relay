"""Public domain API for the ClimateRelayCore backend."""

from .models import ClimateCapabilities, EffectiveTarget, RoomTarget
from .modes import (
    EffectivePresence,
    GlobalMode,
    UnknownStateHandling,
    resolve_presence_mode,
)
from .rooms import resolve_room_target
from .window_actions import WindowActionType, resolve_window_action

__all__ = [
    "ClimateCapabilities",
    "EffectivePresence",
    "EffectiveTarget",
    "GlobalMode",
    "RoomTarget",
    "UnknownStateHandling",
    "WindowActionType",
    "resolve_room_target",
    "resolve_presence_mode",
    "resolve_window_action",
]
