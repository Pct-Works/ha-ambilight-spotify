# Ambilight Spotify

[![HACS Custom](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://hacs.xyz)

Sync your lights with the **accent colour of the album artwork** that is playing on Spotify (or any media player that exposes artwork) in Home Assistant.

*Leer en [español](README.es.md).*

- Works with any `media_player` that has an `entity_picture`: [SpotifyPlus](https://github.com/thlucas1/homeassistantcomponent_spotifyplus), the core Spotify integration, Plex, Music Assistant…
- Four colour modes: **Vibrant**, **Pastel**, **Faithful to artwork** and **Intense / Dramatic**.
- Minimum brightness and minimum saturation sliders; changes apply **instantly** to the song that is playing.
- Never produces a black or dark-grey colour (hard brightness floor).
- Only changes lights that are **already on**, and **never touches their brightness**.
- Optional restrictions: only for certain playback sources (e.g. one Spotify Connect device) and/or only while an entity is on.
- Optional **default colour** restored when the sync stops.
- No YAML, no helpers, no extra integrations: everything is configured from the UI.

## Installation

### HACS (custom repository)

1. HACS → ⋮ → **Custom repositories** → add `https://github.com/Pct-Works/ha-ambilight-spotify` as **Integration**.
2. Install **Ambilight Spotify** and restart Home Assistant.
3. **Settings → Devices & services → Add integration → Ambilight Spotify**.

### Manual

Copy `custom_components/ambilight_spotify` into your `config/custom_components` folder and restart.

## Configuration

**Step 1 — Media player.** The player whose artwork is followed.

**Step 2 — Lights and behaviour** (all editable later with **Configure**):

| Option | Description |
| --- | --- |
| Lights | Lights that receive the colour. |
| Only for these playback sources | Optional. Only sync while the player's `source` attribute matches (case-insensitive). Handy to ignore playback on other devices. |
| Only while this entity is on | Optional. For example `light.all`. |
| Default colour | Optional. Applied to the lights when the sync stops (switch turned off, playback stopped, conditions no longer met). Empty = leave the last colour. |
| Transition | Seconds the lights take to change colour. |

## Entities

Each entry creates one device with:

| Entity | Purpose |
| --- | --- |
| `switch` **Ambilight** | Turns the sync on/off. |
| `select` **Colour mode** | Vibrant / Pastel / Faithful / Intense. |
| `number` **Minimum brightness** | Target brightness of the colour (0–100 %). |
| `number` **Minimum saturation** | Minimum saturation for an artwork colour to be a candidate (0–100 %). |
| `sensor` **Accent colour** | State `#rrggbb`; attributes `rgb_color`, `hs_color`, `mode`. Use it to tint dashboards or drive other devices. |
| `binary_sensor` **Syncing** | On while the lights are being driven (diagnostic). |

## Service `ambilight_spotify.apply`

Re-sends the current colour (or the default colour when the sync is not active) to the lights. Fields are optional:

- `entity_id` — apply to these lights instead of the configured ones.
- `config_entry_id` — limit to one entry.

This is how scene logic stays **outside** the integration. Example: after a scene changes, let only the lights that belong to that scene follow the music:

```yaml
automation:
  - alias: Re-tint indirect lights after a scene change
    triggers:
      - trigger: state
        entity_id: scene.ambient
    actions:
      - action: ambilight_spotify.apply
        data:
          entity_id:
            - light.desk_bar
            - light.wled
```

## How it works

1. Whenever the player's state, source or artwork changes, the artwork is downloaded once and reduced to a 12-colour palette.
2. The best candidate is chosen by saturation × brightness × weight in the image, with a minimum saturation.
3. The hue and saturation are kept and the colour is rebuilt for the selected mode with a minimum brightness.
4. The colour is sent to the lights that are on (`light.turn_on` with `rgb_color` only).

Changing the mode or the sliders reuses the cached palette: no new download.

## Development

```bash
pip install -r requirements_test.txt
pytest
```

## License

MIT
