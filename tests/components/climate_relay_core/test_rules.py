"""Unit tests for pure domain behavior."""

from __future__ import annotations

import unittest
from datetime import datetime, time
from zoneinfo import ZoneInfo

from custom_components.climate_relay_core.domain import (
    ClimateCapabilities,
    EffectivePresence,
    EffectiveTarget,
    GlobalMode,
    ManualOverride,
    RoomTarget,
    UnknownStateHandling,
    WindowActionType,
    build_daily_home_window_schedule,
    resolve_presence_mode,
    resolve_regulation_state,
    resolve_room_target,
    resolve_window_action,
)


class ResolvePresenceModeTests(unittest.TestCase):
    """Test the public presence-resolution behavior."""

    def test_auto_mode_returns_home_if_any_person_is_home(self) -> None:
        result = resolve_presence_mode(["not_home", "home"], GlobalMode.AUTO)
        self.assertEqual(result, EffectivePresence.HOME)

    def test_auto_mode_returns_away_if_everyone_is_away(self) -> None:
        result = resolve_presence_mode(["not_home", "not_home"], GlobalMode.AUTO)
        self.assertEqual(result, EffectivePresence.AWAY)

    def test_manual_home_override_wins(self) -> None:
        result = resolve_presence_mode([], GlobalMode.HOME)
        self.assertEqual(result, EffectivePresence.HOME)

    def test_manual_away_override_wins(self) -> None:
        result = resolve_presence_mode(["home"], GlobalMode.AWAY)
        self.assertEqual(result, EffectivePresence.AWAY)

    def test_unknown_presence_defaults_to_away(self) -> None:
        result = resolve_presence_mode(["unknown"], GlobalMode.AUTO)
        self.assertEqual(result, EffectivePresence.AWAY)

    def test_unavailable_presence_can_be_mapped_to_home(self) -> None:
        result = resolve_presence_mode(
            ["unavailable"],
            GlobalMode.AUTO,
            unknown_state_handling=UnknownStateHandling.HOME,
        )
        self.assertEqual(result, EffectivePresence.HOME)


class DomainExportsTests(unittest.TestCase):
    """Test the public domain package exports."""

    def test_effective_target_is_a_public_domain_type(self) -> None:
        target = EffectiveTarget(hvac_mode="heat", preset_mode=None, target_temperature=21.0)
        self.assertEqual(target.target_temperature, 21.0)

    def test_room_target_is_a_public_domain_type(self) -> None:
        target = RoomTarget(mode="absolute", temperature=21.0)
        self.assertEqual(target.temperature, 21.0)


class ResolveRoomTargetTests(unittest.TestCase):
    """Test room target resolution behavior."""

    def test_home_presence_uses_home_target(self) -> None:
        result = resolve_room_target(
            EffectivePresence.HOME,
            home_target=RoomTarget(mode="absolute", temperature=21.0),
            away_target=RoomTarget(mode="absolute", temperature=17.0),
        )
        self.assertEqual(result, 21.0)

    def test_away_presence_can_use_absolute_target(self) -> None:
        result = resolve_room_target(
            EffectivePresence.AWAY,
            home_target=RoomTarget(mode="absolute", temperature=21.0),
            away_target=RoomTarget(mode="absolute", temperature=17.0),
        )
        self.assertEqual(result, 17.0)

    def test_away_presence_can_use_relative_target_based_on_home_target(self) -> None:
        result = resolve_room_target(
            EffectivePresence.AWAY,
            home_target=RoomTarget(mode="absolute", temperature=21.0),
            away_target=RoomTarget(mode="relative", temperature=-2.5),
        )
        self.assertEqual(result, 18.5)


