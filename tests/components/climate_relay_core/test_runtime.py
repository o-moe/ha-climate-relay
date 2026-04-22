"""Tests for global runtime behavior."""

from __future__ import annotations

from types import SimpleNamespace
from unittest import IsolatedAsyncioTestCase
from unittest.mock import Mock

from custom_components.climate_relay_core.const import (
    DEFAULT_FALLBACK_TEMPERATURE,
    DEFAULT_UNKNOWN_STATE_HANDLING,
)
from custom_components.climate_relay_core.domain import EffectivePresence, GlobalMode
from custom_components.climate_relay_core.runtime import (
    GlobalConfig,
    GlobalRuntime,
    _normalize_bool,
    _normalize_optional_value,
    _normalize_person_entity_ids,
    _normalize_unknown_state_handling,
    build_global_config,
)


class GlobalRuntimeTests(IsolatedAsyncioTestCase):
    """Test the integration runtime state."""

    async def test_auto_mode_defaults_unknown_presence_to_away(self) -> None:
        hass = Mock()
        hass.states.get = Mock(return_value=SimpleNamespace(state="unknown"))
        runtime = GlobalRuntime(
            hass,
            GlobalConfig(
                person_entity_ids=("person.alice",),
                unknown_state_handling=DEFAULT_UNKNOWN_STATE_HANDLING,
                fallback_temperature=DEFAULT_FALLBACK_TEMPERATURE,
                manual_override_reset_time=None,
                simulation_mode=False,
                verbose_logging=False,
            ),
        )

        self.assertEqual(runtime.effective_presence, EffectivePresence.AWAY)

    async def test_auto_mode_can_treat_unknown_presence_as_home(self) -> None:
        hass = Mock()
        hass.states.get = Mock(return_value=SimpleNamespace(state="unavailable"))
        runtime = GlobalRuntime(
            hass,
            GlobalConfig(
                person_entity_ids=("person.alice",),
                unknown_state_handling="home",
                fallback_temperature=DEFAULT_FALLBACK_TEMPERATURE,
                manual_override_reset_time=None,
                simulation_mode=False,
                verbose_logging=False,
            ),
        )

        self.assertEqual(runtime.effective_presence, EffectivePresence.HOME)

    async def test_manual_global_mode_persists_until_changed(self) -> None:
        hass = Mock()
        hass.states.get = Mock(return_value=SimpleNamespace(state="not_home"))
        runtime = GlobalRuntime(
            hass,
            GlobalConfig(
                person_entity_ids=("person.alice",),
                unknown_state_handling=DEFAULT_UNKNOWN_STATE_HANDLING,
                fallback_temperature=DEFAULT_FALLBACK_TEMPERATURE,
                manual_override_reset_time=None,
                simulation_mode=False,
                verbose_logging=False,
            ),
        )

        await runtime.async_set_global_mode(GlobalMode.HOME, source="test")
        self.assertEqual(runtime.global_mode, GlobalMode.HOME)
        self.assertEqual(runtime.effective_presence, EffectivePresence.HOME)

        await runtime.async_set_global_mode(GlobalMode.AWAY, source="test")
        self.assertEqual(runtime.global_mode, GlobalMode.AWAY)
        self.assertEqual(runtime.effective_presence, EffectivePresence.AWAY)

    async def test_runtime_notifies_subscribers_and_can_update_config(self) -> None:
        hass = Mock()
        hass.states.get = Mock(side_effect=[SimpleNamespace(state="not_home"), None])
        runtime = GlobalRuntime(
            hass,
            GlobalConfig(
                person_entity_ids=("person.alice", "person.bob"),
                unknown_state_handling=DEFAULT_UNKNOWN_STATE_HANDLING,
                fallback_temperature=DEFAULT_FALLBACK_TEMPERATURE,
                manual_override_reset_time=None,
                simulation_mode=True,
                verbose_logging=True,
            ),
        )
        subscriber = Mock()
        unsubscribe = runtime.subscribe(subscriber)

        await runtime.async_set_global_mode(GlobalMode.HOME, source="test")
        self.assertEqual(runtime.config.fallback_temperature, DEFAULT_FALLBACK_TEMPERATURE)
        subscriber.assert_called_once()

        runtime.update_config(
            GlobalConfig(
                person_entity_ids=(),
                unknown_state_handling="home",
                fallback_temperature=18.0,
                manual_override_reset_time="06:00:00",
                simulation_mode=False,
                verbose_logging=False,
            )
        )
        self.assertEqual(runtime.config.unknown_state_handling_enum.value, "home")
        self.assertFalse(runtime.config.simulation_mode)

        unsubscribe()
        runtime.update_config(
            GlobalConfig(
                person_entity_ids=(),
                unknown_state_handling="away",
                fallback_temperature=17.0,
                manual_override_reset_time=None,
                simulation_mode=True,
                verbose_logging=False,
            )
        )
        self.assertEqual(subscriber.call_count, 2)
        self.assertTrue(runtime.config.simulation_mode)

    async def test_build_global_config_prefers_options_over_entry_data(self) -> None:
        config = build_global_config(
            {
                "fallback_temperature": 20.0,
                "simulation_mode": False,
                "verbose_logging": False,
            },
            {
                "fallback_temperature": 17.5,
                "simulation_mode": True,
                "verbose_logging": True,
            },
        )

        self.assertEqual(config.fallback_temperature, 17.5)
        self.assertTrue(config.simulation_mode)
        self.assertTrue(config.verbose_logging)

    async def test_build_global_config_normalizes_wrapped_option_values(self) -> None:
        config = build_global_config(
            {},
            {
                "person_entity_ids": {"value": [{"value": "person.bjoern"}]},
                "unknown_state_handling": {"value": "home"},
                "manual_override_reset_time": {"value": "06:15:00"},
                "simulation_mode": {"value": "off"},
                "verbose_logging": {"value": "on"},
            },
        )

        self.assertEqual(config.person_entity_ids, ("person.bjoern",))
        self.assertEqual(config.unknown_state_handling, "home")
        self.assertEqual(config.manual_override_reset_time, "06:15:00")
        self.assertFalse(config.simulation_mode)
        self.assertTrue(config.verbose_logging)

    async def test_runtime_normalizers_cover_scalar_and_error_paths(self) -> None:
        self.assertFalse(_normalize_bool({"value": "off"}))
        self.assertTrue(_normalize_bool({"value": "on"}))
        self.assertTrue(_normalize_bool(2))

        self.assertEqual(_normalize_person_entity_ids(None), [])
        self.assertEqual(_normalize_person_entity_ids("person.alice"), ["person.alice"])
        self.assertEqual(
            _normalize_person_entity_ids({"entity_id": "person.alice"}),
            ["person.alice"],
        )
        self.assertEqual(
            _normalize_person_entity_ids([{"entity_id": "person.alice"}]),
            ["person.alice"],
        )
        with self.assertRaisesRegex(ValueError, "Unsupported person entity selector value"):
            _normalize_person_entity_ids([123])

        self.assertEqual(_normalize_unknown_state_handling({"value": "home"}), "home")
        self.assertEqual(_normalize_unknown_state_handling({"value": ""}), "away")
        self.assertEqual(_normalize_optional_value({"value": "wrapped"}), "wrapped")
        self.assertEqual(_normalize_optional_value("plain"), "plain")
