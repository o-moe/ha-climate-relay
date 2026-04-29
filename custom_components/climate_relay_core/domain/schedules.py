"""Pure schedule validation and evaluation logic."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time, timedelta
from typing import Literal
from zoneinfo import ZoneInfo

ScheduleTarget = Literal["home", "away"]
ScheduleLayout = Literal["all_days", "weekday_weekend", "seven_day"]

DAY_KEYS: tuple[str, ...] = (
    "monday",
    "tuesday",
    "wednesday",
    "thursday",
    "friday",
    "saturday",
    "sunday",
)
WEEKDAY_KEYS: frozenset[str] = frozenset(DAY_KEYS[:5])
WEEKEND_KEYS: frozenset[str] = frozenset(DAY_KEYS[5:])
MINUTES_PER_DAY = 24 * 60


@dataclass(frozen=True, slots=True)
class ScheduleBlock:
    """One continuous schedule block within a local day."""

    start_minute: int
    end_minute: int
    target: ScheduleTarget


@dataclass(frozen=True, slots=True)
class RoomSchedule:
    """A validated room schedule."""

    layout: ScheduleLayout
    blocks_by_key: dict[str, tuple[ScheduleBlock, ...]]


@dataclass(frozen=True, slots=True)
class ScheduleEvaluation:
    """Resolved schedule state for one point in local time."""

    target: ScheduleTarget
    next_change_at: datetime | None


def build_daily_home_window_schedule(
    home_start: time,
    home_end: time,
) -> RoomSchedule:
    """Build an all-days schedule from one daily home window."""
    start_minute = _time_to_minute(home_start)
    end_minute = _time_to_minute(home_end)
    if start_minute == end_minute:
        raise ValueError("Schedule home start and end must be different.")

    if start_minute < end_minute:
        blocks = (
            ScheduleBlock(0, start_minute, "away"),
            ScheduleBlock(start_minute, end_minute, "home"),
            ScheduleBlock(end_minute, MINUTES_PER_DAY, "away"),
        )
    else:
        blocks = (
            ScheduleBlock(0, end_minute, "home"),
            ScheduleBlock(end_minute, start_minute, "away"),
            ScheduleBlock(start_minute, MINUTES_PER_DAY, "home"),
        )
    return validate_schedule("all_days", {"all_days": blocks})


def validate_schedule(
    layout: ScheduleLayout,
    blocks_by_key: dict[str, tuple[ScheduleBlock, ...]],
) -> RoomSchedule:
    """Validate and return a schedule."""
    expected_keys = _expected_keys(layout)
    if set(blocks_by_key) != expected_keys:
        raise ValueError(f"Schedule layout {layout!r} requires keys {sorted(expected_keys)!r}.")

    validated: dict[str, tuple[ScheduleBlock, ...]] = {}
    for key, blocks in blocks_by_key.items():
        if not blocks:
            raise ValueError(f"Schedule key {key!r} must define at least one block.")
        ordered = tuple(sorted(blocks, key=lambda block: block.start_minute))
        expected_start = 0
        for block in ordered:
            if block.target not in {"home", "away"}:
                raise ValueError(f"Schedule key {key!r} has invalid target {block.target!r}.")
            if block.start_minute != expected_start:
                raise ValueError(f"Schedule key {key!r} has a gap or overlap.")
            if block.end_minute <= block.start_minute:
                raise ValueError(f"Schedule key {key!r} has an empty or reversed block.")
            if block.end_minute > MINUTES_PER_DAY:
                raise ValueError(f"Schedule key {key!r} exceeds one local day.")
            expected_start = block.end_minute
        if expected_start != MINUTES_PER_DAY:
            raise ValueError(f"Schedule key {key!r} does not cover the full day.")
        validated[key] = ordered
    return RoomSchedule(layout=layout, blocks_by_key=validated)


def evaluate_schedule(
    schedule: RoomSchedule,
    now: datetime,
    timezone: ZoneInfo,
) -> ScheduleEvaluation:
    """Evaluate a schedule and return its current target and next change."""
    local_now = now.astimezone(timezone)
    minute = local_now.hour * 60 + local_now.minute
    blocks = schedule.blocks_by_key[_schedule_key_for_date(schedule, local_now)]

    active_index = next(
        index
        for index, block in enumerate(blocks)
        if block.start_minute <= minute < block.end_minute
    )
    active_block = blocks[active_index]
    next_change_at = _next_change_at(schedule, local_now, active_index, timezone)
    return ScheduleEvaluation(
        target=active_block.target,
        next_change_at=next_change_at,
    )


def _next_change_at(
    schedule: RoomSchedule,
    local_now: datetime,
    active_index: int,
    timezone: ZoneInfo,
) -> datetime | None:
    current_key = _schedule_key_for_date(schedule, local_now)
    current_blocks = schedule.blocks_by_key[current_key]
    active_block = current_blocks[active_index]

    if active_block.end_minute < MINUTES_PER_DAY:
        return _local_datetime_at_minute(local_now, active_block.end_minute, timezone)

    for day_offset in range(1, 8):
        candidate_day = local_now + timedelta(days=day_offset)
        key = _schedule_key_for_date(schedule, candidate_day)
        first_block = schedule.blocks_by_key[key][0]
        if first_block.target != active_block.target:
            return _local_datetime_at_minute(candidate_day, 0, timezone)
        for block in schedule.blocks_by_key[key]:
            if block.target != active_block.target:
                return _local_datetime_at_minute(candidate_day, block.start_minute, timezone)
    return None


def _local_datetime_at_minute(day: datetime, minute: int, timezone: ZoneInfo) -> datetime:
    midnight = datetime(
        day.year,
        day.month,
        day.day,
        tzinfo=timezone,
    )
    return midnight + timedelta(minutes=minute)


def _schedule_key_for_date(schedule: RoomSchedule, local_now: datetime) -> str:
    if schedule.layout == "all_days":
        return "all_days"
    day_key = DAY_KEYS[local_now.weekday()]
    if schedule.layout == "seven_day":
        return day_key
    return "weekday" if day_key in WEEKDAY_KEYS else "weekend"


def _expected_keys(layout: ScheduleLayout) -> set[str]:
    if layout == "all_days":
        return {"all_days"}
    if layout == "weekday_weekend":
        return {"weekday", "weekend"}
    if layout == "seven_day":
        return set(DAY_KEYS)
    raise ValueError(f"Unsupported schedule layout: {layout!r}")


def _time_to_minute(value: time) -> int:
    return value.hour * 60 + value.minute
