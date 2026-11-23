"""A vertical wipe: a line rises from BOTTOM to TOP, painting a new color over the last one."""

# Heights in meters, in the map's frame; the first strand's map spans about -0.08 to 0.74.
BOTTOM = -0.1
TOP = 0.8
SECONDS_PER_PASS = 3.0
COLORS = [(255, 0, 0), (0, 255, 0), (0, 0, 255)]


def color(led, t):
    passes, progress = divmod(t / SECONDS_PER_PASS, 1)
    line = BOTTOM + progress * (TOP - BOTTOM)
    new = COLORS[int(passes) % len(COLORS)]
    old = COLORS[int(passes - 1) % len(COLORS)]
    return new if led.y <= line else old
