"""Tests for the artwork download paths (not patched here)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from homeassistant.components.media_player import DATA_COMPONENT
from homeassistant.core import HomeAssistant

from .conftest import BLUE, PICTURE_1, PLAYER, make_entry


async def _manager(hass: HomeAssistant):
    entry = make_entry()
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry.runtime_data


async def test_image_comes_from_the_player_entity(hass: HomeAssistant) -> None:
    """The player's own image getter is preferred (no HTTP round trip)."""
    manager = await _manager(hass)

    entity = MagicMock()

    async def get_image():
        return BLUE, "image/png"

    entity.async_get_media_image = get_image
    component = MagicMock()
    component.get_entity.return_value = entity

    with patch.dict(hass.data, {DATA_COMPONENT: component}):
        assert await manager._async_fetch_image(PICTURE_1) == BLUE

    component.get_entity.assert_called_once_with(PLAYER)


async def test_falls_back_to_http_for_relative_urls(hass: HomeAssistant, aioclient_mock) -> None:
    """If the entity cannot give the image, a relative URL is resolved locally."""
    hass.config.internal_url = "http://ha.local:8123"
    manager = await _manager(hass)
    aioclient_mock.get("http://ha.local:8123" + PICTURE_1, content=BLUE)

    component = MagicMock()
    component.get_entity.return_value = None
    with patch.dict(hass.data, {DATA_COMPONENT: component}):
        assert await manager._async_fetch_image(PICTURE_1) == BLUE


async def test_absolute_url_and_http_error(hass: HomeAssistant, aioclient_mock) -> None:
    """Absolute URLs are used as they are; HTTP errors give None, not an exception."""
    manager = await _manager(hass)
    component = MagicMock()
    component.get_entity.return_value = None

    aioclient_mock.get("https://img.example/a.jpg", content=BLUE)
    aioclient_mock.get("https://img.example/missing.jpg", status=404)

    with patch.dict(hass.data, {DATA_COMPONENT: component}):
        assert await manager._async_fetch_image("https://img.example/a.jpg") == BLUE
        assert await manager._async_fetch_image("https://img.example/missing.jpg") is None
