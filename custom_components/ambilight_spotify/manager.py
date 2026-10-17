"""Core logic: follow a media player, extract the accent colour, drive lights."""

from __future__ import annotations

import asyncio
from collections.abc import Callable, Iterable
import logging
from typing import TYPE_CHECKING, Any

import aiohttp

from homeassistant.components.light import (
    ATTR_RGB_COLOR,
    ATTR_TRANSITION,
    DOMAIN as LIGHT_DOMAIN,
)
from homeassistant.const import ATTR_ENTITY_ID, STATE_ON
from homeassistant.core import Event, EventStateChangedData, HomeAssistant, State, callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.helpers.network import NoURLAvailableError, get_url

from .color import compute_accent_color, extract_candidates, rgb_to_hex, Candidates
from .const import (
    CONF_DEFAULT_COLOR,
    CONF_MEDIA_PLAYER,
    CONF_REQUIRE_ENTITY,
    CONF_SOURCE_FILTER,
    CONF_TARGET_LIGHTS,
    CONF_TRANSITION,
    DEFAULT_BRIGHTNESS_MIN,
    DEFAULT_MODE,
    DEFAULT_SATURATION_MIN,
    DEFAULT_TRANSITION,
    DOMAIN,
    INACTIVE_PLAYER_STATES,
    PALETTE_SIZE,
)

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry

_LOGGER = logging.getLogger(__name__)

IMAGE_TIMEOUT = aiohttp.ClientTimeout(total=10)


