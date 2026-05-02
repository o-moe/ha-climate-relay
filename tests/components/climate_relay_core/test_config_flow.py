"""Config flow tests."""

from __future__ import annotations

from types import SimpleNamespace
from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock, Mock, patch

import voluptuous as vol
from homeassistant.helpers import selector

from custom_components.climate_relay_core.config_flow import (
    CONF_PROFILE_ACTION,
    CONF_PROFILE_INDEX,
    PROFILE_ACTION_ADD,
    PROFILE_ACTION_EDIT,
    PROFILE_ACTION_FINISH,
    PROFILE_ACTION_REMOVE,
    ClimateRelayCoreConfigFlow,
    ClimateRelayCoreOptionsFlow,
    _build_options_schema,
    _build_profile_select_schema,
    _build_profiles_schema,
    _build_reset_time_schema,
    _build_room_schema,
    _build_window_custom_temperature_schema,
    _merge_room_submission,
    _normalize_bool,
    _normalize_options_values,
    _normalize_person_entity_ids,
    _normalize_reset_time,
    _normalize_room_options,
    _normalize_select_value,
    _normalize_time_field_value,
    _resolve_entity_id,
    _resolve_room_entity_ids,
    _unwrap_selector_value,
)
from custom_components.climate_relay_core.const import (
    CONF_AWAY_TARGET_TEMPERATURE,
    CONF_AWAY_TARGET_TYPE,
    CONF_FALLBACK_TEMPERATURE,
    CONF_HOME_TARGET_TEMPERATURE,
    CONF_HUMIDITY_ENTITY_ID,
    CONF_MANUAL_OVERRIDE_RESET_ENABLED,
    CONF_MANUAL_OVERRIDE_RESET_TIME,
    CONF_PERSON_ENTITY_IDS,
    CONF_PRIMARY_CLIMATE_ENTITY_ID,
    CONF_ROOMS,
    CONF_SCHEDULE_HOME_END,
    CONF_SCHEDULE_HOME_START,
    CONF_SIMULATION_MODE,
    CONF_UNKNOWN_STATE_HANDLING,
    CONF_VERBOSE_LOGGING,
    CONF_WINDOW_ACTION_TYPE,
    CONF_WINDOW_CUSTOM_TEMPERATURE,
    CONF_WINDOW_ENTITY_ID,
    CONF_WINDOW_OPEN_DELAY_SECONDS,
    DEFAULT_FALLBACK_TEMPERATURE,
    DEFAULT_NAME,
    DEFAULT_UNKNOWN_STATE_HANDLING,
    DEFAULT_WINDOW_ACTION_TYPE,
    DEFAULT_WINDOW_OPEN_DELAY_SECONDS,
    DOMAIN,
)


def _resolved_area() -> SimpleNamespace:
    """Return a resolved Home Assistant area for tests."""
    return SimpleNamespace(area_id="living_room", area_name="Living Room")


class ConfigFlowTests(IsolatedAsyncioTestCase):
    """Test config flow behavior."""

    async def test_user_step_without_input_shows_form(self) -> None:
        flow = ClimateRelayCoreConfigFlow()
        expected_result = {"type": "form"}
        flow.async_show_form = Mock(return_value=expected_result)

        result = await flow.async_step_user()

        self.assertEqual(result, expected_result)
        flow.async_show_form.assert_called_once()
        self.assertEqual(flow.async_show_form.call_args.kwargs["step_id"], "user")
        schema = flow.async_show_form.call_args.kwargs["data_schema"]
        self.assertEqual(schema({}), {"name": DEFAULT_NAME})

    async def test_user_step_with_input_creates_entry(self) -> None:
        flow = ClimateRelayCoreConfigFlow()
        flow.async_set_unique_id = AsyncMock()
        flow._abort_if_unique_id_configured = Mock()
        expected_result = {"type": "create_entry"}
        flow.async_create_entry = Mock(return_value=expected_result)

        result = await flow.async_step_user({"name": "My Dashboard"})

        self.assertEqual(result, expected_result)
        flow.async_set_unique_id.assert_awaited_once_with(DOMAIN)
        flow._abort_if_unique_id_configured.assert_called_once_with()
        flow.async_create_entry.assert_called_once_with(
            title="My Dashboard",
            data={
                CONF_PERSON_ENTITY_IDS: [],
                CONF_UNKNOWN_STATE_HANDLING: DEFAULT_UNKNOWN_STATE_HANDLING,
                CONF_FALLBACK_TEMPERATURE: DEFAULT_FALLBACK_TEMPERATURE,
                CONF_MANUAL_OVERRIDE_RESET_ENABLED: False,
                CONF_MANUAL_OVERRIDE_RESET_TIME: None,
                CONF_SIMULATION_MODE: False,
                CONF_VERBOSE_LOGGING: False,
            },
        )


