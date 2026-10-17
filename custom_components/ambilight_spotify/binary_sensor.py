"""Binary sensor: is the integration driving the lights right now?"""

from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.const import EntityCategory
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
    """Set up the syncing binary sensor."""
    async_add_entities([SyncingBinarySensor(entry.runtime_data)])


class SyncingBinarySensor(AmbilightEntity, BinarySensorEntity):
    """On while the enabled sync, the player and every condition line up."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, manager: AmbilightManager) -> None:
        """Initialise the binary sensor."""
        super().__init__(manager, "syncing")

    @property
    def is_on(self) -> bool:
        """Return whether the lights are being driven."""
        return self.manager.live

    async def async_added_to_hass(self) -> None:
        """Refresh whenever the manager publishes something."""
        await super().async_added_to_hass()
        self.async_on_remove(
            async_dispatcher_connect(self.hass, self.manager.signal, self._handle_update)
        )

    @callback
    def _handle_update(self) -> None:
        self.async_write_ha_state()
