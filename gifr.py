"""CLI entry point for the ApexGifr application."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
if SRC.exists() and str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from apexgifr.cli import main


if __name__ == "__main__":
    raise SystemExit(main())
