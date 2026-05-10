"""Frontend WebSocket API tests."""

from __future__ import annotations

from types import SimpleNamespace
from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock, Mock, patch

from homeassistant.exceptions import Unauthorized

from custom_components.climate_relay_core import room_management
from custom_components.climate_relay_core.const import (
    CONF_AWAY_TARGET_TEMPERATURE,
    CONF_AWAY_TARGET_TYPE,
    CONF_HOME_TARGET_TEMPERATURE,
    CONF_PRIMARY_CLIMATE_ENTITY_ID,
    CONF_ROOMS,
    CONF_SCHEDULE_HOME_END,
    CONF_SCHEDULE_HOME_START,
    DOMAIN,
)
from custom_components.climate_relay_core.frontend_api import (
    ERROR_AREA_ALREADY_ACTIVE,
    ERROR_CONFIG_ENTRY_UPDATE_FAILED,
    ERROR_INVALID_ENTITY_DOMAIN,
    ERROR_MULTIPLE_CONFIG_ENTRIES,
    ERROR_NO_CONFIG_ENTRY,
    ERROR_PRIMARY_CLIMATE_ALREADY_ACTIVE,
    ERROR_PRIMARY_CLIMATE_AREA_REQUIRED,
    ERROR_UNKNOWN_CANDIDATE,
    FrontendApiError,
    async_activate_room_from_frontend,
    async_register_websocket_commands,
    discover_room_candidates,
    websocket_activate_room,
    websocket_room_candidates,
)
from custom_components.climate_relay_core.runtime import AreaReference


