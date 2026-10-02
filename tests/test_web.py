from io import BytesIO
from pathlib import Path

from PIL import Image

from apexgifr.web import create_app


def test_web_homepage_serves_app():
    client = create_app().test_client()

    response = client.get("/")

    assert response.status_code == 200
    assert b"ApexGifr" in response.data
    assert b'id="animationText"' in response.data

    css = client.get("/static/app.css")
    javascript = client.get("/static/app.js")
    assert css.status_code == 200
    assert b"backdrop-filter" in css.data
    assert javascript.status_code == 200
    assert b"/api/generate" in javascript.data
    gif_javascript = client.get("/static/gif-editor.js")
    editor_css = client.get("/static/gif-editor.css")
    assert gif_javascript.status_code == 200
    assert b"/api/gif/convert" in gif_javascript.data
    assert editor_css.status_code == 200
    assert b".gif-workspace" in editor_css.data


def test_web_generates_previewable_gif():
    client = create_app().test_client()

    response = client.post(
        "/api/generate",
        json={"text": "APEX OLED", "duration": 80},
    )

    assert response.status_code == 200
    assert response.mimetype == "image/gif"
    assert response.headers["Cache-Control"].startswith("no-cache")
    with Image.open(BytesIO(response.data)) as gif:
        assert gif.size == (128, 40)
        assert gif.n_frames == 10
        assert gif.info["duration"] == 80
        assert gif.info["loop"] == 0


def test_web_rejects_invalid_inputs():
    client = create_app().test_client()

    cases = [
        ({"text": "  ", "duration": 100}, "Digite o texto"),
        ({"text": "A" * 22, "duration": 100}, "21 caracteres"),
        ({"text": "A", "duration": 0}, "entre 20 e 1000 ms"),
        ({"text": "\\0A5", "duration": 100}, "Invalid escape code"),
    ]
    for payload, message in cases:
        response = client.post("/api/generate", json=payload)
        assert response.status_code == 400
        assert message in response.json["error"]


def test_gif_inspect_and_convert_endpoints():
    client = create_app().test_client()
    source = Path("fish.gif").read_bytes()

    inspected = client.post(
        "/api/gif/inspect",
        data={"file": (BytesIO(source), "fish.gif")},
        content_type="multipart/form-data",
    )
    converted = client.post(
        "/api/gif/convert",
        data={
            "file": (BytesIO(source), "fish.gif"),
            "settings": '{"threshold":32,"speed":2}',
        },
        content_type="multipart/form-data",
    )

    assert inspected.status_code == 200
    assert inspected.json["frames"] == 151
    assert inspected.json["duration_ms"] == 5030
    assert len(inspected.json["durations"]) == 151
    assert converted.status_code == 200
    assert converted.mimetype == "image/gif"
    assert "attachment" in converted.headers["Content-Disposition"]
    with Image.open(BytesIO(converted.data)) as gif:
        assert gif.size == (128, 40)
        assert gif.n_frames <= 151
        assert gif.info["loop"] == 0
        durations = []
        for index in range(gif.n_frames):
            gif.seek(index)
            durations.append(gif.info["duration"])
        assert sum(durations) == round(5030 / 2 / 10) * 10


def test_gif_endpoints_reject_missing_or_invalid_file():
    client = create_app().test_client()

    missing = client.post("/api/gif/inspect", data={})
    invalid = client.post(
        "/api/gif/convert",
        data={"file": (BytesIO(b"not gif"), "fake.gif"), "settings": "{}"},
        content_type="multipart/form-data",
    )

    assert missing.status_code == 400
    assert "Escolha um arquivo" in missing.json["error"]
    assert invalid.status_code == 400
    assert "corrompido" in invalid.json["error"]


def test_gif_endpoints_reject_invalid_settings():
    client = create_app().test_client()
    source = Path("fish.gif").read_bytes()
    response = client.post(
        "/api/gif/convert",
        data={
            "file": (BytesIO(source), "fish.gif"),
            "settings": '{"zoom":99}',
        },
        content_type="multipart/form-data",
    )

    assert response.status_code == 400
    assert "zoom" in response.json["error"].lower()


def test_web_rejects_malformed_payload_and_too_many_lines():
    client = create_app().test_client()

    malformed = client.post("/api/generate", data="not json", content_type="application/json")
    accepted_lines = client.post(
        "/api/generate",
        json={"text": "\n".join(["A"] * 63), "duration": 100},
    )
    too_many_lines = client.post(
        "/api/generate",
        json={"text": "\n".join(["A"] * 101), "duration": 100},
    )

    assert malformed.status_code == 400
    assert accepted_lines.status_code == 200
    assert too_many_lines.status_code == 400
    assert "100 linhas" in too_many_lines.json["error"]
