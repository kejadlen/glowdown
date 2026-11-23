"""Read LED positions, as defined in SPEC.md (LED positions)."""

import csv
import math
from dataclasses import dataclass
from pathlib import Path

from firmament.codes import MAX_LEDS
from firmament.pattern import MIN_LEDS

COLUMNS = ("index", "x", "y", "z", "views")


@dataclass(frozen=True)
class Led:
    index: int
    x: float
    y: float
    z: float
    views: int


def read_leds(path: Path) -> list[Led]:
    """Read `leds.csv`, raising ValueError with the line number of the first problem."""
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        missing = [c for c in COLUMNS if c not in (reader.fieldnames or [])]
        if missing:
            raise ValueError(f"{path}: missing column {', '.join(missing)}")
        leds = [_led(row, reader.line_num, path) for row in reader]
    for expected, led in enumerate(leds):
        if led.index != expected:
            raise ValueError(f"{path}: expected LED {expected} next, found {led.index}")
    if not MIN_LEDS <= len(leds) <= MAX_LEDS:
        raise ValueError(f"{path}: {len(leds)} LEDs is outside {MIN_LEDS} to {MAX_LEDS}")
    return leds


def _led(row: dict[str, str], line: int, path: Path) -> Led:
    try:
        index, views = int(row["index"]), int(row["views"])
        x, y, z = (float(row[c]) for c in "xyz")
    except (TypeError, ValueError):
        raise ValueError(
            f"{path}, line {line}: expected whole numbers for index and views, "
            "and numbers for x, y, and z"
        ) from None
    if not all(math.isfinite(v) for v in (x, y, z)):
        raise ValueError(f"{path}, line {line}: x, y, and z must be finite")
    if views < 0:
        raise ValueError(f"{path}, line {line}: views must be 0 or more")
    return Led(index, x, y, z, views)