class FrontendApiTests(IsolatedAsyncioTestCase):
    """Test frontend-facing room discovery and activation."""

    def setUp(self) -> None:
        self.entity_registry = Mock()
        self.entity_registry.entities.values.return_value = []
        self.entity_registry.async_get.return_value = None
        self.entity_registry_patch = patch(
            "custom_components.climate_relay_core.frontend_api.er.async_get",
            return_value=self.entity_registry,
        )
        self.entity_registry_patch.start()
        self.addCleanup(self.entity_registry_patch.stop)

    def test_candidate_discovery_returns_climate_entities_from_state_machine(self) -> None:
        hass = _hass_with_entities("climate.office")
        entry = _entry(options={})

        with patch(
            "custom_components.climate_relay_core.frontend_api._resolve_area_reference",
            return_value=AreaReference(area_id="office", area_name="Office"),
        ):
            candidates = discover_room_candidates(hass, entry)

        candidate = candidates["climate.office"]
        self.assertEqual("climate.office", candidate.candidate_id)
        self.assertEqual("office", candidate.area_id)
        self.assertEqual("Office", candidate.area_name)
        self.assertEqual("climate.office", candidate.primary_climate_entity_id)
        self.assertEqual("Office Thermostat", candidate.primary_climate_display_name)
        self.assertFalse(candidate.already_active)
        self.assertIsNone(candidate.unavailable_reason)

    def test_candidate_discovery_marks_active_primary_climate_unavailable(self) -> None:
        hass = _hass_with_entities("climate.office")
        entry = _entry(options={CONF_ROOMS: [_room("climate.office")]})

        with patch(
            "custom_components.climate_relay_core.frontend_api._resolve_area_reference",
            return_value=AreaReference(area_id="office", area_name="Office"),
        ):
            candidates = discover_room_candidates(hass, entry)

        candidate = candidates["climate.office"]
        self.assertTrue(candidate.already_active)
        self.assertEqual("duplicate_primary_climate", candidate.unavailable_reason)

    def test_candidate_discovery_marks_missing_area_unavailable(self) -> None:
        hass = _hass_with_entities("climate.loose")
        entry = _entry(options={})

        with patch(
            "custom_components.climate_relay_core.frontend_api._resolve_area_reference",
            return_value=AreaReference(area_id=None, area_name=None),
        ):
            candidates = discover_room_candidates(hass, entry)

        self.assertEqual("missing_area", candidates["climate.loose"].unavailable_reason)

    def test_candidate_discovery_marks_duplicate_area_unavailable(self) -> None:
        hass = _hass_with_entities("climate.office", "climate.office_secondary")
        entry = _entry(options={CONF_ROOMS: [_room("climate.office")]})

        def resolve_area(_hass: object, entity_id: str) -> AreaReference:
            if entity_id == "climate.office":
                return AreaReference(area_id="office", area_name="Office")
            return AreaReference(area_id="office", area_name="Office")

        with patch(
            "custom_components.climate_relay_core.frontend_api._resolve_area_reference",
            side_effect=resolve_area,
        ):
            candidates = discover_room_candidates(hass, entry)

        self.assertEqual(
            "duplicate_area",
            candidates["climate.office_secondary"].unavailable_reason,
        )

    def test_candidate_discovery_excludes_climate_relay_room_states(self) -> None:
        hass = _hass_with_entities("climate.office", "climate.climate_relay_office")
        entry = _entry(options={})

        def state_for_entity(entity_id: str) -> SimpleNamespace:
            if entity_id == "climate.climate_relay_office":
                return SimpleNamespace(
                    attributes={
                        "friendly_name": "Office",
                        "primary_climate_entity_id": "climate.office",
                    }
                )
            return SimpleNamespace(attributes={"friendly_name": "Office Thermostat"})

        hass.states.get.side_effect = state_for_entity

        with patch(
            "custom_components.climate_relay_core.frontend_api._resolve_area_reference",
            return_value=AreaReference(area_id="office", area_name="Office"),
        ):
            candidates = discover_room_candidates(hass, entry)

        self.assertIn("climate.office", candidates)
        self.assertNotIn("climate.climate_relay_office", candidates)

    def test_candidate_discovery_excludes_climate_relay_registry_entries(self) -> None:
        hass = _hass_with_entities()
        entry = _entry(options={})
        hass.states.get.side_effect = lambda _entity_id: None
        self.entity_registry.entities.values.return_value = [
            SimpleNamespace(
                domain="climate",
                entity_id="climate.climate_relay_office",
                platform=DOMAIN,
            ),
            SimpleNamespace(
                domain="climate",
                entity_id="climate.office",
                platform="some_integration",
            ),
        ]

        with patch(
            "custom_components.climate_relay_core.frontend_api._resolve_area_reference",
            return_value=AreaReference(area_id="office", area_name="Office"),
        ):
            candidates = discover_room_candidates(hass, entry)

        self.assertIn("climate.office", candidates)
        self.assertNotIn("climate.climate_relay_office", candidates)

    def test_candidate_discovery_includes_climate_entities_from_registry(self) -> None:
        hass = _hass_with_entities()
        entry = _entry(options={})
        hass.states.get.side_effect = lambda _entity_id: None
        self.entity_registry.entities.values.return_value = [
            SimpleNamespace(domain="climate", entity_id="climate.registry_room")
        ]
        self.entity_registry.async_get.return_value = SimpleNamespace(
            name="Registry Thermostat",
            original_name="Original Thermostat",
        )

        with patch(
            "custom_components.climate_relay_core.frontend_api._resolve_area_reference",
            return_value=AreaReference(area_id="registry_room", area_name="Registry Room"),
        ):
            candidates = discover_room_candidates(hass, entry)

        self.assertEqual(
            "Registry Thermostat",
            candidates["climate.registry_room"].primary_climate_display_name,
        )

    def test_registers_websocket_commands(self) -> None:
        hass = Mock()

        with patch(
            "custom_components.climate_relay_core.frontend_api.websocket_api.async_register_command"
        ) as register_command:
            async_register_websocket_commands(hass)

        self.assertEqual(2, register_command.call_count)

    async def test_activation_updates_config_entry_options_and_relies_on_listener_reload(
        self,
    ) -> None:
        hass = _hass_with_entities("climate.bedroom")
        entry = _entry(entry_id="entry-1", options={})
        hass.data = {DOMAIN: {"entry-1": {}}}
        hass.config_entries.async_entries.return_value = [entry]
        hass.config_entries.async_reload = AsyncMock()

        with patch(
            "custom_components.climate_relay_core.frontend_api._resolve_area_reference",
            return_value=AreaReference(area_id="bedroom", area_name="Bedroom"),
        ):
            result = await async_activate_room_from_frontend(
                hass,
                candidate_id="climate.bedroom",
            )

        self.assertTrue(result["activated"])
        hass.config_entries.async_update_entry.assert_called_once()
        updated_options = hass.config_entries.async_update_entry.call_args.kwargs["options"]
        self.assertEqual(
            "climate.bedroom",
            updated_options[CONF_ROOMS][0][CONF_PRIMARY_CLIMATE_ENTITY_ID],
        )
        self.assertIn(CONF_HOME_TARGET_TEMPERATURE, updated_options[CONF_ROOMS][0])
        hass.config_entries.async_reload.assert_not_called()

    async def test_activation_uses_room_management_activate_room(self) -> None:
        hass = _hass_with_entities("climate.bedroom")
        entry = _entry(entry_id="entry-1", options={})
        hass.data = {DOMAIN: {"entry-1": {}}}
        hass.config_entries.async_entries.return_value = [entry]
        hass.config_entries.async_reload = AsyncMock(return_value=True)

        with (
            patch(
                "custom_components.climate_relay_core.frontend_api._resolve_area_reference",
                return_value=AreaReference(area_id="bedroom", area_name="Bedroom"),
            ),
            patch(
                "custom_components.climate_relay_core.frontend_api.room_management.activate_room",
                return_value=[_room("climate.bedroom")],
            ) as activate_room,
        ):
            await async_activate_room_from_frontend(hass, candidate_id="climate.bedroom")

        activate_room.assert_called_once()

    async def test_activation_rejects_duplicate_primary_climate(self) -> None:
        hass = _hass_with_entities("climate.office")
        entry = _entry(entry_id="entry-1", options={CONF_ROOMS: [_room("climate.office")]})
        hass.data = {DOMAIN: {"entry-1": {}}}
        hass.config_entries.async_entries.return_value = [entry]

        with (
            patch(
                "custom_components.climate_relay_core.frontend_api._resolve_area_reference",
                return_value=AreaReference(area_id="office", area_name="Office"),
            ),
            self.assertRaises(FrontendApiError) as context,
        ):
            await async_activate_room_from_frontend(hass, candidate_id="climate.office")

        self.assertEqual(ERROR_PRIMARY_CLIMATE_ALREADY_ACTIVE, context.exception.code)

    async def test_activation_rejects_duplicate_area(self) -> None:
        hass = _hass_with_entities("climate.office", "climate.office_secondary")
        entry = _entry(entry_id="entry-1", options={CONF_ROOMS: [_room("climate.office")]})
        hass.data = {DOMAIN: {"entry-1": {}}}
        hass.config_entries.async_entries.return_value = [entry]

        with (
            patch(
                "custom_components.climate_relay_core.frontend_api._resolve_area_reference",
                return_value=AreaReference(area_id="office", area_name="Office"),
            ),
            self.assertRaises(FrontendApiError) as context,
        ):
            await async_activate_room_from_frontend(
                hass,
                candidate_id="climate.office_secondary",
            )

        self.assertEqual(ERROR_AREA_ALREADY_ACTIVE, context.exception.code)

    async def test_activation_rejects_missing_area(self) -> None:
        hass = _hass_with_entities("climate.loose")
        entry = _entry(entry_id="entry-1", options={})
        hass.data = {DOMAIN: {"entry-1": {}}}
        hass.config_entries.async_entries.return_value = [entry]

        with (
            patch(
                "custom_components.climate_relay_core.frontend_api._resolve_area_reference",
                return_value=AreaReference(area_id=None, area_name=None),
            ),
            self.assertRaises(FrontendApiError) as context,
        ):
            await async_activate_room_from_frontend(hass, candidate_id="climate.loose")

        self.assertEqual(ERROR_PRIMARY_CLIMATE_AREA_REQUIRED, context.exception.code)

    async def test_activation_rejects_non_climate_entity_domain(self) -> None:
        hass = _hass_with_entities("climate.office")
        entry = _entry(entry_id="entry-1", options={})
        hass.data = {DOMAIN: {"entry-1": {}}}
        hass.config_entries.async_entries.return_value = [entry]

        with self.assertRaises(FrontendApiError) as context:
            await async_activate_room_from_frontend(
                hass,
                primary_climate_entity_id="sensor.office_temperature",
            )

        self.assertEqual(ERROR_INVALID_ENTITY_DOMAIN, context.exception.code)

    async def test_activation_rejects_unknown_candidate(self) -> None:
        hass = _hass_with_entities("climate.office")
        entry = _entry(entry_id="entry-1", options={})
        hass.data = {DOMAIN: {"entry-1": {}}}
        hass.config_entries.async_entries.return_value = [entry]

        with (
            patch(
                "custom_components.climate_relay_core.frontend_api._resolve_area_reference",
                return_value=AreaReference(area_id="office", area_name="Office"),
            ),
            self.assertRaises(FrontendApiError) as context,
        ):
            await async_activate_room_from_frontend(hass, candidate_id="climate.unknown")

        self.assertEqual(ERROR_UNKNOWN_CANDIDATE, context.exception.code)

    async def test_activation_requires_candidate_identifier(self) -> None:
        hass = _hass_with_entities("climate.office")
        entry = _entry(entry_id="entry-1", options={})
        hass.data = {DOMAIN: {"entry-1": {}}}
        hass.config_entries.async_entries.return_value = [entry]

        with self.assertRaises(FrontendApiError) as context:
            await async_activate_room_from_frontend(hass)

        self.assertEqual(ERROR_UNKNOWN_CANDIDATE, context.exception.code)

    async def test_activation_maps_room_management_duplicate_error(self) -> None:
        hass = _hass_with_entities("climate.bedroom")
        entry = _entry(entry_id="entry-1", options={})
        hass.data = {DOMAIN: {"entry-1": {}}}
        hass.config_entries.async_entries.return_value = [entry]

        with (
            patch(
                "custom_components.climate_relay_core.frontend_api._resolve_area_reference",
                return_value=AreaReference(area_id="bedroom", area_name="Bedroom"),
            ),
            patch(
                "custom_components.climate_relay_core.frontend_api.room_management.activate_room",
                side_effect=room_management.DuplicatePrimaryClimateError("duplicate"),
            ),
            self.assertRaises(FrontendApiError) as context,
        ):
            await async_activate_room_from_frontend(hass, candidate_id="climate.bedroom")

        self.assertEqual(ERROR_PRIMARY_CLIMATE_ALREADY_ACTIVE, context.exception.code)

    async def test_activation_maps_room_management_generic_error(self) -> None:
        hass = _hass_with_entities("climate.bedroom")
        entry = _entry(entry_id="entry-1", options={})
        hass.data = {DOMAIN: {"entry-1": {}}}
        hass.config_entries.async_entries.return_value = [entry]

        with (
            patch(
                "custom_components.climate_relay_core.frontend_api._resolve_area_reference",
                return_value=AreaReference(area_id="bedroom", area_name="Bedroom"),
            ),
            patch(
                "custom_components.climate_relay_core.frontend_api.room_management.activate_room",
                side_effect=room_management.MissingPrimaryClimateError("missing"),
            ),
            self.assertRaises(FrontendApiError) as context,
        ):
            await async_activate_room_from_frontend(hass, candidate_id="climate.bedroom")

        self.assertEqual(ERROR_UNKNOWN_CANDIDATE, context.exception.code)

    async def test_activation_maps_config_entry_update_failure(self) -> None:
        hass = _hass_with_entities("climate.bedroom")
        entry = _entry(entry_id="entry-1", options={})
        hass.data = {DOMAIN: {"entry-1": {}}}
        hass.config_entries.async_entries.return_value = [entry]
        hass.config_entries.async_update_entry.side_effect = RuntimeError("update failed")

        with (
            patch(
                "custom_components.climate_relay_core.frontend_api._resolve_area_reference",
                return_value=AreaReference(area_id="bedroom", area_name="Bedroom"),
            ),
            self.assertRaises(FrontendApiError) as context,
        ):
            await async_activate_room_from_frontend(hass, candidate_id="climate.bedroom")

        self.assertEqual(ERROR_CONFIG_ENTRY_UPDATE_FAILED, context.exception.code)

    async def test_activation_requires_one_loaded_config_entry(self) -> None:
        hass = _hass_with_entities("climate.office")
        hass.data = {DOMAIN: {}}

        with self.assertRaises(FrontendApiError) as context:
            await async_activate_room_from_frontend(hass, candidate_id="climate.office")

        self.assertEqual(ERROR_NO_CONFIG_ENTRY, context.exception.code)

        hass.data = {DOMAIN: {"entry-1": {}, "entry-2": {}}}
        with self.assertRaises(FrontendApiError) as context:
            await async_activate_room_from_frontend(hass, candidate_id="climate.office")

        self.assertEqual(ERROR_MULTIPLE_CONFIG_ENTRIES, context.exception.code)

    async def test_activation_rejects_loaded_entry_without_config_entry_object(self) -> None:
        hass = _hass_with_entities("climate.office")
        hass.data = {DOMAIN: {"entry-1": {}}}
        hass.config_entries.async_entries.return_value = []

        with self.assertRaises(FrontendApiError) as context:
            await async_activate_room_from_frontend(hass, candidate_id="climate.office")

        self.assertEqual(ERROR_NO_CONFIG_ENTRY, context.exception.code)

    def test_websocket_commands_require_admin(self) -> None:
        hass = Mock()
        connection = Mock()
        connection.user = SimpleNamespace(is_admin=False)

        with self.assertRaises(Unauthorized):
            websocket_room_candidates(hass, connection, {"id": 1})
        with self.assertRaises(Unauthorized):
            websocket_activate_room(hass, connection, {"id": 2})

    async def test_websocket_room_candidates_sends_result(self) -> None:
        hass = _hass_with_entities("climate.office")
        entry = _entry(entry_id="entry-1", options={})
        hass.data = {DOMAIN: {"entry-1": {}}}
        hass.config_entries.async_entries.return_value = [entry]
        connection = Mock()

        with patch(
            "custom_components.climate_relay_core.frontend_api._resolve_area_reference",
            return_value=AreaReference(area_id="office", area_name="Office"),
        ):
            await websocket_room_candidates.__wrapped__.__wrapped__(hass, connection, {"id": 7})

        connection.send_result.assert_called_once()
        self.assertEqual(7, connection.send_result.call_args.args[0])

    async def test_websocket_room_candidates_sends_structured_error(self) -> None:
        hass = _hass_with_entities()
        hass.data = {DOMAIN: {}}
        connection = Mock()

        await websocket_room_candidates.__wrapped__.__wrapped__(hass, connection, {"id": 8})

        connection.send_error.assert_called_once_with(
            8,
            ERROR_NO_CONFIG_ENTRY,
            "No loaded Climate Relay config entry.",
        )

    async def test_websocket_activate_room_sends_result_and_structured_error(self) -> None:
        hass = _hass_with_entities("climate.bedroom")
        entry = _entry(entry_id="entry-1", options={})
        hass.data = {DOMAIN: {"entry-1": {}}}
        hass.config_entries.async_entries.return_value = [entry]
        hass.config_entries.async_reload = AsyncMock(return_value=True)
        connection = Mock()

        with patch(
            "custom_components.climate_relay_core.frontend_api._resolve_area_reference",
            return_value=AreaReference(area_id="bedroom", area_name="Bedroom"),
        ):
            await websocket_activate_room.__wrapped__.__wrapped__(
                hass,
                connection,
                {"id": 9, "candidate_id": "climate.bedroom"},
            )

        connection.send_result.assert_called_once()

        error_connection = Mock()
        await websocket_activate_room.__wrapped__.__wrapped__(hass, error_connection, {"id": 10})
        error_connection.send_error.assert_called_once()


def _hass_with_entities(*entity_ids: str) -> Mock:
    hass = Mock()
    hass.data = {}
    hass.states.async_entity_ids.return_value = list(entity_ids)
    hass.states.get.side_effect = lambda entity_id: SimpleNamespace(
        attributes={"friendly_name": f"{entity_id.partition('.')[2].title()} Thermostat"}
    )
    hass.config_entries.async_update_entry = Mock()
    hass.config_entries.async_entries.return_value = []
    return hass


def _entry(entry_id: str = "entry-1", options: dict | None = None) -> Mock:
    entry = Mock()
    entry.entry_id = entry_id
    entry.data = {}
    entry.options = options or {}
    return entry


def _room(primary_climate_entity_id: str) -> dict[str, object]:
    return {
        CONF_PRIMARY_CLIMATE_ENTITY_ID: primary_climate_entity_id,
        CONF_HOME_TARGET_TEMPERATURE: 20.0,
        CONF_AWAY_TARGET_TYPE: "absolute",
        CONF_AWAY_TARGET_TEMPERATURE: 17.0,
        CONF_SCHEDULE_HOME_START: "06:00:00",
        CONF_SCHEDULE_HOME_END: "22:00:00",
    }
