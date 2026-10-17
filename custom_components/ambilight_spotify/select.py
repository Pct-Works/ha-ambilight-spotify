"""Select: colour mode."""

from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

from . import AmbilightConfigEntry
from .const import MODES
from .entity import AmbilightEntity
from .manager import AmbilightManager


async def async_setup_entry(
    hass: HomeAssistant,
    entry: AmbilightConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the mode select."""
    async_add_entities([AmbilightModeSelect(entry.runtime_data)])


class AmbilightModeSelect(AmbilightEntity, SelectEntity, RestoreEntity):
    """Chooses how the accent colour is built from the artwork."""

    _attr_entity_category = EntityCategory.CONFIG
    _attr_options = MODES

    def __init__(self, manager: AmbilightManager) -> None:
        """Initialise the select."""
        super().__init__(manager, "mode")

    @property
    def current_option(self) -> str:
        """Return the active mode."""
        return self.manager.mode

    async def async_added_to_hass(self) -> None:
        """Restore the last mode."""
        await super().async_added_to_hass()
        last = await self.async_get_last_state()
        if last is not None and last.state in MODES:
            self.manager.mode = last.state

    async def async_select_option(self, option: str) -> None:
        """Change the mode; it applies immediately to the current song."""
        self.manager.async_update_settings(mode=option)
        self.async_write_ha_state()
