"""Config flow tests."""

from __future__ import annotations

from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock, Mock

from homeassistant.helpers import selector

from custom_components.climate_relay_core.config_flow import (
    ClimateRelayCoreConfigFlow,
    ClimateRelayCoreOptionsFlow,
    _build_options_schema,
    _normalize_reset_time,
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

    async def test_init_step_rejects_missing_reset_time_when_enabled(self) -> None:
        config_entry = Mock()
        config_entry.options = {}
        flow = ClimateRelayCoreOptionsFlow(config_entry)
        flow.async_show_form = Mock(return_value={"type": "form"})

        await flow.async_step_init(
            {
                CONF_PERSON_ENTITY_IDS: [],
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

    async def test_config_flow_returns_options_flow_handler(self) -> None:
        config_entry = Mock()

        result = ClimateRelayCoreConfigFlow.async_get_options_flow(config_entry)

        self.assertIsInstance(result, ClimateRelayCoreOptionsFlow)

    async def test_normalize_reset_time_returns_none_when_disabled(self) -> None:
        self.assertIsNone(_normalize_reset_time(False, "05:30"))

    async def test_build_options_schema_includes_reset_time_only_when_enabled(self) -> None:
        disabled_schema = _build_options_schema(
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
        enabled_schema = _build_options_schema(
            {
                CONF_PERSON_ENTITY_IDS: [],
                CONF_UNKNOWN_STATE_HANDLING: DEFAULT_UNKNOWN_STATE_HANDLING,
                CONF_FALLBACK_TEMPERATURE: DEFAULT_FALLBACK_TEMPERATURE,
                CONF_MANUAL_OVERRIDE_RESET_ENABLED: True,
                CONF_MANUAL_OVERRIDE_RESET_TIME: "05:30:00",
                CONF_SIMULATION_MODE: False,
                CONF_VERBOSE_LOGGING: False,
            }
        )

        self.assertFalse(
            any(key.schema == CONF_MANUAL_OVERRIDE_RESET_TIME for key in disabled_schema.schema)
        )
        self.assertTrue(
            any(key.schema == CONF_MANUAL_OVERRIDE_RESET_TIME for key in enabled_schema.schema)
        )
