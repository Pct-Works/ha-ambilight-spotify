"""Switch: enable or disable the Ambilight sync."""

from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.const import STATE_ON
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

from . import AmbilightConfigEntry
from .entity import AmbilightEntity
from .manager import AmbilightManager


async def async_setup_entry(
    hass: HomeAssistant,
    entry: AmbilightConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the switch."""
    async_add_entities([AmbilightSwitch(entry.runtime_data)])


class AmbilightSwitch(AmbilightEntity, SwitchEntity, RestoreEntity):
    """Turns the sync on or off."""

    def __init__(self, manager: AmbilightManager) -> None:
        """Initialise the switch."""
        super().__init__(manager, "ambilight")

    @property
    def is_on(self) -> bool:
        """Return whether the sync is enabled."""
        return self.manager.enabled

    async def async_added_to_hass(self) -> None:
        """Restore the last value (enabled by default on first run)."""
        await super().async_added_to_hass()
        if (last := await self.async_get_last_state()) is not None:
            self.manager.enabled = last.state == STATE_ON

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Enable the sync."""
        self.manager.async_update_settings(enabled=True)
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Disable the sync."""
        self.manager.async_update_settings(enabled=False)
        self.async_write_ha_state()
