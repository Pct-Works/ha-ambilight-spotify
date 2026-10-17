"""Behaviour tests: player -> accent colour -> lights."""

from __future__ import annotations

import colorsys

from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from custom_components.ambilight_spotify.const import (
    CONF_DEFAULT_COLOR,
    CONF_REQUIRE_ENTITY,
    CONF_SOURCE_FILTER,
    DOMAIN,
)

from .conftest import LIGHT_A, LIGHT_B, PICTURE_1, PICTURE_2, PLAYER, make_entry


def _entity_id(hass: HomeAssistant, entry, platform: str, key: str) -> str:
    registry = er.async_get(hass)
    entity_id = registry.async_get_entity_id(platform, DOMAIN, f"{entry.entry_id}_{key}")
    assert entity_id, f"{platform}/{key} not registered"
    return entity_id


def _play(hass: HomeAssistant, picture: str = PICTURE_1, source: str = "PC", state: str = "playing") -> None:
    hass.states.async_set(
        PLAYER, state, {"entity_picture": picture, "source": source, "friendly_name": "Spotify"}
    )


def _lights_on(hass: HomeAssistant, *lights: str) -> None:
    for light in lights or (LIGHT_A, LIGHT_B):
        hass.states.async_set(light, "on")


async def _setup(hass: HomeAssistant, **options):
    entry = make_entry(**options)
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


def _hue(rgb: list[int]) -> float:
    return colorsys.rgb_to_hsv(*(c / 255 for c in rgb))[0]


async def test_entities_are_created(hass: HomeAssistant, images, light_calls) -> None:
    entry = await _setup(hass)
    for platform, key in (
        ("switch", "ambilight"),
        ("select", "mode"),
        ("number", "brightness_min"),
        ("number", "saturation_min"),
        ("sensor", "accent_color"),
        ("binary_sensor", "syncing"),
    ):
        _entity_id(hass, entry, platform, key)
    assert hass.states.get(_entity_id(hass, entry, "switch", "ambilight")).state == "on"


async def test_song_sets_sensor_and_lights(hass: HomeAssistant, images, light_calls) -> None:
    entry = await _setup(hass)
    _lights_on(hass)
    _play(hass)
    await hass.async_block_till_done()

    sensor = hass.states.get(_entity_id(hass, entry, "sensor", "accent_color"))
    assert sensor.state.startswith("#")
    assert 0.55 < _hue(sensor.attributes["rgb_color"]) < 0.72  # blue artwork
    assert hass.states.get(_entity_id(hass, entry, "binary_sensor", "syncing")).state == "on"

    assert len(light_calls) == 1
    data = light_calls[0].data
    assert data["entity_id"] == [LIGHT_A, LIGHT_B]
    assert data["rgb_color"] == sensor.attributes["rgb_color"]
    assert data["transition"] == 1.0
    assert "brightness" not in data and "brightness_pct" not in data


async def test_new_artwork_updates_colour(hass: HomeAssistant, images, light_calls) -> None:
    entry = await _setup(hass)
    _lights_on(hass)
    _play(hass, PICTURE_1)
    await hass.async_block_till_done()
    _play(hass, PICTURE_2)
    await hass.async_block_till_done()

    assert len(light_calls) == 2
    red = light_calls[1].data["rgb_color"]
    assert _hue(red) < 0.05 or _hue(red) > 0.95


async def test_only_lights_that_are_on_are_touched(hass: HomeAssistant, images, light_calls) -> None:
    await _setup(hass)
    hass.states.async_set(LIGHT_A, "on")
    hass.states.async_set(LIGHT_B, "off")
    _play(hass)
    await hass.async_block_till_done()

    assert light_calls[0].data["entity_id"] == [LIGHT_A]


async def test_light_turning_on_during_playback_gets_the_colour(
    hass: HomeAssistant, images, light_calls
) -> None:
    await _setup(hass)
    hass.states.async_set(LIGHT_A, "off")
    hass.states.async_set(LIGHT_B, "off")
    _play(hass)
    await hass.async_block_till_done()
    assert not light_calls

    hass.states.async_set(LIGHT_A, "on")
    await hass.async_block_till_done()
    assert len(light_calls) == 1
    assert light_calls[0].data["entity_id"] == [LIGHT_A]


async def test_source_filter(hass: HomeAssistant, images, light_calls) -> None:
    entry = await _setup(hass, **{CONF_SOURCE_FILTER: ["PC"]})
    _lights_on(hass)

    _play(hass, source="Phone")
    await hass.async_block_till_done()
    assert not light_calls
    assert hass.states.get(_entity_id(hass, entry, "binary_sensor", "syncing")).state == "off"
    # The accent colour is still published for dashboards.
    assert hass.states.get(_entity_id(hass, entry, "sensor", "accent_color")).state.startswith("#")

    _play(hass, source="pc")  # case-insensitive
    await hass.async_block_till_done()
    assert len(light_calls) == 1


async def test_require_entity(hass: HomeAssistant, images, light_calls) -> None:
    await _setup(hass, **{CONF_REQUIRE_ENTITY: "light.all"})
    _lights_on(hass)
    hass.states.async_set("light.all", "off")
    _play(hass)
    await hass.async_block_till_done()
    assert not light_calls

    hass.states.async_set("light.all", "on")
    await hass.async_block_till_done()
    assert len(light_calls) == 1


