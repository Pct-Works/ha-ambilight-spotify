"""Shared fixtures."""

from __future__ import annotations

import io
from collections.abc import Generator
from unittest.mock import patch

from PIL import Image
import pytest

from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component
from pytest_homeassistant_custom_component.common import MockConfigEntry, async_mock_service

from custom_components.ambilight_spotify.const import (
    CONF_MEDIA_PLAYER,
    CONF_TARGET_LIGHTS,
    CONF_TRANSITION,
    DOMAIN,
)

PLAYER = "media_player.spotify"
LIGHT_A = "light.strip_a"
LIGHT_B = "light.strip_b"
PICTURE_1 = "/api/media_player_proxy/media_player.spotify?token=a&cache=1"
PICTURE_2 = "/api/media_player_proxy/media_player.spotify?token=a&cache=2"


def png(color: tuple[int, int, int]) -> bytes:
    """Return a solid-colour PNG."""
    buf = io.BytesIO()
    Image.new("RGB", (48, 48), color).save(buf, format="PNG")
    return buf.getvalue()


BLUE = png((10, 30, 210))
RED = png((210, 30, 20))


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations: None) -> None:
    """Let Home Assistant load custom_components/."""


@pytest.fixture
def images() -> Generator[dict[str, bytes]]:
    """Map artwork URL -> image bytes served by the patched downloader."""
    served = {PICTURE_1: BLUE, PICTURE_2: RED}

    async def fake_fetch(self, picture: str) -> bytes | None:
        return served.get(picture)

    with patch(
        "custom_components.ambilight_spotify.manager.AmbilightManager._async_fetch_image",
        fake_fetch,
    ):
        yield served


@pytest.fixture
async def light_calls(hass: HomeAssistant) -> list:
    """Record light.turn_on calls.

    The real light component is loaded first, otherwise setting up the
    integration would load it later and replace the mocked service.
    """
    assert await async_setup_component(hass, "light", {})
    return async_mock_service(hass, "light", "turn_on")


def make_entry(**options) -> MockConfigEntry:
    """Create a config entry with sensible defaults."""
    base = {CONF_TARGET_LIGHTS: [LIGHT_A, LIGHT_B], CONF_TRANSITION: 1.0}
    base.update(options)
    return MockConfigEntry(
        domain=DOMAIN,
        title="Spotify",
        unique_id=PLAYER,
        data={CONF_MEDIA_PLAYER: PLAYER},
        options=base,
    )
