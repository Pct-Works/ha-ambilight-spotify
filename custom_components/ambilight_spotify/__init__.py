"""Ambilight Spotify: sync lights with the accent colour of the album artwork."""

from __future__ import annotations

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry, ConfigEntryState
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.typing import ConfigType

from .const import ATTR_CONFIG_ENTRY_ID, DOMAIN, SERVICE_APPLY
from .manager import AmbilightManager

type AmbilightConfigEntry = ConfigEntry[AmbilightManager]

PLATFORMS: list[Platform] = [
    Platform.BINARY_SENSOR,
    Platform.NUMBER,
    Platform.SELECT,
    Platform.SENSOR,
    Platform.SWITCH,
]

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

SERVICE_APPLY_SCHEMA = vol.Schema(
    {
        vol.Optional(ATTR_CONFIG_ENTRY_ID): cv.string,
        vol.Optional("entity_id"): cv.entity_ids,
    }
)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Register the integration services."""

    async def async_handle_apply(call: ServiceCall) -> None:
        """Re-send the current colour (or the default one) to the lights."""
        entries: list[AmbilightConfigEntry] = [
            entry
            for entry in hass.config_entries.async_entries(DOMAIN)
            if entry.state is ConfigEntryState.LOADED
        ]
        if entry_id := call.data.get(ATTR_CONFIG_ENTRY_ID):
            entries = [entry for entry in entries if entry.entry_id == entry_id]
            if not entries:
                raise ServiceValidationError(
                    translation_domain=DOMAIN,
                    translation_key="entry_not_found",
                    translation_placeholders={"entry_id": entry_id},
                )

        targets = call.data.get("entity_id")
        for entry in entries:
            await entry.runtime_data.async_refresh(force_any=True, targets=targets)

    hass.services.async_register(
        DOMAIN, SERVICE_APPLY, async_handle_apply, schema=SERVICE_APPLY_SCHEMA
    )
    return True


async def async_setup_entry(hass: HomeAssistant, entry: AmbilightConfigEntry) -> bool:
    """Set up Ambilight Spotify from a config entry."""
    manager = AmbilightManager(hass, entry)
    entry.runtime_data = manager

    # Entities restore their last value into the manager while they are added.
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    await manager.async_start()

    entry.async_on_unload(manager.async_stop)
    entry.async_on_unload(entry.add_update_listener(_async_options_updated))
    return True


async def _async_options_updated(hass: HomeAssistant, entry: AmbilightConfigEntry) -> None:
    """Reload when the options change."""
    hass.config_entries.async_schedule_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: AmbilightConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
