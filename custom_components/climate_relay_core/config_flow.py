"""Config flow for ClimateRelayCore."""

from __future__ import annotations

from datetime import time
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.helpers import selector

from .const import (
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
            return self.async_create_entry(
                title=user_input["name"],
                data=_default_config_data(),
            )

        schema = vol.Schema({vol.Required("name", default=DEFAULT_NAME): str})
        return self.async_show_form(step_id="user", data_schema=schema)

    @staticmethod
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> ClimateRelayCoreOptionsFlow:
        """Return the options flow handler for this config entry."""
        return ClimateRelayCoreOptionsFlow(config_entry)


class ClimateRelayCoreOptionsFlow(config_entries.OptionsFlowWithReload):
    """Manage iteration 1.1 global configuration."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self._config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Manage the integration options."""
        errors: dict[str, str] = {}

        if user_input is not None:
            normalized_time = _normalize_reset_time(
                user_input[CONF_MANUAL_OVERRIDE_RESET_ENABLED],
                user_input.get(CONF_MANUAL_OVERRIDE_RESET_TIME),
            )
            if user_input[CONF_MANUAL_OVERRIDE_RESET_ENABLED] and normalized_time is None:
                errors[CONF_MANUAL_OVERRIDE_RESET_TIME] = "required"
            else:
                return self.async_create_entry(
                    title="",
                    data={
                        CONF_PERSON_ENTITY_IDS: user_input[CONF_PERSON_ENTITY_IDS],
                        CONF_UNKNOWN_STATE_HANDLING: user_input[CONF_UNKNOWN_STATE_HANDLING],
                        CONF_FALLBACK_TEMPERATURE: user_input[CONF_FALLBACK_TEMPERATURE],
                        CONF_MANUAL_OVERRIDE_RESET_ENABLED: user_input[
                            CONF_MANUAL_OVERRIDE_RESET_ENABLED
                        ],
                        CONF_MANUAL_OVERRIDE_RESET_TIME: normalized_time,
                        CONF_SIMULATION_MODE: user_input[CONF_SIMULATION_MODE],
                        CONF_VERBOSE_LOGGING: user_input[CONF_VERBOSE_LOGGING],
                    },
                )

        defaults = {**_default_config_data(), **self._config_entry.options}
        schema = vol.Schema(
            {
                vol.Required(
                    CONF_PERSON_ENTITY_IDS,
                    default=defaults[CONF_PERSON_ENTITY_IDS],
                ): selector.EntitySelector(
                    selector.EntitySelectorConfig(
                        domain="person",
                        multiple=True,
                    )
                ),
                vol.Required(
                    CONF_UNKNOWN_STATE_HANDLING,
                    default=defaults[CONF_UNKNOWN_STATE_HANDLING],
                ): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=["away", "home"],
                        sort=False,
                    )
                ),
                vol.Required(
                    CONF_FALLBACK_TEMPERATURE,
                    default=defaults[CONF_FALLBACK_TEMPERATURE],
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=5,
                        max=35,
                        step=0.5,
                        mode=selector.NumberSelectorMode.BOX,
                        unit_of_measurement="°C",
                    )
                ),
                vol.Required(
                    CONF_MANUAL_OVERRIDE_RESET_ENABLED,
                    default=defaults[CONF_MANUAL_OVERRIDE_RESET_ENABLED],
                ): selector.BooleanSelector(),
                vol.Optional(
                    CONF_MANUAL_OVERRIDE_RESET_TIME,
                    default=defaults[CONF_MANUAL_OVERRIDE_RESET_TIME] or None,
                ): selector.TimeSelector(),
                vol.Required(
                    CONF_SIMULATION_MODE,
                    default=defaults[CONF_SIMULATION_MODE],
                ): selector.BooleanSelector(),
                vol.Required(
                    CONF_VERBOSE_LOGGING,
                    default=defaults[CONF_VERBOSE_LOGGING],
                ): selector.BooleanSelector(),
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema, errors=errors)


def _default_config_data() -> dict[str, Any]:
    """Return the default stored configuration for a new entry."""
    return {
        CONF_PERSON_ENTITY_IDS: [],
        CONF_UNKNOWN_STATE_HANDLING: DEFAULT_UNKNOWN_STATE_HANDLING,
        CONF_FALLBACK_TEMPERATURE: DEFAULT_FALLBACK_TEMPERATURE,
        CONF_MANUAL_OVERRIDE_RESET_ENABLED: False,
        CONF_MANUAL_OVERRIDE_RESET_TIME: None,
        CONF_SIMULATION_MODE: False,
        CONF_VERBOSE_LOGGING: False,
    }


def _normalize_reset_time(enabled: bool, raw_value: str | None) -> str | None:
    """Normalize the configured daily reset time."""
    if not enabled:
        return None
    value = (raw_value or "").strip()
    if not value:
        return None
    parsed = time.fromisoformat(value)
    return parsed.isoformat()
