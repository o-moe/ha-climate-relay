"""Domain logic for mapping window actions to effective targets."""

from __future__ import annotations

from enum import StrEnum

from .models import ClimateCapabilities, EffectiveTarget


class WindowActionType(StrEnum):
    """How to react to an open window."""

    OFF = "off"
    FROST_PROTECTION = "frost_protection"
    MINIMUM_TEMPERATURE = "minimum_temperature"
    CUSTOM_TEMPERATURE = "custom_temperature"


def resolve_window_action(
    action_type: WindowActionType,
    capabilities: ClimateCapabilities,
    *,
    custom_temperature: float | None = None,
) -> EffectiveTarget:
    """Map open-window behavior to a device-compatible effective target."""
    if action_type is WindowActionType.OFF and capabilities.supports_off:
        return EffectiveTarget(hvac_mode="off", preset_mode=None, target_temperature=None)

    if action_type is WindowActionType.FROST_PROTECTION and capabilities.supports_preset_frost:
        return EffectiveTarget(
            hvac_mode="heat",
            preset_mode="frost_protection",
            target_temperature=None,
        )

    if action_type is WindowActionType.MINIMUM_TEMPERATURE:
        return EffectiveTarget(
            hvac_mode="heat",
            preset_mode=None,
            target_temperature=capabilities.min_temperature,
        )

    if action_type is WindowActionType.CUSTOM_TEMPERATURE:
        if custom_temperature is None:
            raise ValueError("custom_temperature is required for custom_temperature mode")
        return EffectiveTarget(
            hvac_mode="heat",
            preset_mode=None,
            target_temperature=custom_temperature,
        )

    return EffectiveTarget(
        hvac_mode="heat",
        preset_mode=None,
        target_temperature=capabilities.min_temperature,
    )