class OptionsFlowTests(IsolatedAsyncioTestCase):
    """Test options flow behavior."""

    async def test_init_step_without_input_shows_form(self) -> None:
        config_entry = Mock()
        config_entry.options = {}
        flow = ClimateRelayCoreOptionsFlow(config_entry)
        expected_result = {"type": "form"}
        flow.async_show_form = Mock(return_value=expected_result)

        result = await flow.async_step_init()

        self.assertEqual(result, expected_result)
        flow.async_show_form.assert_called_once()
        self.assertEqual(flow.async_show_form.call_args.kwargs["step_id"], "init")
        schema = flow.async_show_form.call_args.kwargs["data_schema"]
        validators = schema.schema
        person_entities = validators[
            next(key for key in validators if key.schema == CONF_PERSON_ENTITY_IDS)
        ]
        unknown_handling = validators[
            next(key for key in validators if key.schema == CONF_UNKNOWN_STATE_HANDLING)
        ]
        fallback_temperature = validators[
            next(key for key in validators if key.schema == CONF_FALLBACK_TEMPERATURE)
        ]
        reset_enabled = validators[
            next(key for key in validators if key.schema == CONF_MANUAL_OVERRIDE_RESET_ENABLED)
        ]
        simulation_mode = validators[
            next(key for key in validators if key.schema == CONF_SIMULATION_MODE)
        ]
        verbose_logging = validators[
            next(key for key in validators if key.schema == CONF_VERBOSE_LOGGING)
        ]

        self.assertIsInstance(person_entities, selector.EntitySelector)
        self.assertIsInstance(unknown_handling, selector.SelectSelector)
        self.assertIsInstance(fallback_temperature, selector.NumberSelector)
        self.assertIsInstance(reset_enabled, selector.BooleanSelector)
        self.assertFalse(any(key.schema == CONF_MANUAL_OVERRIDE_RESET_TIME for key in validators))
        self.assertIsInstance(simulation_mode, selector.BooleanSelector)
        self.assertIsInstance(verbose_logging, selector.BooleanSelector)

    async def test_init_step_with_input_creates_options_entry(self) -> None:
        config_entry = Mock()
        config_entry.options = {}
        flow = ClimateRelayCoreOptionsFlow(config_entry)
        flow.hass = Mock()
        expected_form_result = {"type": "form"}
        expected_entry_result = {"type": "create_entry"}
        flow.async_show_form = Mock(return_value=expected_form_result)
        flow.async_create_entry = Mock(return_value=expected_entry_result)

        result = await flow.async_step_init(
            {
                CONF_PERSON_ENTITY_IDS: ["person.alice", "person.bob"],
                CONF_UNKNOWN_STATE_HANDLING: "home",
                CONF_FALLBACK_TEMPERATURE: 18.5,
                CONF_MANUAL_OVERRIDE_RESET_ENABLED: True,
                CONF_SIMULATION_MODE: True,
                CONF_VERBOSE_LOGGING: True,
            }
        )

        self.assertEqual(result, expected_form_result)
        self.assertEqual(flow.async_show_form.call_args.kwargs["step_id"], "reset_time")

        result = await flow.async_step_reset_time({CONF_MANUAL_OVERRIDE_RESET_TIME: "05:30"})

        self.assertEqual(result, expected_form_result)
        self.assertEqual(flow.async_show_form.call_args.kwargs["step_id"], "profiles")

        with patch(
            "custom_components.climate_relay_core.config_flow._resolve_area_reference",
            return_value=_resolved_area(),
        ):
            result = await flow.async_step_room(
                {
                    CONF_PRIMARY_CLIMATE_ENTITY_ID: "climate.living_room",
                    CONF_HUMIDITY_ENTITY_ID: "sensor.living_room_humidity",
                    CONF_WINDOW_ENTITY_ID: "binary_sensor.living_room_window",
                    CONF_HOME_TARGET_TEMPERATURE: 20.5,
                    CONF_AWAY_TARGET_TYPE: "relative",
                    CONF_AWAY_TARGET_TEMPERATURE: -2.0,
                    CONF_SCHEDULE_HOME_START: "06:30",
                    CONF_SCHEDULE_HOME_END: "22:15",
                }
            )

        self.assertEqual(result, expected_entry_result)
        flow.async_create_entry.assert_called_once_with(
            title="",
            data={
                CONF_PERSON_ENTITY_IDS: ["person.alice", "person.bob"],
                CONF_UNKNOWN_STATE_HANDLING: "home",
                CONF_FALLBACK_TEMPERATURE: 18.5,
                CONF_MANUAL_OVERRIDE_RESET_ENABLED: True,
                CONF_MANUAL_OVERRIDE_RESET_TIME: "05:30:00",
                CONF_SIMULATION_MODE: True,
                CONF_VERBOSE_LOGGING: True,
                CONF_ROOMS: [
                    {
                        CONF_PRIMARY_CLIMATE_ENTITY_ID: "climate.living_room",
                        CONF_HUMIDITY_ENTITY_ID: "sensor.living_room_humidity",
                        CONF_WINDOW_ENTITY_ID: "binary_sensor.living_room_window",
                        CONF_WINDOW_ACTION_TYPE: DEFAULT_WINDOW_ACTION_TYPE,
                        CONF_WINDOW_CUSTOM_TEMPERATURE: None,
                        CONF_WINDOW_OPEN_DELAY_SECONDS: DEFAULT_WINDOW_OPEN_DELAY_SECONDS,
                        CONF_HOME_TARGET_TEMPERATURE: 20.5,
                        CONF_AWAY_TARGET_TYPE: "relative",
                        CONF_AWAY_TARGET_TEMPERATURE: -2.0,
                        CONF_SCHEDULE_HOME_START: "06:30",
                        CONF_SCHEDULE_HOME_END: "22:15",
                    }
                ],
            },
        )

    async def test_init_step_normalizes_selector_dict_values(self) -> None:
        config_entry = Mock()
        config_entry.options = {}
        flow = ClimateRelayCoreOptionsFlow(config_entry)
        flow.hass = Mock()
        expected_result = {"type": "create_entry"}
        flow.async_show_form = Mock(return_value={"type": "form"})
        flow.async_create_entry = Mock(return_value=expected_result)

        result = await flow.async_step_init(
            {
                CONF_PERSON_ENTITY_IDS: [{"entity_id": "person.alice"}],
                CONF_UNKNOWN_STATE_HANDLING: "away",
                CONF_FALLBACK_TEMPERATURE: 20.0,
                CONF_MANUAL_OVERRIDE_RESET_ENABLED: False,
                CONF_MANUAL_OVERRIDE_RESET_TIME: "",
                CONF_SIMULATION_MODE: False,
                CONF_VERBOSE_LOGGING: False,
            }
        )

        self.assertEqual(result, {"type": "form"})
        self.assertEqual(flow.async_show_form.call_args.kwargs["step_id"], "profiles")

        with patch(
            "custom_components.climate_relay_core.config_flow._resolve_area_reference",
            return_value=_resolved_area(),
        ):
            result = await flow.async_step_room(
                {
                    CONF_PRIMARY_CLIMATE_ENTITY_ID: "climate.living_room",
                    CONF_HOME_TARGET_TEMPERATURE: 21.0,
                    CONF_AWAY_TARGET_TYPE: "absolute",
                    CONF_AWAY_TARGET_TEMPERATURE: 17.0,
                }
            )

        self.assertEqual(result, expected_result)
        flow.async_create_entry.assert_called_once_with(
            title="",
            data={
                CONF_PERSON_ENTITY_IDS: ["person.alice"],
                CONF_UNKNOWN_STATE_HANDLING: "away",
                CONF_FALLBACK_TEMPERATURE: 20.0,
                CONF_MANUAL_OVERRIDE_RESET_ENABLED: False,
                CONF_MANUAL_OVERRIDE_RESET_TIME: None,
                CONF_SIMULATION_MODE: False,
                CONF_VERBOSE_LOGGING: False,
                CONF_ROOMS: [
                    {
                        CONF_PRIMARY_CLIMATE_ENTITY_ID: "climate.living_room",
                        CONF_HUMIDITY_ENTITY_ID: None,
                        CONF_WINDOW_ENTITY_ID: None,
                        CONF_WINDOW_ACTION_TYPE: DEFAULT_WINDOW_ACTION_TYPE,
                        CONF_WINDOW_CUSTOM_TEMPERATURE: None,
                        CONF_WINDOW_OPEN_DELAY_SECONDS: DEFAULT_WINDOW_OPEN_DELAY_SECONDS,
                        CONF_HOME_TARGET_TEMPERATURE: 21.0,
                        CONF_AWAY_TARGET_TYPE: "absolute",
                        CONF_AWAY_TARGET_TEMPERATURE: 17.0,
                        CONF_SCHEDULE_HOME_START: "06:00:00",
                        CONF_SCHEDULE_HOME_END: "22:00:00",
                    }
                ],
            },
        )

    async def test_init_step_normalizes_wrapped_selector_values(self) -> None:
        config_entry = Mock()
        config_entry.options = {}
        flow = ClimateRelayCoreOptionsFlow(config_entry)
        flow.hass = Mock()
        expected_result = {"type": "create_entry"}
        flow.async_show_form = Mock(return_value={"type": "form"})
        flow.async_create_entry = Mock(return_value=expected_result)

        result = await flow.async_step_init(
            {
                CONF_PERSON_ENTITY_IDS: {"value": [{"value": "person.alice"}]},
                CONF_UNKNOWN_STATE_HANDLING: {"value": "home"},
                CONF_FALLBACK_TEMPERATURE: 20.0,
                CONF_MANUAL_OVERRIDE_RESET_ENABLED: {"value": "off"},
                CONF_MANUAL_OVERRIDE_RESET_TIME: {"value": "06:15"},
                CONF_SIMULATION_MODE: {"value": "on"},
                CONF_VERBOSE_LOGGING: {"value": False},
            }
        )

        self.assertEqual(result, {"type": "form"})
        self.assertEqual(flow.async_show_form.call_args.kwargs["step_id"], "profiles")

        with patch(
            "custom_components.climate_relay_core.config_flow._resolve_area_reference",
            return_value=_resolved_area(),
        ):
            result = await flow.async_step_room(
                {
                    CONF_PRIMARY_CLIMATE_ENTITY_ID: {"value": "climate.living_room"},
                    CONF_HUMIDITY_ENTITY_ID: {"value": "sensor.living_room_humidity"},
                    CONF_WINDOW_ENTITY_ID: {"value": "binary_sensor.living_room_window"},
                    CONF_HOME_TARGET_TEMPERATURE: 21.0,
                    CONF_AWAY_TARGET_TYPE: {"value": "absolute"},
                    CONF_AWAY_TARGET_TEMPERATURE: 17.0,
                }
            )

        self.assertEqual(result, expected_result)
        flow.async_create_entry.assert_called_once_with(
            title="",
            data={
                CONF_PERSON_ENTITY_IDS: ["person.alice"],
                CONF_UNKNOWN_STATE_HANDLING: "home",
                CONF_FALLBACK_TEMPERATURE: 20.0,
                CONF_MANUAL_OVERRIDE_RESET_ENABLED: False,
                CONF_MANUAL_OVERRIDE_RESET_TIME: None,
                CONF_SIMULATION_MODE: True,
                CONF_VERBOSE_LOGGING: False,
                CONF_ROOMS: [
                    {
                        CONF_PRIMARY_CLIMATE_ENTITY_ID: "climate.living_room",
                        CONF_HUMIDITY_ENTITY_ID: "sensor.living_room_humidity",
                        CONF_WINDOW_ENTITY_ID: "binary_sensor.living_room_window",
                        CONF_WINDOW_ACTION_TYPE: DEFAULT_WINDOW_ACTION_TYPE,
                        CONF_WINDOW_CUSTOM_TEMPERATURE: None,
                        CONF_WINDOW_OPEN_DELAY_SECONDS: DEFAULT_WINDOW_OPEN_DELAY_SECONDS,
                        CONF_HOME_TARGET_TEMPERATURE: 21.0,
                        CONF_AWAY_TARGET_TYPE: "absolute",
                        CONF_AWAY_TARGET_TEMPERATURE: 17.0,
                        CONF_SCHEDULE_HOME_START: "06:00:00",
                        CONF_SCHEDULE_HOME_END: "22:00:00",
                    }
                ],
            },
        )

    async def test_room_step_resolves_registry_uuids_before_area_validation(self) -> None:
        config_entry = Mock()
        config_entry.options = {}
        flow = ClimateRelayCoreOptionsFlow(config_entry)
        flow.hass = Mock()
        flow.async_show_form = Mock(return_value={"type": "form"})
        flow.async_create_entry = Mock(return_value={"type": "create_entry"})
        await flow.async_step_init(
            {
                CONF_PERSON_ENTITY_IDS: ["person.alice"],
                CONF_UNKNOWN_STATE_HANDLING: DEFAULT_UNKNOWN_STATE_HANDLING,
                CONF_FALLBACK_TEMPERATURE: DEFAULT_FALLBACK_TEMPERATURE,
                CONF_MANUAL_OVERRIDE_RESET_ENABLED: False,
                CONF_SIMULATION_MODE: False,
                CONF_VERBOSE_LOGGING: False,
            }
        )

        with (
            patch(
                "custom_components.climate_relay_core.config_flow.er.async_get",
                return_value="registry",
            ),
            patch(
                "custom_components.climate_relay_core.config_flow.er.async_resolve_entity_id",
                side_effect=lambda _registry, value: {
                    "uuid-climate": "climate.living_room",
                    "uuid-humidity": "sensor.living_room_humidity",
                }[value],
            ),
            patch(
                "custom_components.climate_relay_core.config_flow._resolve_area_reference",
                return_value=_resolved_area(),
            ),
        ):
            result = await flow.async_step_room(
                {
                    CONF_PRIMARY_CLIMATE_ENTITY_ID: "uuid-climate",
                    CONF_HUMIDITY_ENTITY_ID: "uuid-humidity",
                    CONF_HOME_TARGET_TEMPERATURE: 21.0,
                    CONF_AWAY_TARGET_TYPE: "absolute",
                    CONF_AWAY_TARGET_TEMPERATURE: 17.0,
                }
            )

        self.assertEqual(result, {"type": "create_entry"})
        flow.async_create_entry.assert_called_once_with(
            title="",
            data={
                CONF_PERSON_ENTITY_IDS: ["person.alice"],
                CONF_UNKNOWN_STATE_HANDLING: DEFAULT_UNKNOWN_STATE_HANDLING,
                CONF_FALLBACK_TEMPERATURE: DEFAULT_FALLBACK_TEMPERATURE,
                CONF_MANUAL_OVERRIDE_RESET_ENABLED: False,
                CONF_MANUAL_OVERRIDE_RESET_TIME: None,
                CONF_SIMULATION_MODE: False,
                CONF_VERBOSE_LOGGING: False,
                CONF_ROOMS: [
                    {
                        CONF_PRIMARY_CLIMATE_ENTITY_ID: "climate.living_room",
                        CONF_HUMIDITY_ENTITY_ID: "sensor.living_room_humidity",
                        CONF_WINDOW_ENTITY_ID: None,
                        CONF_WINDOW_ACTION_TYPE: DEFAULT_WINDOW_ACTION_TYPE,
                        CONF_WINDOW_CUSTOM_TEMPERATURE: None,
                        CONF_WINDOW_OPEN_DELAY_SECONDS: DEFAULT_WINDOW_OPEN_DELAY_SECONDS,
                        CONF_HOME_TARGET_TEMPERATURE: 21.0,
                        CONF_AWAY_TARGET_TYPE: "absolute",
                        CONF_AWAY_TARGET_TEMPERATURE: 17.0,
                        CONF_SCHEDULE_HOME_START: "06:00:00",
                        CONF_SCHEDULE_HOME_END: "22:00:00",
                    }
                ],
            },
        )

    async def test_init_step_allows_missing_reset_time_when_disabled(self) -> None:
        config_entry = Mock()
        config_entry.options = {}
        flow = ClimateRelayCoreOptionsFlow(config_entry)
        flow.hass = Mock()
        expected_result = {"type": "create_entry"}
        flow.async_show_form = Mock(return_value={"type": "form"})
        flow.async_create_entry = Mock(return_value=expected_result)

        result = await flow.async_step_init(
            {
                CONF_PERSON_ENTITY_IDS: ["person.alice"],
                CONF_UNKNOWN_STATE_HANDLING: "away",
                CONF_FALLBACK_TEMPERATURE: 19.0,
                CONF_MANUAL_OVERRIDE_RESET_ENABLED: False,
                CONF_SIMULATION_MODE: True,
                CONF_VERBOSE_LOGGING: False,
            }
        )

        self.assertEqual(result, {"type": "form"})

        with patch(
            "custom_components.climate_relay_core.config_flow._resolve_area_reference",
            return_value=_resolved_area(),
        ):
            result = await flow.async_step_room(
                {
                    CONF_PRIMARY_CLIMATE_ENTITY_ID: "climate.living_room",
                    CONF_HOME_TARGET_TEMPERATURE: 21.0,
                    CONF_AWAY_TARGET_TYPE: "absolute",
                    CONF_AWAY_TARGET_TEMPERATURE: 18.0,
                }
            )

        self.assertEqual(result, expected_result)
        flow.async_create_entry.assert_called_once_with(
            title="",
            data={
                CONF_PERSON_ENTITY_IDS: ["person.alice"],
                CONF_UNKNOWN_STATE_HANDLING: "away",
                CONF_FALLBACK_TEMPERATURE: 19.0,
                CONF_MANUAL_OVERRIDE_RESET_ENABLED: False,
                CONF_MANUAL_OVERRIDE_RESET_TIME: None,
                CONF_SIMULATION_MODE: True,
                CONF_VERBOSE_LOGGING: False,
                CONF_ROOMS: [
                    {
                        CONF_PRIMARY_CLIMATE_ENTITY_ID: "climate.living_room",
                        CONF_HUMIDITY_ENTITY_ID: None,
                        CONF_WINDOW_ENTITY_ID: None,
                        CONF_WINDOW_ACTION_TYPE: DEFAULT_WINDOW_ACTION_TYPE,
                        CONF_WINDOW_CUSTOM_TEMPERATURE: None,
                        CONF_WINDOW_OPEN_DELAY_SECONDS: DEFAULT_WINDOW_OPEN_DELAY_SECONDS,
                        CONF_HOME_TARGET_TEMPERATURE: 21.0,
                        CONF_AWAY_TARGET_TYPE: "absolute",
                        CONF_AWAY_TARGET_TEMPERATURE: 18.0,
                        CONF_SCHEDULE_HOME_START: "06:00:00",
                        CONF_SCHEDULE_HOME_END: "22:00:00",
                    }
                ],
            },
        )

    async def test_init_step_rejects_missing_person_entities(self) -> None:
        config_entry = Mock()
        config_entry.options = {}
        flow = ClimateRelayCoreOptionsFlow(config_entry)
        flow.async_show_form = Mock(return_value={"type": "form"})

        await flow.async_step_init(
            {
                CONF_UNKNOWN_STATE_HANDLING: DEFAULT_UNKNOWN_STATE_HANDLING,
                CONF_FALLBACK_TEMPERATURE: DEFAULT_FALLBACK_TEMPERATURE,
                CONF_MANUAL_OVERRIDE_RESET_ENABLED: False,
                CONF_MANUAL_OVERRIDE_RESET_TIME: "",
                CONF_SIMULATION_MODE: False,
                CONF_VERBOSE_LOGGING: False,
            }
        )

        self.assertEqual(
            flow.async_show_form.call_args.kwargs["errors"],
            {CONF_PERSON_ENTITY_IDS: "person_entities_required"},
        )

    async def test_init_step_rejects_missing_reset_time_when_enabled(self) -> None:
        config_entry = Mock()
        config_entry.options = {}
        flow = ClimateRelayCoreOptionsFlow(config_entry)
        flow.async_show_form = Mock(return_value={"type": "form"})

        await flow.async_step_init(
            {
                CONF_PERSON_ENTITY_IDS: ["person.alice"],
                CONF_UNKNOWN_STATE_HANDLING: DEFAULT_UNKNOWN_STATE_HANDLING,
                CONF_FALLBACK_TEMPERATURE: DEFAULT_FALLBACK_TEMPERATURE,
                CONF_MANUAL_OVERRIDE_RESET_ENABLED: True,
                CONF_SIMULATION_MODE: False,
                CONF_VERBOSE_LOGGING: False,
            }
        )

        flow.async_show_form.reset_mock()
        await flow.async_step_reset_time({CONF_MANUAL_OVERRIDE_RESET_TIME: ""})

        self.assertEqual(
            flow.async_show_form.call_args.kwargs["errors"],
            {CONF_MANUAL_OVERRIDE_RESET_TIME: "reset_time_required"},
        )

    async def test_init_step_routes_enabled_reset_to_second_step(self) -> None:
        config_entry = Mock()
        config_entry.options = {}
        flow = ClimateRelayCoreOptionsFlow(config_entry)
        flow.async_show_form = Mock(return_value={"type": "form"})

        await flow.async_step_init(
            {
                CONF_PERSON_ENTITY_IDS: ["person.alice"],
                CONF_UNKNOWN_STATE_HANDLING: DEFAULT_UNKNOWN_STATE_HANDLING,
                CONF_FALLBACK_TEMPERATURE: DEFAULT_FALLBACK_TEMPERATURE,
                CONF_MANUAL_OVERRIDE_RESET_ENABLED: True,
                CONF_MANUAL_OVERRIDE_RESET_TIME: None,
                CONF_SIMULATION_MODE: True,
                CONF_VERBOSE_LOGGING: False,
            }
        )

        self.assertEqual(flow.async_show_form.call_args.kwargs["step_id"], "reset_time")

    async def test_init_step_routes_valid_input_to_room_step(self) -> None:
        config_entry = Mock()
        config_entry.options = {}
        flow = ClimateRelayCoreOptionsFlow(config_entry)
        flow.async_show_form = Mock(return_value={"type": "form"})

        await flow.async_step_init(
            {
                CONF_PERSON_ENTITY_IDS: ["person.alice"],
                CONF_UNKNOWN_STATE_HANDLING: DEFAULT_UNKNOWN_STATE_HANDLING,
                CONF_FALLBACK_TEMPERATURE: DEFAULT_FALLBACK_TEMPERATURE,
                CONF_MANUAL_OVERRIDE_RESET_ENABLED: False,
                CONF_SIMULATION_MODE: False,
                CONF_VERBOSE_LOGGING: False,
            }
        )

        self.assertEqual(flow.async_show_form.call_args.kwargs["step_id"], "profiles")

    async def test_profiles_step_adds_edits_removes_and_finishes_multiple_profiles(self) -> None:
        config_entry = Mock()
        config_entry.options = {}
        flow = ClimateRelayCoreOptionsFlow(config_entry)
        flow.hass = Mock()
        flow.async_show_form = Mock(return_value={"type": "form"})
        flow.async_create_entry = Mock(return_value={"type": "create_entry"})
        await flow.async_step_init(
            {
                CONF_PERSON_ENTITY_IDS: ["person.alice"],
                CONF_UNKNOWN_STATE_HANDLING: DEFAULT_UNKNOWN_STATE_HANDLING,
                CONF_FALLBACK_TEMPERATURE: DEFAULT_FALLBACK_TEMPERATURE,
                CONF_MANUAL_OVERRIDE_RESET_ENABLED: False,
                CONF_SIMULATION_MODE: False,
                CONF_VERBOSE_LOGGING: False,
            }
        )

        result = await flow.async_step_profiles({CONF_PROFILE_ACTION: PROFILE_ACTION_ADD})
        self.assertEqual(result, {"type": "form"})
        self.assertEqual(flow.async_show_form.call_args.kwargs["step_id"], "room")

        with patch(
            "custom_components.climate_relay_core.config_flow._resolve_area_reference",
            return_value=SimpleNamespace(area_id="office", area_name="Office"),
        ):
            result = await flow.async_step_room(
                {
                    CONF_PRIMARY_CLIMATE_ENTITY_ID: "climate.office",
                    CONF_HOME_TARGET_TEMPERATURE: 20.0,
                    CONF_AWAY_TARGET_TYPE: "absolute",
                    CONF_AWAY_TARGET_TEMPERATURE: 17.0,
                }
            )
        self.assertEqual(result, {"type": "form"})
        self.assertEqual(flow.async_show_form.call_args.kwargs["step_id"], "profiles")

        await flow.async_step_profiles({CONF_PROFILE_ACTION: PROFILE_ACTION_ADD})
        with patch(
            "custom_components.climate_relay_core.config_flow._resolve_area_reference",
            side_effect=[
                SimpleNamespace(area_id="bedroom", area_name="Bedroom"),
                SimpleNamespace(area_id="office", area_name="Office"),
            ],
        ):
            result = await flow.async_step_room(
                {
                    CONF_PRIMARY_CLIMATE_ENTITY_ID: "climate.bedroom",
                    CONF_HOME_TARGET_TEMPERATURE: 19.0,
                    CONF_AWAY_TARGET_TYPE: "absolute",
                    CONF_AWAY_TARGET_TEMPERATURE: 16.0,
                }
            )
        self.assertEqual(result, {"type": "form"})
        self.assertEqual(len(flow._pending_rooms), 2)

        result = await flow.async_step_profiles({CONF_PROFILE_ACTION: PROFILE_ACTION_EDIT})
        self.assertEqual(result, {"type": "form"})
        self.assertEqual(flow.async_show_form.call_args.kwargs["step_id"], "profile_select_edit")
        result = await flow.async_step_profile_select_edit({CONF_PROFILE_INDEX: "1"})
        self.assertEqual(result, {"type": "form"})
        self.assertEqual(flow.async_show_form.call_args.kwargs["step_id"], "room")
        with patch(
            "custom_components.climate_relay_core.config_flow._resolve_area_reference",
            side_effect=[
                SimpleNamespace(area_id="bedroom", area_name="Bedroom"),
                SimpleNamespace(area_id="office", area_name="Office"),
            ],
        ):
            result = await flow.async_step_room(
                {
                    CONF_PRIMARY_CLIMATE_ENTITY_ID: "climate.bedroom",
                    CONF_HOME_TARGET_TEMPERATURE: 18.5,
                    CONF_AWAY_TARGET_TYPE: "absolute",
                    CONF_AWAY_TARGET_TEMPERATURE: 15.5,
                }
            )
        self.assertEqual(result, {"type": "form"})
        self.assertEqual(flow._pending_rooms[1][CONF_HOME_TARGET_TEMPERATURE], 18.5)

        await flow.async_step_profiles({CONF_PROFILE_ACTION: PROFILE_ACTION_REMOVE})
        result = await flow.async_step_profile_select_remove({CONF_PROFILE_INDEX: "0"})
        self.assertEqual(result, {"type": "form"})
        self.assertEqual(len(flow._pending_rooms), 1)

        result = await flow.async_step_profiles({CONF_PROFILE_ACTION: PROFILE_ACTION_FINISH})
        self.assertEqual(result, {"type": "create_entry"})
        data = flow.async_create_entry.call_args.kwargs["data"]
        self.assertEqual(data[CONF_PERSON_ENTITY_IDS], ["person.alice"])
        self.assertEqual(len(data[CONF_ROOMS]), 1)
        self.assertEqual(data[CONF_ROOMS][0][CONF_PRIMARY_CLIMATE_ENTITY_ID], "climate.bedroom")

    async def test_profiles_step_rejects_finish_edit_and_remove_without_profiles(self) -> None:
        config_entry = Mock()
        config_entry.options = {}
        flow = ClimateRelayCoreOptionsFlow(config_entry)
        flow.async_show_form = Mock(return_value={"type": "form"})

        await flow.async_step_profiles({CONF_PROFILE_ACTION: PROFILE_ACTION_FINISH})
        self.assertEqual(
            flow.async_show_form.call_args.kwargs["errors"],
            {CONF_PROFILE_ACTION: "profile_required"},
        )
        await flow.async_step_profiles({CONF_PROFILE_ACTION: PROFILE_ACTION_EDIT})
        self.assertEqual(
            flow.async_show_form.call_args.kwargs["errors"],
            {CONF_PROFILE_ACTION: "profile_required"},
        )
        await flow.async_step_profiles({CONF_PROFILE_ACTION: PROFILE_ACTION_REMOVE})
        self.assertEqual(
            flow.async_show_form.call_args.kwargs["errors"],
            {CONF_PROFILE_ACTION: "profile_required"},
        )

    async def test_profiles_step_rejects_invalid_action_payload(self) -> None:
        config_entry = Mock()
        config_entry.options = {}
        flow = ClimateRelayCoreOptionsFlow(config_entry)
        flow.async_show_form = Mock(return_value={"type": "form"})

        await flow.async_step_profiles({CONF_PROFILE_ACTION: "unsupported"})
        self.assertEqual(
            flow.async_show_form.call_args.kwargs["errors"],
            {CONF_PROFILE_ACTION: "profile_action_required"},
        )

        await flow.async_step_profiles({CONF_PROFILE_ACTION: {"value": 123}})
        self.assertEqual(flow.async_show_form.call_args.kwargs["errors"], {"base": "unknown"})

    async def test_profile_select_step_rejects_invalid_selection(self) -> None:
        config_entry = Mock()
        config_entry.options = {
            CONF_ROOMS: [
                {
                    CONF_PRIMARY_CLIMATE_ENTITY_ID: "climate.office",
                    CONF_HOME_TARGET_TEMPERATURE: 20.0,
                    CONF_AWAY_TARGET_TYPE: "absolute",
                    CONF_AWAY_TARGET_TEMPERATURE: 17.0,
                }
            ]
        }
        flow = ClimateRelayCoreOptionsFlow(config_entry)
        flow.async_show_form = Mock(return_value={"type": "form"})

        await flow.async_step_profile_select_edit({})
        self.assertEqual(
            flow.async_show_form.call_args.kwargs["errors"],
            {CONF_PROFILE_INDEX: "profile_required"},
        )

        await flow.async_step_profile_select_edit({CONF_PROFILE_INDEX: "5"})
        self.assertEqual(
            flow.async_show_form.call_args.kwargs["errors"],
            {CONF_PROFILE_INDEX: "profile_required"},
        )

        await flow.async_step_profile_select_remove({CONF_PROFILE_INDEX: "invalid"})
        self.assertEqual(flow.async_show_form.call_args.kwargs["errors"], {"base": "unknown"})

    async def test_room_step_rejects_duplicate_primary_climate_or_area(self) -> None:
        config_entry = Mock()
        config_entry.options = {
            CONF_ROOMS: [
                {
                    CONF_PRIMARY_CLIMATE_ENTITY_ID: "climate.office",
                    CONF_HOME_TARGET_TEMPERATURE: 20.0,
                    CONF_AWAY_TARGET_TYPE: "absolute",
                    CONF_AWAY_TARGET_TEMPERATURE: 17.0,
                }
            ]
        }
        flow = ClimateRelayCoreOptionsFlow(config_entry)
        flow.hass = Mock()
        flow.async_show_form = Mock(return_value={"type": "form"})
        flow._profile_management_active = True

        with patch(
            "custom_components.climate_relay_core.config_flow._resolve_area_reference",
            side_effect=[
                SimpleNamespace(area_id="office", area_name="Office"),
                SimpleNamespace(area_id="office", area_name="Office"),
            ],
        ):
            await flow.async_step_room(
                {
                    CONF_PRIMARY_CLIMATE_ENTITY_ID: "climate.bedroom",
                    CONF_HOME_TARGET_TEMPERATURE: 19.0,
                    CONF_AWAY_TARGET_TYPE: "absolute",
                    CONF_AWAY_TARGET_TEMPERATURE: 16.0,
                }
            )

        self.assertEqual(
            flow.async_show_form.call_args.kwargs["errors"],
            {CONF_PRIMARY_CLIMATE_ENTITY_ID: "profile_duplicate_area"},
        )

    async def test_room_step_rejects_missing_primary_climate_entity(self) -> None:
        config_entry = Mock()
        config_entry.options = {}
        flow = ClimateRelayCoreOptionsFlow(config_entry)
        flow.hass = Mock()
        flow.async_show_form = Mock(return_value={"type": "form"})
        await flow.async_step_init(
            {
                CONF_PERSON_ENTITY_IDS: ["person.alice"],
                CONF_UNKNOWN_STATE_HANDLING: DEFAULT_UNKNOWN_STATE_HANDLING,
                CONF_FALLBACK_TEMPERATURE: DEFAULT_FALLBACK_TEMPERATURE,
                CONF_MANUAL_OVERRIDE_RESET_ENABLED: False,
                CONF_SIMULATION_MODE: False,
                CONF_VERBOSE_LOGGING: False,
            }
        )

        await flow.async_step_room(
            {
                CONF_HOME_TARGET_TEMPERATURE: 21.0,
                CONF_AWAY_TARGET_TYPE: "absolute",
                CONF_AWAY_TARGET_TEMPERATURE: 18.0,
            }
        )

        self.assertEqual(
            flow.async_show_form.call_args.kwargs["errors"],
            {CONF_PRIMARY_CLIMATE_ENTITY_ID: "primary_climate_required"},
        )

    async def test_room_step_rejects_primary_climate_without_area_mapping(self) -> None:
        config_entry = Mock()
        config_entry.options = {}
        flow = ClimateRelayCoreOptionsFlow(config_entry)
        flow.hass = Mock()
        flow.async_show_form = Mock(return_value={"type": "form"})
        await flow.async_step_init(
            {
                CONF_PERSON_ENTITY_IDS: ["person.alice"],
                CONF_UNKNOWN_STATE_HANDLING: DEFAULT_UNKNOWN_STATE_HANDLING,
                CONF_FALLBACK_TEMPERATURE: DEFAULT_FALLBACK_TEMPERATURE,
                CONF_MANUAL_OVERRIDE_RESET_ENABLED: False,
                CONF_SIMULATION_MODE: False,
                CONF_VERBOSE_LOGGING: False,
            }
        )

        with patch(
            "custom_components.climate_relay_core.config_flow._resolve_area_reference",
            return_value=SimpleNamespace(area_id=None, area_name=None),
        ):
            await flow.async_step_room(
                {
                    CONF_PRIMARY_CLIMATE_ENTITY_ID: "climate.living_room",
                    CONF_HOME_TARGET_TEMPERATURE: 21.0,
                    CONF_AWAY_TARGET_TYPE: "absolute",
                    CONF_AWAY_TARGET_TEMPERATURE: 18.0,
                }
            )

        self.assertEqual(
            flow.async_show_form.call_args.kwargs["errors"],
            {CONF_PRIMARY_CLIMATE_ENTITY_ID: "primary_climate_area_required"},
        )

    async def test_reset_time_step_surfaces_unknown_error_for_invalid_time(self) -> None:
        config_entry = Mock()
        config_entry.options = {}
        flow = ClimateRelayCoreOptionsFlow(config_entry)
        flow.async_show_form = Mock(return_value={"type": "form"})
        await flow.async_step_init(
            {
                CONF_PERSON_ENTITY_IDS: ["person.alice"],
                CONF_UNKNOWN_STATE_HANDLING: DEFAULT_UNKNOWN_STATE_HANDLING,
                CONF_FALLBACK_TEMPERATURE: DEFAULT_FALLBACK_TEMPERATURE,
                CONF_MANUAL_OVERRIDE_RESET_ENABLED: True,
                CONF_SIMULATION_MODE: False,
                CONF_VERBOSE_LOGGING: False,
            }
        )
        flow.async_show_form.reset_mock()

        await flow.async_step_reset_time({CONF_MANUAL_OVERRIDE_RESET_TIME: "bad-time"})

        self.assertEqual(flow.async_show_form.call_args.kwargs["errors"], {"base": "unknown"})

    async def test_room_step_surfaces_unknown_error_for_invalid_entity_payload(self) -> None:
        config_entry = Mock()
        config_entry.options = {}
        flow = ClimateRelayCoreOptionsFlow(config_entry)
        flow.hass = Mock()
        flow.async_show_form = Mock(return_value={"type": "form"})
        await flow.async_step_init(
            {
                CONF_PERSON_ENTITY_IDS: ["person.alice"],
                CONF_UNKNOWN_STATE_HANDLING: DEFAULT_UNKNOWN_STATE_HANDLING,
                CONF_FALLBACK_TEMPERATURE: DEFAULT_FALLBACK_TEMPERATURE,
                CONF_MANUAL_OVERRIDE_RESET_ENABLED: False,
                CONF_SIMULATION_MODE: False,
                CONF_VERBOSE_LOGGING: False,
            }
        )

        await flow.async_step_room(
            {
                CONF_PRIMARY_CLIMATE_ENTITY_ID: 123,
                CONF_HOME_TARGET_TEMPERATURE: 21.0,
                CONF_AWAY_TARGET_TYPE: "absolute",
                CONF_AWAY_TARGET_TEMPERATURE: 18.0,
            }
        )

        self.assertEqual(flow.async_show_form.call_args.kwargs["errors"], {"base": "unknown"})

    async def test_init_step_preserves_submitted_presence_selection_when_validation_fails(
        self,
    ) -> None:
        config_entry = Mock()
        config_entry.options = {CONF_PERSON_ENTITY_IDS: ["person.alice"]}
        flow = ClimateRelayCoreOptionsFlow(config_entry)
        flow.async_show_form = Mock(return_value={"type": "form"})

        await flow.async_step_init(
            {
                CONF_PERSON_ENTITY_IDS: [],
                CONF_UNKNOWN_STATE_HANDLING: DEFAULT_UNKNOWN_STATE_HANDLING,
                CONF_FALLBACK_TEMPERATURE: DEFAULT_FALLBACK_TEMPERATURE,
                CONF_MANUAL_OVERRIDE_RESET_ENABLED: False,
                CONF_SIMULATION_MODE: False,
                CONF_VERBOSE_LOGGING: False,
            }
        )

        schema = flow.async_show_form.call_args.kwargs["data_schema"]
        defaults = {key.schema: key.default() for key in schema.schema}
        self.assertEqual(
            flow.async_show_form.call_args.kwargs["errors"],
            {CONF_PERSON_ENTITY_IDS: "person_entities_required"},
        )
        self.assertEqual(defaults[CONF_PERSON_ENTITY_IDS], [])

    async def test_init_step_surfaces_unknown_error_for_invalid_selector_payload(
        self,
    ) -> None:
        config_entry = Mock()
        config_entry.options = {}
        flow = ClimateRelayCoreOptionsFlow(config_entry)
        flow.async_show_form = Mock(return_value={"type": "form"})

        await flow.async_step_init(
            {
                CONF_PERSON_ENTITY_IDS: ["person.alice"],
                CONF_UNKNOWN_STATE_HANDLING: {"value": 123},
                CONF_FALLBACK_TEMPERATURE: DEFAULT_FALLBACK_TEMPERATURE,
                CONF_MANUAL_OVERRIDE_RESET_ENABLED: False,
                CONF_MANUAL_OVERRIDE_RESET_TIME: "",
                CONF_SIMULATION_MODE: False,
                CONF_VERBOSE_LOGGING: False,
            }
        )

        self.assertEqual(flow.async_show_form.call_args.kwargs["errors"], {"base": "unknown"})

    async def test_config_flow_returns_options_flow_handler(self) -> None:
        config_entry = Mock()

        result = ClimateRelayCoreConfigFlow.async_get_options_flow(config_entry)

        self.assertIsInstance(result, ClimateRelayCoreOptionsFlow)

    async def test_normalize_reset_time_returns_none_when_disabled(self) -> None:
        self.assertIsNone(_normalize_reset_time(False, "05:30"))

    async def test_build_options_schema_hides_reset_time_when_disabled(self) -> None:
        schema = _build_options_schema(
            {
                CONF_PERSON_ENTITY_IDS: [],
                CONF_UNKNOWN_STATE_HANDLING: DEFAULT_UNKNOWN_STATE_HANDLING,
                CONF_FALLBACK_TEMPERATURE: DEFAULT_FALLBACK_TEMPERATURE,
                CONF_MANUAL_OVERRIDE_RESET_ENABLED: False,
                CONF_MANUAL_OVERRIDE_RESET_TIME: None,
                CONF_SIMULATION_MODE: False,
                CONF_VERBOSE_LOGGING: False,
            },
            include_reset_time=False,
        )
        self.assertFalse(
            any(key.schema == CONF_MANUAL_OVERRIDE_RESET_TIME for key in schema.schema)
        )

    async def test_build_options_schema_includes_reset_time_when_enabled(self) -> None:
        schema = _build_options_schema(
            {
                CONF_PERSON_ENTITY_IDS: [],
                CONF_UNKNOWN_STATE_HANDLING: DEFAULT_UNKNOWN_STATE_HANDLING,
                CONF_FALLBACK_TEMPERATURE: DEFAULT_FALLBACK_TEMPERATURE,
                CONF_MANUAL_OVERRIDE_RESET_ENABLED: True,
                CONF_MANUAL_OVERRIDE_RESET_TIME: "06:15:00",
                CONF_SIMULATION_MODE: False,
                CONF_VERBOSE_LOGGING: False,
            },
            include_reset_time=True,
        )
        validators = schema.schema
        reset_time = validators[
            next(key for key in validators if key.schema == CONF_MANUAL_OVERRIDE_RESET_TIME)
        ]
        self.assertIsInstance(reset_time, selector.TimeSelector)

    async def test_build_reset_time_schema_uses_time_selector(self) -> None:
        schema = _build_reset_time_schema("06:15:00")
        validators = schema.schema
        reset_time = validators[
            next(key for key in validators if key.schema == CONF_MANUAL_OVERRIDE_RESET_TIME)
        ]
        self.assertIsInstance(reset_time, selector.TimeSelector)

    async def test_build_window_custom_temperature_schema_uses_text_number_selector(self) -> None:
        schema = _build_window_custom_temperature_schema(12.5)
        validators = schema.schema
        custom_temperature = validators[
            next(key for key in validators if key.schema == CONF_WINDOW_CUSTOM_TEMPERATURE)
        ]

        self.assertIsInstance(custom_temperature, selector.TextSelector)
        self.assertEqual(
            custom_temperature.config["type"],
            selector.TextSelectorType.NUMBER,
        )

    async def test_build_room_schema_uses_expected_selectors(self) -> None:
        schema = _build_room_schema(
            {
                CONF_PRIMARY_CLIMATE_ENTITY_ID: "climate.living_room",
                CONF_HUMIDITY_ENTITY_ID: None,
                CONF_WINDOW_ENTITY_ID: None,
                CONF_HOME_TARGET_TEMPERATURE: 21.0,
                CONF_AWAY_TARGET_TYPE: "absolute",
                CONF_AWAY_TARGET_TEMPERATURE: 17.0,
            }
        )
        validators = schema.schema
        primary_climate = validators[
            next(key for key in validators if key.schema == CONF_PRIMARY_CLIMATE_ENTITY_ID)
        ]
        home_target = validators[
            next(key for key in validators if key.schema == CONF_HOME_TARGET_TEMPERATURE)
        ]
        self.assertIsInstance(
            primary_climate,
            selector.EntitySelector,
        )
        self.assertIsInstance(
            validators[next(key for key in validators if key.schema == CONF_HUMIDITY_ENTITY_ID)],
            selector.EntitySelector,
        )
        self.assertIsInstance(
            validators[next(key for key in validators if key.schema == CONF_WINDOW_ENTITY_ID)],
            selector.EntitySelector,
        )
        self.assertIsInstance(
            home_target,
            selector.NumberSelector,
        )
        self.assertIsInstance(
            validators[next(key for key in validators if key.schema == CONF_AWAY_TARGET_TYPE)],
            selector.SelectSelector,
        )
        self.assertFalse(any(key.schema == CONF_WINDOW_CUSTOM_TEMPERATURE for key in validators))

    async def test_build_profile_management_schemas_use_expected_selectors(self) -> None:
        profiles_schema = _build_profiles_schema([])
        profile_action = profiles_schema.schema[
            next(key for key in profiles_schema.schema if key.schema == CONF_PROFILE_ACTION)
        ]
        self.assertIsInstance(profile_action, selector.SelectSelector)

        select_schema = _build_profile_select_schema(
            [
                {
                    CONF_PRIMARY_CLIMATE_ENTITY_ID: "climate.office",
                    CONF_HOME_TARGET_TEMPERATURE: 20.0,
                    CONF_AWAY_TARGET_TYPE: "absolute",
                    CONF_AWAY_TARGET_TEMPERATURE: 17.0,
                },
                {
                    CONF_HOME_TARGET_TEMPERATURE: 19.0,
                    CONF_AWAY_TARGET_TYPE: "absolute",
                    CONF_AWAY_TARGET_TEMPERATURE: 16.0,
                },
            ]
        )
        profile_index = select_schema.schema[
            next(key for key in select_schema.schema if key.schema == CONF_PROFILE_INDEX)
        ]
        self.assertIsInstance(profile_index, selector.SelectSelector)
        self.assertEqual(profile_index.config["options"][0]["label"], "climate.office")
        self.assertEqual(profile_index.config["options"][1]["label"], "New regulation profile")

    async def test_build_room_schema_omits_none_defaults_for_optional_entity_selectors(
        self,
    ) -> None:
        schema = _build_room_schema(
            {
                CONF_PRIMARY_CLIMATE_ENTITY_ID: None,
                CONF_HUMIDITY_ENTITY_ID: None,
                CONF_WINDOW_ENTITY_ID: None,
                CONF_HOME_TARGET_TEMPERATURE: 21.0,
                CONF_AWAY_TARGET_TYPE: "absolute",
                CONF_AWAY_TARGET_TEMPERATURE: 17.0,
            }
        )

        validated = schema(
            {
                CONF_HOME_TARGET_TEMPERATURE: 21.0,
                CONF_AWAY_TARGET_TYPE: "absolute",
                CONF_AWAY_TARGET_TEMPERATURE: 17.0,
            }
        )

        self.assertEqual(
            validated,
            {
                CONF_HOME_TARGET_TEMPERATURE: 21.0,
                CONF_AWAY_TARGET_TYPE: "absolute",
                CONF_AWAY_TARGET_TEMPERATURE: 17.0,
                CONF_WINDOW_ACTION_TYPE: DEFAULT_WINDOW_ACTION_TYPE,
                CONF_WINDOW_OPEN_DELAY_SECONDS: DEFAULT_WINDOW_OPEN_DELAY_SECONDS,
                CONF_SCHEDULE_HOME_START: "06:00:00",
                CONF_SCHEDULE_HOME_END: "22:00:00",
            },
        )
        for key in schema.schema:
            if key.schema in {
                CONF_PRIMARY_CLIMATE_ENTITY_ID,
                CONF_HUMIDITY_ENTITY_ID,
                CONF_WINDOW_ENTITY_ID,
            }:
                self.assertIs(key.default, vol.UNDEFINED)

    async def test_normalize_person_entity_ids_supports_strings_and_selector_dicts(
        self,
    ) -> None:
        self.assertEqual(_normalize_person_entity_ids(None), [])
        self.assertEqual(_normalize_person_entity_ids("person.alice"), ["person.alice"])
        self.assertEqual(
            _normalize_person_entity_ids({"entity_id": "person.alice"}),
            ["person.alice"],
        )
        self.assertEqual(
            _normalize_person_entity_ids(["person.alice", "person.bob"]),
            ["person.alice", "person.bob"],
        )
        self.assertEqual(
            _normalize_person_entity_ids(
                [{"entity_id": "person.alice"}, {"entity_id": "person.bob"}]
            ),
            ["person.alice", "person.bob"],
        )
        self.assertEqual(
            _normalize_person_entity_ids([{"value": "person.alice"}, {"value": "person.bob"}]),
            ["person.alice", "person.bob"],
        )
        with self.assertRaisesRegex(ValueError, "Unsupported person entity selector value"):
            _normalize_person_entity_ids([123])

    async def test_normalize_bool_supports_boolean_like_strings(self) -> None:
        self.assertFalse(_normalize_bool(False))
        self.assertTrue(_normalize_bool(True))
        self.assertFalse(_normalize_bool("false"))
        self.assertFalse(_normalize_bool("off"))
        self.assertTrue(_normalize_bool("true"))
        self.assertTrue(_normalize_bool("on"))
        self.assertFalse(_normalize_bool({"value": "off"}))
        self.assertTrue(_normalize_bool({"value": "on"}))
        self.assertTrue(_normalize_bool(2))

    async def test_unwrap_selector_value_supports_value_wrapper(self) -> None:
        self.assertEqual(_unwrap_selector_value({"value": "person.alice"}), "person.alice")
        self.assertEqual(_unwrap_selector_value("away"), "away")

    async def test_normalize_select_value_supports_value_wrapper(self) -> None:
        self.assertEqual(_normalize_select_value({"value": "home"}), "home")
        self.assertEqual(_normalize_select_value("away"), "away")
        with self.assertRaisesRegex(ValueError, "Unsupported select selector value"):
            _normalize_select_value({"value": 123})

    async def test_resolve_entity_id_accepts_none(self) -> None:
        self.assertIsNone(_resolve_entity_id(Mock(), None))

    async def test_resolve_room_entity_ids_converts_uuid_inputs(self) -> None:
        hass = Mock()
        with (
            patch(
                "custom_components.climate_relay_core.config_flow.er.async_get",
                return_value="registry",
            ),
            patch(
                "custom_components.climate_relay_core.config_flow.er.async_resolve_entity_id",
                side_effect=lambda _registry, value: {
                    "uuid-climate": "climate.living_room",
                    "uuid-humidity": "sensor.living_room_humidity",
                    "uuid-window": "binary_sensor.living_room_window",
                }[value],
            ),
        ):
            resolved = _resolve_room_entity_ids(
                hass,
                {
                    CONF_PRIMARY_CLIMATE_ENTITY_ID: "uuid-climate",
                    CONF_HUMIDITY_ENTITY_ID: "uuid-humidity",
                    CONF_WINDOW_ENTITY_ID: "uuid-window",
                    CONF_HOME_TARGET_TEMPERATURE: 21.0,
                    CONF_AWAY_TARGET_TYPE: "absolute",
                    CONF_AWAY_TARGET_TEMPERATURE: 17.0,
                },
            )

        self.assertEqual(
            resolved,
            {
                CONF_PRIMARY_CLIMATE_ENTITY_ID: "climate.living_room",
                CONF_HUMIDITY_ENTITY_ID: "sensor.living_room_humidity",
                CONF_WINDOW_ENTITY_ID: "binary_sensor.living_room_window",
                CONF_HOME_TARGET_TEMPERATURE: 21.0,
                CONF_AWAY_TARGET_TYPE: "absolute",
                CONF_AWAY_TARGET_TEMPERATURE: 17.0,
            },
        )

    async def test_merge_room_submission_clears_omitted_entity_selectors(self) -> None:
        merged = _merge_room_submission(
            {
                CONF_PRIMARY_CLIMATE_ENTITY_ID: "climate.living_room",
                CONF_HUMIDITY_ENTITY_ID: "sensor.living_room_humidity",
                CONF_WINDOW_ENTITY_ID: "binary_sensor.living_room_window",
                CONF_HOME_TARGET_TEMPERATURE: 21.0,
                CONF_AWAY_TARGET_TYPE: "absolute",
                CONF_AWAY_TARGET_TEMPERATURE: 17.0,
            },
            {
                CONF_PRIMARY_CLIMATE_ENTITY_ID: "climate.living_room",
                CONF_HOME_TARGET_TEMPERATURE: 21.0,
                CONF_AWAY_TARGET_TYPE: "absolute",
                CONF_AWAY_TARGET_TEMPERATURE: 17.0,
            },
        )

        self.assertEqual(merged[CONF_PRIMARY_CLIMATE_ENTITY_ID], "climate.living_room")
        self.assertIsNone(merged[CONF_HUMIDITY_ENTITY_ID])
        self.assertIsNone(merged[CONF_WINDOW_ENTITY_ID])

    async def test_room_step_clears_optional_entities_when_selector_fields_are_omitted(
        self,
    ) -> None:
        config_entry = Mock()
        config_entry.options = {
            CONF_ROOMS: [
                {
                    CONF_PRIMARY_CLIMATE_ENTITY_ID: "climate.living_room",
                    CONF_HUMIDITY_ENTITY_ID: "sensor.living_room_humidity",
                    CONF_WINDOW_ENTITY_ID: "binary_sensor.living_room_window",
                    CONF_HOME_TARGET_TEMPERATURE: 21.0,
                    CONF_AWAY_TARGET_TYPE: "absolute",
                    CONF_AWAY_TARGET_TEMPERATURE: 17.0,
                }
            ]
        }
        flow = ClimateRelayCoreOptionsFlow(config_entry)
        flow.hass = Mock()
        flow._editing_room_index = 0
        flow.async_create_entry = Mock(return_value={"type": "create_entry"})

        with patch(
            "custom_components.climate_relay_core.config_flow._resolve_area_reference",
            return_value=_resolved_area(),
        ):
            result = await flow.async_step_room(
                {
                    CONF_PRIMARY_CLIMATE_ENTITY_ID: "climate.living_room",
                    CONF_HOME_TARGET_TEMPERATURE: 21.0,
                    CONF_AWAY_TARGET_TYPE: "absolute",
                    CONF_AWAY_TARGET_TEMPERATURE: 17.0,
                }
            )

        self.assertEqual(result, {"type": "create_entry"})
        flow.async_create_entry.assert_called_once_with(
            title="",
            data={
                CONF_ROOMS: [
                    {
                        CONF_PRIMARY_CLIMATE_ENTITY_ID: "climate.living_room",
                        CONF_HUMIDITY_ENTITY_ID: None,
                        CONF_WINDOW_ENTITY_ID: None,
                        CONF_WINDOW_ACTION_TYPE: DEFAULT_WINDOW_ACTION_TYPE,
                        CONF_WINDOW_CUSTOM_TEMPERATURE: None,
                        CONF_WINDOW_OPEN_DELAY_SECONDS: DEFAULT_WINDOW_OPEN_DELAY_SECONDS,
                        CONF_HOME_TARGET_TEMPERATURE: 21.0,
                        CONF_AWAY_TARGET_TYPE: "absolute",
                        CONF_AWAY_TARGET_TEMPERATURE: 17.0,
                        CONF_SCHEDULE_HOME_START: "06:00:00",
                        CONF_SCHEDULE_HOME_END: "22:00:00",
                    }
                ]
            },
        )

    async def test_room_step_rejects_omitted_primary_entity_in_existing_profile(self) -> None:
        config_entry = Mock()
        config_entry.options = {
            CONF_ROOMS: [
                {
                    CONF_PRIMARY_CLIMATE_ENTITY_ID: "climate.living_room",
                    CONF_HUMIDITY_ENTITY_ID: "sensor.living_room_humidity",
                    CONF_WINDOW_ENTITY_ID: "binary_sensor.living_room_window",
                    CONF_HOME_TARGET_TEMPERATURE: 21.0,
                    CONF_AWAY_TARGET_TYPE: "absolute",
                    CONF_AWAY_TARGET_TEMPERATURE: 17.0,
                }
            ]
        }
        flow = ClimateRelayCoreOptionsFlow(config_entry)
        flow.hass = Mock()
        flow.async_show_form = Mock(return_value={"type": "form"})

        await flow.async_step_room(
            {
                CONF_HOME_TARGET_TEMPERATURE: 21.0,
                CONF_AWAY_TARGET_TYPE: "absolute",
                CONF_AWAY_TARGET_TEMPERATURE: 17.0,
            }
        )

        self.assertEqual(
            flow.async_show_form.call_args.kwargs["errors"],
            {CONF_PRIMARY_CLIMATE_ENTITY_ID: "primary_climate_required"},
        )

    async def test_room_step_routes_custom_window_action_to_temperature_step(self) -> None:
        config_entry = Mock()
        config_entry.options = {}
        flow = ClimateRelayCoreOptionsFlow(config_entry)
        flow.hass = Mock()
        flow.async_show_form = Mock(return_value={"type": "form"})

        with patch(
            "custom_components.climate_relay_core.config_flow._resolve_area_reference",
            return_value=_resolved_area(),
        ):
            result = await flow.async_step_room(
                {
                    CONF_PRIMARY_CLIMATE_ENTITY_ID: "climate.living_room",
                    CONF_WINDOW_ACTION_TYPE: "custom_temperature",
                    CONF_HOME_TARGET_TEMPERATURE: 21.0,
                    CONF_AWAY_TARGET_TYPE: "absolute",
                    CONF_AWAY_TARGET_TEMPERATURE: 17.0,
                }
            )

        self.assertEqual(result, {"type": "form"})
        self.assertEqual(
            flow.async_show_form.call_args.kwargs["step_id"],
            "window_custom_temperature",
        )
        self.assertEqual(flow._pending_room[CONF_WINDOW_ACTION_TYPE], "custom_temperature")

    async def test_custom_temperature_step_requires_value(self) -> None:
        config_entry = Mock()
        config_entry.options = {}
        flow = ClimateRelayCoreOptionsFlow(config_entry)
        flow._pending_room = {
            CONF_PRIMARY_CLIMATE_ENTITY_ID: "climate.living_room",
            CONF_WINDOW_ACTION_TYPE: "custom_temperature",
            CONF_WINDOW_CUSTOM_TEMPERATURE: None,
            CONF_WINDOW_OPEN_DELAY_SECONDS: DEFAULT_WINDOW_OPEN_DELAY_SECONDS,
            CONF_HOME_TARGET_TEMPERATURE: 21.0,
            CONF_AWAY_TARGET_TYPE: "absolute",
            CONF_AWAY_TARGET_TEMPERATURE: 17.0,
            CONF_SCHEDULE_HOME_START: "06:00:00",
            CONF_SCHEDULE_HOME_END: "22:00:00",
        }
        flow.async_show_form = Mock(return_value={"type": "form"})

        result = await flow.async_step_window_custom_temperature(
            {CONF_WINDOW_CUSTOM_TEMPERATURE: ""}
        )

        self.assertEqual(result, {"type": "form"})
        self.assertEqual(
            flow.async_show_form.call_args.kwargs["errors"][CONF_WINDOW_CUSTOM_TEMPERATURE],
            "window_custom_temperature_required",
        )

    async def test_custom_temperature_step_rejects_out_of_range_value(self) -> None:
        config_entry = Mock()
        config_entry.options = {}
        flow = ClimateRelayCoreOptionsFlow(config_entry)
        flow._pending_room = {
            CONF_PRIMARY_CLIMATE_ENTITY_ID: "climate.living_room",
            CONF_WINDOW_ACTION_TYPE: "custom_temperature",
            CONF_WINDOW_CUSTOM_TEMPERATURE: None,
            CONF_WINDOW_OPEN_DELAY_SECONDS: DEFAULT_WINDOW_OPEN_DELAY_SECONDS,
            CONF_HOME_TARGET_TEMPERATURE: 21.0,
            CONF_AWAY_TARGET_TYPE: "absolute",
            CONF_AWAY_TARGET_TEMPERATURE: 17.0,
            CONF_SCHEDULE_HOME_START: "06:00:00",
            CONF_SCHEDULE_HOME_END: "22:00:00",
        }
        flow.async_show_form = Mock(return_value={"type": "form"})

        result = await flow.async_step_window_custom_temperature(
            {CONF_WINDOW_CUSTOM_TEMPERATURE: "40"}
        )

        self.assertEqual(result, {"type": "form"})
        self.assertEqual(
            flow.async_show_form.call_args.kwargs["errors"][CONF_WINDOW_CUSTOM_TEMPERATURE],
            "window_custom_temperature_range",
        )

    async def test_custom_temperature_step_creates_options_entry(self) -> None:
        config_entry = Mock()
        config_entry.options = {}
        flow = ClimateRelayCoreOptionsFlow(config_entry)
        flow._pending_options = {CONF_PERSON_ENTITY_IDS: ["person.alice"]}
        flow._pending_room = {
            CONF_PRIMARY_CLIMATE_ENTITY_ID: "climate.living_room",
            CONF_WINDOW_ACTION_TYPE: "custom_temperature",
            CONF_WINDOW_CUSTOM_TEMPERATURE: None,
            CONF_WINDOW_OPEN_DELAY_SECONDS: DEFAULT_WINDOW_OPEN_DELAY_SECONDS,
            CONF_HOME_TARGET_TEMPERATURE: 21.0,
            CONF_AWAY_TARGET_TYPE: "absolute",
            CONF_AWAY_TARGET_TEMPERATURE: 17.0,
            CONF_SCHEDULE_HOME_START: "06:00:00",
            CONF_SCHEDULE_HOME_END: "22:00:00",
        }
        flow.async_create_entry = Mock(return_value={"type": "create_entry"})

        result = await flow.async_step_window_custom_temperature(
            {CONF_WINDOW_CUSTOM_TEMPERATURE: "12.5"}
        )

        self.assertEqual(result, {"type": "create_entry"})
        flow.async_create_entry.assert_called_once()
        created_data = flow.async_create_entry.call_args.kwargs["data"]
        self.assertEqual(created_data[CONF_PERSON_ENTITY_IDS], ["person.alice"])
        self.assertEqual(
            created_data[CONF_ROOMS][0][CONF_WINDOW_CUSTOM_TEMPERATURE],
            12.5,
        )

    async def test_custom_temperature_step_accepts_locale_decimal_comma(self) -> None:
        config_entry = Mock()
        config_entry.options = {}
        flow = ClimateRelayCoreOptionsFlow(config_entry)
        flow._pending_options = {CONF_PERSON_ENTITY_IDS: ["person.alice"]}
        flow._pending_room = {
            CONF_PRIMARY_CLIMATE_ENTITY_ID: "climate.living_room",
            CONF_WINDOW_ACTION_TYPE: "custom_temperature",
            CONF_WINDOW_CUSTOM_TEMPERATURE: None,
            CONF_WINDOW_OPEN_DELAY_SECONDS: DEFAULT_WINDOW_OPEN_DELAY_SECONDS,
            CONF_HOME_TARGET_TEMPERATURE: 21.0,
            CONF_AWAY_TARGET_TYPE: "absolute",
            CONF_AWAY_TARGET_TEMPERATURE: 17.0,
            CONF_SCHEDULE_HOME_START: "06:00:00",
            CONF_SCHEDULE_HOME_END: "22:00:00",
        }
        flow.async_create_entry = Mock(return_value={"type": "create_entry"})

        result = await flow.async_step_window_custom_temperature(
            {CONF_WINDOW_CUSTOM_TEMPERATURE: "12,5"}
        )

        self.assertEqual(result, {"type": "create_entry"})
        created_data = flow.async_create_entry.call_args.kwargs["data"]
        self.assertEqual(
            created_data[CONF_ROOMS][0][CONF_WINDOW_CUSTOM_TEMPERATURE],
            12.5,
        )

    async def test_normalize_options_values_coerces_stored_wrapped_values(self) -> None:
        normalized = _normalize_options_values(
            {
                CONF_PERSON_ENTITY_IDS: {"value": [{"value": "person.alice"}]},
                CONF_UNKNOWN_STATE_HANDLING: {"value": "home"},
                CONF_FALLBACK_TEMPERATURE: DEFAULT_FALLBACK_TEMPERATURE,
                CONF_MANUAL_OVERRIDE_RESET_ENABLED: {"value": "off"},
                CONF_MANUAL_OVERRIDE_RESET_TIME: {"value": "06:15"},
                CONF_SIMULATION_MODE: {"value": "on"},
                CONF_VERBOSE_LOGGING: {"value": False},
            }
        )

        self.assertEqual(normalized[CONF_PERSON_ENTITY_IDS], ["person.alice"])
        self.assertEqual(normalized[CONF_UNKNOWN_STATE_HANDLING], "home")
        self.assertFalse(normalized[CONF_MANUAL_OVERRIDE_RESET_ENABLED])
        self.assertEqual(normalized[CONF_MANUAL_OVERRIDE_RESET_TIME], "06:15")
        self.assertTrue(normalized[CONF_SIMULATION_MODE])
        self.assertFalse(normalized[CONF_VERBOSE_LOGGING])

    async def test_normalize_time_field_value_returns_string_or_none(self) -> None:
        self.assertIsNone(_normalize_time_field_value(None))
        self.assertIsNone(_normalize_time_field_value(""))
        self.assertEqual(_normalize_time_field_value({"value": "06:15:00"}), "06:15:00")

    async def test_normalize_room_options_coerces_stored_wrapped_values(self) -> None:
        normalized = _normalize_room_options(
            {
                CONF_PRIMARY_CLIMATE_ENTITY_ID: {"value": "climate.living_room"},
                CONF_HUMIDITY_ENTITY_ID: {"value": "sensor.living_room_humidity"},
                CONF_WINDOW_ENTITY_ID: {"value": "binary_sensor.living_room_window"},
                CONF_HOME_TARGET_TEMPERATURE: 21.0,
                CONF_AWAY_TARGET_TYPE: {"value": "relative"},
                CONF_AWAY_TARGET_TEMPERATURE: -2.0,
            }
        )

        self.assertEqual(normalized[CONF_PRIMARY_CLIMATE_ENTITY_ID], "climate.living_room")
        self.assertEqual(normalized[CONF_HUMIDITY_ENTITY_ID], "sensor.living_room_humidity")
        self.assertEqual(normalized[CONF_WINDOW_ENTITY_ID], "binary_sensor.living_room_window")
        self.assertEqual(normalized[CONF_WINDOW_ACTION_TYPE], DEFAULT_WINDOW_ACTION_TYPE)
        self.assertIsNone(normalized[CONF_WINDOW_CUSTOM_TEMPERATURE])
        self.assertEqual(
            normalized[CONF_WINDOW_OPEN_DELAY_SECONDS],
            DEFAULT_WINDOW_OPEN_DELAY_SECONDS,
        )
        self.assertEqual(normalized[CONF_AWAY_TARGET_TYPE], "relative")

    async def test_normalize_room_options_rejects_invalid_target_type(self) -> None:
        with self.assertRaisesRegex(ValueError, "Unsupported away target type"):
            _normalize_room_options(
                {
                    CONF_PRIMARY_CLIMATE_ENTITY_ID: "climate.living_room",
                    CONF_HOME_TARGET_TEMPERATURE: 21.0,
                    CONF_AWAY_TARGET_TYPE: "invalid",
                    CONF_AWAY_TARGET_TEMPERATURE: 18.0,
                }
            )
