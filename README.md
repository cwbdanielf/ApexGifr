# ApexGifr

ApexGifr is a Python 3.10 application that converts Kaypro II styled text
into animated GIFs compatible with the SteelSeries Apex Pro TKL OLED
display. The project is inspired by and functionally equivalent to the
[SteelseriesAnimGif](https://github.com/bolner/SteelseriesAnimGif)
utility by Tamás Bolner.

## Features

- Converts plain text files (with optional numeric escape sequences) to
  scrolling animations.
- Uses the authentic Kaypro II 8x8 bitmap font extracted from the
  original project.
- Generates 128x40 monochrome GIFs ready for the SteelSeries Apex Pro
  TKL OLED display.
- Provides a simple command-line interface and unit test suite.

## Requirements

- Python 3.10+
- [Pillow](https://python-pillow.org/)
- [pytest](https://docs.pytest.org/) for running the test suite

Install the dependencies with:

```bash
pip install .[dev]
```

## Usage

Create a text file describing the animation script (21 columns x 4 rows
visible per frame). Then execute:

```bash
python gifr.py input.txt
```

This writes `input.gif` next to the input file. You can override
the destination path or frame duration:

```bash
python gifr.py input.txt output.gif --duration 80
```

Escape sequences like `\065` are supported and reference the Kaypro II
character codes. 

<img width="760" height="1000" alt="image" src="https://github.com/user-attachments/assets/f7f66d6e-f7f2-4152-9cfa-54d09b8285ee" />


## Development

Run the unit tests to validate changes:

```bash
pytest
```

## Acknowledgements

This project reuses the Kaypro II font bitmaps and overall animation
approach from Tamás Bolner's SteelseriesAnimGif project, licensed under
Apache 2.0. The remainder of ApexGifr is distributed under the MIT
License.
