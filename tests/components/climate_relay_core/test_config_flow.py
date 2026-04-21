"""Config flow tests."""

from __future__ import annotations

from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock, Mock

from homeassistant.helpers import selector

from custom_components.climate_relay_core.config_flow import (
    ClimateRelayCoreConfigFlow,
    ClimateRelayCoreOptionsFlow,
    _build_options_schema,
    _normalize_bool,
    _normalize_options_values,
    _normalize_person_entity_ids,
    _normalize_reset_time,
    _normalize_select_value,
    _unwrap_selector_value,
)
from custom_components.climate_relay_core.const import (
    CONF_FALLBACK_TEMPERATURE,
    CONF_MANUAL_OVERRIDE_RESET_ENABLED,
    CONF_MANUAL_OVERRIDE_RESET_TIME,
    CONF_PERSON_ENTITY_IDS,
    CONF_SIMULATION_MODE,
    CONF_UNKNOWN_STATE_HANDLING,
    CONF_VERBOSE_LOGGING,
    DEFAULT_FALLBACK_TEMPERATURE,
    DEFAULT_NAME,
    DEFAULT_UNKNOWN_STATE_HANDLING,
    DOMAIN,
)


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
        reset_time = validators[
            next(key for key in validators if key.schema == CONF_MANUAL_OVERRIDE_RESET_TIME)
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
        self.assertIsInstance(reset_time, selector.TextSelector)
        self.assertIsInstance(simulation_mode, selector.BooleanSelector)
        self.assertIsInstance(verbose_logging, selector.BooleanSelector)

    async def test_init_step_with_input_creates_options_entry(self) -> None:
        config_entry = Mock()
        config_entry.options = {}
        flow = ClimateRelayCoreOptionsFlow(config_entry)
        expected_result = {"type": "create_entry"}
        flow.async_create_entry = Mock(return_value=expected_result)

        result = await flow.async_step_init(
            {
                CONF_PERSON_ENTITY_IDS: ["person.alice", "person.bob"],
                CONF_UNKNOWN_STATE_HANDLING: "home",
                CONF_FALLBACK_TEMPERATURE: 18.5,
                CONF_MANUAL_OVERRIDE_RESET_ENABLED: True,
                CONF_MANUAL_OVERRIDE_RESET_TIME: "05:30",
                CONF_SIMULATION_MODE: True,
                CONF_VERBOSE_LOGGING: True,
            }
        )

        self.assertEqual(result, expected_result)
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
            },
        )

    async def test_init_step_normalizes_selector_dict_values(self) -> None:
        config_entry = Mock()
        config_entry.options = {}
        flow = ClimateRelayCoreOptionsFlow(config_entry)
        expected_result = {"type": "create_entry"}
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
            },
        )

    async def test_init_step_normalizes_wrapped_selector_values(self) -> None:
        config_entry = Mock()
        config_entry.options = {}
        flow = ClimateRelayCoreOptionsFlow(config_entry)
        expected_result = {"type": "create_entry"}
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
            },
        )

    async def test_init_step_allows_missing_reset_time_when_disabled(self) -> None:
        config_entry = Mock()
        config_entry.options = {}
        flow = ClimateRelayCoreOptionsFlow(config_entry)
        expected_result = {"type": "create_entry"}
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
            {CONF_PERSON_ENTITY_IDS: "required"},
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
                CONF_MANUAL_OVERRIDE_RESET_TIME: "",
                CONF_SIMULATION_MODE: False,
                CONF_VERBOSE_LOGGING: False,
            }
        )

        self.assertEqual(
            flow.async_show_form.call_args.kwargs["errors"],
            {CONF_MANUAL_OVERRIDE_RESET_TIME: "required"},
        )

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

    async def test_build_options_schema_always_includes_reset_time_input(self) -> None:
        schema = _build_options_schema(
            {
                CONF_PERSON_ENTITY_IDS: [],
                CONF_UNKNOWN_STATE_HANDLING: DEFAULT_UNKNOWN_STATE_HANDLING,
                CONF_FALLBACK_TEMPERATURE: DEFAULT_FALLBACK_TEMPERATURE,
                CONF_MANUAL_OVERRIDE_RESET_ENABLED: False,
                CONF_MANUAL_OVERRIDE_RESET_TIME: None,
                CONF_SIMULATION_MODE: False,
                CONF_VERBOSE_LOGGING: False,
            }
        )
        self.assertTrue(any(key.schema == CONF_MANUAL_OVERRIDE_RESET_TIME for key in schema.schema))

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
