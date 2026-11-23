"""A live 3D preview of the LEDs in the Rerun viewer."""

from collections.abc import Sequence

import rerun as rr

from firmament.positions import Led

# Unlit LEDs as faint dots, so the strand's shape stays visible when the effect is dark.
SOCKET_COLOR = (60, 60, 60)
SOCKET_RADIUS = 0.006
LED_RADIUS = 0.015


class Preview:
    def __init__(self, leds: Sequence[Led]) -> None:
        rr.init("firmament", spawn=True)
        rr.log("/", rr.ViewCoordinates.RIGHT_HAND_Y_UP, static=True)
        self._positions = [(led.x, led.y, led.z) for led in leds]
        rr.log(
            "sockets",
            rr.Points3D(self._positions, colors=SOCKET_COLOR, radii=SOCKET_RADIUS),
            static=True,
        )

    def show(self, t: float, frame: bytes) -> None:
        """Show one unscaled RGB frame at `t` seconds; black LEDs are left out."""
        rr.set_time("t", duration=t)
        lit = [i for i in range(len(self._positions)) if any(frame[3 * i : 3 * i + 3])]
        rr.log(
            "leds",
            rr.Points3D(
                [self._positions[i] for i in lit],
                colors=[tuple(frame[3 * i : 3 * i + 3]) for i in lit],
                radii=LED_RADIUS,
            ),
        )
