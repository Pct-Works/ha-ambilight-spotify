"""Cover-art colour extraction.

Pure functions with no Home Assistant dependency so they can be unit tested.

Algorithm: instead of using the dominant colour of the artwork as-is (which is
often almost black or almost white), pick the most "interesting" palette
entry (saturated, bright and well represented in the image), then rebuild the
final colour from its hue and saturation, forcing a minimum brightness so the
result is always a vivid colour and never a dark grey.
"""

from __future__ import annotations

import colorsys
import io

from .const import (
    HARD_MIN_VALUE,
    MODE_FAITHFUL,
    MODE_INTENSE,
    MODE_PASTEL,
    PALETTE_SIZE,
)

type Candidates = list[tuple[int, tuple[int, int, int]]]
type HSV = tuple[float, float, float]

# Saturation below this is treated as monochrome (white/black/grey artwork):
# we then adjust brightness only instead of inventing a hue.
GRAYSCALE_SATURATION = 0.06
# Palette entries brighter than this are almost white and are skipped.
MAX_CANDIDATE_VALUE = 0.97


def extract_candidates(
    image_bytes: bytes, palette_size: int = PALETTE_SIZE
) -> Candidates:
    """Quantise the image and return ``[(pixel_count, (r, g, b)), ...]``.

    Blocking (Pillow): call it from an executor.
    """
    from PIL import Image  # noqa: PLC0415  (keep the import off the event loop)

    with Image.open(io.BytesIO(image_bytes)) as source:
        img = source.convert("RGB")
    img.thumbnail((120, 120))

    quantized = img.quantize(colors=palette_size, method=Image.Quantize.MEDIANCUT)
    return quantized.convert("RGB").getcolors(maxcolors=palette_size * 4) or []


def _clamp(value: float, lower: float, upper: float) -> float:
    return max(lower, min(upper, value))


def pick_best_candidate(candidates: Candidates, min_saturation: float) -> HSV:
    """Pick the most interesting palette entry as ``(h, s, v)`` in 0..1.

    Score = saturation * brightness weight * pixel count, requiring a minimum
    saturation. If nothing qualifies, fall back to the most frequent colour.
    """
    best: HSV | None = None
    best_score = -1.0
    fallback: HSV | None = None
    fallback_count = -1

    for count, (r, g, b) in candidates:
        h, s, v = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)

        if count > fallback_count:
            fallback_count = count
            fallback = (h, s, v)

        if s < min_saturation or v > MAX_CANDIDATE_VALUE:
            continue

        score = s * (0.4 + 0.6 * v) * count
        if score > best_score:
            best_score = score
            best = (h, s, v)

    return best or fallback or (0.0, 0.0, 0.3)


def apply_mode(mode: str, hsv: HSV, brightness_min: float) -> HSV:
    """Rebuild the final colour for the chosen mode.

    ``brightness_min`` is 0..1. Every mode guarantees ``HARD_MIN_VALUE``.
    """
    h, s, v = hsv
    is_grayscale = s < GRAYSCALE_SATURATION

    if mode == MODE_PASTEL:
        v_final = max(v, max(brightness_min, 0.80))
        s_final = 0.0 if is_grayscale else _clamp(s, 0.18, 0.45)
    elif mode == MODE_FAITHFUL:
        v_final = max(v, brightness_min * 0.6)
        s_final = s
    elif mode == MODE_INTENSE:
        v_final = _clamp(max(v, brightness_min * 0.85), 0.55, 0.90)
        s_final = 0.0 if is_grayscale else max(s, 0.75)
    else:  # MODE_VIBRANT, also the fallback for unknown values
        v_final = max(v, brightness_min)
        s_final = 0.0 if is_grayscale else max(s, 0.70)

    return h, s_final, max(v_final, HARD_MIN_VALUE)


def compute_accent_color(
    candidates: Candidates,
    mode: str,
    brightness_min_pct: float,
    saturation_min_pct: float,
) -> tuple[int, int, int]:
    """Compute the final ``(r, g, b)`` accent colour from the cached palette."""
    hsv = pick_best_candidate(candidates, saturation_min_pct / 100)
    h, s, v = apply_mode(mode, hsv, brightness_min_pct / 100)
    r, g, b = colorsys.hsv_to_rgb(h, s, v)
    return round(r * 255), round(g * 255), round(b * 255)


def rgb_to_hex(rgb: tuple[int, int, int]) -> str:
    """Format an ``(r, g, b)`` tuple as ``#rrggbb``."""
    return "#{:02x}{:02x}{:02x}".format(*rgb)