async def test_switch_off_applies_default_colour_then_back_on(
    hass: HomeAssistant, images, light_calls
) -> None:
    entry = await _setup(hass, **{CONF_DEFAULT_COLOR: [127, 172, 255]})
    _lights_on(hass)
    _play(hass)
    await hass.async_block_till_done()
    light_calls.clear()

    switch = _entity_id(hass, entry, "switch", "ambilight")
    await hass.services.async_call("switch", "turn_off", {"entity_id": switch}, blocking=True)
    await hass.async_block_till_done()
    assert [c.data["rgb_color"] for c in light_calls] == [[127, 172, 255]]

    light_calls.clear()
    await hass.services.async_call("switch", "turn_on", {"entity_id": switch}, blocking=True)
    await hass.async_block_till_done()
    assert len(light_calls) == 1
    assert light_calls[0].data["rgb_color"] != [127, 172, 255]


async def test_switch_off_without_default_leaves_lights_alone(
    hass: HomeAssistant, images, light_calls
) -> None:
    entry = await _setup(hass)
    _lights_on(hass)
    _play(hass)
    await hass.async_block_till_done()
    light_calls.clear()

    switch = _entity_id(hass, entry, "switch", "ambilight")
    await hass.services.async_call("switch", "turn_off", {"entity_id": switch}, blocking=True)
    await hass.async_block_till_done()
    assert not light_calls


async def test_playback_stopping_applies_default(hass: HomeAssistant, images, light_calls) -> None:
    await _setup(hass, **{CONF_DEFAULT_COLOR: [10, 20, 30]})
    _lights_on(hass)
    _play(hass)
    await hass.async_block_till_done()
    light_calls.clear()

    _play(hass, state="idle")
    await hass.async_block_till_done()
    assert [c.data["rgb_color"] for c in light_calls] == [[10, 20, 30]]

    # No repeat on further idle updates
    light_calls.clear()
    hass.states.async_set(PLAYER, "off")
    await hass.async_block_till_done()
    assert not light_calls


async def test_mode_change_applies_immediately(hass: HomeAssistant, images, light_calls) -> None:
    entry = await _setup(hass)
    _lights_on(hass)
    _play(hass)
    await hass.async_block_till_done()
    vibrant = light_calls[-1].data["rgb_color"]

    await hass.services.async_call(
        "select",
        "select_option",
        {"entity_id": _entity_id(hass, entry, "select", "mode"), "option": "pastel"},
        blocking=True,
    )
    await hass.async_block_till_done()
    pastel = light_calls[-1].data["rgb_color"]
    assert pastel != vibrant
    assert colorsys.rgb_to_hsv(*(c / 255 for c in pastel))[1] < 0.5


async def test_slider_change_applies_immediately(hass: HomeAssistant, images, light_calls) -> None:
    entry = await _setup(hass)
    _lights_on(hass)
    _play(hass)
    await hass.async_block_till_done()
    before = light_calls[-1].data["rgb_color"]

    await hass.services.async_call(
        "number",
        "set_value",
        {"entity_id": _entity_id(hass, entry, "number", "brightness_min"), "value": 100},
        blocking=True,
    )
    await hass.async_block_till_done()
    after = light_calls[-1].data["rgb_color"]
    assert max(after) > max(before)


async def test_apply_service_with_override(hass: HomeAssistant, images, light_calls) -> None:
    await _setup(hass)
    _lights_on(hass)
    _play(hass)
    await hass.async_block_till_done()
    light_calls.clear()

    hass.states.async_set("light.other", "on")
    await hass.services.async_call(DOMAIN, "apply", {"entity_id": ["light.other"]}, blocking=True)
    await hass.async_block_till_done()
    assert len(light_calls) == 1
    assert light_calls[0].data["entity_id"] == ["light.other"]


async def test_apply_service_unknown_entry(hass: HomeAssistant, images, light_calls) -> None:
    from homeassistant.exceptions import ServiceValidationError
    import pytest

    await _setup(hass)
    with pytest.raises(ServiceValidationError):
        await hass.services.async_call(DOMAIN, "apply", {"config_entry_id": "nope"}, blocking=True)


async def test_failed_download_is_not_retried_for_the_same_picture(
    hass: HomeAssistant, light_calls
) -> None:
    from unittest.mock import patch

    calls = 0

    async def failing_fetch(self, picture):
        nonlocal calls
        calls += 1
        return None

    with patch(
        "custom_components.ambilight_spotify.manager.AmbilightManager._async_fetch_image",
        failing_fetch,
    ):
        entry = await _setup(hass)
        _lights_on(hass)
        _play(hass)
        await hass.async_block_till_done()
        # A different state change with the same artwork must not retry.
        _play(hass, state="paused")
        await hass.async_block_till_done()

    assert calls == 1
    assert not light_calls
    assert hass.states.get(_entity_id(hass, entry, "sensor", "accent_color")).state == "unknown"


async def test_settings_survive_reload(hass: HomeAssistant, images, light_calls) -> None:
    entry = await _setup(hass)
    mode = _entity_id(hass, entry, "select", "mode")
    switch = _entity_id(hass, entry, "switch", "ambilight")
    await hass.services.async_call(
        "select", "select_option", {"entity_id": mode, "option": "intense"}, blocking=True
    )
    await hass.services.async_call("switch", "turn_off", {"entity_id": switch}, blocking=True)

    assert await hass.config_entries.async_reload(entry.entry_id)
    await hass.async_block_till_done()

    assert hass.states.get(mode).state == "intense"
    assert hass.states.get(switch).state == "off"
