"""Central regulation-state resolution."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Literal
from zoneinfo import ZoneInfo

from .models import RoomTarget
from .modes import EffectivePresence
from .overrides import ManualOverride
from .rooms import resolve_room_target
from .schedules import RoomSchedule, evaluate_schedule

RegulationContext = Literal["manual_override", "schedule", "fallback"]


@dataclass(frozen=True, slots=True)
class RegulationResolution:
    """Resolved effective regulation state for one area-bound profile."""

    target_temperature: float
    active_context: RegulationContext
    next_change_at: datetime | None
    override_ends_at: datetime | None
    window_priority_pending: bool = False


def resolve_regulation_state(
    *,
    home_target: RoomTarget,
    away_target: RoomTarget,
    schedule: RoomSchedule,
    effective_presence: EffectivePresence,
    manual_override: ManualOverride | None,
    primary_available: bool,
    fallback_temperature: float,
    now: datetime,
    timezone: ZoneInfo,
) -> RegulationResolution:
    """Resolve the effective regulation state with Epic 1 priority order."""
    if manual_override is not None:
        return RegulationResolution(
            target_temperature=manual_override.target_temperature,
            active_context="manual_override",
            next_change_at=None,
            override_ends_at=manual_override.ends_at,
        )

    if not primary_available:
        return RegulationResolution(
            target_temperature=fallback_temperature,
            active_context="fallback",
            next_change_at=None,
            override_ends_at=None,
        )

    if effective_presence is EffectivePresence.AWAY:
        return RegulationResolution(
            target_temperature=resolve_room_target(
                EffectivePresence.AWAY,
                home_target=home_target,
                away_target=away_target,
            ),
            active_context="schedule",
            next_change_at=None,
            override_ends_at=None,
        )

    schedule_evaluation = evaluate_schedule(schedule, now, timezone)
    schedule_presence = (
        EffectivePresence.HOME
        if schedule_evaluation.target == EffectivePresence.HOME.value
        else EffectivePresence.AWAY
    )
    return RegulationResolution(
        target_temperature=resolve_room_target(
            schedule_presence,
            home_target=home_target,
            away_target=away_target,
        ),
        active_context="schedule",
        next_change_at=schedule_evaluation.next_change_at,
        override_ends_at=None,
    )
