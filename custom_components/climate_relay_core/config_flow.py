"""Config flow for ClimateRelayCore."""

from __future__ import annotations

import logging
from datetime import time
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers import selector

from . import room_config
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
    CONF_SCHEDULE,
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
    DEFAULT_SCHEDULE_HOME_END,
    DEFAULT_SCHEDULE_HOME_START,
    DEFAULT_UNKNOWN_STATE_HANDLING,
    DEFAULT_WINDOW_ACTION_TYPE,
    DEFAULT_WINDOW_CUSTOM_TEMPERATURE,
    DEFAULT_WINDOW_OPEN_DELAY_SECONDS,
    DOMAIN,
)
from .runtime import _resolve_area_reference

_LOGGER = logging.getLogger(__name__)
CONF_PROFILE_ACTION = "profile_action"
CONF_PROFILE_INDEX = "profile_index"
PROFILE_ACTION_ADD = "add"
PROFILE_ACTION_EDIT = "edit"
PROFILE_ACTION_REMOVE = "remove"
PROFILE_ACTION_FINISH = "finish"


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
    """Manage global configuration."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self._config_entry = config_entry
        self._pending_options: dict[str, Any] | None = None
        self._pending_rooms: list[dict[str, Any]] | None = None
        self._pending_room: dict[str, Any] | None = None
        self._editing_room_index: int | None = None
        self._profile_management_active = False

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
                    return await self.async_step_profiles()
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
                    return await self.async_step_profiles()
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

    async def async_step_profiles(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Manage configured regulation profiles."""
        errors: dict[str, str] = {}
        rooms = self._current_pending_rooms()

        if user_input is not None:
            try:
                action = _normalize_select_value(user_input.get(CONF_PROFILE_ACTION))
                if action == PROFILE_ACTION_ADD:
                    self._profile_management_active = True
                    self._pending_room = None
                    self._editing_room_index = None
                    return await self.async_step_room()
                if action == PROFILE_ACTION_EDIT:
                    if not rooms:
                        errors[CONF_PROFILE_ACTION] = "profile_required"
                    else:
                        self._profile_management_active = True
                        return await self.async_step_profile_select_edit()
                elif action == PROFILE_ACTION_REMOVE:
                    if not rooms:
                        errors[CONF_PROFILE_ACTION] = "profile_required"
                    else:
                        self._profile_management_active = True
                        return await self.async_step_profile_select_remove()
                elif action == PROFILE_ACTION_FINISH:
                    if not rooms:
                        errors[CONF_PROFILE_ACTION] = "profile_required"
                    else:
                        return self._create_options_entry(rooms)
                else:
                    errors[CONF_PROFILE_ACTION] = "profile_action_required"
            except Exception:
                _LOGGER.exception("Failed to validate profile action payload: %r", user_input)
                errors["base"] = "unknown"

        return self.async_show_form(
            step_id="profiles",
            data_schema=_build_profiles_schema(rooms),
            errors=errors,
        )

    async def async_step_profile_select_edit(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Select the regulation profile to edit."""
        return await self._async_select_profile(user_input, remove=False)

    async def async_step_profile_select_remove(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Select the regulation profile to remove."""
        return await self._async_select_profile(user_input, remove=True)

    async def async_step_room(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Collect one regulation-profile configuration."""
        errors: dict[str, str] = {}
        rooms = self._current_pending_rooms()
        room_values = self._room_values_for_edit(rooms)

        if user_input is not None:
            try:
                submitted = _normalize_room_options(_merge_room_submission(room_values, user_input))
                submitted = _resolve_room_entity_ids(self.hass, submitted)
                area_id = None
                if not submitted[CONF_PRIMARY_CLIMATE_ENTITY_ID]:
                    errors[CONF_PRIMARY_CLIMATE_ENTITY_ID] = "primary_climate_required"
                else:
                    area_id = _resolve_area_reference(
                        self.hass,
                        submitted[CONF_PRIMARY_CLIMATE_ENTITY_ID],
                    ).area_id
                    if area_id is None:
                        errors[CONF_PRIMARY_CLIMATE_ENTITY_ID] = "primary_climate_area_required"
                    elif _has_duplicate_profile_anchor(
                        self.hass,
                        rooms,
                        submitted[CONF_PRIMARY_CLIMATE_ENTITY_ID],
                        area_id,
                        exclude_index=self._editing_room_index,
                    ):
                        errors[CONF_PRIMARY_CLIMATE_ENTITY_ID] = "profile_duplicate_area"
                if not room_config.validate_room_schedule_window(
                    submitted[CONF_SCHEDULE_HOME_START],
                    submitted[CONF_SCHEDULE_HOME_END],
                ):
                    errors[CONF_SCHEDULE_HOME_END] = "schedule_window_required"
                if not errors:
                    if submitted[CONF_WINDOW_ACTION_TYPE] == "custom_temperature":
                        self._pending_room = submitted
                        return await self.async_step_window_custom_temperature()
                    submitted = {**submitted, CONF_WINDOW_CUSTOM_TEMPERATURE: None}
                    self._store_pending_room(submitted)
                    if not self._profile_management_active:
                        return self._create_options_entry(self._current_pending_rooms())
                    return await self.async_step_profiles()
                room_values = submitted
            except Exception:
                _LOGGER.exception("Failed to validate room settings payload: %r", user_input)
                errors["base"] = "unknown"

        return self.async_show_form(
            step_id="room",
            data_schema=self.add_suggested_values_to_schema(
                _build_room_schema(room_values),
                room_values,
            ),
            errors=errors,
        )

    async def async_step_window_custom_temperature(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Collect the custom temperature required by the selected window action."""
        errors: dict[str, str] = {}
        room_values = self._pending_room or self._room_values_for_edit(
            self._current_pending_rooms()
        )
        value = room_values.get(CONF_WINDOW_CUSTOM_TEMPERATURE)
        default_value = DEFAULT_WINDOW_CUSTOM_TEMPERATURE if value is None else value

        if user_input is not None:
            try:
                raw_value = user_input.get(
                    CONF_WINDOW_CUSTOM_TEMPERATURE,
                    default_value,
                )
                if raw_value in (None, ""):
                    raw_value = default_value
                value = _normalize_optional_float_selector(raw_value)
                if value is None:
                    errors[CONF_WINDOW_CUSTOM_TEMPERATURE] = "window_custom_temperature_required"
                elif not 5 <= value <= 35:
                    errors[CONF_WINDOW_CUSTOM_TEMPERATURE] = "window_custom_temperature_range"
                else:
                    submitted = {**room_values, CONF_WINDOW_CUSTOM_TEMPERATURE: value}
                    self._store_pending_room(submitted)
                    if not self._profile_management_active:
                        return self._create_options_entry(self._current_pending_rooms())
                    return await self.async_step_profiles()
            except ValueError:
                errors[CONF_WINDOW_CUSTOM_TEMPERATURE] = "window_custom_temperature_invalid"
            except Exception:
                _LOGGER.exception(
                    "Failed to validate window custom-temperature payload: %r",
                    user_input,
                )
                errors["base"] = "unknown"

        return self.async_show_form(
            step_id="window_custom_temperature",
            data_schema=_build_window_custom_temperature_schema(value),
            errors=errors,
        )

    def _current_pending_rooms(self) -> list[dict[str, Any]]:
        """Return the mutable pending regulation-profile list."""
        if self._pending_rooms is None:
            self._pending_rooms = _current_rooms(self._config_entry.options)
        return self._pending_rooms

    def _room_values_for_edit(self, rooms: list[dict[str, Any]]) -> dict[str, Any]:
        """Return form values for the profile currently being edited or added."""
        if self._pending_room is not None:
            return self._pending_room
        if self._editing_room_index is not None and self._editing_room_index < len(rooms):
            return _normalize_room_options(rooms[self._editing_room_index])
        return _default_room_data()

    def _store_pending_room(self, room: dict[str, Any]) -> None:
        """Store the submitted profile in the pending profile list."""
        rooms = self._current_pending_rooms()
        if self._editing_room_index is None:
            rooms.append(room)
        else:
            rooms[self._editing_room_index] = room
        self._pending_room = None
        self._editing_room_index = None

    def _create_options_entry(
        self,
        rooms: list[dict[str, Any]],
    ) -> config_entries.ConfigFlowResult:
        """Persist pending options and regulation-profile list."""
        return self.async_create_entry(
            title="",
            data={
                **(self._pending_options or {}),
                CONF_ROOMS: rooms,
            },
        )

    async def _async_select_profile(
        self,
        user_input: dict[str, Any] | None,
        *,
        remove: bool,
    ) -> config_entries.ConfigFlowResult:
        errors: dict[str, str] = {}
        rooms = self._current_pending_rooms()

        if user_input is not None:
            try:
                raw_index = _unwrap_selector_value(user_input.get(CONF_PROFILE_INDEX))
                if raw_index in (None, ""):
                    errors[CONF_PROFILE_INDEX] = "profile_required"
                else:
                    index = int(raw_index)
                    if index < 0 or index >= len(rooms):
                        errors[CONF_PROFILE_INDEX] = "profile_required"
                    elif remove:
                        rooms.pop(index)
                        self._pending_room = None
                        self._editing_room_index = None
                        return await self.async_step_profiles()
                    else:
                        self._editing_room_index = index
                        self._pending_room = None
                        return await self.async_step_room()
            except Exception:
                _LOGGER.exception("Failed to validate profile selection payload: %r", user_input)
                errors["base"] = "unknown"

        return self.async_show_form(
            step_id="profile_select_remove" if remove else "profile_select_edit",
            data_schema=_build_profile_select_schema(rooms),
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
    return room_config.default_room_data()


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
    return room_config.normalize_room_options(_unwrap_room_selector_values(values))


def _normalize_rooms(values: dict[str, Any]) -> list[dict[str, Any]]:
    """Normalize stored regulation-profile list data."""
    raw_rooms = values.get(CONF_ROOMS) or []
    return [_normalize_room_options(room) for room in raw_rooms if isinstance(room, dict)]


def _current_rooms(values: dict[str, Any]) -> list[dict[str, Any]]:
    """Return normalized stored regulation-profile data."""
    return _normalize_rooms(values)


def _normalize_time_field_value(raw_value: Any) -> str | None:
    """Normalize reset-time values for displaying them back in the form."""
    return room_config.normalize_time_field_value(_unwrap_selector_value(raw_value))


def _normalize_optional_entity_selector(raw_value: Any) -> str | None:
    """Normalize an optional entity selector value."""
    normalized = _unwrap_selector_value(raw_value)
    if isinstance(normalized, dict):
        normalized = normalized.get("entity_id") or normalized.get("value")
    try:
        return room_config.normalize_optional_entity_id(normalized)
    except ValueError as err:
        raise ValueError(f"Unsupported entity selector value: {raw_value!r}") from err


def _normalize_target_type_selector(raw_value: Any) -> str:
    """Normalize the away-target-type selector."""
    normalized = _normalize_select_value(raw_value)
    try:
        return room_config.normalize_target_type(normalized)
    except ValueError as err:
        raise ValueError(f"Unsupported away target type: {raw_value!r}") from err


def _normalize_window_action_type_selector(raw_value: Any) -> str:
    """Normalize the window-action selector."""
    normalized = _normalize_select_value(raw_value)
    try:
        return room_config.normalize_window_action_type(normalized)
    except ValueError as err:
        raise ValueError(f"Unsupported window action type: {raw_value!r}") from err


def _normalize_optional_float_selector(raw_value: Any) -> float | None:
    """Normalize an optional number selector value."""
    return room_config.normalize_optional_float(_unwrap_selector_value(raw_value))


def _normalize_non_negative_int_selector(raw_value: Any, *, default: int) -> int:
    """Normalize a non-negative integer selector value."""
    return room_config.normalize_non_negative_int(
        _unwrap_selector_value(raw_value),
        default=default,
    )


def _unwrap_room_selector_values(values: dict[str, Any]) -> dict[str, Any]:
    """Unwrap room selector payloads before backend-owned normalization."""
    unwrapped = dict(values)
    for key in (
        CONF_PRIMARY_CLIMATE_ENTITY_ID,
        CONF_HUMIDITY_ENTITY_ID,
        CONF_WINDOW_ENTITY_ID,
    ):
        unwrapped[key] = _normalize_optional_entity_selector(values.get(key))
    for key in (
        CONF_WINDOW_CUSTOM_TEMPERATURE,
        CONF_WINDOW_OPEN_DELAY_SECONDS,
        CONF_HOME_TARGET_TEMPERATURE,
        CONF_AWAY_TARGET_TEMPERATURE,
        CONF_SCHEDULE_HOME_START,
        CONF_SCHEDULE_HOME_END,
    ):
        if key in values:
            unwrapped[key] = _unwrap_selector_value(values.get(key))
    if CONF_WINDOW_ACTION_TYPE in values:
        unwrapped[CONF_WINDOW_ACTION_TYPE] = _normalize_window_action_type_selector(
            values.get(CONF_WINDOW_ACTION_TYPE)
        )
    if CONF_AWAY_TARGET_TYPE in values:
        unwrapped[CONF_AWAY_TARGET_TYPE] = _normalize_target_type_selector(
            values.get(CONF_AWAY_TARGET_TYPE)
        )
    raw_schedule = _unwrap_selector_value(values.get(CONF_SCHEDULE))
    if isinstance(raw_schedule, dict):
        unwrapped[CONF_SCHEDULE] = {
            key: _unwrap_selector_value(value) for key, value in raw_schedule.items()
        }
    return unwrapped


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


def _merge_room_submission(
    stored_values: dict[str, Any],
    submitted_values: dict[str, Any],
) -> dict[str, Any]:
    """Merge room form submissions while allowing cleared selectors to stay cleared."""
    merged = {**stored_values, **submitted_values}
    for entity_key in (
        CONF_PRIMARY_CLIMATE_ENTITY_ID,
        CONF_HUMIDITY_ENTITY_ID,
        CONF_WINDOW_ENTITY_ID,
    ):
        if entity_key not in submitted_values:
            merged[entity_key] = None
    return merged


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
                options=[
                    {"value": "away", "label": "Treat as away"},
                    {"value": "home", "label": "Treat as home"},
                ],
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


def _build_window_custom_temperature_schema(value: float | None) -> vol.Schema:
    """Build the custom-temperature step schema for window automation."""
    return vol.Schema(
        {
            vol.Required(
                CONF_WINDOW_CUSTOM_TEMPERATURE,
                default=DEFAULT_WINDOW_CUSTOM_TEMPERATURE if value is None else value,
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=5,
                    max=35,
                    step=0.5,
                    mode=selector.NumberSelectorMode.BOX,
                    unit_of_measurement="°C",
                )
            ),
        }
    )


def _build_profiles_schema(rooms: list[dict[str, Any]]) -> vol.Schema:
    """Build the regulation-profile management schema."""
    return vol.Schema(
        {
            vol.Required(CONF_PROFILE_ACTION): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=[
                        {"value": PROFILE_ACTION_ADD, "label": "Add profile"},
                        {"value": PROFILE_ACTION_EDIT, "label": "Edit profile"},
                        {"value": PROFILE_ACTION_REMOVE, "label": "Remove profile"},
                        {"value": PROFILE_ACTION_FINISH, "label": "Finish"},
                    ],
                    sort=False,
                )
            )
        }
    )


