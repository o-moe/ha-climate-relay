"""Manual override lifecycle and termination logic."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time, timedelta
from typing import Literal
from zoneinfo import ZoneInfo

OverrideTerminationType = Literal["duration", "until_time", "next_timeblock", "never"]


@dataclass(frozen=True, slots=True)
class ManualOverride:
    """One active manual area override."""

    profile_id: str
    area_id: str
    target_temperature: float
    termination_type: OverrideTerminationType
    created_at: datetime
    ends_at: datetime | None

    def is_active(self, now: datetime) -> bool:
        """Return whether this override still applies at the given time."""
        return self.ends_at is None or now.astimezone(self.created_at.tzinfo) < self.ends_at


def build_manual_override(
    *,
    profile_id: str,
    area_id: str,
    target_temperature: float,
    termination_type: OverrideTerminationType,
    now: datetime,
    timezone: ZoneInfo,
    duration_minutes: int | None = None,
    until_time: time | str | None = None,
    next_change_at: datetime | None = None,
) -> ManualOverride:
    """Build a validated manual override with a concrete end time when applicable."""
    local_now = now.astimezone(timezone)
    ends_at = _resolve_ends_at(
        termination_type=termination_type,
        local_now=local_now,
        timezone=timezone,
        duration_minutes=duration_minutes,
        until_time=until_time,
        next_change_at=next_change_at,
    )
    return ManualOverride(
        profile_id=profile_id,
        area_id=area_id,
        target_temperature=float(target_temperature),
        termination_type=termination_type,
        created_at=local_now,
        ends_at=ends_at,
    )


def _resolve_ends_at(
    *,
    termination_type: OverrideTerminationType,
    local_now: datetime,
    timezone: ZoneInfo,
    duration_minutes: int | None,
    until_time: time | str | None,
    next_change_at: datetime | None,
) -> datetime | None:
    if termination_type == "duration":
        if duration_minutes is None or duration_minutes <= 0:
            raise ValueError("duration termination requires positive duration_minutes.")
        if until_time is not None:
            raise ValueError("duration termination does not accept until_time.")
        return local_now + timedelta(minutes=duration_minutes)

    if termination_type == "until_time":
        if until_time is None:
            raise ValueError("until_time termination requires until_time.")
        if duration_minutes is not None:
            raise ValueError("until_time termination does not accept duration_minutes.")
        parsed_until_time = (
            time.fromisoformat(until_time) if isinstance(until_time, str) else until_time
        )
        candidate = datetime.combine(local_now.date(), parsed_until_time, tzinfo=timezone)
        if candidate <= local_now:
            candidate += timedelta(days=1)
        return candidate

    if termination_type == "next_timeblock":
        if duration_minutes is not None or until_time is not None:
            raise ValueError(
                "next_timeblock termination does not accept duration_minutes or until_time."
            )
        if next_change_at is None:
            raise ValueError("next_timeblock termination requires next_change_at.")
        return next_change_at.astimezone(timezone)

    if termination_type == "never":
        if duration_minutes is not None or until_time is not None:
            raise ValueError("never termination does not accept duration_minutes or until_time.")
        return None

    raise ValueError(f"Unsupported override termination type: {termination_type!r}")
