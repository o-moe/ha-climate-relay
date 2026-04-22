"""Pure domain models."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True, slots=True)
class ClimateCapabilities:
    """Subset of climate capabilities relevant to open-window handling."""

    supports_off: bool
    supports_preset_frost: bool
    min_temperature: float


@dataclass(frozen=True, slots=True)
class EffectiveTarget:
    """Resolved target written to a climate entity."""

    hvac_mode: str | None
    preset_mode: str | None
    target_temperature: float | None


@dataclass(frozen=True, slots=True)
class RoomTarget:
    """A temperature target configured for a room."""

    mode: Literal["absolute", "relative"]
    temperature: float
