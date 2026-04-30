"""Tests for schedule validation and evaluation."""

from __future__ import annotations

from datetime import datetime, time
from unittest import TestCase
from zoneinfo import ZoneInfo

from custom_components.climate_relay_core.domain import (
    ScheduleBlock,
    build_daily_home_window_schedule,
    evaluate_schedule,
    validate_schedule,
)


class ScheduleTests(TestCase):
    """Test pure schedule behavior."""

    def test_daily_home_window_evaluates_target_and_next_change(self) -> None:
        timezone = ZoneInfo("Europe/Berlin")
        schedule = build_daily_home_window_schedule(time(6, 30), time(22, 15))

        morning = evaluate_schedule(
            schedule,
            datetime(2026, 4, 29, 7, 0, tzinfo=timezone),
            timezone,
        )
        night = evaluate_schedule(
            schedule,
            datetime(2026, 4, 29, 23, 0, tzinfo=timezone),
            timezone,
        )

        self.assertEqual(morning.target, "home")
        self.assertEqual(
            morning.next_change_at,
            datetime(2026, 4, 29, 22, 15, tzinfo=timezone),
        )
        self.assertEqual(night.target, "away")
        self.assertEqual(
            night.next_change_at,
            datetime(2026, 4, 30, 6, 30, tzinfo=timezone),
        )

    def test_schedule_validation_rejects_gaps_overlaps_and_missing_layout_keys(self) -> None:
        with self.assertRaisesRegex(ValueError, "requires keys"):
            validate_schedule("weekday_weekend", {"weekday": (ScheduleBlock(0, 1440, "home"),)})

        with self.assertRaisesRegex(ValueError, "gap or overlap"):
            validate_schedule(
                "all_days",
                {
                    "all_days": (
                        ScheduleBlock(0, 600, "away"),
                        ScheduleBlock(601, 1440, "home"),
                    )
                },
            )

        with self.assertRaisesRegex(ValueError, "full day"):
            validate_schedule(
                "all_days",
                {"all_days": (ScheduleBlock(0, 600, "away"),)},
            )

    def test_supported_layouts_include_all_days_weekday_weekend_and_seven_day(self) -> None:
        full_day = (ScheduleBlock(0, 1440, "home"),)

        self.assertEqual(
            validate_schedule("all_days", {"all_days": full_day}).layout,
            "all_days",
        )
        self.assertEqual(
            validate_schedule(
                "weekday_weekend",
                {"weekday": full_day, "weekend": full_day},
            ).layout,
            "weekday_weekend",
        )
        self.assertEqual(
            validate_schedule(
                "seven_day",
                {
                    "monday": full_day,
                    "tuesday": full_day,
                    "wednesday": full_day,
                    "thursday": full_day,
                    "friday": full_day,
                    "saturday": full_day,
                    "sunday": full_day,
                },
            ).layout,
            "seven_day",
        )

    def test_daily_home_window_rejects_equal_boundaries(self) -> None:
        with self.assertRaisesRegex(ValueError, "must be different"):
            build_daily_home_window_schedule(time(6), time(6))
