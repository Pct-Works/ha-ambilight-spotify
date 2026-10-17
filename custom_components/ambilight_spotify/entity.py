"""Base entity for Ambilight Spotify."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity import Entity

from .const import DOMAIN
from .manager import AmbilightManager


class AmbilightEntity(Entity):
    """Entity attached to one Ambilight Spotify config entry."""

    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(self, manager: AmbilightManager, key: str) -> None:
        """Initialise the entity."""
        self.manager = manager
        self._attr_translation_key = key
        self._attr_unique_id = f"{manager.entry.entry_id}_{key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, manager.entry.entry_id)},
            name=manager.entry.title,
            entry_type=DeviceEntryType.SERVICE,
            manufacturer="Ambilight Spotify",
        )
