"""Tests for global runtime behavior."""

from __future__ import annotations

from datetime import datetime
from types import SimpleNamespace
from unittest import IsolatedAsyncioTestCase
from unittest.mock import Mock, patch
from zoneinfo import ZoneInfo

from custom_components.climate_relay_core.const import (
    DEFAULT_FALLBACK_TEMPERATURE,
    DEFAULT_SCHEDULE_HOME_END,
    DEFAULT_SCHEDULE_HOME_START,
    DEFAULT_UNKNOWN_STATE_HANDLING,
)
from custom_components.climate_relay_core.domain import EffectivePresence, GlobalMode
from custom_components.climate_relay_core.runtime import (
    AreaReference,
    GlobalConfig,
    GlobalRuntime,
    _normalize_bool,
    _normalize_entity_id,
    _normalize_optional_value,
    _normalize_person_entity_ids,
    _normalize_schedule,
    _normalize_time,
    _normalize_unknown_state_handling,
    _resolve_area_reference,
    _resolve_profile_display_name,
    build_global_config,
    build_room_configs,
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

    async def test_area_override_lifecycle_replaces_clears_and_expires(self) -> None:
        hass = Mock()
        hass.states.get = Mock(return_value=SimpleNamespace(state="home"))
        timezone = ZoneInfo("Europe/Berlin")
        with patch(
            "custom_components.climate_relay_core.runtime._resolve_area_reference",
            return_value=AreaReference(area_id="office", area_name="Office"),
        ):
            room_configs = build_room_configs(
                {},
                {
                    "rooms": [
                        {
                            "primary_climate_entity_id": "climate.office",
                            "home_target_temperature": 20.0,
                            "away_target_type": "absolute",
                            "away_target_temperature": 17.0,
                        }
                    ]
                },
                hass=hass,
            )
        runtime = GlobalRuntime(
            hass,
            build_global_config({}, {}),
            room_configs,
        )
        subscriber = Mock()
        runtime.subscribe(subscriber)

        with (
            patch(
                "custom_components.climate_relay_core.runtime.dt_util.now",
                return_value=datetime(2026, 4, 30, 12, 0, tzinfo=timezone),
            ),
            patch(
                "custom_components.climate_relay_core.runtime.dt_util.DEFAULT_TIME_ZONE",
                timezone,
            ),
        ):
            first = await runtime.async_set_area_override(
                area_id="office",
                target_temperature=22.0,
                termination_type="duration",
                duration_minutes=30,
                source="test",
            )
            second = await runtime.async_set_area_override(
                area_id="office",
                target_temperature=19.0,
                termination_type="never",
                source="test",
            )

        self.assertEqual(first.ends_at, datetime(2026, 4, 30, 12, 30, tzinfo=timezone))
        self.assertEqual(
            runtime.manual_override_for_profile(room_configs[0].profile_id),
            second,
        )
        self.assertEqual(second.target_temperature, 19.0)

        await runtime.async_clear_area_override(area_id="office", source="test")
        self.assertIsNone(runtime.manual_override_for_profile(room_configs[0].profile_id))
        self.assertGreaterEqual(subscriber.call_count, 3)

    async def test_area_override_uses_daily_reset_and_rejects_unknown_area(self) -> None:
        hass = Mock()
        hass.states.get = Mock(return_value=SimpleNamespace(state="home"))
        timezone = ZoneInfo("Europe/Berlin")
        with patch(
            "custom_components.climate_relay_core.runtime._resolve_area_reference",
            return_value=AreaReference(area_id="office", area_name="Office"),
        ):
            room_configs = build_room_configs(
                {},
                {
                    "rooms": [
                        {
                            "primary_climate_entity_id": "climate.office",
                            "home_target_temperature": 20.0,
                            "away_target_type": "absolute",
                            "away_target_temperature": 17.0,
                        }
                    ]
                },
                hass=hass,
            )
        runtime = GlobalRuntime(
            hass,
            build_global_config({}, {"manual_override_reset_time": "05:30:00"}),
            room_configs,
        )

        with (
            patch(
                "custom_components.climate_relay_core.runtime.dt_util.now",
                return_value=datetime(2026, 4, 30, 22, 0, tzinfo=timezone),
            ),
            patch(
                "custom_components.climate_relay_core.runtime.dt_util.DEFAULT_TIME_ZONE",
                timezone,
            ),
        ):
            await runtime.async_set_area_override(
                area_id="climate.office",
                target_temperature=22.0,
                termination_type="never",
                source="test",
            )

        with (
            patch(
                "custom_components.climate_relay_core.runtime.dt_util.now",
                return_value=datetime(2026, 5, 1, 5, 31, tzinfo=timezone),
            ),
            patch(
                "custom_components.climate_relay_core.runtime.dt_util.DEFAULT_TIME_ZONE",
                timezone,
            ),
        ):
            self.assertIsNone(runtime.manual_override_for_profile(room_configs[0].profile_id))

        with (
            patch(
                "custom_components.climate_relay_core.runtime.dt_util.now",
                return_value=datetime(2026, 5, 1, 5, 0, tzinfo=timezone),
            ),
            patch(
                "custom_components.climate_relay_core.runtime.dt_util.DEFAULT_TIME_ZONE",
                timezone,
            ),
        ):
            override = await runtime.async_set_area_override(
                area_id="office",
                target_temperature=22.0,
                termination_type="never",
                source="test",
            )
            self.assertEqual(
                runtime.next_manual_override_reset_at(override),
                datetime(2026, 5, 1, 5, 30, tzinfo=timezone),
            )

        with self.assertRaisesRegex(ValueError, "Unknown Climate Relay area"):
            await runtime.async_clear_area_override(area_id="unknown", source="test")

    async def test_room_config_update_drops_stale_overrides_and_reset_can_be_disabled(
        self,
    ) -> None:
        hass = Mock()
        hass.states.get = Mock(return_value=SimpleNamespace(state="home"))
        timezone = ZoneInfo("Europe/Berlin")
        with patch(
            "custom_components.climate_relay_core.runtime._resolve_area_reference",
            return_value=AreaReference(area_id="office", area_name="Office"),
        ):
            room_configs = build_room_configs(
                {},
                {
                    "rooms": [
                        {
                            "primary_climate_entity_id": "climate.office",
                            "home_target_temperature": 20.0,
                            "away_target_type": "absolute",
                            "away_target_temperature": 17.0,
                        }
                    ]
                },
                hass=hass,
            )
        runtime = GlobalRuntime(hass, build_global_config({}, {}), room_configs)

        with (
            patch(
                "custom_components.climate_relay_core.runtime.dt_util.now",
                return_value=datetime(2026, 4, 30, 12, 0, tzinfo=timezone),
            ),
            patch(
                "custom_components.climate_relay_core.runtime.dt_util.DEFAULT_TIME_ZONE",
                timezone,
            ),
        ):
            override = await runtime.async_set_area_override(
                area_id="office",
                target_temperature=22.0,
                termination_type="duration",
                duration_minutes=15,
                source="test",
            )
            self.assertIsNone(runtime.next_manual_override_reset_at(override))

        runtime.update_room_configs(())

        self.assertIsNone(runtime.manual_override_for_profile(room_configs[0].profile_id))

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
            _normalize_person_entity_ids({"value": [{"value": "person.alice"}]}),
            ["person.alice"],
        )
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
        self.assertTrue(_normalize_bool("maybe"))
        self.assertEqual(
            _normalize_entity_id({"entity_id": "climate.living_room"}, required=True),
            "climate.living_room",
        )
        with self.assertRaisesRegex(ValueError, "Unsupported entity selector value"):
            _normalize_entity_id(123, required=True)

    async def test_build_room_configs_normalizes_single_room_payload(self) -> None:
        (room_config,) = build_room_configs(
            {},
            {
                "rooms": [
                    {
                        "primary_climate_entity_id": {"value": "climate.living_room"},
                        "humidity_entity_id": {"value": "sensor.living_room_humidity"},
                        "window_entity_id": {"value": "binary_sensor.living_room_window"},
                        "home_target_temperature": 21.0,
                        "away_target_type": {"value": "relative"},
                        "away_target_temperature": -2.0,
                    }
                ]
            },
        )

        self.assertEqual(room_config.display_name, "Living Room")
        self.assertEqual(room_config.profile_id, "climate_living_room")
        self.assertEqual(room_config.primary_climate_entity_id, "climate.living_room")
        self.assertIsNone(room_config.area_id)
        self.assertIsNone(room_config.area_name)
        self.assertEqual(room_config.humidity_entity_id, "sensor.living_room_humidity")
        self.assertEqual(room_config.window_entity_id, "binary_sensor.living_room_window")
        self.assertEqual(room_config.home_target.temperature, 21.0)
        self.assertEqual(room_config.away_target.mode, "relative")
        self.assertEqual(room_config.schedule.layout, "all_days")

    async def test_runtime_can_target_multiple_existing_profile_configs(self) -> None:
        hass = Mock()
        hass.states.get = Mock(return_value=SimpleNamespace(state="home"))
        timezone = ZoneInfo("Europe/Berlin")
        with patch(
            "custom_components.climate_relay_core.runtime._resolve_area_reference",
            side_effect=[
                AreaReference(area_id="office", area_name="Office"),
                AreaReference(area_id="bedroom", area_name="Bedroom"),
            ],
        ):
            room_configs = build_room_configs(
                {},
                {
                    "rooms": [
                        {
                            "primary_climate_entity_id": "climate.office",
                            "home_target_temperature": 20.0,
                            "away_target_type": "absolute",
                            "away_target_temperature": 17.0,
                        },
                        {
                            "primary_climate_entity_id": "climate.bedroom",
                            "home_target_temperature": 19.0,
                            "away_target_type": "absolute",
                            "away_target_temperature": 16.0,
                        },
                    ]
                },
                hass=hass,
            )
        runtime = GlobalRuntime(hass, build_global_config({}, {}), room_configs)

        with (
            patch(
                "custom_components.climate_relay_core.runtime.dt_util.now",
                return_value=datetime(2026, 4, 30, 12, 0, tzinfo=timezone),
            ),
            patch(
                "custom_components.climate_relay_core.runtime.dt_util.DEFAULT_TIME_ZONE",
                timezone,
            ),
        ):
            office_override = await runtime.async_set_area_override(
                area_id="office",
                target_temperature=22.0,
                termination_type="never",
                source="test",
            )
            bedroom_override = await runtime.async_set_area_override(
                area_id="climate_bedroom",
                target_temperature=18.5,
                termination_type="never",
                source="test",
            )

        self.assertEqual(
            runtime.manual_override_for_profile(room_configs[0].profile_id),
            office_override,
        )
        self.assertEqual(
            runtime.manual_override_for_profile(room_configs[1].profile_id),
            bedroom_override,
        )

        await runtime.async_clear_area_override(area_id="climate.office", source="test")

        self.assertIsNone(runtime.manual_override_for_profile(room_configs[0].profile_id))
        self.assertEqual(
            runtime.manual_override_for_profile(room_configs[1].profile_id),
            bedroom_override,
        )

    async def test_build_room_configs_uses_default_target_type_and_optional_entities(self) -> None:
        (room_config,) = build_room_configs(
            {},
            {
                "rooms": [
                    {
                        "primary_climate_entity_id": "climate.office",
                        "home_target_temperature": 20.0,
                        "away_target_type": "unsupported",
                        "away_target_temperature": 17.0,
                    }
                ]
            },
        )

        self.assertIsNone(room_config.humidity_entity_id)
        self.assertIsNone(room_config.window_entity_id)
        self.assertEqual(room_config.away_target.mode, "absolute")
        self.assertEqual(
            _normalize_time(None, default=DEFAULT_SCHEDULE_HOME_START).isoformat(),
            DEFAULT_SCHEDULE_HOME_START,
        )
        self.assertEqual(
            _normalize_time({"value": "22:00"}, default=DEFAULT_SCHEDULE_HOME_END).isoformat(),
            DEFAULT_SCHEDULE_HOME_END,
        )

    async def test_build_room_configs_normalizes_schedule_times(self) -> None:
        (room_config,) = build_room_configs(
            {},
            {
                "rooms": [
                    {
                        "primary_climate_entity_id": "climate.office",
                        "home_target_temperature": 20.0,
                        "away_target_type": "absolute",
                        "away_target_temperature": 17.0,
                        "schedule_home_start": "07:15",
                        "schedule_home_end": "21:45",
                    }
                ]
            },
        )

        self.assertEqual(room_config.schedule.layout, "all_days")
        self.assertEqual(room_config.schedule.blocks_by_key["all_days"][1].start_minute, 435)
        self.assertEqual(room_config.schedule.blocks_by_key["all_days"][1].end_minute, 1305)

        nested_schedule = _normalize_schedule(
            {
                "schedule": {
                    "schedule_home_start": {"value": "08:00"},
                    "schedule_home_end": {"value": "20:00"},
                }
            }
        )
        self.assertEqual(nested_schedule.blocks_by_key["all_days"][1].start_minute, 480)

    async def test_build_room_configs_derives_area_context_when_hass_is_available(self) -> None:
        hass = Mock()
        with patch(
            "custom_components.climate_relay_core.runtime._resolve_area_reference",
            return_value=AreaReference(area_id="living_room", area_name="Living Room"),
        ):
            (room_config,) = build_room_configs(
                {},
                {
                    "rooms": [
                        {
                            "primary_climate_entity_id": "climate.living_room",
                            "home_target_temperature": 20.0,
                            "away_target_type": "absolute",
                            "away_target_temperature": 17.0,
                        }
                    ]
                },
                hass=hass,
            )

        self.assertEqual(room_config.area_id, "living_room")
        self.assertEqual(room_config.area_name, "Living Room")
        self.assertEqual(room_config.display_name, "Living Room")

    async def test_resolve_area_reference_accepts_entity_registry_uuid(self) -> None:
        hass = Mock()
        entity_registry = Mock()
        device_registry = Mock()
        area_registry = Mock()

        with (
            patch(
                "custom_components.climate_relay_core.runtime.er.async_get",
                return_value=entity_registry,
            ),
            patch(
                "custom_components.climate_relay_core.runtime.er.async_resolve_entity_id",
                return_value="climate.living_room",
            ),
            patch(
                "custom_components.climate_relay_core.runtime.dr.async_get",
                return_value=device_registry,
            ),
            patch(
                "custom_components.climate_relay_core.runtime.ar.async_get",
                return_value=area_registry,
            ),
        ):
            entity_registry.async_get.return_value = SimpleNamespace(
                area_id=None,
                device_id="device-1",
            )
            device_registry.async_get.return_value = SimpleNamespace(area_id="device_area")
            area_registry.async_get_area.return_value = SimpleNamespace(name="Device Area")

            resolved = _resolve_area_reference(hass, "uuid-climate")

        self.assertEqual(resolved.area_id, "device_area")
        self.assertEqual(resolved.area_name, "Device Area")

    async def test_resolve_profile_display_name_prefers_area_then_legacy_then_entity_name(
        self,
    ) -> None:
        self.assertEqual(
            _resolve_profile_display_name(
                "climate.living_room",
                AreaReference(area_id="living_room", area_name="Living Room"),
                legacy_name="Legacy",
            ),
            "Living Room",
        )
        self.assertEqual(
            _resolve_profile_display_name(
                "climate.living_room",
                AreaReference(area_id=None, area_name=None),
                legacy_name="Legacy",
            ),
            "Legacy",
        )
        self.assertEqual(
            _resolve_profile_display_name(
                "climate.guest_suite",
                AreaReference(area_id=None, area_name=None),
                legacy_name=None,
            ),
            "Guest Suite",
        )

    async def test_resolve_area_reference_prefers_entity_area_then_device_area(self) -> None:
        hass = Mock()
        entity_registry = Mock()
        device_registry = Mock()
        area_registry = Mock()

        with (
            patch(
                "custom_components.climate_relay_core.runtime.er.async_get",
                return_value=entity_registry,
            ),
            patch(
                "custom_components.climate_relay_core.runtime.er.async_resolve_entity_id",
                side_effect=lambda _registry, value: value,
            ),
            patch(
                "custom_components.climate_relay_core.runtime.dr.async_get",
                return_value=device_registry,
            ),
            patch(
                "custom_components.climate_relay_core.runtime.ar.async_get",
                return_value=area_registry,
            ),
        ):
            entity_registry.async_get.return_value = SimpleNamespace(
                area_id="entity_area",
                device_id="device-1",
            )
            area_registry.async_get_area.return_value = SimpleNamespace(name="Entity Area")
            resolved = _resolve_area_reference(hass, "climate.living_room")
            self.assertEqual(resolved.area_id, "entity_area")
            self.assertEqual(resolved.area_name, "Entity Area")

            entity_registry.async_get.return_value = SimpleNamespace(
                area_id=None,
                device_id="device-2",
            )
            device_registry.async_get.return_value = SimpleNamespace(area_id="device_area")
            area_registry.async_get_area.return_value = SimpleNamespace(name="Device Area")
            resolved = _resolve_area_reference(hass, "climate.office")
            self.assertEqual(resolved.area_id, "device_area")
            self.assertEqual(resolved.area_name, "Device Area")

            entity_registry.async_get.return_value = None
            resolved = _resolve_area_reference(hass, "climate.unknown")
            self.assertIsNone(resolved.area_id)
            self.assertIsNone(resolved.area_name)

            entity_registry.async_get.return_value = SimpleNamespace(
                area_id=None,
                device_id=None,
            )
            resolved = _resolve_area_reference(hass, "climate.no_area")
            self.assertIsNone(resolved.area_id)
            self.assertIsNone(resolved.area_name)

    async def test_build_room_configs_rejects_invalid_required_entity_selector(self) -> None:
        with self.assertRaisesRegex(ValueError, "Required entity_id is missing"):
            build_room_configs(
                {},
                {
                    "rooms": [
                        {
                            "primary_climate_entity_id": None,
                            "home_target_temperature": 20.0,
                            "away_target_type": "absolute",
                            "away_target_temperature": 17.0,
                        }
                    ]
                },
            )

    async def test_build_room_configs_rejects_non_dict_room_payload(self) -> None:
        with self.assertRaisesRegex(ValueError, "Unsupported room configuration"):
            build_room_configs({}, {"rooms": ["invalid"]})
