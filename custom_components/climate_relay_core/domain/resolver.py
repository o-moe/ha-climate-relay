"""Central regulation-state resolution."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Literal
from zoneinfo import ZoneInfo

from .models import EffectiveTarget, RoomTarget
from .modes import EffectivePresence
from .overrides import ManualOverride
from .rooms import resolve_room_target
from .schedules import RoomSchedule, evaluate_schedule

RegulationContext = Literal["window_override", "manual_override", "schedule", "fallback"]


@dataclass(frozen=True, slots=True)
class RegulationResolution:
    """Resolved effective regulation state for one area-bound profile."""

    effective_target: EffectiveTarget
    active_context: RegulationContext
    next_change_at: datetime | None
    override_ends_at: datetime | None
    window_priority_pending: bool = False

    @property
    def target_temperature(self) -> float | None:
        """Return the resolved target temperature when the target includes one."""
        return self.effective_target.target_temperature


def resolve_regulation_state(
    *,
    home_target: RoomTarget,
    away_target: RoomTarget,
    schedule: RoomSchedule,
    effective_presence: EffectivePresence,
    manual_override: ManualOverride | None,
    window_target: EffectiveTarget | None = None,
    primary_available: bool,
    fallback_temperature: float,
    last_valid_target_temperature: float | None = None,
    default_fallback_temperature: float = 20.0,
    now: datetime,
    timezone: ZoneInfo,
) -> RegulationResolution:
    """Resolve the effective regulation state with deterministic rule priority."""
    if not primary_available:
        return RegulationResolution(
            effective_target=EffectiveTarget(
                hvac_mode="heat",
                preset_mode=None,
                target_temperature=fallback_temperature,
            ),
            active_context="fallback",
            next_change_at=None,
            override_ends_at=None,
        )

    if window_target is not None:
        return RegulationResolution(
            effective_target=window_target,
            active_context="window_override",
            next_change_at=None,
            override_ends_at=None,
        )

    if manual_override is not None:
        return RegulationResolution(
            effective_target=EffectiveTarget(
                hvac_mode="heat",
                preset_mode=None,
                target_temperature=manual_override.target_temperature,
            ),
            active_context="manual_override",
            next_change_at=None,
            override_ends_at=manual_override.ends_at,
        )

    if effective_presence is EffectivePresence.AWAY:
        try:
            target_temperature = resolve_room_target(
                EffectivePresence.AWAY,
                home_target=home_target,
                away_target=away_target,
            )
        except ValueError:
            return _resolve_exceptional_fallback(
                last_valid_target_temperature=last_valid_target_temperature,
                default_fallback_temperature=default_fallback_temperature,
            )
        return RegulationResolution(
            effective_target=EffectiveTarget(
                hvac_mode="heat",
                preset_mode=None,
                target_temperature=target_temperature,
            ),
            active_context="schedule",
            next_change_at=None,
            override_ends_at=None,
        )

    try:
        schedule_evaluation = evaluate_schedule(schedule, now, timezone)
        schedule_presence = (
            EffectivePresence.HOME
            if schedule_evaluation.target == EffectivePresence.HOME.value
            else EffectivePresence.AWAY
        )
        target_temperature = resolve_room_target(
            schedule_presence,
            home_target=home_target,
            away_target=away_target,
        )
    except ValueError:
        return _resolve_exceptional_fallback(
            last_valid_target_temperature=last_valid_target_temperature,
            default_fallback_temperature=default_fallback_temperature,
        )
    return RegulationResolution(
        effective_target=EffectiveTarget(
            hvac_mode="heat",
            preset_mode=None,
            target_temperature=target_temperature,
        ),
        active_context="schedule",
        next_change_at=schedule_evaluation.next_change_at,
        override_ends_at=None,
    )


def _resolve_exceptional_fallback(
    *,
    last_valid_target_temperature: float | None,
    default_fallback_temperature: float,
) -> RegulationResolution:
    target_temperature = (
        last_valid_target_temperature
        if last_valid_target_temperature is not None
        else default_fallback_temperature
    )
    return RegulationResolution(
        effective_target=EffectiveTarget(
            hvac_mode="heat",
            preset_mode=None,
            target_temperature=target_temperature,
        ),
        active_context="fallback",
        next_change_at=None,
        override_ends_at=None,
    )
