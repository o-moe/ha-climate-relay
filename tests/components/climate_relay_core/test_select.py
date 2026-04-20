"""Tests for the global mode select entity."""

from __future__ import annotations

from types import SimpleNamespace
from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock, Mock

from custom_components.climate_relay_core.const import ATTR_SIMULATION_MODE, DOMAIN
from custom_components.climate_relay_core.domain import EffectivePresence, GlobalMode
from custom_components.climate_relay_core.select import (
    ClimateRelayCoreGlobalModeSelect,
    async_setup_entry,
)


class GlobalModeSelectTests(IsolatedAsyncioTestCase):
    """Test the global mode select behavior."""

    async def test_entity_exposes_expected_options_and_current_option(self) -> None:
        runtime = Mock()
        runtime.global_mode = GlobalMode.AUTO
        runtime.effective_presence = EffectivePresence.AWAY
        runtime.config = SimpleNamespace(
            unknown_state_handling="away",
            fallback_temperature=20.0,
            manual_override_reset_time=None,
            simulation_mode=False,
        )

        entity = ClimateRelayCoreGlobalModeSelect("entry-1", "ClimateRelayCore", runtime)

        self.assertEqual(entity.options, ["auto", "home", "away"])
        self.assertEqual(entity.current_option, "auto")
        self.assertEqual(entity.extra_state_attributes["effective_presence"], "away")
        self.assertEqual(entity.extra_state_attributes[ATTR_SIMULATION_MODE], "off")

    async def test_selecting_an_option_updates_runtime(self) -> None:
        runtime = Mock()
        runtime.global_mode = GlobalMode.AUTO
        runtime.effective_presence = EffectivePresence.HOME
        runtime.config = SimpleNamespace(
            unknown_state_handling="away",
            fallback_temperature=20.0,
            manual_override_reset_time=None,
            simulation_mode=True,
        )
        runtime.async_set_global_mode = AsyncMock()

        entity = ClimateRelayCoreGlobalModeSelect("entry-1", "ClimateRelayCore", runtime)

        await entity.async_select_option("away")

        runtime.async_set_global_mode.assert_awaited_once_with(
            GlobalMode.AWAY,
            source="select",
        )

    async def test_setup_entry_adds_global_mode_entity(self) -> None:
        runtime = Mock()
        hass = Mock()
        hass.data = {DOMAIN: {"entry-1": {"runtime": runtime}}}
        entry = SimpleNamespace(entry_id="entry-1", title="ClimateRelayCore")
        async_add_entities = Mock()

        await async_setup_entry(hass, entry, async_add_entities)

        async_add_entities.assert_called_once()
        (entity,) = async_add_entities.call_args.args[0]
        self.assertIsInstance(entity, ClimateRelayCoreGlobalModeSelect)

    async def test_entity_registers_runtime_updates_when_added_to_hass(self) -> None:
        runtime = Mock()
        runtime.global_mode = GlobalMode.AUTO
        runtime.effective_presence = EffectivePresence.AWAY
        runtime.config = SimpleNamespace(
            unknown_state_handling="away",
            fallback_temperature=20.0,
            manual_override_reset_time=None,
            simulation_mode=False,
        )
        runtime.subscribe = Mock(return_value=lambda: None)

        entity = ClimateRelayCoreGlobalModeSelect("entry-1", "ClimateRelayCore", runtime)
        entity.async_on_remove = Mock()
        entity.async_write_ha_state = Mock()

        await entity.async_added_to_hass()
        entity._handle_runtime_update()

        runtime.subscribe.assert_called_once()
        entity.async_on_remove.assert_called_once()
        entity.async_write_ha_state.assert_called_once()