class AmbilightManager:
    """Keeps one media player and a set of lights in sync."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialise the manager (nothing runs until ``async_start``)."""
        self.hass = hass
        self.entry = entry
        self.signal = f"{DOMAIN}_{entry.entry_id}_update"

        # Runtime settings, owned by the switch / select / number entities
        # (they restore their last value and push it here).
        self.enabled = True
        self.mode = DEFAULT_MODE
        self.brightness_min = float(DEFAULT_BRIGHTNESS_MIN)
        self.saturation_min = float(DEFAULT_SATURATION_MIN)

        # Published state
        self.accent: tuple[int, int, int] | None = None
        self.live = False  # True while the integration is driving the lights

        self._candidates: Candidates | None = None
        self._picture: str | None = None
        self._failed_picture: str | None = None
        self._applied: tuple[int, int, int] | None = None
        self._was_live = False
        self._started = False
        self._refresh_queued = False
        self._force_live_pending = False
        self._lock = asyncio.Lock()
        self._unsubs: list[Callable[[], None]] = []
        self._player_snapshot: tuple[Any, ...] | None = None

    # ------------------------------------------------------------------
    # Configuration helpers
    # ------------------------------------------------------------------
    @property
    def media_player(self) -> str:
        """Entity id of the followed media player."""
        return self.entry.data[CONF_MEDIA_PLAYER]

    @property
    def target_lights(self) -> list[str]:
        """Lights that receive the colour."""
        return list(self.entry.options.get(CONF_TARGET_LIGHTS, []))

    @property
    def source_filter(self) -> list[str]:
        """Playback sources (e.g. Spotify Connect devices) that are allowed."""
        return [s.strip().casefold() for s in self.entry.options.get(CONF_SOURCE_FILTER) or [] if s.strip()]

    @property
    def require_entity(self) -> str | None:
        """Optional entity that must be ``on`` for the sync to run."""
        return self.entry.options.get(CONF_REQUIRE_ENTITY) or None

    @property
    def default_color(self) -> tuple[int, int, int] | None:
        """Colour applied when the sync stops, or ``None`` to leave lights alone."""
        color = self.entry.options.get(CONF_DEFAULT_COLOR)
        if not color:
            return None
        return (int(color[0]), int(color[1]), int(color[2]))

    @property
    def transition(self) -> float:
        """Transition time, in seconds."""
        return float(self.entry.options.get(CONF_TRANSITION, DEFAULT_TRANSITION))

    @property
    def accent_hex(self) -> str | None:
        """Accent colour as ``#rrggbb``."""
        return rgb_to_hex(self.accent) if self.accent else None

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------
    async def async_start(self) -> None:
        """Start listening for changes and run a first evaluation."""
        watched = [self.media_player]
        if self.require_entity:
            watched.append(self.require_entity)

        self._unsubs.append(
            async_track_state_change_event(self.hass, watched, self._handle_watched_event)
        )
        if self.target_lights:
            self._unsubs.append(
                async_track_state_change_event(
                    self.hass, self.target_lights, self._handle_light_event
                )
            )

        self._started = True
        await self.async_refresh()

    @callback
    def async_stop(self) -> None:
        """Stop listening. Lights are left as they are."""
        self._started = False
        for unsub in self._unsubs:
            unsub()
        self._unsubs.clear()

    # ------------------------------------------------------------------
    # Setters used by the entities
    # ------------------------------------------------------------------
    @callback
    def async_update_settings(self, **settings: Any) -> None:
        """Change runtime settings and re-evaluate right away."""
        for key, value in settings.items():
            setattr(self, key, value)
        self._schedule_refresh()

    # ------------------------------------------------------------------
    # Event handling
    # ------------------------------------------------------------------
    @callback
    def _handle_watched_event(self, event: Event[EventStateChangedData]) -> None:
        entity_id = event.data["entity_id"]
        new_state = event.data["new_state"]

        if entity_id == self.media_player:
            # Media players update their position attribute constantly: only
            # react to what matters (state, artwork, source).
            snapshot = (
                new_state.state if new_state else None,
                new_state.attributes.get("entity_picture") if new_state else None,
                new_state.attributes.get("source") if new_state else None,
            )
            if snapshot == self._player_snapshot:
                return
            self._player_snapshot = snapshot
        else:
            old_state = event.data["old_state"]
            if old_state and new_state and old_state.state == new_state.state:
                return

        self._schedule_refresh()

    @callback
    def _handle_light_event(self, event: Event[EventStateChangedData]) -> None:
        """Reapply the live colour when a target light turns on."""
        old_state = event.data["old_state"]
        new_state = event.data["new_state"]
        if (
            new_state is not None
            and new_state.state == STATE_ON
            and (old_state is None or old_state.state != STATE_ON)
        ):
            self._schedule_refresh(force_live=True)

    def _schedule_refresh(self, *, force_live: bool = False) -> None:
        """Queue one refresh; events arriving meanwhile are merged into it.

        A scene turning on several lights at once therefore sends the colour
        once, not once per light.
        """
        if not self._started:
            return
        self._force_live_pending = self._force_live_pending or force_live
        if self._refresh_queued:
            return
        self._refresh_queued = True
        # Not eager: the task must start after the events already queued, or
        # they could not be merged into it.
        self.entry.async_create_task(
            self.hass,
            self._async_run_queued_refresh(),
            f"{DOMAIN} refresh",
            eager_start=False,
        )

    async def _async_run_queued_refresh(self) -> None:
        self._refresh_queued = False
        force_live, self._force_live_pending = self._force_live_pending, False
        await self.async_refresh(force_live=force_live)

    # ------------------------------------------------------------------
    # Evaluation
    # ------------------------------------------------------------------
    async def async_refresh(
        self,
        *,
        force_live: bool = False,
        force_any: bool = False,
        targets: Iterable[str] | None = None,
    ) -> None:
        """Re-evaluate everything and apply the right colour to the lights.

        ``force_live`` re-sends the accent colour even if unchanged (only when
        the sync is live). ``force_any`` also applies the default colour when
        the sync is not live. ``targets`` overrides the configured lights.
        """
        async with self._lock:
            player = self.hass.states.get(self.media_player)
            player_active =player is not None and player.state not in INACTIVE_PLAYER_STATES

            if player_active:
                await self._async_update_palette(player)

            accent = None
            if self._candidates:
                accent = compute_accent_color(
                    self._candidates,
                    self.mode,
                    self.brightness_min,
                    self.saturation_min,
                )
            accent_changed = accent != self.accent
            if accent is not None:
                self.accent = accent

            live = bool(
                self.enabled
                and player_active
                and self.accent is not None
                and self._source_allowed(player)
                and self._required_entity_on()
            )
            live_changed = live != self.live
            self.live = live

            override = list(targets) if targets is not None else None
            if live:
                if force_live or force_any or self.accent != self._applied:
                    await self._async_apply(self.accent, override)
                    self._applied = self.accent
                self._was_live = True
            else:
                default = self.default_color
                if default and (self._was_live or force_any):
                    await self._async_apply(default, override)
                self._was_live = False
                self._applied = None

            if accent_changed or live_changed:
                async_dispatcher_send(self.hass, self.signal)

    def _source_allowed(self, player: State | None) -> bool:
        allowed = self.source_filter
        if not allowed:
            return True
        source = player.attributes.get("source") if player else None
        return isinstance(source, str) and source.strip().casefold() in allowed

    def _required_entity_on(self) -> bool:
        entity_id = self.require_entity
        if not entity_id:
            return True
        state = self.hass.states.get(entity_id)
        return state is not None and state.state == STATE_ON

    # ------------------------------------------------------------------
    # Artwork
    # ------------------------------------------------------------------
    async def _async_update_palette(self, player: State) -> None:
        picture = player.attributes.get("entity_picture")
        if not picture or picture in (self._picture, self._failed_picture):
            return

        data = await self._async_fetch_image(picture)
        if data is None:
            self._failed_picture = picture
            return

        try:
            candidates = await self.hass.async_add_executor_job(
                extract_candidates, data, PALETTE_SIZE
            )
        except Exception as err:  # noqa: BLE001 - Pillow raises many types
            _LOGGER.warning("Could not analyse the artwork of %s: %s", self.media_player, err)
            self._failed_picture = picture
            return

        self._picture = picture
        self._failed_picture = None
        self._candidates = candidates

    async def _async_fetch_image(self, picture: str) -> bytes | None:
        """Download the artwork, preferring the player's own image getter."""
        content = await self._async_fetch_from_entity()
        if content:
            return content

        url = picture
        if picture.startswith("/"):
            try:
                base = get_url(self.hass, prefer_external=False)
            except NoURLAvailableError:
                port = self.hass.config.api.port if self.hass.config.api else 8123
                base = f"http://127.0.0.1:{port}"
            url = base + picture

        try:
            session = async_get_clientsession(self.hass)
            async with session.get(url, timeout=IMAGE_TIMEOUT) as resp:
                resp.raise_for_status()
                return await resp.read()
        except (aiohttp.ClientError, TimeoutError) as err:
            _LOGGER.warning("Could not download the artwork of %s: %s", self.media_player, err)
            return None

    async def _async_fetch_from_entity(self) -> bytes | None:
        """Ask the media player entity for its image (no HTTP round trip)."""
        try:
            from homeassistant.components.media_player import (  # noqa: PLC0415
                DATA_COMPONENT,
            )

            entity = self.hass.data[DATA_COMPONENT].get_entity(self.media_player)
            if entity is None:
                return None
            content, _ = await entity.async_get_media_image()
        except Exception:  # noqa: BLE001 - fall back to the URL
            _LOGGER.debug("Media player image getter unavailable", exc_info=True)
            return None
        return content or None

    # ------------------------------------------------------------------
    # Lights
    # ------------------------------------------------------------------
    async def _async_apply(
        self, rgb: tuple[int, int, int], targets: list[str] | None
    ) -> None:
        """Set the colour on the lights that are currently on.

        Brightness is never touched, and lights that are off stay off.
        """
        lights = targets if targets is not None else self.target_lights
        on_lights = [
            entity_id
            for entity_id in lights
            if (state := self.hass.states.get(entity_id)) and state.state == STATE_ON
        ]
        if not on_lights:
            return

        data: dict[str, Any] = {ATTR_ENTITY_ID: on_lights, ATTR_RGB_COLOR: list(rgb)}
        if self.transition:
            data[ATTR_TRANSITION] = self.transition
        await self.hass.services.async_call(LIGHT_DOMAIN, "turn_on", data, blocking=False)
