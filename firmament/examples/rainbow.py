"""A rainbow that climbs: the hue follows each LED's height and shifts with time."""

import colorsys

BANDS = 1.5
CYCLES_PER_SECOND = 0.2


def color(led, t):
    hue = (led.h * BANDS - t * CYCLES_PER_SECOND) % 1.0
    r, g, b = colorsys.hsv_to_rgb(hue, 1.0, 1.0)
    return (r * 255, g * 255, b * 255)
