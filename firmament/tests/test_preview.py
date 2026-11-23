from firmament.positions import Led
from firmament.preview import groups, label


def _led(index: int, views: int) -> Led:
    return Led(index, 0.0, 0.0, 0.0, views)


def test_groups_separate_interpolated_leds():
    leds = [_led(0, 2), _led(1, 0), _led(2, 1), _led(3, 0)]

    assert groups(leds) == {"seen": [0, 2], "interpolated": [1, 3]}


def test_label_says_how_each_led_was_placed():
    assert [label(_led(4, v)) for v in (0, 1, 3)] == [
        "LED 4, interpolated",
        "LED 4, 1 view",
        "LED 4, 3 views",
    ]
