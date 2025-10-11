from pathlib import Path

import pytest

from apexgifr.kaypro2_font import Kaypro2Font


def test_convert_text_basic():
    converted = Kaypro2Font.convert_text("AB\nCD")
    assert converted.length == 2
    assert converted.data[0][0] == ord("A")
    assert converted.data[1][0] == ord("B")
    assert converted.data[0][1] == ord("C")
    assert converted.data[1][1] == ord("D")


def test_convert_text_escape_sequence():
    converted = Kaypro2Font.convert_text("\\065")
    assert converted.length == 1
    assert converted.data[0][0] == ord("A")


def test_convert_text_invalid_escape():
    with pytest.raises(ValueError):
        Kaypro2Font.convert_text("\\0A5")


def test_font_bitmap_completeness():
    bits = Kaypro2Font.BITS
    assert len(bits) == 128 * 8
    # Spot-check well-known glyphs to ensure the bitmap table remains intact.
    start_a = ord("A") * 8
    assert bits[start_a : start_a + 8] == [
        0x04,
        0x0A,
        0x11,
        0x11,
        0x1F,
        0x11,
        0x11,
        0x00,
    ]

    start_zero = ord("0") * 8
    assert bits[start_zero : start_zero + 8] == [
        0x0E,
        0x11,
        0x13,
        0x15,
        0x19,
        0x11,
        0x0E,
        0x00,
    ]


@pytest.mark.parametrize("code", [-5, 0, 200])
def test_draw_character_handles_invalid_codes(code, tmp_path):
    from PIL import Image

    img = Image.new("P", (10, 10), color=0)
    img.putpalette([0, 0, 0, 255, 255, 255] + [0, 0, 0] * 254)
    pixels = img.load()

    Kaypro2Font.draw_character(pixels, 10, 10, code, 0, 0)

    assert img.getpixel((0, 0)) in {0, 1}
