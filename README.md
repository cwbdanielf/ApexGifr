# ApexGifr

ApexGifr creates animated monochrome GIFs for the 128×40 OLED display on the SteelSeries Apex Pro TKL. It includes a text-animation generator and a local web editor for converting existing animated GIFs.

## Features

- Create scrolling text animations using the Kaypro II bitmap font.
- Convert animated GIFs to 128×40, 1-bit black-and-white animations.
- Preview and adjust framing with **cover/crop** or **contain**, zoom, and drag-to-position controls.
- Tune the grayscale threshold, invert black and white, apply Floyd–Steinberg dithering, and adjust playback speed.
- Preserve source frame delays (GIF timing uses 10 ms increments) and export an infinitely looping GIF.
- Process uploaded files locally; they are not sent to a third-party service.

## Requirements

- Python 3.10 or newer
- Pillow
- Flask for the web interface

## Install

From the repository root, install the web app and development/test dependencies:

```bash
python -m pip install -e ".[web,dev]"
```

For just the web app, use `python -m pip install -e ".[web]"`.

## Web app

Start the local server:

```bash
python -m apexgifr.web
```

Open <http://127.0.0.1:5000/> in your browser. The server binds to localhost by default. To choose a different port, run `python -m apexgifr.web --port 5050`.

### Convert an animated GIF

1. Choose **Converter GIF** and upload a `.gif` file (or drag it into the upload area).
2. Set the fit mode. **Preencher / recortar** fills the OLED frame and crops overflow; **Conter com fundo preto** fits the whole image and adds black bars as needed.
3. Adjust zoom and drag the preview to reposition the crop. Tune threshold, inversion, dithering, and speed as desired.
4. Select **Converter para OLED**, review the result, then download `apex-oled.gif`.

Uploads are limited to 20 MB, 300 frames, 2048 pixels per source dimension, and 20 million decoded source pixels. The exported animation is 128×40, black and white, and loops indefinitely.

### Create a text animation

Choose **Texto animado**, enter text, set the frame duration, create the animation, and download the resulting GIF. Lines wrap automatically to the 21-character OLED width. Numeric escapes such as `\065` insert a Kaypro character code (valid range 000–127).

The command-line text generator is also available:

```bash
python gifr.py input.txt [output.gif] --duration 80
```

The input is UTF-8. If no output path is supplied, the GIF is written next to the text file with a `.gif` extension. Frame duration is in milliseconds; it defaults to 100 ms.

## Tests

Install the development extra and run:

```bash
python -m pytest
```

The suite covers text generation, web routes, animated GIF conversion, and the `fish.gif` example.

## License and acknowledgements

ApexGifr is distributed under the MIT License. The Kaypro II font bitmap data and parts of the animation approach are adapted from [SteelseriesAnimGif](https://github.com/bolner/SteelseriesAnimGif) by Tamás Bolner and remain under that project's Apache 2.0 license. See `LICENSE` for details.
