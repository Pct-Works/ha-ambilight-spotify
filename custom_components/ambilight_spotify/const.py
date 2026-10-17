"""Constants for the Ambilight Spotify integration."""

from __future__ import annotations

from typing import Final

DOMAIN: Final = "ambilight_spotify"

# Config entry data / options keys
CONF_MEDIA_PLAYER: Final = "media_player"
CONF_TARGET_LIGHTS: Final = "target_lights"
CONF_SOURCE_FILTER: Final = "source_filter"
CONF_REQUIRE_ENTITY: Final = "require_entity"
CONF_DEFAULT_COLOR: Final = "default_color"
CONF_TRANSITION: Final = "transition"

DEFAULT_TRANSITION: Final = 1.0

# Colour modes (also the translation keys of the mode select)
MODE_VIBRANT: Final = "vibrant"
MODE_PASTEL: Final = "pastel"
MODE_FAITHFUL: Final = "faithful"
MODE_INTENSE: Final = "intense"
MODES: Final = [MODE_VIBRANT, MODE_PASTEL, MODE_FAITHFUL, MODE_INTENSE]

DEFAULT_MODE: Final = MODE_VIBRANT
DEFAULT_BRIGHTNESS_MIN: Final = 75
DEFAULT_SATURATION_MIN: Final = 30

# Number of colours in the palette extracted from the artwork.
PALETTE_SIZE: Final = 12

# Absolute brightness floor (0..1): whatever the user settings are, the final
# colour is never darker than this, so a black/near-black colour never shows.
HARD_MIN_VALUE: Final = 0.12

# Media player states in which there is nothing to sync with.
INACTIVE_PLAYER_STATES: Final = frozenset(
    {"off", "idle", "standby", "unavailable", "unknown"}
)

# Services
SERVICE_APPLY: Final = "apply"
ATTR_CONFIG_ENTRY_ID: Final = "config_entry_id"
