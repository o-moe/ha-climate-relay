"""Tests for manual override lifecycle semantics."""

from __future__ import annotations

from datetime import datetime, time
from unittest import TestCase
from zoneinfo import ZoneInfo

from custom_components.climate_relay_core.domain import build_manual_override


class ManualOverrideTests(TestCase):
    """Test pure manual override behavior."""

    def test_duration_override_expires_after_minute_precise_duration(self) -> None:
        timezone = ZoneInfo("Europe/Berlin")
        now = datetime(2026, 4, 30, 12, 0, tzinfo=timezone)

        override = build_manual_override(
            profile_id="climate_office",
            area_id="office",
            target_temperature=22.5,
            termination_type="duration",
            duration_minutes=90,
            now=now,
            timezone=timezone,
        )

        self.assertEqual(override.ends_at, datetime(2026, 4, 30, 13, 30, tzinfo=timezone))
        self.assertTrue(override.is_active(datetime(2026, 4, 30, 13, 29, tzinfo=timezone)))
        self.assertFalse(override.is_active(datetime(2026, 4, 30, 13, 30, tzinfo=timezone)))

    def test_until_time_uses_next_occurrence_when_clock_time_already_passed(self) -> None:
        timezone = ZoneInfo("Europe/Berlin")

        override = build_manual_override(
            profile_id="climate_office",
            area_id="office",
            target_temperature=21.0,
            termination_type="until_time",
            until_time=time(6, 0),
            now=datetime(2026, 4, 30, 22, 0, tzinfo=timezone),
            timezone=timezone,
        )

        self.assertEqual(override.ends_at, datetime(2026, 5, 1, 6, 0, tzinfo=timezone))

    def test_until_time_uses_today_when_clock_time_is_still_future(self) -> None:
        timezone = ZoneInfo("Europe/Berlin")

        override = build_manual_override(
            profile_id="climate_office",
            area_id="office",
            target_temperature=21.0,
            termination_type="until_time",
            until_time=time(23, 0),
            now=datetime(2026, 4, 30, 22, 0, tzinfo=timezone),
            timezone=timezone,
        )

        self.assertEqual(override.ends_at, datetime(2026, 4, 30, 23, 0, tzinfo=timezone))

    def test_next_timeblock_uses_schedule_boundary_and_never_has_no_end_time(self) -> None:
        timezone = ZoneInfo("Europe/Berlin")
        next_change_at = datetime(2026, 4, 30, 22, 0, tzinfo=timezone)

        temporary = build_manual_override(
            profile_id="climate_office",
            area_id="office",
            target_temperature=20.5,
            termination_type="next_timeblock",
            next_change_at=next_change_at,
            now=datetime(2026, 4, 30, 12, 0, tzinfo=timezone),
            timezone=timezone,
        )
        persistent = build_manual_override(
            profile_id="climate_office",
            area_id="office",
            target_temperature=20.5,
            termination_type="never",
            now=datetime(2026, 4, 30, 12, 0, tzinfo=timezone),
            timezone=timezone,
        )

        self.assertEqual(temporary.ends_at, next_change_at)
        self.assertIsNone(persistent.ends_at)

    def test_next_timeblock_boundary_expires_at_boundary(self) -> None:
        timezone = ZoneInfo("Europe/Berlin")
        boundary = datetime(2026, 4, 30, 22, 0, tzinfo=timezone)

        override = build_manual_override(
            profile_id="climate_office",
            area_id="office",
            target_temperature=20.5,
            termination_type="next_timeblock",
            next_change_at=boundary,
            now=datetime(2026, 4, 30, 21, 59, tzinfo=timezone),
            timezone=timezone,
        )

        self.assertTrue(override.is_active(datetime(2026, 4, 30, 21, 59, tzinfo=timezone)))
        self.assertFalse(override.is_active(boundary))

    def test_termination_specific_parameters_are_required(self) -> None:
        timezone = ZoneInfo("Europe/Berlin")
        now = datetime(2026, 4, 30, 12, 0, tzinfo=timezone)

        with self.assertRaisesRegex(ValueError, "duration_minutes"):
            build_manual_override(
                profile_id="climate_office",
                area_id="office",
                target_temperature=22.0,
                termination_type="duration",
                now=now,
                timezone=timezone,
            )
        with self.assertRaisesRegex(ValueError, "until_time"):
            build_manual_override(
                profile_id="climate_office",
                area_id="office",
                target_temperature=22.0,
                termination_type="until_time",
                now=now,
                timezone=timezone,
            )
        with self.assertRaisesRegex(ValueError, "next_change_at"):
            build_manual_override(
                profile_id="climate_office",
                area_id="office",
                target_temperature=22.0,
                termination_type="next_timeblock",
                now=now,
                timezone=timezone,
            )

    def test_termination_rejects_parameters_from_other_types(self) -> None:
        timezone = ZoneInfo("Europe/Berlin")
        now = datetime(2026, 4, 30, 12, 0, tzinfo=timezone)

        with self.assertRaisesRegex(ValueError, "does not accept"):
            build_manual_override(
                profile_id="climate_office",
                area_id="office",
                target_temperature=22.0,
                termination_type="never",
                duration_minutes=30,
                now=now,
                timezone=timezone,
            )
        with self.assertRaisesRegex(ValueError, "does not accept until_time"):
            build_manual_override(
                profile_id="climate_office",
                area_id="office",
                target_temperature=22.0,
                termination_type="duration",
                duration_minutes=30,
                until_time="13:00:00",
                now=now,
                timezone=timezone,
            )
        with self.assertRaisesRegex(ValueError, "does not accept duration_minutes"):
            build_manual_override(
                profile_id="climate_office",
                area_id="office",
                target_temperature=22.0,
                termination_type="until_time",
                duration_minutes=30,
                until_time="13:00:00",
                now=now,
                timezone=timezone,
            )
        with self.assertRaisesRegex(ValueError, "next_timeblock termination does not accept"):
            build_manual_override(
                profile_id="climate_office",
                area_id="office",
                target_temperature=22.0,
                termination_type="next_timeblock",
                duration_minutes=30,
                next_change_at=datetime(2026, 4, 30, 13, 0, tzinfo=timezone),
                now=now,
                timezone=timezone,
            )
        with self.assertRaisesRegex(ValueError, "Unsupported override termination type"):
            build_manual_override(
                profile_id="climate_office",
                area_id="office",
                target_temperature=22.0,
                termination_type="unsupported",  # type: ignore[arg-type]
                now=now,
                timezone=timezone,
            )
