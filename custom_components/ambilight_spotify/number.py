"""Numbers: minimum brightness and minimum saturation."""

from __future__ import annotations

from homeassistant.components.number import NumberMode, RestoreNumber
from homeassistant.const import PERCENTAGE, EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import AmbilightConfigEntry
from .entity import AmbilightEntity
from .manager import AmbilightManager

KEY_BRIGHTNESS = "brightness_min"
KEY_SATURATION = "saturation_min"


async def async_setup_entry(
    hass: HomeAssistant,
    entry: AmbilightConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the number entities."""
    manager = entry.runtime_data
    async_add_entities(
        [AmbilightNumber(manager, KEY_BRIGHTNESS), AmbilightNumber(manager, KEY_SATURATION)]
    )


class AmbilightNumber(AmbilightEntity, RestoreNumber):
    """A 0-100 % tuning slider stored on the manager."""

    _attr_entity_category = EntityCategory.CONFIG
    _attr_native_min_value = 0
    _attr_native_max_value = 100
    _attr_native_step = 1
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_mode = NumberMode.SLIDER

    def __init__(self, manager: AmbilightManager, key: str) -> None:
        """Initialise the number."""
        super().__init__(manager, key)
        self._key = key

    @property
    def native_value(self) -> float:
        """Return the current value."""
        return getattr(self.manager, self._key)

    async def async_added_to_hass(self) -> None:
        """Restore the last value."""
        await super().async_added_to_hass()
        last = await self.async_get_last_number_data()
        if last is not None and last.native_value is not None:
            setattr(self.manager, self._key, float(last.native_value))

    async def async_set_native_value(self, value: float) -> None:
        """Change the value; it applies immediately to the current song."""
        self.manager.async_update_settings(**{self._key: float(value)})
        self.async_write_ha_state()
