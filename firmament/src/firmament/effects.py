"""Load an effect file, which defines `color(led, t)`, and render it into RGB frames."""

import importlib.util
import math
import traceback
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path

from firmament.positions import Led


@dataclass(frozen=True)
class EffectLed(Led):
    """An LED as an effect sees it: its position, plus normalized and cylindrical coordinates.

    Positions are in SPEC.md's start view: x right, y up, z back toward the starting camera.
    The axis is vertical, through the middle of the map's horizontal bounding box.
    """

    h: float  # Height, 0 at the lowest LED to 1 at the highest.
    r: float  # Distance from the axis, 0 to 1 at the farthest LED.
    theta: float  # Around the axis, -pi to pi; 0 faces the start view, positive to its right.
    nx: float  # nx, ny, nz: centered on the map, scaled so the largest span is -1 to 1.
    ny: float
    nz: float


type ColorFn = Callable[[EffectLed, float], object]
type Report = Callable[[str], None]


def effect_leds(leds: Sequence[Led]) -> list[EffectLed]:
    lo = [min(getattr(led, a) for led in leds) for a in "xyz"]
    hi = [max(getattr(led, a) for led in leds) for a in "xyz"]
    center = [(a + b) / 2 for a, b in zip(lo, hi, strict=True)]
    half_span = max((b - a) / 2 for a, b in zip(lo, hi, strict=True))
    height = hi[1] - lo[1]
    cx, cy, cz = center

    def radius(led: Led) -> float:
        return math.hypot(led.x - cx, led.z - cz)

    farthest = max(radius(led) for led in leds)
    # A map with no extent along some direction (all LEDs level, or on the axis) gets 0 there.
    return [
        EffectLed(
            led.index,
            led.x,
            led.y,
            led.z,
            led.views,
            h=(led.y - lo[1]) / height if height else 0.0,
            r=radius(led) / farthest if farthest else 0.0,
            theta=math.atan2(led.x - cx, led.z - cz),
            nx=(led.x - cx) / half_span if half_span else 0.0,
            ny=(led.y - cy) / half_span if half_span else 0.0,
            nz=(led.z - cz) / half_span if half_span else 0.0,
        )
        for led in leds
    ]


class EffectError(Exception):
    pass


def load(path: Path) -> ColorFn:
    """Run the effect file and return its `color` function."""
    spec = importlib.util.spec_from_file_location(f"firmament_effect_{path.stem}", path)
    if spec is None or spec.loader is None:
        raise EffectError(f"{path} isn't a Python file")
    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
    except OSError as e:
        raise EffectError(f"can't read {path}: {e.strerror}") from None
    except Exception as e:  # noqa: BLE001 - effect code can raise anything.
        raise EffectError(_describe(e, path)) from None
    color = getattr(module, "color", None)
    if not callable(color):
        raise EffectError(f"{path.name} doesn't define color(led, t)")
    return color


def render(color: ColorFn, leds: Sequence[EffectLed], t: float, path: Path) -> bytes:
    """One RGB frame, clamping each channel to 0 to 255."""
    frame = bytearray()
    for led in leds:
        try:
            value = color(led, t)
        except Exception as e:  # noqa: BLE001 - effect code can raise anything.
            raise EffectError(_describe(e, path)) from None
        frame += _rgb(value, led)
    return bytes(frame)


def scale(frame: bytes, brightness: int) -> bytes:
    return bytes(round(c * brightness / 255) for c in frame)


class LiveEffect:
    """An effect file that reloads when it changes, and falls back to the last version that worked."""

    def __init__(self, path: Path, report: Report) -> None:
        self._path = path
        self._report = report
        self._mtime: int | None = None
        self._current: ColorFn | None = None
        self._working: ColorFn | None = None

    def frame(self, leds: Sequence[EffectLed], t: float) -> bytes:
        self._reload_if_changed()
        while self._current is not None:
            try:
                frame = render(self._current, leds, t, self._path)
            except EffectError as e:
                fallback = self._working if self._working is not self._current else None
                then = (
                    "going back to the last version that worked"
                    if fallback
                    else "showing black until the file changes"
                )
                self._report(f"{e}; {then}")
                self._current = self._working = fallback
            else:
                self._working = self._current
                return frame
        return bytes(3 * len(leds))

    def _reload_if_changed(self) -> None:
        try:
            mtime = self._path.stat().st_mtime_ns
        except OSError:
            # Editors that save by renaming leave the path missing for a moment.
            return
        if mtime == self._mtime:
            return
        first = self._mtime is None
        self._mtime = mtime
        try:
            self._current = load(self._path)
        except EffectError as e:
            keeping = "; keeping the current version" if self._current else ""
            self._report(f"{e}{keeping}")
        else:
            if not first:
                self._report(f"reloaded {self._path.name}")


def _rgb(value: object, led: Led) -> bytes:
    if not isinstance(value, Sequence) or isinstance(value, str) or len(value) != 3:
        raise EffectError(f"color() returned {value!r} for LED {led.index}; expected (r, g, b)")
    channels = []
    for c in value:
        if isinstance(c, bool) or not isinstance(c, int | float) or not math.isfinite(c):
            raise EffectError(f"color() returned {value!r} for LED {led.index}; expected numbers")
        channels.append(round(min(max(c, 0), 255)))
    return bytes(channels)


def _describe(e: Exception, path: Path) -> str:
    """The error and the line of the effect file it came from, without firmament's frames."""
    if isinstance(e, SyntaxError) and e.lineno is not None:
        return f"{path.name}:{e.lineno}: SyntaxError: {e.msg}"
    lines = [f.lineno for f in traceback.extract_tb(e.__traceback__) if f.filename == str(path)]
    where = f"{path.name}:{lines[-1]}" if lines and lines[-1] is not None else path.name
    return f"{where}: {type(e).__name__}: {e}"
