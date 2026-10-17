"""Tests for the config and options flows."""

from __future__ import annotations

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from custom_components.ambilight_spotify.const import (
    CONF_DEFAULT_COLOR,
    CONF_MEDIA_PLAYER,
    CONF_SOURCE_FILTER,
    CONF_TARGET_LIGHTS,
    DOMAIN,
)

from .conftest import LIGHT_A, LIGHT_B, PLAYER, make_entry


async def test_full_flow(hass: HomeAssistant) -> None:
    """Player, then lights and options -> entry created."""
    hass.states.async_set(PLAYER, "idle", {"friendly_name": "Spotify", "source_list": ["PC", "Phone"]})

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_MEDIA_PLAYER: PLAYER}
    )
    assert result["step_id"] == "lights"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_TARGET_LIGHTS: [LIGHT_A],
            CONF_SOURCE_FILTER: ["PC"],
            CONF_DEFAULT_COLOR: [127, 172, 255],
        },
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Spotify"
    assert result["data"] == {CONF_MEDIA_PLAYER: PLAYER}
    assert result["options"][CONF_TARGET_LIGHTS] == [LIGHT_A]
    assert result["options"][CONF_SOURCE_FILTER] == ["PC"]
    assert result["options"][CONF_DEFAULT_COLOR] == [127, 172, 255]


async def test_no_lights_is_an_error(hass: HomeAssistant) -> None:
    """At least one light is required."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_MEDIA_PLAYER: PLAYER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_TARGET_LIGHTS: []}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {CONF_TARGET_LIGHTS: "no_lights"}


async def test_same_player_twice_aborts(hass: HomeAssistant) -> None:
    """One entry per media player."""
    make_entry().add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_MEDIA_PLAYER: PLAYER}
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_options_flow(hass: HomeAssistant, images, light_calls) -> None:
    """Options can be edited; clearing an optional field removes it."""
    entry = make_entry(**{CONF_DEFAULT_COLOR: [1, 2, 3]})
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "init"

    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {CONF_TARGET_LIGHTS: [LIGHT_B]}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert entry.options[CONF_TARGET_LIGHTS] == [LIGHT_B]
    assert CONF_DEFAULT_COLOR not in entry.options
