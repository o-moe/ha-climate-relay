"""Config flow for ClimateRelayCore."""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant import config_entries

from .const import DEFAULT_NAME, DOMAIN


class ClimateRelayCoreConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for the integration."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Handle the initial step."""
        if user_input is not None:
            await self.async_set_unique_id(DOMAIN)
            self._abort_if_unique_id_configured()
            return self.async_create_entry(title=user_input["name"], data={})

        schema = vol.Schema({vol.Required("name", default=DEFAULT_NAME): str})
        return self.async_show_form(step_id="user", data_schema=schema)
