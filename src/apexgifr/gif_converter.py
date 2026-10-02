"""Convert animated GIFs to the Apex OLED's monochrome format."""

from __future__ import annotations

import math
import warnings
from dataclasses import dataclass
from io import BytesIO

from PIL import Image, ImageOps, UnidentifiedImageError

OUTPUT_SIZE = (128, 40)
MAX_UPLOAD_BYTES = 20 * 1024 * 1024
MAX_FRAMES = 300
MAX_SOURCE_SIDE = 2048
MAX_TOTAL_PIXELS = 20_000_000
DEFAULT_FRAME_DURATION_MS = 100


class GifConversionError(ValueError):
    """Raised when an uploaded GIF or conversion setting is unsupported."""


@dataclass(frozen=True)
class GifMetadata:
    width: int
    height: int
    frame_count: int
    duration_ms: int
    loop: int | None
    durations: list[int]


@dataclass(frozen=True)
class GifConversionSettings:
    fit: str = "cover"
    zoom: float = 1.0
    position_x: int = 0
    position_y: int = 0
    threshold: int = 64
    invert: bool = False
    dither: bool = False
    speed: float = 1.0

    @classmethod
    def from_mapping(cls, values: dict) -> "GifConversionSettings":
        fit = values.get("fit", "cover")
        zoom = values.get("zoom", 1.0)
        position_x = values.get("position_x", 0)
        position_y = values.get("position_y", 0)
        threshold = values.get("threshold", 64)
        invert = values.get("invert", False)
        dither = values.get("dither", False)
        speed = values.get("speed", 1.0)

        if not isinstance(fit, str) or fit not in {"cover", "contain"}:
            raise GifConversionError("O ajuste deve ser 'cover' ou 'contain'.")
        for name, value, minimum, maximum, label in (
            ("zoom", zoom, 0.5, 3, "O zoom"),
            ("speed", speed, 0.25, 4, "A velocidade"),
        ):
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise GifConversionError(f"{label} deve ser numérica.")
            if not math.isfinite(value) or not minimum <= value <= maximum:
                raise GifConversionError(f"{label} deve ficar entre {minimum} e {maximum}.")
        for value in (position_x, position_y):
            if isinstance(value, bool) or not isinstance(value, int) or not -100 <= value <= 100:
                raise GifConversionError("A posição deve ficar entre -100 e 100.")
        if isinstance(threshold, bool) or not isinstance(threshold, int) or not 0 <= threshold <= 255:
            raise GifConversionError("O limiar de brilho deve ficar entre 0 e 255.")
        if not isinstance(invert, bool) or not isinstance(dither, bool):
            raise GifConversionError("As opções inverter e dithering devem ser booleanas.")

        return cls(
            fit=fit,
            zoom=float(zoom),
            position_x=position_x,
            position_y=position_y,
            threshold=threshold,
            invert=invert,
            dither=dither,
            speed=float(speed),
        )


def _open_gif(data: bytes) -> Image.Image:
    if not data:
        raise GifConversionError("Selecione um arquivo GIF válido.")
    if len(data) > MAX_UPLOAD_BYTES:
        raise GifConversionError("O GIF deve ter no máximo 20 MB.")

    try:
        image = Image.open(BytesIO(data))
    except (OSError, UnidentifiedImageError, Image.DecompressionBombError) as exc:
        raise GifConversionError("Não foi possível abrir o GIF. Verifique se o arquivo não está corrompido.") from exc

    if image.format != "GIF":
        image.close()
        raise GifConversionError("O arquivo enviado não é um GIF válido.")

    width, height = image.size
    if width <= 0 or height <= 0 or width > MAX_SOURCE_SIDE or height > MAX_SOURCE_SIDE:
        image.close()
        raise GifConversionError("Cada lado do GIF deve ter no máximo 2048 pixels.")
    try:
        frame_count = image.n_frames
    except (OSError, ValueError) as exc:
        image.close()
        raise GifConversionError("O GIF está corrompido ou não pode ser decodificado.") from exc
    if frame_count > MAX_FRAMES:
        image.close()
        raise GifConversionError(f"O GIF pode ter no máximo {MAX_FRAMES} quadros.")
    if width * height * frame_count > MAX_TOTAL_PIXELS:
        image.close()
        raise GifConversionError("A animação excede o limite total de pixels para processamento.")
    return image


def _safe_open_gif(data: bytes) -> Image.Image:
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            return _open_gif(data)
    except Image.DecompressionBombWarning as exc:
        raise GifConversionError("As dimensões do GIF são grandes demais para processar com segurança.") from exc
    except Image.DecompressionBombError as exc:
        raise GifConversionError("As dimensões do GIF são grandes demais para processar com segurança.") from exc


