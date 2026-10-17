"""Config flow for Ambilight Spotify."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.core import callback
from homeassistant.helpers.selector import (
    ColorRGBSelector,
    EntitySelector,
    EntitySelectorConfig,
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
)

from .const import (
    CONF_DEFAULT_COLOR,
    CONF_MEDIA_PLAYER,
    CONF_REQUIRE_ENTITY,
    CONF_SOURCE_FILTER,
    CONF_TARGET_LIGHTS,
    CONF_TRANSITION,
    DEFAULT_TRANSITION,
    DOMAIN,
)


def _options_schema(source_list: list[str]) -> vol.Schema:
    """Schema of the per-user settings (shared by setup and the options flow)."""
    return vol.Schema(
        {
            vol.Required(CONF_TARGET_LIGHTS): EntitySelector(
                EntitySelectorConfig(domain="light", multiple=True)
            ),
            vol.Optional(CONF_SOURCE_FILTER): SelectSelector(
                SelectSelectorConfig(
                    options=source_list,
                    multiple=True,
                    custom_value=True,
                    mode=SelectSelectorMode.DROPDOWN,
                )
            ),
            vol.Optional(CONF_REQUIRE_ENTITY): EntitySelector(EntitySelectorConfig()),
            vol.Optional(CONF_DEFAULT_COLOR): ColorRGBSelector(),
            vol.Optional(CONF_TRANSITION, default=DEFAULT_TRANSITION): NumberSelector(
                NumberSelectorConfig(
                    min=0,
                    max=10,
                    step=0.5,
                    unit_of_measurement="s",
                    mode=NumberSelectorMode.SLIDER,
                )
            ),
        }
    )


class AmbilightConfigFlow(ConfigFlow, domain=DOMAIN):
    """Set up the integration: pick a media player, then the lights."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialise the flow."""
        self._media_player: str | None = None

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> AmbilightOptionsFlow:
        """Return the options flow."""
        return AmbilightOptionsFlow()

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Choose the media player to follow."""
        if user_input is not None:
            self._media_player = user_input[CONF_MEDIA_PLAYER]
            await self.async_set_unique_id(self._media_player)
            self._abort_if_unique_id_configured()
            return await self.async_step_lights()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_MEDIA_PLAYER): EntitySelector(
                        EntitySelectorConfig(domain="media_player")
                    )
                }
            ),
        )

    async def async_step_lights(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Choose the lights and the optional behaviour."""
        assert self._media_player is not None
        errors: dict[str, str] = {}

        if user_input is not None:
            if not user_input.get(CONF_TARGET_LIGHTS):
                errors[CONF_TARGET_LIGHTS] = "no_lights"
            else:
                state = self.hass.states.get(self._media_player)
                title = state.name if state else self._media_player
                return self.async_create_entry(
                    title=title,
                    data={CONF_MEDIA_PLAYER: self._media_player},
                    options=user_input,
                )

        return self.async_show_form(
            step_id="lights",
            data_schema=self.add_suggested_values_to_schema(
                _options_schema(_source_list(self.hass, self._media_player)),
                user_input,
            ),
            errors=errors,
        )


class AmbilightOptionsFlow(OptionsFlow):
    """Edit the settings of an existing entry."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Edit lights and behaviour."""
        errors: dict[str, str] = {}

        if user_input is not None:
            if not user_input.get(CONF_TARGET_LIGHTS):
                errors[CONF_TARGET_LIGHTS] = "no_lights"
            else:
                return self.async_create_entry(data=user_input)

        schema = _options_schema(
            _source_list(self.hass, self.config_entry.data[CONF_MEDIA_PLAYER])
        )
        return self.async_show_form(
            step_id="init",
            data_schema=self.add_suggested_values_to_schema(
                schema, user_input or self.config_entry.options
            ),
            errors=errors,
        )


def _source_list(hass: Any, media_player: str) -> list[str]:
    """Sources the player currently advertises, as dropdown suggestions."""
    state = hass.states.get(media_player)
    sources = state.attributes.get("source_list") if state else None
    return [str(source) for source in sources] if sources else []