def _build_profile_select_schema(rooms: list[dict[str, Any]]) -> vol.Schema:
    """Build the profile selection schema for edit/remove actions."""
    return vol.Schema(
        {
            vol.Required(CONF_PROFILE_INDEX): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=[
                        {"value": str(index), "label": _profile_label(room)}
                        for index, room in enumerate(rooms)
                    ],
                    sort=False,
                )
            )
        }
    )


def _profile_label(room: dict[str, Any]) -> str:
    """Return a compact label for one configured profile."""
    entity_id = room.get(CONF_PRIMARY_CLIMATE_ENTITY_ID)
    if isinstance(entity_id, str) and entity_id:
        return entity_id
    return "New regulation profile"


def _has_duplicate_profile_anchor(
    hass: Any,
    rooms: list[dict[str, Any]],
    primary_climate_entity_id: str,
    area_id: str,
    *,
    exclude_index: int | None,
) -> bool:
    """Return whether a profile duplicates an existing primary climate or HA area."""
    for index, room in enumerate(rooms):
        if index == exclude_index:
            continue
        if room.get(CONF_PRIMARY_CLIMATE_ENTITY_ID) == primary_climate_entity_id:
            return True
        existing_primary_climate_entity_id = room.get(CONF_PRIMARY_CLIMATE_ENTITY_ID)
        if not isinstance(existing_primary_climate_entity_id, str):
            continue
        existing_area_id = _resolve_area_reference(hass, existing_primary_climate_entity_id).area_id
        if existing_area_id is not None and existing_area_id == area_id:
            return True
    return False


