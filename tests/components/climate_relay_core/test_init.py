"""Basic integration entry-point tests."""

from __future__ import annotations

from types import SimpleNamespace
from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock, Mock

from homeassistant.const import Platform

from custom_components.climate_relay_core import (
    PLATFORMS,
    _async_handle_set_global_mode,
    _async_register_services,
    async_setup,
    async_setup_entry,
    async_unload_entry,
)
from custom_components.climate_relay_core.const import DOMAIN, SERVICE_SET_GLOBAL_MODE
from custom_components.climate_relay_core.domain import GlobalMode


class IntegrationSetupTests(IsolatedAsyncioTestCase):
    """Test integration setup entry points."""

    async def test_async_setup_initializes_domain_storage(self) -> None:
        hass = AsyncMock()
        hass.data = {}

        self.assertTrue(await async_setup(hass, {}))
        self.assertIn(DOMAIN, hass.data)

    async def test_async_setup_entry_stores_entry_metadata(self) -> None:
        hass = AsyncMock()
        hass.data = {}
        hass.config_entries.async_forward_entry_setups = AsyncMock()
        hass.services.has_service = Mock(return_value=False)
        hass.services.async_register = Mock()
        hass.services.async_remove = Mock()

        entry = AsyncMock()
        entry.entry_id = "entry-1"
        entry.title = "Test Entry"
        entry.data = {}
        entry.options = {}
        entry.add_update_listener = Mock(return_value=lambda: None)

        self.assertTrue(await async_setup_entry(hass, entry))
        self.assertEqual(hass.data[DOMAIN]["entry-1"]["title"], "Test Entry")
        self.assertEqual(PLATFORMS, [Platform.SELECT, Platform.CLIMATE])
        hass.services.async_register.assert_called_once()
        self.assertEqual(hass.services.async_register.call_args.args[1], SERVICE_SET_GLOBAL_MODE)

    async def test_async_unload_entry_removes_entry_metadata(self) -> None:
        hass = AsyncMock()
        remove_listener = Mock()
        hass.data = {
            DOMAIN: {"entry-1": {"title": "Test Entry", "remove_listener": remove_listener}}
        }
        hass.config_entries.async_unload_platforms = AsyncMock(return_value=True)
        hass.services.async_remove = Mock()

        entry = AsyncMock()
        entry.entry_id = "entry-1"

        self.assertTrue(await async_unload_entry(hass, entry))
        self.assertNotIn("entry-1", hass.data[DOMAIN])
        hass.services.async_remove.assert_called_once_with(DOMAIN, SERVICE_SET_GLOBAL_MODE)

    async def test_async_unload_entry_keeps_service_when_other_entries_remain(self) -> None:
        hass = AsyncMock()
        remove_listener = Mock()
        hass.data = {
            DOMAIN: {
                "entry-1": {"remove_listener": remove_listener},
                "entry-2": {"remove_listener": Mock()},
            }
        }
        hass.config_entries.async_unload_platforms = AsyncMock(return_value=True)
        hass.services.async_remove = Mock()

        entry = AsyncMock()
        entry.entry_id = "entry-1"

        self.assertTrue(await async_unload_entry(hass, entry))
        hass.services.async_remove.assert_not_called()

    async def test_register_services_is_idempotent(self) -> None:
        hass = AsyncMock()
        hass.services.has_service = Mock(return_value=True)
        hass.services.async_register = Mock()

        _async_register_services(hass)

        hass.services.async_register.assert_not_called()

    async def test_set_global_mode_service_updates_runtime(self) -> None:
        runtime = Mock()
        runtime.async_set_global_mode = AsyncMock()
        hass = AsyncMock()
        hass.data = {DOMAIN: {"entry-1": {"runtime": runtime}}}
        service_call = SimpleNamespace(
            hass=hass,
            data={"mode": "home"},
        )

        await _async_handle_set_global_mode(service_call)

        runtime.async_set_global_mode.assert_awaited_once_with(
            GlobalMode.HOME,
            source="service",
        )

    async def test_set_global_mode_service_returns_when_no_entries_exist(self) -> None:
        hass = AsyncMock()
        hass.data = {DOMAIN: {}}
        service_call = SimpleNamespace(
            hass=hass,
            data={"mode": "away"},
        )

        self.assertIsNone(await _async_handle_set_global_mode(service_call))

    async def test_entry_update_reloads_config_entry(self) -> None:
        hass = AsyncMock()
        hass.config_entries.async_reload = AsyncMock()
        entry = SimpleNamespace(
            entry_id="entry-1",
            data={},
            options={"fallback_temperature": 17.5},
        )

        from custom_components.climate_relay_core import _async_handle_entry_update

        await _async_handle_entry_update(hass, entry)

        hass.config_entries.async_reload.assert_awaited_once_with("entry-1")
