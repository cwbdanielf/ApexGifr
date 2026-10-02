"""GIF animation generator for SteelSeries Apex OLED displays."""

from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import BinaryIO, Iterable, List

from PIL import Image

from .kaypro2_font import ConvertedText, Kaypro2Font


@dataclass
class AnimationSettings:
    """Configuration values for GIF generation."""

    frame_duration_ms: int = 100
    width: int = 128
    height: int = 40
    columns: int = 21
    line_height: int = 10


class AnimationGenerator:
    """Generate scrolling Kaypro II text animations."""

    def __init__(self, settings: AnimationSettings | None = None) -> None:
        self.settings = settings or AnimationSettings()

    def _create_frame(self) -> Image.Image:
        frame = Image.new("P", (self.settings.width, self.settings.height), color=0)
        frame.putpalette([0, 0, 0, 255, 255, 255] + [0, 0, 0] * 254)
        return frame

    def _iter_offsets(self, text: ConvertedText) -> Iterable[int]:
        total_steps = text.length * self.settings.line_height
        for offset in range(0, -total_steps, -1):
            yield offset

    def _full_length(self, text: ConvertedText) -> int:
        return max(text.length * 2, 8)

    def render_frames(self, text: ConvertedText) -> List[Image.Image]:
        """Render every frame required for the animation."""

        if text.length <= 0:
            raise ValueError("Converted text must contain at least one line.")

        frames: List[Image.Image] = []
        full_length = self._full_length(text)
        width = self.settings.width
        height = self.settings.height

        for y_offset in self._iter_offsets(text):
            frame = self._create_frame()
            pixels = frame.load()

            for column in range(self.settings.columns):
                if column >= len(text.data):
                    break

                column_values = text.column(column)
                for line_index in range(full_length):
                    char_code = column_values[line_index % text.length]
                    x = column * 6 + 1
                    y = line_index * self.settings.line_height + y_offset
                    Kaypro2Font.draw_character(
                        pixels,
                        width,
                        height,
                        char_code,
                        x,
                        y,
                        color=1,
                    )

            frames.append(frame)

        return frames

    def _save_gif(self, frames: List[Image.Image], output: BinaryIO) -> None:
        if not frames:
            raise ValueError("No frames to save.")

        frames[0].save(
            output,
            format="GIF",
            save_all=True,
            append_images=frames[1:],
            loop=0,
            duration=self.settings.frame_duration_ms,
            disposal=2,
        )

    def save_gif(self, frames: List[Image.Image], output_path: Path) -> None:
        """Persist the provided frames as a looping GIF animation."""

        if not frames:
            raise ValueError("No frames to save.")

        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with output_path.open("wb") as output:
            self._save_gif(frames, output)

    def generate_bytes(self, text: ConvertedText) -> bytes:
        """Render the text animation as GIF bytes."""

        with BytesIO() as output:
            self._save_gif(self.render_frames(text), output)
            return output.getvalue()

    def generate(self, text: ConvertedText, output_path: Path) -> Path:
        """Generate and store an animation for the provided text."""

        frames = self.render_frames(text)
        self.save_gif(frames, output_path)
        return Path(output_path)
