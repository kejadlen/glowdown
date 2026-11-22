"""Frames for the ID pattern and the debug modes, as defined in SPEC.md (Pattern)."""

from collections.abc import Callable

from firmament.codes import BITS, MAX_LEDS, bit

SLOT_SECONDS = 0.150
SLOT_COUNT = 2 + BITS
ALL_ON = 0
ALL_OFF = 1
MIN_LEDS = 2


def slot_frame(slot: int, led_count: int, level: int) -> bytes:
    if not 0 <= slot < SLOT_COUNT:
        raise ValueError(f"slot {slot} is outside 0 to {SLOT_COUNT - 1}")
    if slot == ALL_ON:
        return _frame(led_count, level, lambda _: True)
    if slot == ALL_OFF:
        return _frame(led_count, level, lambda _: False)
    return _frame(led_count, level, lambda i: bit(i, slot - 2))


def index_frame(index: int, led_count: int, level: int) -> bytes:
    if not 0 <= index < led_count:
        raise ValueError(f"LED index {index} is outside 0 to {led_count - 1}")
    return _frame(led_count, level, lambda i: i == index)


def strand_frame(strand: int, strand_length: int, led_count: int, level: int) -> bytes:
    if strand_length < 1:
        raise ValueError(f"strand length {strand_length} must be at least 1")
    strand_count = -(-led_count // strand_length)
    if not 0 <= strand < strand_count:
        raise ValueError(f"strand {strand} is outside 0 to {strand_count - 1}")
    return _frame(led_count, level, lambda i: i // strand_length == strand)


def _frame(led_count: int, level: int, lit: Callable[[int], bool]) -> bytes:
    if not MIN_LEDS <= led_count <= MAX_LEDS:
        raise ValueError(f"LED count {led_count} is outside {MIN_LEDS} to {MAX_LEDS}")
    if not 0 <= level <= 255:
        raise ValueError(f"level {level} is outside 0 to 255")
    on = bytes([level] * 3)
    off = bytes(3)
    return b"".join(on if lit(i) else off for i in range(led_count))
