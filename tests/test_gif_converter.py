from io import BytesIO

import pytest
from PIL import Image, ImageDraw

from apexgifr.gif_converter import (
    GifConversionError,
    GifConversionSettings,
    convert_gif,
    inspect_gif,
)


def make_gif(frames, durations=None, loop=0, **save_options):
    output = BytesIO()
    frames[0].save(
        output,
        format="GIF",
        save_all=True,
        append_images=frames[1:],
        duration=durations or [50] * len(frames),
        loop=loop,
        optimize=False,
        **save_options,
    )
    return output.getvalue()


def open_frames(data):
    image = Image.open(BytesIO(data))
    frames = []
    durations = []
    for index in range(image.n_frames):
        image.seek(index)
        frames.append(image.convert("RGB").copy())
        durations.append(image.info.get("duration"))
    metadata = image.info.copy()
    image.close()
    return frames, durations, metadata


def test_fish_gif_metadata_and_conversion():
    with open("fish.gif", "rb") as source_file:
        source = source_file.read()
    metadata = inspect_gif(source)

    result = convert_gif(source, GifConversionSettings(threshold=32))
    frames, durations, output_metadata = open_frames(result)

    assert (metadata.width, metadata.height, metadata.frame_count) == (144, 144, 151)
    assert metadata.duration_ms == 5030
    # Pillow coalesces adjacent identical output frames, retaining their total timing.
    assert 1 < len(frames) <= metadata.frame_count
    assert sum(durations) == metadata.duration_ms
    assert all(frame.size == (128, 40) for frame in frames)
    assert set(value for frame in frames for value in frame.get_flattened_data()) <= {
        (0, 0, 0),
        (255, 255, 255),
    }
    assert output_metadata["loop"] == 0
    assert output_metadata.get("transparency") is None


def test_convert_outputs_binary_frames_with_individual_timing_and_loop():
    first = Image.new("RGB", (32, 16), "black")
    second = Image.new("RGB", (32, 16), "white")
    source = make_gif([first, second], durations=[30, 80], loop=2)

    result = convert_gif(source, GifConversionSettings(fit="contain", threshold=128))
    frames, durations, metadata = open_frames(result)

    assert len(frames) == 2
    assert [frame.getpixel((64, 20)) for frame in frames] == [(0, 0, 0), (255, 255, 255)]
    assert durations == [30, 80]
    assert metadata["loop"] == 0


def test_transparent_pixels_compose_over_black():
    palette = [0, 0, 0, 255, 255, 255] + [0, 0, 0] * 254
    first = Image.new("P", (16, 16), 1)
    first.putpalette(palette)
    second = Image.new("P", (16, 16), 0)
    second.putpalette(palette)
    ImageDraw.Draw(second).rectangle((4, 4, 11, 11), fill=1)
    source = make_gif(
        [first, second],
        durations=[50, 50],
        transparency=0,
        disposal=2,
    )

    frames, _, _ = open_frames(convert_gif(source, GifConversionSettings(threshold=64)))

    assert len(frames) == 2
    assert frames[0].getpixel((64, 20)) == (255, 255, 255)
    assert frames[1].getpixel((10, 20)) == (0, 0, 0)
    assert frames[1].getpixel((64, 20)) == (255, 255, 255)


def test_position_controls_shift_the_crop():
    image = Image.new("L", (128, 128), 0)
    ImageDraw.Draw(image).rectangle((0, 0, 127, 29), fill=255)
    source = make_gif([image], durations=[50])

    top_frames, _, _ = open_frames(
        convert_gif(source, GifConversionSettings(threshold=100, position_y=-100))
    )
    bottom_frames, _, _ = open_frames(
        convert_gif(source, GifConversionSettings(threshold=100, position_y=100))
    )

    assert top_frames[0].getpixel((64, 10)) == (255, 255, 255)
    assert bottom_frames[0].getpixel((64, 10)) == (0, 0, 0)


def test_threshold_invert_and_speed_controls():
    image = Image.new("L", (128, 40), 96)
    source = make_gif([image], durations=[100])

    dark = convert_gif(source, GifConversionSettings(threshold=64, speed=2))
    light = convert_gif(source, GifConversionSettings(threshold=64, invert=True, speed=2))
    dark_frames, dark_durations, _ = open_frames(dark)
    light_frames, light_durations, _ = open_frames(light)

    assert dark_frames[0].getpixel((64, 20)) == (255, 255, 255)
    assert light_frames[0].getpixel((64, 20)) == (0, 0, 0)
    assert dark_durations == [50]
    assert light_durations == [50]


def test_fit_contain_pads_with_black():
    image = Image.new("L", (128, 32), 255)
    source = make_gif([image])

    frames, _, _ = open_frames(convert_gif(source, GifConversionSettings(fit="contain")))

    assert frames[0].getpixel((64, 0)) == (0, 0, 0)
    assert frames[0].getpixel((64, 20)) == (255, 255, 255)


@pytest.mark.parametrize(
    "settings",
    [
        {"fit": "stretch"},
        {"zoom": 5},
        {"position_x": 101},
        {"threshold": 256},
        {"invert": "yes"},
        {"speed": 0},
    ],
)
def test_reject_invalid_settings(settings):
    with pytest.raises(GifConversionError):
        GifConversionSettings.from_mapping(settings)


def test_reject_non_gif_and_invalid_input():
    with pytest.raises(GifConversionError, match="corrompido"):
        inspect_gif(b"not an image")

    png = BytesIO()
    Image.new("RGB", (4, 4)).save(png, format="PNG")
    with pytest.raises(GifConversionError, match="não é um GIF"):
        convert_gif(png.getvalue())


def test_reject_more_than_frame_limit():
    frames = [
        Image.new("RGB", (1, 1), "white" if index % 2 else "black")
        for index in range(301)
    ]
    source = make_gif(frames, durations=[10] * len(frames))

    with pytest.raises(GifConversionError, match="300 quadros"):
        inspect_gif(source)


def test_dither_produces_only_binary_palette():
    image = Image.new("L", (128, 40))
    for x in range(128):
        for y in range(40):
            image.putpixel((x, y), (x + y) % 256)
    result = convert_gif(make_gif([image]), GifConversionSettings(dither=True))
    frames, _, _ = open_frames(result)
    assert set(frames[0].get_flattened_data()) <= {(0, 0, 0), (255, 255, 255)}
