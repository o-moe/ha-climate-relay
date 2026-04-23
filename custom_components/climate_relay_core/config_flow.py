"""Config flow for ClimateRelayCore."""

from __future__ import annotations

import logging
from datetime import time
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers import selector

from .const import (
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
    CONF_SIMULATION_MODE,
    CONF_UNKNOWN_STATE_HANDLING,
    CONF_VERBOSE_LOGGING,
    CONF_WINDOW_ENTITY_ID,
    DEFAULT_AWAY_TARGET_TYPE,
    DEFAULT_FALLBACK_TEMPERATURE,
    DEFAULT_NAME,
    DEFAULT_UNKNOWN_STATE_HANDLING,
    DOMAIN,
)
from .runtime import _resolve_area_reference

_LOGGER = logging.getLogger(__name__)


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


class ClimateRelayCoreOptionsFlow(config_entries.OptionsFlow):
    """Manage iteration 1.1 global configuration."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self._config_entry = config_entry
        self._pending_options: dict[str, Any] | None = None

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Manage the integration options."""
        errors: dict[str, str] = {}
        form_values = _normalize_options_values(
            {**_default_config_data(), **self._config_entry.options}
        )

        if user_input is not None:
            try:
                submitted = {**form_values, **user_input}
                manual_override_reset_enabled = _normalize_bool(
                    submitted.get(CONF_MANUAL_OVERRIDE_RESET_ENABLED, False)
                )
                simulation_mode = _normalize_bool(submitted.get(CONF_SIMULATION_MODE, False))
                verbose_logging = _normalize_bool(submitted.get(CONF_VERBOSE_LOGGING, False))
                person_entity_ids = _normalize_person_entity_ids(
                    submitted.get(CONF_PERSON_ENTITY_IDS)
                )
                unknown_state_handling = _normalize_select_value(
                    submitted.get(CONF_UNKNOWN_STATE_HANDLING)
                )
                form_values = _normalize_options_values(submitted)
                if not person_entity_ids:
                    errors[CONF_PERSON_ENTITY_IDS] = "person_entities_required"
                if not errors:
                    self._pending_options = {
                        CONF_PERSON_ENTITY_IDS: person_entity_ids,
                        CONF_UNKNOWN_STATE_HANDLING: unknown_state_handling,
                        CONF_FALLBACK_TEMPERATURE: submitted[CONF_FALLBACK_TEMPERATURE],
                        CONF_MANUAL_OVERRIDE_RESET_ENABLED: manual_override_reset_enabled,
                        CONF_MANUAL_OVERRIDE_RESET_TIME: form_values[
                            CONF_MANUAL_OVERRIDE_RESET_TIME
                        ],
                        CONF_SIMULATION_MODE: simulation_mode,
                        CONF_VERBOSE_LOGGING: verbose_logging,
                    }
                    if manual_override_reset_enabled:
                        return await self.async_step_reset_time()

                    self._pending_options = {
                        **self._pending_options,
                        CONF_MANUAL_OVERRIDE_RESET_TIME: None,
                    }
                    return await self.async_step_room()
            except Exception:
                _LOGGER.exception(
                    "Failed to validate global settings payload: %r; defaults=%r",
                    user_input,
                    form_values,
                )
                errors["base"] = "unknown"

        schema = _build_options_schema(form_values, include_reset_time=False)
        return self.async_show_form(step_id="init", data_schema=schema, errors=errors)

    async def async_step_reset_time(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Collect the daily reset time when the feature is enabled."""
        errors: dict[str, str] = {}
        pending_options = self._pending_options or _normalize_options_values(
            {**_default_config_data(), **self._config_entry.options}
        )

        if user_input is not None:
            try:
                normalized_time = _normalize_reset_time(
                    True,
                    user_input.get(CONF_MANUAL_OVERRIDE_RESET_TIME),
                )
                if normalized_time is None:
                    errors[CONF_MANUAL_OVERRIDE_RESET_TIME] = "reset_time_required"
                else:
                    self._pending_options = {
                        **pending_options,
                        CONF_MANUAL_OVERRIDE_RESET_TIME: normalized_time,
                    }
                    return await self.async_step_room()
            except Exception:
                _LOGGER.exception(
                    "Failed to validate reset-time payload: %r; pending_options=%r",
                    user_input,
                    pending_options,
                )
                errors["base"] = "unknown"

        schema = _build_reset_time_schema(
            pending_options.get(CONF_MANUAL_OVERRIDE_RESET_TIME),
        )
        return self.async_show_form(
            step_id="reset_time",
            data_schema=schema,
            errors=errors,
        )

    async def async_step_room(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Collect the first regulation-profile baseline configuration."""
        errors: dict[str, str] = {}
        room_values = _normalize_room_options(
            (_normalize_rooms(self._config_entry.options) or [_default_room_data()])[0]
        )

        if user_input is not None:
            try:
                submitted = _normalize_room_options({**room_values, **user_input})
                submitted = _resolve_room_entity_ids(self.hass, submitted)
                if not submitted[CONF_PRIMARY_CLIMATE_ENTITY_ID]:
                    errors[CONF_PRIMARY_CLIMATE_ENTITY_ID] = "primary_climate_required"
                elif (
                    _resolve_area_reference(
                        self.hass,
                        submitted[CONF_PRIMARY_CLIMATE_ENTITY_ID],
                    ).area_id
                    is None
                ):
                    errors[CONF_PRIMARY_CLIMATE_ENTITY_ID] = "primary_climate_area_required"

                if not errors:
                    return self.async_create_entry(
                        title="",
                        data={
                            **(self._pending_options or {}),
                            CONF_ROOMS: [submitted],
                        },
                    )
                room_values = submitted
            except Exception:
                _LOGGER.exception("Failed to validate room settings payload: %r", user_input)
                errors["base"] = "unknown"

        return self.async_show_form(
            step_id="room",
            data_schema=_build_room_schema(room_values),
            errors=errors,
        )


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


def _default_room_data() -> dict[str, Any]:
    """Return the default regulation-profile configuration form values."""
    return {
        CONF_PRIMARY_CLIMATE_ENTITY_ID: None,
        CONF_HUMIDITY_ENTITY_ID: None,
        CONF_WINDOW_ENTITY_ID: None,
        CONF_HOME_TARGET_TEMPERATURE: DEFAULT_FALLBACK_TEMPERATURE,
        CONF_AWAY_TARGET_TYPE: DEFAULT_AWAY_TARGET_TYPE,
        CONF_AWAY_TARGET_TEMPERATURE: DEFAULT_FALLBACK_TEMPERATURE - 3.0,
    }


def _normalize_reset_time(enabled: bool, raw_value: str | None) -> str | None:
    """Normalize the configured daily reset time."""
    if not enabled:
        return None
    value = str(_unwrap_selector_value(raw_value) or "").strip()
    if not value:
        return None
    parsed = time.fromisoformat(value)
    return parsed.isoformat()


def _normalize_bool(raw_value: Any) -> bool:
    """Normalize Home Assistant form booleans from frontend payloads."""
    raw_value = _unwrap_selector_value(raw_value)
    if isinstance(raw_value, bool):
        return raw_value
    if isinstance(raw_value, str):
        normalized = raw_value.strip().lower()
        if normalized in {"true", "on", "yes", "1"}:
            return True
        if normalized in {"false", "off", "no", "0", ""}:
            return False
    return bool(raw_value)


def _normalize_person_entity_ids(raw_value: Any) -> list[str]:
    """Normalize selector output to a list of entity IDs."""
    raw_value = _unwrap_selector_value(raw_value)
    if raw_value is None:
        return []
    if isinstance(raw_value, str):
        return [raw_value]
    if isinstance(raw_value, dict):
        entity_id = raw_value.get("entity_id") or raw_value.get("value")
        if isinstance(entity_id, str):
            return [entity_id]
        raw_value = entity_id

    normalized: list[str] = []
    for item in raw_value:
        item = _unwrap_selector_value(item)
        if isinstance(item, str):
            normalized.append(item)
            continue
        if isinstance(item, dict):
            entity_id = item.get("entity_id") or item.get("value")
            if isinstance(entity_id, str):
                normalized.append(entity_id)
                continue
        raise ValueError(f"Unsupported person entity selector value: {item!r}")
    return normalized


def _normalize_select_value(raw_value: Any) -> str:
    """Normalize select/radio selector payloads to a plain string value."""
    normalized = _unwrap_selector_value(raw_value)
    if not isinstance(normalized, str):
        raise ValueError(f"Unsupported select selector value: {raw_value!r}")
    return normalized


def _normalize_options_values(values: dict[str, Any]) -> dict[str, Any]:
    """Normalize stored options before rendering them back into selectors."""
    normalized = dict(values)
    normalized[CONF_PERSON_ENTITY_IDS] = _normalize_person_entity_ids(
        values.get(CONF_PERSON_ENTITY_IDS)
    )
    normalized[CONF_UNKNOWN_STATE_HANDLING] = _normalize_select_value(
        values.get(CONF_UNKNOWN_STATE_HANDLING, DEFAULT_UNKNOWN_STATE_HANDLING)
    )
    normalized[CONF_MANUAL_OVERRIDE_RESET_ENABLED] = _normalize_bool(
        values.get(CONF_MANUAL_OVERRIDE_RESET_ENABLED, False)
    )
    normalized[CONF_MANUAL_OVERRIDE_RESET_TIME] = _normalize_time_field_value(
        values.get(CONF_MANUAL_OVERRIDE_RESET_TIME)
    )
    normalized[CONF_SIMULATION_MODE] = _normalize_bool(values.get(CONF_SIMULATION_MODE, False))
    normalized[CONF_VERBOSE_LOGGING] = _normalize_bool(values.get(CONF_VERBOSE_LOGGING, False))
    return normalized


def _normalize_room_options(values: dict[str, Any]) -> dict[str, Any]:
    """Normalize one regulation-profile configuration for rendering and persistence."""
    return {
        CONF_PRIMARY_CLIMATE_ENTITY_ID: _normalize_optional_entity_selector(
            values.get(CONF_PRIMARY_CLIMATE_ENTITY_ID)
        ),
        CONF_HUMIDITY_ENTITY_ID: _normalize_optional_entity_selector(
            values.get(CONF_HUMIDITY_ENTITY_ID)
        ),
        CONF_WINDOW_ENTITY_ID: _normalize_optional_entity_selector(
            values.get(CONF_WINDOW_ENTITY_ID)
        ),
        CONF_HOME_TARGET_TEMPERATURE: float(
            values.get(CONF_HOME_TARGET_TEMPERATURE, DEFAULT_FALLBACK_TEMPERATURE)
        ),
        CONF_AWAY_TARGET_TYPE: _normalize_target_type_selector(
            values.get(CONF_AWAY_TARGET_TYPE, DEFAULT_AWAY_TARGET_TYPE)
        ),
        CONF_AWAY_TARGET_TEMPERATURE: float(
            values.get(CONF_AWAY_TARGET_TEMPERATURE, DEFAULT_FALLBACK_TEMPERATURE - 3.0)
        ),
    }


def _normalize_rooms(values: dict[str, Any]) -> list[dict[str, Any]]:
    """Normalize stored regulation-profile list data."""
    raw_rooms = values.get(CONF_ROOMS) or []
    return [_normalize_room_options(room) for room in raw_rooms if isinstance(room, dict)]


def _normalize_time_field_value(raw_value: Any) -> str | None:
    """Normalize reset-time values for displaying them back in the form."""
    normalized = _unwrap_selector_value(raw_value)
    if normalized in (None, ""):
        return None
    return str(normalized)


def _normalize_optional_entity_selector(raw_value: Any) -> str | None:
    """Normalize an optional entity selector value."""
    normalized = _unwrap_selector_value(raw_value)
    if isinstance(normalized, dict):
        normalized = normalized.get("entity_id") or normalized.get("value")
    if normalized in (None, ""):
        return None
    if not isinstance(normalized, str):
        raise ValueError(f"Unsupported entity selector value: {raw_value!r}")
    return normalized


def _normalize_target_type_selector(raw_value: Any) -> str:
    """Normalize the away-target-type selector."""
    normalized = _normalize_select_value(raw_value)
    if normalized not in {"absolute", "relative"}:
        raise ValueError(f"Unsupported away target type: {raw_value!r}")
    return normalized


def _resolve_room_entity_ids(
    hass: Any,
    values: dict[str, Any],
) -> dict[str, Any]:
    """Resolve selector UUIDs to stable entity IDs before validation and storage."""
    resolved = dict(values)
    resolved[CONF_PRIMARY_CLIMATE_ENTITY_ID] = _resolve_entity_id(
        hass,
        values.get(CONF_PRIMARY_CLIMATE_ENTITY_ID),
    )
    resolved[CONF_HUMIDITY_ENTITY_ID] = _resolve_entity_id(
        hass,
        values.get(CONF_HUMIDITY_ENTITY_ID),
    )
    resolved[CONF_WINDOW_ENTITY_ID] = _resolve_entity_id(
        hass,
        values.get(CONF_WINDOW_ENTITY_ID),
    )
    return resolved


def _resolve_entity_id(
    hass: Any,
    entity_id_or_uuid: str | None,
) -> str | None:
    """Resolve an entity ID or registry UUID to a plain entity_id."""
    if entity_id_or_uuid is None:
        return None
    if "." in entity_id_or_uuid:
        return entity_id_or_uuid
    return er.async_resolve_entity_id(er.async_get(hass), entity_id_or_uuid)


def _unwrap_selector_value(raw_value: Any) -> Any:
    """Unwrap common Home Assistant selector payload wrappers."""
    if isinstance(raw_value, dict) and "value" in raw_value:
        return raw_value["value"]
    return raw_value


def _build_options_schema(values: dict[str, Any], *, include_reset_time: bool) -> vol.Schema:
    """Build the options schema for the current form state."""
    schema_fields: dict[Any, Any] = {
        vol.Required(
            CONF_PERSON_ENTITY_IDS,
            default=values[CONF_PERSON_ENTITY_IDS],
        ): selector.EntitySelector(
            selector.EntitySelectorConfig(
                domain="person",
                multiple=True,
            )
        ),
        vol.Required(
            CONF_UNKNOWN_STATE_HANDLING,
            default=values[CONF_UNKNOWN_STATE_HANDLING],
        ): selector.SelectSelector(
            selector.SelectSelectorConfig(
                options=["away", "home"],
                sort=False,
            )
        ),
        vol.Required(
            CONF_FALLBACK_TEMPERATURE,
            default=values[CONF_FALLBACK_TEMPERATURE],
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
            default=values[CONF_MANUAL_OVERRIDE_RESET_ENABLED],
        ): selector.BooleanSelector(),
        vol.Required(
            CONF_SIMULATION_MODE,
            default=values[CONF_SIMULATION_MODE],
        ): selector.BooleanSelector(),
        vol.Required(
            CONF_VERBOSE_LOGGING,
            default=values[CONF_VERBOSE_LOGGING],
        ): selector.BooleanSelector(),
    }
    if include_reset_time:
        schema_fields[
            vol.Optional(
                CONF_MANUAL_OVERRIDE_RESET_TIME,
                default=values[CONF_MANUAL_OVERRIDE_RESET_TIME],
            )
        ] = selector.TimeSelector()
    return vol.Schema(schema_fields)


def _build_reset_time_schema(value: str | None) -> vol.Schema:
    """Build the dedicated reset-time step schema."""
    return vol.Schema(
        {
            vol.Optional(
                CONF_MANUAL_OVERRIDE_RESET_TIME,
                default=value,
            ): selector.TimeSelector(),
        }
    )


def _build_room_schema(values: dict[str, Any]) -> vol.Schema:
    """Build the regulation-profile schema."""
    primary_climate_field: Any
    humidity_field: Any
    window_field: Any

    if values[CONF_PRIMARY_CLIMATE_ENTITY_ID] is None:
        primary_climate_field = vol.Optional(CONF_PRIMARY_CLIMATE_ENTITY_ID)
    else:
        primary_climate_field = vol.Optional(
            CONF_PRIMARY_CLIMATE_ENTITY_ID,
            default=values[CONF_PRIMARY_CLIMATE_ENTITY_ID],
        )

    if values[CONF_HUMIDITY_ENTITY_ID] is None:
        humidity_field = vol.Optional(CONF_HUMIDITY_ENTITY_ID)
    else:
        humidity_field = vol.Optional(
            CONF_HUMIDITY_ENTITY_ID,
            default=values[CONF_HUMIDITY_ENTITY_ID],
        )

    if values[CONF_WINDOW_ENTITY_ID] is None:
        window_field = vol.Optional(CONF_WINDOW_ENTITY_ID)
    else:
        window_field = vol.Optional(
            CONF_WINDOW_ENTITY_ID,
            default=values[CONF_WINDOW_ENTITY_ID],
        )

    return vol.Schema(
        {
            primary_climate_field: selector.EntitySelector(
                selector.EntitySelectorConfig(
                    domain="climate",
                    multiple=False,
                )
            ),
            humidity_field: selector.EntitySelector(
                selector.EntitySelectorConfig(
                    domain="sensor",
                    multiple=False,
                )
            ),
            window_field: selector.EntitySelector(
                selector.EntitySelectorConfig(
                    domain="binary_sensor",
                    multiple=False,
                )
            ),
            vol.Required(
                CONF_HOME_TARGET_TEMPERATURE,
                default=values[CONF_HOME_TARGET_TEMPERATURE],
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
                CONF_AWAY_TARGET_TYPE,
                default=values[CONF_AWAY_TARGET_TYPE],
            ): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=["absolute", "relative"],
                    sort=False,
                )
            ),
            vol.Required(
                CONF_AWAY_TARGET_TEMPERATURE,
                default=values[CONF_AWAY_TARGET_TEMPERATURE],
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=-10,
                    max=35,
                    step=0.5,
                    mode=selector.NumberSelectorMode.BOX,
                    unit_of_measurement="°C",
                )
            ),
        }
    )
