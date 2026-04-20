"""Config flow tests."""

from __future__ import annotations

from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock, Mock

from custom_components.climate_relay_core.config_flow import ClimateRelayCoreConfigFlow
from custom_components.climate_relay_core.const import DEFAULT_NAME, DOMAIN


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
        flow.async_create_entry.assert_called_once_with(title="My Dashboard", data={})