class ResolveRegulationStateTests(unittest.TestCase):
    """Test central area regulation priority resolution."""

    def setUp(self) -> None:
        self.timezone = ZoneInfo("Europe/Berlin")
        self.home_target = RoomTarget(mode="absolute", temperature=21.0)
        self.away_target = RoomTarget(mode="absolute", temperature=17.0)
        self.schedule = build_daily_home_window_schedule(time(6), time(22))

    def test_schedule_derived_target_exposes_next_change(self) -> None:
        result = resolve_regulation_state(
            home_target=self.home_target,
            away_target=self.away_target,
            schedule=self.schedule,
            effective_presence=EffectivePresence.HOME,
            manual_override=None,
            primary_available=True,
            fallback_temperature=16.0,
            now=datetime(2026, 4, 30, 7, 0, tzinfo=self.timezone),
            timezone=self.timezone,
        )

        self.assertEqual(result.target_temperature, 21.0)
        self.assertEqual(result.active_context, "schedule")
        self.assertEqual(result.next_change_at, datetime(2026, 4, 30, 22, 0, tzinfo=self.timezone))

    def test_away_mode_uses_away_target_without_next_change(self) -> None:
        result = resolve_regulation_state(
            home_target=self.home_target,
            away_target=self.away_target,
            schedule=self.schedule,
            effective_presence=EffectivePresence.AWAY,
            manual_override=None,
            primary_available=True,
            fallback_temperature=16.0,
            now=datetime(2026, 4, 30, 7, 0, tzinfo=self.timezone),
            timezone=self.timezone,
        )

        self.assertEqual(result.target_temperature, 17.0)
        self.assertEqual(result.active_context, "schedule")
        self.assertIsNone(result.next_change_at)

    def test_manual_override_precedes_schedule_and_fallback(self) -> None:
        ends_at = datetime(2026, 4, 30, 8, 0, tzinfo=self.timezone)
        override = ManualOverride(
            profile_id="climate_living_room",
            area_id="living_room",
            target_temperature=23.0,
            termination_type="until_time",
            created_at=datetime(2026, 4, 30, 7, 0, tzinfo=self.timezone),
            ends_at=ends_at,
        )

        result = resolve_regulation_state(
            home_target=self.home_target,
            away_target=self.away_target,
            schedule=self.schedule,
            effective_presence=EffectivePresence.HOME,
            manual_override=override,
            primary_available=False,
            fallback_temperature=16.0,
            now=datetime(2026, 4, 30, 7, 15, tzinfo=self.timezone),
            timezone=self.timezone,
        )

        self.assertEqual(result.target_temperature, 23.0)
        self.assertEqual(result.active_context, "manual_override")
        self.assertEqual(result.override_ends_at, ends_at)

    def test_window_override_precedes_manual_override_and_schedule(self) -> None:
        ends_at = datetime(2026, 4, 30, 8, 0, tzinfo=self.timezone)
        override = ManualOverride(
            profile_id="climate_living_room",
            area_id="living_room",
            target_temperature=23.0,
            termination_type="until_time",
            created_at=datetime(2026, 4, 30, 7, 0, tzinfo=self.timezone),
            ends_at=ends_at,
        )

        result = resolve_regulation_state(
            home_target=self.home_target,
            away_target=self.away_target,
            schedule=self.schedule,
            effective_presence=EffectivePresence.HOME,
            manual_override=override,
            window_target=EffectiveTarget(
                hvac_mode="heat",
                preset_mode=None,
                target_temperature=7.0,
            ),
            primary_available=True,
            fallback_temperature=16.0,
            now=datetime(2026, 4, 30, 7, 15, tzinfo=self.timezone),
            timezone=self.timezone,
        )

        self.assertEqual(result.target_temperature, 7.0)
        self.assertEqual(result.active_context, "window_override")
        self.assertIsNone(result.next_change_at)
        self.assertIsNone(result.override_ends_at)

    def test_window_close_reevaluates_against_current_schedule(self) -> None:
        result = resolve_regulation_state(
            home_target=self.home_target,
            away_target=self.away_target,
            schedule=self.schedule,
            effective_presence=EffectivePresence.HOME,
            manual_override=None,
            window_target=None,
            primary_available=True,
            fallback_temperature=16.0,
            now=datetime(2026, 4, 30, 23, 0, tzinfo=self.timezone),
            timezone=self.timezone,
        )

        self.assertEqual(result.target_temperature, 17.0)
        self.assertEqual(result.active_context, "schedule")

    def test_fallback_applies_when_primary_is_unavailable(self) -> None:
        result = resolve_regulation_state(
            home_target=self.home_target,
            away_target=self.away_target,
            schedule=self.schedule,
            effective_presence=EffectivePresence.HOME,
            manual_override=None,
            primary_available=False,
            fallback_temperature=16.0,
            now=datetime(2026, 4, 30, 7, 0, tzinfo=self.timezone),
            timezone=self.timezone,
        )

        self.assertEqual(result.target_temperature, 16.0)
        self.assertEqual(result.active_context, "fallback")
        self.assertFalse(result.window_priority_pending)


class ResolveWindowActionTests(unittest.TestCase):
    """Test window action mapping behavior."""

    def setUp(self) -> None:
        self.capabilities = ClimateCapabilities(
            supports_off=True,
            supports_preset_frost=True,
            min_temperature=7.0,
        )

    def test_off_action_prefers_hvac_off_when_supported(self) -> None:
        result = resolve_window_action(WindowActionType.OFF, self.capabilities)
        self.assertEqual(result.hvac_mode, "off")
        self.assertIsNone(result.target_temperature)

    def test_frost_protection_uses_preset_when_supported(self) -> None:
        result = resolve_window_action(WindowActionType.FROST_PROTECTION, self.capabilities)
        self.assertEqual(result.preset_mode, "frost_protection")

    def test_minimum_temperature_uses_device_minimum(self) -> None:
        result = resolve_window_action(WindowActionType.MINIMUM_TEMPERATURE, self.capabilities)
        self.assertEqual(result.target_temperature, 7.0)

    def test_custom_temperature_requires_value(self) -> None:
        with self.assertRaises(ValueError):
            resolve_window_action(WindowActionType.CUSTOM_TEMPERATURE, self.capabilities)

    def test_custom_temperature_sets_explicit_value(self) -> None:
        result = resolve_window_action(
            WindowActionType.CUSTOM_TEMPERATURE,
            self.capabilities,
            custom_temperature=11.5,
        )
        self.assertEqual(result.target_temperature, 11.5)

    def test_unsupported_off_falls_back_to_minimum_temperature(self) -> None:
        capabilities = ClimateCapabilities(
            supports_off=False,
            supports_preset_frost=False,
            min_temperature=6.0,
        )
        result = resolve_window_action(WindowActionType.OFF, capabilities)
        self.assertEqual(result.hvac_mode, "heat")
        self.assertEqual(result.target_temperature, 6.0)


if __name__ == "__main__":
    unittest.main()