def inspect_gif(data: bytes) -> GifMetadata:
    """Validate an input GIF and return basic animation metadata."""

    image = _safe_open_gif(data)
    try:
        durations = []
        for index in range(image.n_frames):
            image.seek(index)
            duration = image.info.get("duration", DEFAULT_FRAME_DURATION_MS) or 0
            durations.append(max(10, int(duration)))
        return GifMetadata(
            width=image.width,
            height=image.height,
            frame_count=image.n_frames,
            duration_ms=sum(durations),
            loop=image.info.get("loop"),
            durations=durations,
        )
    except (OSError, ValueError, Image.DecompressionBombError) as exc:
        raise GifConversionError("O GIF está corrompido ou não pode ser decodificado.") from exc
    finally:
        image.close()


def _position_offset(source_size: int, target_size: int, position: int) -> int:
    difference = source_size - target_size
    if difference >= 0:
        return -round(difference * (position + 100) / 200)
    return round(-difference * (position + 100) / 200)


def _transform_frame(frame: Image.Image, settings: GifConversionSettings) -> Image.Image:
    width, height = frame.size
    target_width, target_height = OUTPUT_SIZE
    if settings.fit == "cover":
        scale = max(target_width / width, target_height / height)
    else:
        scale = min(target_width / width, target_height / height)
    scale *= settings.zoom
    resized_size = (max(1, round(width * scale)), max(1, round(height * scale)))
    resized = frame.resize(resized_size, Image.Resampling.LANCZOS)

    canvas = Image.new("L", OUTPUT_SIZE, 0)
    offset = (
        _position_offset(resized.width, target_width, settings.position_x),
        _position_offset(resized.height, target_height, settings.position_y),
    )
    canvas.paste(resized, offset)
    return canvas


def _monochrome_frame(gray: Image.Image, settings: GifConversionSettings) -> Image.Image:
    if settings.dither:
        adjusted = gray.point(lambda value: max(0, min(255, value - settings.threshold + 128)))
        binary = adjusted.convert("1", dither=Image.Dither.FLOYDSTEINBERG)
    else:
        binary = gray.point(lambda value: 255 if value >= settings.threshold else 0).convert(
            "1", dither=Image.Dither.NONE
        )

    if settings.invert:
        binary = ImageOps.invert(binary.convert("L")).convert("1", dither=Image.Dither.NONE)

    pixels = binary.convert("L").point(lambda value: 1 if value else 0)
    palette_frame = Image.frombytes("P", OUTPUT_SIZE, pixels.tobytes())
    palette_frame.putpalette([0, 0, 0, 255, 255, 255] + [0, 0, 0] * 254)
    return palette_frame


def _scale_durations(source_durations: list[int], speed: float) -> list[int]:
    result = []
    elapsed = 0.0
    previous_target = 0
    for duration in source_durations:
        elapsed += max(10, duration) / speed
        target = round(elapsed / 10) * 10
        result.append(max(10, min(655_350, target - previous_target)))
        previous_target = target
    return result


def convert_gif(data: bytes, settings: GifConversionSettings | None = None) -> bytes:
    """Convert composited frames to a 128×40 infinite-loop monochrome GIF."""

    settings = settings or GifConversionSettings()
    frames: list[Image.Image] = []
    source_durations: list[int] = []

    image = _safe_open_gif(data)
    try:
        for index in range(image.n_frames):
            image.seek(index)
            duration = image.info.get("duration", DEFAULT_FRAME_DURATION_MS)
            rgba = image.convert("RGBA")
            background = Image.new("RGBA", rgba.size, (0, 0, 0, 255))
            background.alpha_composite(rgba)
            gray = background.convert("RGB").convert("L")
            transformed = _transform_frame(gray, settings)
            frames.append(_monochrome_frame(transformed, settings))
            try:
                source_durations.append(int(duration) if duration is not None else DEFAULT_FRAME_DURATION_MS)
            except (TypeError, ValueError):
                source_durations.append(DEFAULT_FRAME_DURATION_MS)
    except GifConversionError:
        raise
    except (OSError, ValueError, Image.DecompressionBombError) as exc:
        raise GifConversionError("O GIF está corrompido ou não pode ser decodificado.") from exc
    finally:
        image.close()

    if not frames:
        raise GifConversionError("O GIF não contém quadros para converter.")
    durations = _scale_durations(source_durations, settings.speed)

    with BytesIO() as output:
        frames[0].save(
            output,
            format="GIF",
            save_all=True,
            append_images=frames[1:],
            loop=0,
            duration=durations,
            disposal=2,
            optimize=False,
        )
        return output.getvalue()
