"""LED ID codewords, as defined in SPEC.md (ID code)."""

from functools import cache

BITS = 12
WEIGHT = 6
MAX_LEDS = 500

_ALL_ONES = (1 << BITS) - 1


@cache
def _table() -> tuple[int, ...]:
    low_half = [c for c in range(1 << (BITS - 1)) if c.bit_count() == WEIGHT]
    return tuple(word for c in low_half for word in (c, c ^ _ALL_ONES))


def code(index: int) -> int:
    if not 0 <= index < MAX_LEDS:
        raise ValueError(f"LED index {index} is outside 0 to {MAX_LEDS - 1}")
    return _table()[index]


def bit(index: int, position: int) -> bool:
    if not 0 <= position < BITS:
        raise ValueError(f"bit position {position} is outside 0 to {BITS - 1}")
    return bool(code(index) >> position & 1)
