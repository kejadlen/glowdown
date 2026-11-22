import pytest

from firmament.codes import code
from firmament.pattern import ALL_OFF, ALL_ON, SLOT_COUNT, index_frame, slot_frame, strand_frame


def _lit(frame: bytes) -> list[int]:
    pixels = [frame[i : i + 3] for i in range(0, len(frame), 3)]
    return [i for i, pixel in enumerate(pixels) if any(pixel)]


def test_all_on_lights_every_led_white_at_level():
    assert slot_frame(ALL_ON, 4, 32) == bytes([32] * 12)


def test_all_off_is_black():
    assert slot_frame(ALL_OFF, 4, 32) == bytes(12)


def test_data_slots_follow_each_leds_code():
    led_count = 300
    for slot in range(2, SLOT_COUNT):
        expected = [i for i in range(led_count) if code(i) >> (slot - 2) & 1]
        assert _lit(slot_frame(slot, led_count, 32)) == expected


def test_index_frame_lights_one_led():
    assert _lit(index_frame(250, 300, 32)) == [250]


def test_strand_frame_lights_one_strand():
    assert _lit(strand_frame(2, 50, 300, 32)) == list(range(100, 150))


def test_last_strand_can_be_partial():
    assert _lit(strand_frame(2, 50, 120, 32)) == list(range(100, 120))


@pytest.mark.parametrize(
    ("make", "match"),
    [
        (lambda: slot_frame(SLOT_COUNT, 10, 32), "slot"),
        (lambda: slot_frame(ALL_ON, 1, 32), "LED count"),
        (lambda: slot_frame(ALL_ON, 501, 32), "LED count"),
        (lambda: slot_frame(ALL_ON, 10, 256), "level"),
        (lambda: index_frame(10, 10, 32), "LED index"),
        (lambda: strand_frame(2, 50, 100, 32), "strand"),
        (lambda: strand_frame(0, 0, 100, 32), "strand length"),
    ],
)
def test_rejects_out_of_range_arguments(make, match):
    with pytest.raises(ValueError, match=match):
        make()
