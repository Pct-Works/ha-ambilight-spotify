"""Tests for the pure colour logic."""

from __future__ import annotations

import colorsys
import io

from PIL import Image
import pytest

from custom_components.ambilight_spotify.color import (
    apply_mode,
    compute_accent_color,
    extract_candidates,
    pick_best_candidate,
    rgb_to_hex,
)
from custom_components.ambilight_spotify.const import (
    HARD_MIN_VALUE,
    MODE_FAITHFUL,
    MODE_INTENSE,
    MODE_PASTEL,
    MODE_VIBRANT,
    MODES,
)


def _png(color: tuple[int, int, int], size: int = 64) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (size, size), color).save(buf, format="PNG")
    return buf.getvalue()


def _hsv(rgb: tuple[int, int, int]) -> tuple[float, float, float]:
    return colorsys.rgb_to_hsv(*(c / 255 for c in rgb))


def test_extract_candidates_solid_image() -> None:
    candidates = extract_candidates(_png((200, 30, 30)))
    assert candidates
    (_, rgb) = max(candidates)
    assert rgb[0] > 180 and rgb[1] < 60 and rgb[2] < 60


def test_extract_candidates_handles_rgba_and_palette_images() -> None:
    buf = io.BytesIO()
    Image.new("RGBA", (32, 32), (10, 200, 10, 128)).save(buf, format="PNG")
    assert extract_candidates(buf.getvalue())

    buf = io.BytesIO()
    Image.new("P", (32, 32), 3).save(buf, format="PNG")
    assert extract_candidates(buf.getvalue()) is not None


def test_pick_prefers_saturated_over_frequent_grey() -> None:
    # A big grey area and a smaller strong blue: blue should win.
    candidates = [(900, (128, 128, 128)), (100, (20, 40, 220))]
    h, s, v = pick_best_candidate(candidates, 0.30)
    assert s > 0.8
    assert 0.55 < h < 0.70  # blue


def test_pick_falls_back_to_most_frequent_when_nothing_qualifies() -> None:
    candidates = [(500, (10, 10, 10)), (50, (240, 240, 240))]
    h, s, v = pick_best_candidate(candidates, 0.30)
    assert v == pytest.approx(10 / 255)


def test_pick_skips_near_white_candidates() -> None:
    candidates = [(100, (255, 250, 250)), (10, (200, 40, 40))]
    h, s, v = pick_best_candidate(candidates, 0.0)
    assert v < 0.97


def test_pick_empty_candidates() -> None:
    assert pick_best_candidate([], 0.3) == (0.0, 0.0, 0.3)


@pytest.mark.parametrize("mode", MODES)
def test_every_mode_respects_hard_floor_and_brightness_min(mode: str) -> None:
    dark = (0.6, 0.9, 0.02)
    _, _, v = apply_mode(mode, dark, 0.0)
    assert v >= HARD_MIN_VALUE


def test_vibrant_enforces_minimum_brightness_and_saturation() -> None:
    h, s, v = apply_mode(MODE_VIBRANT, (0.1, 0.3, 0.2), 0.75)
    assert v == pytest.approx(0.75)
    assert s == pytest.approx(0.70)


def test_pastel_is_light_and_soft() -> None:
    h, s, v = apply_mode(MODE_PASTEL, (0.1, 0.95, 0.5), 0.2)
    assert v >= 0.80
    assert 0.18 <= s <= 0.45


def test_faithful_keeps_saturation() -> None:
    h, s, v = apply_mode(MODE_FAITHFUL, (0.1, 0.5, 0.9), 0.75)
    assert s == pytest.approx(0.5)
    assert v == pytest.approx(0.9)


def test_intense_is_saturated_and_bounded() -> None:
    h, s, v = apply_mode(MODE_INTENSE, (0.1, 0.2, 0.99), 1.0)
    assert s >= 0.75
    assert 0.55 <= v <= 0.90


@pytest.mark.parametrize("mode", [MODE_VIBRANT, MODE_PASTEL, MODE_INTENSE])
def test_grayscale_artwork_does_not_invent_a_hue(mode: str) -> None:
    h, s, v = apply_mode(mode, (0.0, 0.02, 0.5), 0.75)
    assert s == 0.0


def test_unknown_mode_behaves_like_vibrant() -> None:
    hsv = (0.3, 0.4, 0.3)
    assert apply_mode("nope", hsv, 0.5) == apply_mode(MODE_VIBRANT, hsv, 0.5)


def test_compute_accent_color_end_to_end() -> None:
    candidates = extract_candidates(_png((10, 20, 200)))
    rgb = compute_accent_color(candidates, MODE_VIBRANT, 75, 30)
    h, s, v = _hsv(rgb)
    assert v >= 0.74
    assert s >= 0.69
    assert 0.55 < h < 0.72


def test_rgb_to_hex() -> None:
    assert rgb_to_hex((204, 114, 112)) == "#cc7270"
    assert rgb_to_hex((0, 0, 0)) == "#000000"
