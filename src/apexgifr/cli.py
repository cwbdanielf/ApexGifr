"""Command-line interface for the ApexGifr application."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Optional

from .generator import AnimationGenerator
from .kaypro2_font import Kaypro2Font


def parse_args(args: Optional[list[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Generate a scrolling Kaypro II GIF for SteelSeries Apex OLED displays."
        )
    )
    parser.add_argument(
        "input_file",
        type=Path,
        help="Path to the input text file containing the animation script.",
    )
    parser.add_argument(
        "output_file",
        nargs="?",
        type=Path,
        help=(
            "Optional path to the output GIF file. Defaults to replacing the input"
            " extension with .gif"
        ),
    )
    parser.add_argument(
        "--duration",
        type=int,
        default=100,
        help="Frame duration in milliseconds (default: 100).",
    )
    return parser.parse_args(args=args)


def resolve_output_path(input_path: Path, output_path: Optional[Path]) -> Path:
    if output_path is not None:
        return output_path

    if input_path.suffix.lower() != ".txt":
        raise ValueError("The input must be a text file with '.txt' extension.")

    return input_path.with_suffix(".gif")


def run(input_file: Path, output_file: Path, frame_duration: int) -> Path:
    if not input_file.exists():
        raise FileNotFoundError(f"Input file not found: {input_file}")

    text = input_file.read_text(encoding="utf-8")
    converted = Kaypro2Font.convert_text(text)

    generator = AnimationGenerator()
    generator.settings.frame_duration_ms = frame_duration

    return generator.generate(converted, output_file)


def main(args: Optional[list[str]] = None) -> int:
    parsed = parse_args(args)

    try:
        output_path = resolve_output_path(parsed.input_file, parsed.output_file)
        result = run(parsed.input_file, output_path, parsed.duration)
    except (ValueError, FileNotFoundError) as exc:
        print(f"Error: {exc}")
        return 1

    print(f"Animation written to {result}")
    return 0


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    raise SystemExit(main())
