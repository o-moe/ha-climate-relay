"""Basic integration entry-point tests."""

from __future__ import annotations

from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock

from custom_components.climate_relay_core import (
    async_setup,
    async_setup_entry,
    async_unload_entry,
)
from custom_components.climate_relay_core.const import DOMAIN


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

        entry = AsyncMock()
        entry.entry_id = "entry-1"
        entry.title = "Test Entry"

        self.assertTrue(await async_setup_entry(hass, entry))
        self.assertEqual(hass.data[DOMAIN]["entry-1"]["title"], "Test Entry")

    async def test_async_unload_entry_removes_entry_metadata(self) -> None:
        hass = AsyncMock()
        hass.data = {DOMAIN: {"entry-1": {"title": "Test Entry"}}}
        hass.config_entries.async_unload_platforms = AsyncMock(return_value=True)

        entry = AsyncMock()
        entry.entry_id = "entry-1"

        self.assertTrue(await async_unload_entry(hass, entry))
        self.assertNotIn("entry-1", hass.data[DOMAIN])
