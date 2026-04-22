"""Unit tests for pure domain behavior."""

from __future__ import annotations

import unittest

from custom_components.climate_relay_core.domain import (
    ClimateCapabilities,
    EffectivePresence,
    EffectiveTarget,
    GlobalMode,
    UnknownStateHandling,
    WindowActionType,
    resolve_presence_mode,
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
