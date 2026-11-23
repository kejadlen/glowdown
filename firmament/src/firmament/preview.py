"""A live 3D preview of the LEDs in the Rerun viewer."""

from collections.abc import Sequence

import rerun as rr

from firmament.positions import Led

# Unlit LEDs as faint dots, so the strand's shape stays visible when the effect is dark.
# Interpolated ones get their own color, since their positions are guesses.
SOCKET_COLORS = {"seen": (60, 60, 60), "interpolated": (150, 50, 150)}
SOCKET_RADIUS = 0.006
LED_RADIUS = 0.015
LED_SHADING = {
    "seen": rr.components.PointShading.Gradient,
    "interpolated": rr.components.PointShading.Flat,
}


def groups(leds: Sequence[Led]) -> dict[str, list[int]]:
    """Indices into `leds` of the LEDs the solver saw and the ones it interpolated."""
    return {
        "seen": [i for i, led in enumerate(leds) if led.views > 0],
        "interpolated": [i for i, led in enumerate(leds) if led.views == 0],
    }


def label(led: Led) -> str:
    if led.views == 0:
        return f"LED {led.index}, interpolated"
    return f"LED {led.index}, {led.views} view{'' if led.views == 1 else 's'}"


class Preview:
    def __init__(self, leds: Sequence[Led], *, spawn: bool = True) -> None:
        rr.init("firmament", spawn=spawn)
        rr.log("/", rr.ViewCoordinates.RIGHT_HAND_Y_UP, static=True)
        self._positions = [(led.x, led.y, led.z) for led in leds]
        self._labels = [label(led) for led in leds]
        self._groups = {name: indices for name, indices in groups(leds).items() if indices}
        for name, indices in self._groups.items():
            rr.log(
                f"sockets/{name}",
                rr.Points3D(
                    [self._positions[i] for i in indices],
                    colors=SOCKET_COLORS[name],
                    radii=SOCKET_RADIUS,
                    labels=[self._labels[i] for i in indices],
                    show_labels=False,
                ),
                static=True,
            )

    def show(self, t: float, frame: bytes) -> None:
        """Show one unscaled RGB frame at `t` seconds; black LEDs are left out."""
        rr.set_time("t", duration=t)
        for name, indices in self._groups.items():
            lit = [i for i in indices if any(frame[3 * i : 3 * i + 3])]
            rr.log(
                f"leds/{name}",
                rr.Points3D(
                    [self._positions[i] for i in lit],
                    colors=[tuple(frame[3 * i : 3 * i + 3]) for i in lit],
                    radii=LED_RADIUS,
                    labels=[self._labels[i] for i in lit],
                    show_labels=False,
                    point_shading=LED_SHADING[name],
                ),
            )
