"""Local web interface for generating Apex OLED animations."""

from __future__ import annotations

import argparse
import json
from io import BytesIO
from pathlib import Path
from typing import Optional

from flask import Flask, jsonify, render_template, request, send_file

from .generator import AnimationGenerator
from .gif_converter import (
    MAX_UPLOAD_BYTES,
    GifConversionError,
    GifConversionSettings,
    convert_gif,
    inspect_gif,
)
from .kaypro2_font import Kaypro2Font

MAX_TEXT_LENGTH = 4096
MAX_LINES = 100
MAX_COLUMNS = 21
MIN_FRAME_DURATION = 20
MAX_FRAME_DURATION = 1000
MAX_REQUEST_BYTES = MAX_UPLOAD_BYTES + 64 * 1024


def _visible_line_length(line: str) -> int:
    length = 0
    index = 0
    while index < len(line):
        if (
            line[index] == "\\"
            and index + 3 < len(line)
            and line[index + 1 : index + 4].isdigit()
        ):
            index += 4
        else:
            index += 1
        length += 1
    return length


def create_app() -> Flask:
    package_dir = Path(__file__).resolve().parent
    app = Flask(
        __name__,
        template_folder=str(package_dir / "templates"),
        static_folder=str(package_dir / "static"),
    )
    app.config["MAX_CONTENT_LENGTH"] = MAX_REQUEST_BYTES
    app.config["SEND_FILE_MAX_AGE_DEFAULT"] = 0

    @app.get("/")
    def index():
        return render_template("index.html")

    @app.post("/api/generate")
    def generate():
        payload = request.get_json(silent=True)
        if not isinstance(payload, dict):
            return jsonify(error="Envie os dados da animação em formato JSON."), 400

        text = payload.get("text")
        duration = payload.get("duration", 100)
        if not isinstance(text, str) or not text.strip():
            return jsonify(error="Digite o texto que deseja animar."), 400
        if len(text) > MAX_TEXT_LENGTH:
            return jsonify(error=f"O texto deve ter no máximo {MAX_TEXT_LENGTH} caracteres."), 400

        lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
        if len(lines) > MAX_LINES:
            return jsonify(error=f"A animação deve ter no máximo {MAX_LINES} linhas."), 400
        if any(_visible_line_length(line) > MAX_COLUMNS for line in lines):
            return jsonify(
                error=f"Cada linha pode ter no máximo {MAX_COLUMNS} caracteres visíveis."
            ), 400
        if isinstance(duration, bool) or not isinstance(duration, int):
            return jsonify(error="A duração deve ser um número inteiro em milissegundos."), 400
        if not MIN_FRAME_DURATION <= duration <= MAX_FRAME_DURATION:
            return jsonify(
                error=f"A duração deve ficar entre {MIN_FRAME_DURATION} e {MAX_FRAME_DURATION} ms."
            ), 400

        try:
            converted = Kaypro2Font.convert_text(text)
            generator = AnimationGenerator()
            generator.settings.frame_duration_ms = duration
            gif_data = generator.generate_bytes(converted)
        except ValueError as exc:
            return jsonify(error=str(exc)), 400

        return send_file(
            BytesIO(gif_data),
            mimetype="image/gif",
            as_attachment=False,
            download_name="apexgifr.gif",
            max_age=0,
        )

    def read_upload() -> bytes:
        upload = request.files.get("file")
        if upload is None or not upload.filename:
            raise GifConversionError("Escolha um arquivo GIF para continuar.")
        data = upload.stream.read(MAX_UPLOAD_BYTES + 1)
        if len(data) > MAX_UPLOAD_BYTES:
            raise GifConversionError("O GIF deve ter no máximo 20 MB.")
        return data

    @app.post("/api/gif/inspect")
    def inspect_uploaded_gif():
        try:
            metadata = inspect_gif(read_upload())
        except GifConversionError as exc:
            return jsonify(error=str(exc)), 400
        return jsonify(
            width=metadata.width,
            height=metadata.height,
            frames=metadata.frame_count,
            duration_ms=metadata.duration_ms,
            durations=metadata.durations,
            loop=metadata.loop,
        )

    @app.post("/api/gif/convert")
    def convert_uploaded_gif():
        try:
            data = read_upload()
            try:
                payload = json.loads(request.form.get("settings", "{}"))
            except (TypeError, json.JSONDecodeError) as exc:
                raise GifConversionError("As opções de conversão são inválidas.") from exc
            if not isinstance(payload, dict):
                raise GifConversionError("As opções de conversão são inválidas.")
            settings = GifConversionSettings.from_mapping(payload)
            result = convert_gif(data, settings)
        except GifConversionError as exc:
            return jsonify(error=str(exc)), 400
        return send_file(
            BytesIO(result),
            mimetype="image/gif",
            as_attachment=True,
            download_name="apex-oled.gif",
            max_age=0,
        )

    @app.errorhandler(413)
    def too_large(_error):
        return jsonify(error="O arquivo é grande demais para processar (limite de 20 MB)."), 413

    return app


def main(args: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Run the local ApexGifr web interface.")
    parser.add_argument(
        "--host", default="127.0.0.1", help="Host interface (default: 127.0.0.1)."
    )
    parser.add_argument("--port", type=int, default=5000, help="Port to listen on (default: 5000).")
    parser.add_argument(
        "--debug", action="store_true", help="Enable Flask debug mode for development only."
    )
    parsed = parser.parse_args(args)
    create_app().run(host=parsed.host, port=parsed.port, debug=parsed.debug)
    return 0


if __name__ == "__main__":  # pragma: no cover - module entry point
    raise SystemExit(main())
