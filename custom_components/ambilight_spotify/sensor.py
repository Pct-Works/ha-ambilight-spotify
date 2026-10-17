"""Sensor: accent colour of the current artwork."""

from __future__ import annotations

import colorsys
from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import AmbilightConfigEntry
from .entity import AmbilightEntity
from .manager import AmbilightManager


async def async_setup_entry(
    hass: HomeAssistant,
    entry: AmbilightConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the accent colour sensor."""
    async_add_entities([AccentColorSensor(entry.runtime_data)])


class AccentColorSensor(AmbilightEntity, SensorEntity):
    """Publishes the accent colour (``#rrggbb``) so dashboards can use it."""

    def __init__(self, manager: AmbilightManager) -> None:
        """Initialise the sensor."""
        super().__init__(manager, "accent_color")

    @property
    def native_value(self) -> str | None:
        """Return the colour as hex, or None until a song has been analysed."""
        return self.manager.accent_hex

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return the colour in other formats, ready for light.turn_on."""
        if (rgb := self.manager.accent) is None:
            return None
        h, s, _ = colorsys.rgb_to_hsv(*(c / 255 for c in rgb))
        return {
            "rgb_color": list(rgb),
            "hs_color": [round(h * 360, 1), round(s * 100, 1)],
            "mode": self.manager.mode,
        }

    async def async_added_to_hass(self) -> None:
        """Refresh whenever the manager publishes something."""
        await super().async_added_to_hass()
        self.async_on_remove(
            async_dispatcher_connect(self.hass, self.manager.signal, self._handle_update)
        )

    @callback
    def _handle_update(self) -> None:
        self.async_write_ha_state()
