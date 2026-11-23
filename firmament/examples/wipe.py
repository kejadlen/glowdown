"""A vertical wipe: a line rises from the lowest LED to the highest, painting over the last color."""

SECONDS_PER_PASS = 3.0
COLORS = [(255, 0, 0), (0, 255, 0), (0, 0, 255)]


def color(led, t):
    passes, line = divmod(t / SECONDS_PER_PASS, 1)
    new = COLORS[int(passes) % len(COLORS)]
    old = COLORS[int(passes - 1) % len(COLORS)]
    return new if led.h <= line else old