def _build_room_schema(values: dict[str, Any]) -> vol.Schema:
    """Build the regulation-profile schema."""
    return vol.Schema(
        {
            vol.Optional(CONF_PRIMARY_CLIMATE_ENTITY_ID): selector.EntitySelector(
                selector.EntitySelectorConfig(
                    domain="climate",
                    multiple=False,
                )
            ),
            vol.Optional(CONF_HUMIDITY_ENTITY_ID): selector.EntitySelector(
                selector.EntitySelectorConfig(
                    domain="sensor",
                    multiple=False,
                )
            ),
            vol.Optional(CONF_WINDOW_ENTITY_ID): selector.EntitySelector(
                selector.EntitySelectorConfig(
                    domain="binary_sensor",
                    multiple=False,
                )
            ),
            vol.Required(
                CONF_WINDOW_ACTION_TYPE,
                default=values.get(CONF_WINDOW_ACTION_TYPE, DEFAULT_WINDOW_ACTION_TYPE),
            ): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=[
                        {"value": "off", "label": "Turn off if supported"},
                        {
                            "value": "frost_protection",
                            "label": "Use frost protection if supported",
                        },
                        {"value": "minimum_temperature", "label": "Use minimum temperature"},
                        {"value": "custom_temperature", "label": "Use custom temperature"},
                    ],
                    sort=False,
                )
            ),
            vol.Required(
                CONF_WINDOW_OPEN_DELAY_SECONDS,
                default=values.get(
                    CONF_WINDOW_OPEN_DELAY_SECONDS,
                    DEFAULT_WINDOW_OPEN_DELAY_SECONDS,
                ),
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=0,
                    max=3600,
                    step=1,
                    mode=selector.NumberSelectorMode.BOX,
                    unit_of_measurement="s",
                )
            ),
            vol.Required(
                CONF_HOME_TARGET_TEMPERATURE,
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
            ): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=[
                        {"value": "absolute", "label": "Absolute temperature"},
                        {"value": "relative", "label": "Relative delta"},
                    ],
                    sort=False,
                )
            ),
            vol.Required(
                CONF_AWAY_TARGET_TEMPERATURE,
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=-10,
                    max=35,
                    step=0.5,
                    mode=selector.NumberSelectorMode.BOX,
                    unit_of_measurement="°C",
                )
            ),
            vol.Required(
                CONF_SCHEDULE_HOME_START,
                default=values.get(CONF_SCHEDULE_HOME_START, DEFAULT_SCHEDULE_HOME_START),
            ): selector.TimeSelector(),
            vol.Required(
                CONF_SCHEDULE_HOME_END,
                default=values.get(CONF_SCHEDULE_HOME_END, DEFAULT_SCHEDULE_HOME_END),
            ): selector.TimeSelector(),
        }
    )
