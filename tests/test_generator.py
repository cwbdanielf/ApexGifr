from pathlib import Path

def build_sample_text(tmp_path: Path) -> Path:
    sample = tmp_path / "sample.txt"
    sample.write_text("Hello\nWorld\nfrom\nApex", encoding="utf-8")
    return sample


def test_render_frames_and_generate(tmp_path):
    from PIL import Image

    from apexgifr.generator import AnimationGenerator
    from apexgifr.kaypro2_font import Kaypro2Font

    input_file = build_sample_text(tmp_path)
    converted = Kaypro2Font.convert_text(input_file.read_text(encoding="utf-8"))

    generator = AnimationGenerator()
    frames = generator.render_frames(converted)

    assert frames, "Expected frames to be generated"
    assert all(frame.size == (128, 40) for frame in frames)

    output_file = tmp_path / "output.gif"
    generator.save_gif(frames, output_file)

    assert output_file.exists()

    with Image.open(output_file) as gif:
        assert gif.size == (128, 40)
        assert gif.n_frames == converted.length * generator.settings.line_height


def test_first_frame_contains_expected_text():
    from apexgifr.generator import AnimationGenerator
    from apexgifr.kaypro2_font import Kaypro2Font

    message = "Vai revisar gif?"
    converted = Kaypro2Font.convert_text(message)
    frames = AnimationGenerator().render_frames(converted)

    frame = frames[0]
    decoded = []
    for column in range(len(message)):
        # Reconstruct the glyph from the frame by sampling the top-most
        # character row and matching it against the font table.
        for code in range(128):
            matches = True
            for dx in range(2, 8):
                for dy in range(8):
                    x = column * 6 + (dx - 2) + 1
                    y = dy
                    if x >= frame.width or y >= frame.height:
                        continue
                    pixel = frame.getpixel((x, y))
                    bit_set = bool(Kaypro2Font.BITS[code * 8 + dy] & (0x80 >> dx))
                    if bool(pixel) != bit_set:
                        matches = False
                        break
                if not matches:
                    break
            if matches:
                decoded.append(chr(code))
                break

    assert "".join(decoded) == message


def test_cli_run(tmp_path):
    from apexgifr.cli import run

    input_file = build_sample_text(tmp_path)
    output_file = tmp_path / "result.gif"

    run(input_file, output_file, frame_duration=80)

    assert output_file.exists()
