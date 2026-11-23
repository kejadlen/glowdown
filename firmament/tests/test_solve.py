import math

import numpy as np
import pytest

from firmament.codes import bit, code
from firmament.pattern import ALL_ON, SLOT_COUNT, SLOT_SECONDS
from firmament.positions import Led, read_leds, write_leds
from firmament.solve import (
    Capture,
    decode,
    interpolate,
    quaternion_rotation,
    read_odometry,
    solve,
    start_view,
)

WIDTH, HEIGHT = 320, 240
FX, CX, CY = 200.0, 160.0, 120.0
DEPTH = 2.0
FPS = 30
# Camera to world for an upright camera looking down world -z, in OpenCV camera axes.
UPRIGHT = np.diag([1.0, -1.0, -1.0])


def _synthetic(led_count: int, hidden: set[int], cycles: int = 4) -> tuple[Capture, np.ndarray]:
    """A still camera watching LEDs in a row, 30 px apart, playing the ID pattern."""
    pixels = [(40 + 30 * i, 60 + 12 * i) for i in range(led_count)]
    truth = np.array(
        [UPRIGHT @ [(u - CX) / FX * DEPTH, (v - CY) / FX * DEPTH, DEPTH] for u, v in pixels]
    )
    n = int(cycles * SLOT_COUNT * SLOT_SECONDS * FPS)
    # Start partway into a cycle, as a real capture would.
    times = 100.0 + 0.4 + np.arange(n) / FPS
    frames = []
    for t in times:
        slot = int((t - 100.0) / SLOT_SECONDS) % SLOT_COUNT
        frame = np.zeros((HEIGHT, WIDTH), np.uint8)
        for i, (u, v) in enumerate(pixels):
            lit = slot == ALL_ON or (slot >= 2 and bit(i, slot - 2))
            if lit and i not in hidden:
                frame[v - 1 : v + 2, u - 1 : u + 2] = 255
        frames.append(frame)
    capture = Capture(
        times=times,
        rotations=np.repeat(UPRIGHT[None], n, axis=0),
        positions=np.zeros((n, 3)),
        intrinsics=np.tile([FX, FX, CX, CY], (n, 1)),
        frames=frames,
        depth=lambda _: np.full((HEIGHT // 4, WIDTH // 4), DEPTH),
    )
    return capture, truth


def test_solve_places_each_lit_led_where_it_is():
    capture, truth = _synthetic(8, hidden=set())

    solution = solve(capture, led_count=8, strand_length=50)

    assert solution.cycles == 4
    assert solution.slot_seconds == pytest.approx(SLOT_SECONDS, rel=0.05)
    # The capture ends during the last cycle, so only 3 decode.
    assert solution.rejects == 8
    assert all(led.views == 3 for led in solution.leds)
    placed = np.array([(led.x, led.y, led.z) for led in solution.leds])
    np.testing.assert_allclose(placed, truth, atol=0.01)


def test_solve_interpolates_a_hidden_led_along_the_strand():
    capture, truth = _synthetic(8, hidden={3})

    solution = solve(capture, led_count=8, strand_length=50)

    hidden = solution.leds[3]
    assert hidden.views == 0
    np.testing.assert_allclose((hidden.x, hidden.y, hidden.z), truth[3], atol=0.01)


def test_solve_rejects_a_capture_without_the_pattern():
    capture, _ = _synthetic(8, hidden=set(range(8)))

    with pytest.raises(ValueError, match="found 0 all-off slots"):
        solve(capture, led_count=8, strand_length=50)


def _levels(index: int, on: float = 250, off: float = 10) -> list[float]:
    word = code(index)
    return [on, off] + [on if word >> b & 1 else off for b in range(12)]


TABLE = {code(i): i for i in range(50)}


def test_decode_reads_each_leds_codeword():
    assert [decode(_levels(i), TABLE) for i in range(50)] == list(range(50))


@pytest.mark.parametrize(
    "level",
    [
        _levels(7, on=40, off=10),  # Too little contrast.
        [250, 10] + [250] * 6 + [200] + [10] * 5,  # 6th and 7th brightest too close.
        _levels(60),  # A codeword beyond the LED count.
    ],
)
def test_decode_rejects_unclear_readings(level):
    assert decode(level, TABLE) is None


def _known(*indices: int) -> dict[int, np.ndarray]:
    return {i: np.array([float(i), 0.0, 0.0]) for i in indices}


def test_interpolate_fills_between_and_past_known_leds():
    xyz, borrowed = interpolate(_known(2, 4, 5), led_count=8, strand_length=8)

    assert [p[0] for p in xyz] == pytest.approx(range(8))
    assert borrowed == []


def test_interpolate_stays_within_each_strand():
    known = {0: np.zeros(3), 1: np.array([1.0, 0, 0]), 2: np.array([0, 5.0, 0])}
    known[3] = np.array([0, 6.0, 0])

    xyz, borrowed = interpolate(known | {5: np.array([0, 8.0, 0])}, led_count=6, strand_length=3)

    # LED 4 lies between 3 and 5 on the second strand, ignoring the first strand's LEDs.
    np.testing.assert_allclose(xyz[4], [0, 7.0, 0])
    assert borrowed == []


def test_interpolate_borrows_for_a_strand_with_too_few_known_leds():
    xyz, borrowed = interpolate(_known(0, 1, 5), led_count=6, strand_length=3)

    np.testing.assert_allclose([p[0] for p in xyz], range(6))
    assert borrowed == [1]


def test_quaternion_rotation_turns_about_y():
    half = math.radians(90) / 2
    rotation = quaternion_rotation(np.array([0, math.sin(half), 0, math.cos(half)]))

    np.testing.assert_allclose(rotation @ [1, 0, 0], [0, 0, -1], atol=1e-12)


def test_start_view_faces_the_first_camera():
    # A camera tilted down still gives a level view: z back toward it, y up.
    tilt = math.radians(30)
    tilted = UPRIGHT @ np.array(
        [[1, 0, 0], [0, math.cos(tilt), -math.sin(tilt)], [0, math.sin(tilt), math.cos(tilt)]]
    )

    np.testing.assert_allclose(start_view(tilted), np.eye(3), atol=1e-12)


def test_read_odometry_reads_stray_scanners_columns(tmp_path):
    path = tmp_path / "odometry.csv"
    path.write_text(
        "timestamp, frame, x, y, z, qx, qy, qz, qw, fx, fy, cx, cy, distortion_center_x\n"
        "10.5, 000000, 1, 2, 3, 0, 0, 0, 1, 1369.1, 1369.2, 965.5, 726.0, \n"
    )

    times, rotations, positions, intrinsics = read_odometry(path)

    assert times.tolist() == [10.5]
    np.testing.assert_allclose(rotations[0], np.eye(3))
    assert positions.tolist() == [[1, 2, 3]]
    assert intrinsics.tolist() == [[1369.1, 1369.2, 965.5, 726.0]]


@pytest.mark.parametrize(
    ("text", "match"),
    [
        ("timestamp, x, y\n", "expected the columns"),
        ("timestamp, x, y, z, qx, qy, qz, qw, fx, fy, cx, cy\n", "no frames"),
        ("timestamp, x, y, z, qx, qy, qz, qw, fx, fy, cx, cy\n1, 2\n", "line 2: expected numbers"),
    ],
)
def test_read_odometry_rejects_malformed_files(tmp_path, text, match):
    path = tmp_path / "odometry.csv"
    path.write_text(text)

    with pytest.raises(ValueError, match=match):
        read_odometry(path)


def test_write_leds_round_trips(tmp_path):
    leds = [Led(0, 0.1234, -0.5, 2.0, 3), Led(1, 1.0, 0.0, -1.25, 0)]
    path = tmp_path / "leds.csv"

    write_leds(path, leds)

    assert read_leds(path) == leds
