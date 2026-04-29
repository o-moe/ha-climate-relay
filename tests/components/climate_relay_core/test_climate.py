"""Tests for the regulation climate entity."""

from __future__ import annotations

from dataclasses import replace
from types import SimpleNamespace
from unittest import IsolatedAsyncioTestCase
from unittest.mock import Mock, patch

from homeassistant.components.climate import HVACMode

from custom_components.climate_relay_core import climate as climate_platform
from custom_components.climate_relay_core.climate import (
    ClimateRelayCoreRoomClimateEntity,
    _is_unavailable,
    async_setup_entry,
)
from custom_components.climate_relay_core.const import (
    ATTR_ACTIVE_CONTROL_CONTEXT,
    ATTR_DEGRADATION_STATUS,
    ATTR_HUMIDITY_ENTITY_ID,
    ATTR_PRIMARY_CLIMATE_ENTITY_ID,
    ATTR_WINDOW_ENTITY_ID,
    CONF_ROOMS,
    DOMAIN,
)
from custom_components.climate_relay_core.domain import EffectivePresence
from custom_components.climate_relay_core.runtime import build_global_config, build_room_configs


class RoomClimateEntityTests(IsolatedAsyncioTestCase):
    """Test the regulation climate entity behavior."""

    def _build_entity(
        self,
        *,
        effective_presence: EffectivePresence = EffectivePresence.HOME,
        primary_state: object | None = None,
        humidity_state: object | None = None,
        window_state: object | None = None,
    ) -> ClimateRelayCoreRoomClimateEntity:
        hass = Mock()

        def get_state(entity_id: str) -> object | None:
            mapping = {
                "climate.living_room": primary_state,
                "sensor.living_room_humidity": humidity_state,
                "binary_sensor.living_room_window": window_state,
            }
            return mapping.get(entity_id)

        hass.states.get = Mock(side_effect=get_state)

        global_runtime = Mock()
        global_runtime.effective_presence = effective_presence
        global_runtime.config = build_global_config({}, {"fallback_temperature": 16.5})
        global_runtime.subscribe = Mock(return_value=lambda: None)

        (room_config,) = build_room_configs(
            {},
            {
                CONF_ROOMS: [
                    {
                        "primary_climate_entity_id": "climate.living_room",
                        "humidity_entity_id": "sensor.living_room_humidity",
                        "window_entity_id": "binary_sensor.living_room_window",
                        "home_target_temperature": 21.5,
                        "away_target_type": "relative",
                        "away_target_temperature": -2.0,
                    }
                ]
            },
        )

        entity = ClimateRelayCoreRoomClimateEntity(
            "entry-1",
            hass,
            global_runtime,
            room_config,
        )
        return entity

    async def test_entity_uses_home_target_and_exposes_sparse_context(self) -> None:
        entity = self._build_entity(
            primary_state=SimpleNamespace(
                state="heat",
                attributes={
                    "temperature": 20.0,
                    "current_temperature": 19.2,
                    "hvac_modes": ["off", "heat"],
                },
            ),
            humidity_state=SimpleNamespace(state="47.5", attributes={}),
            window_state=SimpleNamespace(state="off", attributes={}),
        )

        self.assertEqual(entity.hvac_mode, HVACMode.HEAT)
        self.assertEqual(entity.hvac_modes, [HVACMode.OFF, HVACMode.HEAT])
        self.assertEqual(entity.target_temperature, 21.5)
        self.assertEqual(entity.current_temperature, 19.2)
        self.assertEqual(entity.current_humidity, 47.5)
        self.assertEqual(entity.extra_state_attributes[ATTR_ACTIVE_CONTROL_CONTEXT], "schedule")
        self.assertNotIn(ATTR_DEGRADATION_STATUS, entity.extra_state_attributes)
        self.assertEqual(
            entity.extra_state_attributes[ATTR_PRIMARY_CLIMATE_ENTITY_ID],
            "climate.living_room",
        )
        self.assertEqual(
            entity.extra_state_attributes[ATTR_HUMIDITY_ENTITY_ID],
            "sensor.living_room_humidity",
        )
        self.assertEqual(
            entity.extra_state_attributes[ATTR_WINDOW_ENTITY_ID],
            "binary_sensor.living_room_window",
        )

    async def test_entity_sets_suggested_area_on_device_info_when_available(self) -> None:
        entity = self._build_entity(
            primary_state=SimpleNamespace(state="heat", attributes={}),
        )
        entity._room_config = replace(entity._room_config, area_name="Living Room")
        entity._attr_device_info["suggested_area"] = entity._room_config.area_name

        self.assertEqual(entity.device_info["suggested_area"], "Living Room")

    async def test_entity_resolves_relative_away_target_from_home_target(self) -> None:
        entity = self._build_entity(
            effective_presence=EffectivePresence.AWAY,
            primary_state=SimpleNamespace(
                state="heat",
                attributes={"temperature": 19.0, "current_temperature": 18.0},
            ),
        )

        self.assertEqual(entity.target_temperature, 19.5)

    async def test_entity_marks_optional_sensor_unavailability_as_degraded(self) -> None:
        entity = self._build_entity(
            primary_state=SimpleNamespace(
                state="heat",
                attributes={"temperature": 20.0, "current_temperature": 19.0},
            ),
            humidity_state=SimpleNamespace(state="unavailable", attributes={}),
        )

        self.assertEqual(
            entity.extra_state_attributes[ATTR_DEGRADATION_STATUS],
            "optional_sensor_unavailable",
        )
        self.assertEqual(entity.target_temperature, 21.5)

    async def test_entity_uses_fallback_when_primary_climate_is_missing(self) -> None:
        entity = self._build_entity(primary_state=None)

        self.assertEqual(entity.hvac_mode, HVACMode.HEAT)
        self.assertEqual(entity.target_temperature, 16.5)
        self.assertIsNone(entity.current_temperature)
        self.assertEqual(entity.hvac_modes, [HVACMode.HEAT])
        self.assertEqual(entity.extra_state_attributes[ATTR_ACTIVE_CONTROL_CONTEXT], "fallback")
        self.assertEqual(
            entity.extra_state_attributes[ATTR_DEGRADATION_STATUS],
            "required_component_fallback",
        )

    async def test_entity_falls_back_for_unknown_hvac_mode_and_invalid_hvac_modes(self) -> None:
        entity = self._build_entity(
            primary_state=SimpleNamespace(
                state="invalid_mode",
                attributes={"hvac_modes": ["heat", "bogus"], "current_temperature": "bad"},
            )
        )

        self.assertEqual(entity.hvac_mode, HVACMode.HEAT)
        self.assertEqual(entity.hvac_modes, [HVACMode.HEAT])
        self.assertIsNone(entity.current_temperature)

    async def test_entity_returns_none_for_non_numeric_humidity(self) -> None:
        entity = self._build_entity(
            primary_state=SimpleNamespace(state="heat", attributes={"current_temperature": 19.0}),
            humidity_state=SimpleNamespace(state="not-a-number", attributes={}),
        )

        self.assertIsNone(entity.current_humidity)

    async def test_entity_handles_missing_optional_sources_without_extra_attributes(self) -> None:
        hass = Mock()
        hass.states.get = Mock(return_value=SimpleNamespace(state="heat", attributes={}))
        global_runtime = Mock()
        global_runtime.effective_presence = EffectivePresence.HOME
        global_runtime.config = build_global_config({}, {})
        global_runtime.subscribe = Mock(return_value=lambda: None)
        (room_config,) = build_room_configs(
            {},
            {
                CONF_ROOMS: [
                    {
                        "primary_climate_entity_id": "climate.office",
                        "home_target_temperature": 20.0,
                        "away_target_type": "absolute",
                        "away_target_temperature": 17.0,
                    }
                ]
            },
        )

        entity = ClimateRelayCoreRoomClimateEntity(
            "entry-1",
            hass,
            global_runtime,
            room_config,
        )

        self.assertIsNone(entity.current_humidity)
        self.assertNotIn(ATTR_HUMIDITY_ENTITY_ID, entity.extra_state_attributes)
        self.assertNotIn(ATTR_WINDOW_ENTITY_ID, entity.extra_state_attributes)

    async def test_entity_registers_runtime_and_state_listeners(self) -> None:
        entity = self._build_entity(
            primary_state=SimpleNamespace(state="heat", attributes={}),
            humidity_state=SimpleNamespace(state="50", attributes={}),
            window_state=SimpleNamespace(state="off", attributes={}),
        )
        entity.async_on_remove = Mock()
        entity.async_write_ha_state = Mock()

        with patch.object(
            climate_platform,
            "async_track_state_change_event",
            return_value=lambda: None,
        ) as track_state_change:
            await entity.async_added_to_hass()

        entity._handle_runtime_update()
        entity._handle_source_state_change(None)

        self.assertEqual(entity.async_on_remove.call_count, 2)
        track_state_change.assert_called_once()
        tracked_entities = track_state_change.call_args.args[1]
        self.assertEqual(
            tracked_entities,
            [
                "climate.living_room",
                "sensor.living_room_humidity",
                "binary_sensor.living_room_window",
            ],
        )
        self.assertEqual(entity.async_write_ha_state.call_count, 2)

    async def test_is_unavailable_distinguishes_none_and_unknown_states(self) -> None:
        self.assertFalse(_is_unavailable(None))
        self.assertTrue(_is_unavailable(SimpleNamespace(state="unknown")))
        self.assertTrue(_is_unavailable(SimpleNamespace(state="unavailable")))
        self.assertFalse(_is_unavailable(SimpleNamespace(state="off")))

    async def test_setup_entry_adds_room_entity_when_room_is_configured(self) -> None:
        hass = Mock()
        hass.data = {
            DOMAIN: {
                "entry-1": {
                    "runtime": Mock(
                        effective_presence=EffectivePresence.HOME,
                        config=build_global_config({}, {}),
                    ),
                    "room_configs": build_room_configs(
                        {},
                        {
                            CONF_ROOMS: [
                                {
                                    "primary_climate_entity_id": "climate.living_room",
                                    "home_target_temperature": 21.0,
                                    "away_target_type": "absolute",
                                    "away_target_temperature": 17.0,
                                }
                            ]
                        },
                    ),
                    "title": "Climate Relay",
                }
            }
        }
        entry = SimpleNamespace(entry_id="entry-1", title="Climate Relay")
        async_add_entities = Mock()

        await async_setup_entry(hass, entry, async_add_entities)

        async_add_entities.assert_called_once()
        (entity,) = async_add_entities.call_args.args[0]
        self.assertIsInstance(entity, ClimateRelayCoreRoomClimateEntity)

    async def test_setup_entry_adds_no_entities_when_no_room_is_configured(self) -> None:
        hass = Mock()
        hass.data = {
            DOMAIN: {
                "entry-1": {
                    "runtime": Mock(
                        effective_presence=EffectivePresence.HOME,
                        config=build_global_config({}, {}),
                    ),
                    "room_configs": (),
                    "title": "Climate Relay",
                }
            }
        }
        entry = SimpleNamespace(entry_id="entry-1", title="Climate Relay")
        async_add_entities = Mock()

        await async_setup_entry(hass, entry, async_add_entities)

        async_add_entities.assert_called_once_with([])
