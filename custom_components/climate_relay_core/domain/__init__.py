"""Public domain API for the ClimateRelayCore backend."""

from .models import ClimateCapabilities, EffectiveTarget, RoomTarget
from .modes import (
    EffectivePresence,
    GlobalMode,
    UnknownStateHandling,
    resolve_presence_mode,
)
from .overrides import ManualOverride, OverrideTerminationType, build_manual_override
from .rooms import resolve_room_target
from .schedules import (
    RoomSchedule,
    ScheduleBlock,
    ScheduleEvaluation,
    build_daily_home_window_schedule,
    evaluate_schedule,
    validate_schedule,
)
from .window_actions import WindowActionType, resolve_window_action

__all__ = [
    "ClimateCapabilities",
    "EffectivePresence",
    "EffectiveTarget",
    "GlobalMode",
    "ManualOverride",
    "OverrideTerminationType",
    "RoomSchedule",
    "RoomTarget",
    "ScheduleBlock",
    "ScheduleEvaluation",
    "UnknownStateHandling",
    "WindowActionType",
    "build_daily_home_window_schedule",
    "build_manual_override",
    "evaluate_schedule",
    "resolve_room_target",
    "resolve_presence_mode",
    "resolve_window_action",
    "validate_schedule",
]
