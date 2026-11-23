"""Find each LED's position from a Stray Scanner capture of the ID pattern.

Each LED is found lit in an all-on slot, placed in 3D from that pixel's depth and the camera
pose, then followed through the cycle's other slots by projecting that point into each frame.
Stations aren't needed, so this reads a walking capture, not the session format in SPEC.md.
"""

import csv
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np

from firmament.codes import BITS, WEIGHT, code
from firmament.pattern import ALL_OFF, ALL_ON, SLOT_COUNT
from firmament.positions import Led

# A lit LED saturates to a small, roughly round blob on a dark surround.
LIT_LEVEL = 235
BLOB_AREA = (4, 150)
BLOB_MAX_ASPECT = 3
SURROUND_SIZE = 31
SURROUND_MAX = 170

# A frame is part of an all-off slot when its blob count drops below this share of the nearby
# median.
OFF_SHARE = 0.6
OFF_MIN_FRAMES = 3
COUNT_WINDOW_FRAMES = 60

# Frames this close to a slot boundary, as a fraction of a slot, may straddle two slots.
BOUNDARY_MARGIN = 0.2
SAMPLE_RADIUS = 6
EDGE_MARGIN = 8
MIN_DEPTH = 0.05

# A decode needs this much on/off contrast, and this gap between the 6th and 7th brightest data
# slots relative to that contrast.
MIN_CONTRAST = 40
MIN_GAP = 0.3


@dataclass(frozen=True)
class Capture:
    """Per-frame poses, intrinsics, and images, with depth loaded on demand."""

    times: np.ndarray  # (n,) seconds.
    rotations: np.ndarray  # (n, 3, 3) camera to world, OpenCV camera axes (x right, y down).
    positions: np.ndarray  # (n, 3) meters, gravity-aligned world with y up.
    intrinsics: np.ndarray  # (n, 4) fx, fy, cx, cy in pixels.
    frames: list[np.ndarray]  # (n,) grayscale uint8 images.
    depth: Callable[[int], np.ndarray]  # Frame index to a depth map in meters.


@dataclass(frozen=True)
class Solution:
    leds: list[Led]
    cycles: int
    slot_seconds: float
    decodes: int
    rejects: int
    borrowed_strands: list[int]  # Strands placed from other strands' LEDs.


def read_stray(path: Path) -> Capture:
    """Read a Stray Scanner capture directory, raising ValueError if it's incomplete."""
    odometry = path / "odometry.csv"
    video = path / "rgb.mp4"
    depth_dir = path / "depth"
    for needed in (odometry, video, depth_dir):
        if not needed.exists():
            raise ValueError(f"{path}: missing {needed.name}; is this a Stray Scanner capture?")
    times, rotations, positions, intrinsics = read_odometry(odometry)
    frames = _read_video(video, limit=len(times))
    n = len(frames)

    def depth(i: int) -> np.ndarray:
        image = cv2.imread(str(depth_dir / f"{i:06d}.png"), cv2.IMREAD_UNCHANGED)
        if image is None:
            raise ValueError(f"{path}: can't read depth/{i:06d}.png")
        return image.astype(np.float64) / 1000.0

    return Capture(times[:n], rotations[:n], positions[:n], intrinsics[:n], frames, depth)


def read_odometry(path: Path) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Read Stray Scanner's `odometry.csv` into times, rotations, positions, and intrinsics."""
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.reader(f, skipinitialspace=True)
        header = next(reader, None)
        columns = ["timestamp", "x", "y", "z", "qx", "qy", "qz", "qw", "fx", "fy", "cx", "cy"]
        if header is None or any(c not in header for c in columns):
            raise ValueError(f"{path}: expected the columns {', '.join(columns)}")
        at = [header.index(c) for c in columns]
        try:
            rows = np.array([[float(row[i]) for i in at] for row in reader])
        except (IndexError, ValueError):
            raise ValueError(f"{path}, line {reader.line_num}: expected numbers") from None
    if len(rows) == 0:
        raise ValueError(f"{path}: no frames")
    rotations = np.array([quaternion_rotation(q) for q in rows[:, 4:8]])
    return rows[:, 0], rotations, rows[:, 1:4], rows[:, 8:12]


def quaternion_rotation(q: np.ndarray) -> np.ndarray:
    """Rotation matrix for a unit quaternion given as (x, y, z, w)."""
    x, y, z, w = q / np.linalg.norm(q)
    return np.array(
        [
            [1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
            [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
            [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)],
        ]
    )


def _read_video(path: Path, limit: int) -> list[np.ndarray]:
    video = cv2.VideoCapture(str(path))
    frames = []
    try:
        while len(frames) < limit:
            ok, image = video.read()
            if not ok:
                break
            frames.append(cv2.cvtColor(image, cv2.COLOR_BGR2GRAY))
    finally:
        video.release()
    if not frames:
        raise ValueError(f"{path}: can't read any video frames")
    return frames


def solve(capture: Capture, led_count: int, strand_length: int) -> Solution:
    """Decode and place every LED, interpolating the ones never decoded along their strand."""
    off_starts, slot = find_cycles(capture)
    table = {code(i): i for i in range(led_count)}
    seen: dict[int, list[np.ndarray]] = {}
    rejects = 0
    cycles = 0
    for off in off_starts:
        decoded = _decode_cycle(capture, capture.times[off] - slot, slot, table)
        if decoded is None:
            continue
        cycles += 1
        for index, point in decoded:
            if index is None:
                rejects += 1
            else:
                seen.setdefault(index, []).append(point)
    if len(seen) < 2:
        raise ValueError(
            f"decoded {len(seen)} LEDs; need at least 2 to place the rest. "
            "Check that the pattern was playing and the LEDs aren't too bright."
        )

    to_start_view = start_view(capture.rotations[0])
    known = {i: to_start_view @ np.median(points, axis=0) for i, points in seen.items()}
    xyz, borrowed = interpolate(known, led_count, strand_length)
    leds = [Led(i, *map(float, xyz[i]), len(seen.get(i, []))) for i in range(led_count)]
    decodes = sum(len(points) for points in seen.values())
    return Solution(leds, cycles, slot, decodes, rejects, borrowed)


def find_cycles(capture: Capture) -> tuple[list[int], float]:
    """Find the first frame of each all-off slot, and the slot length in seconds."""
    counts = np.array([len(blobs(frame)) for frame in capture.frames])
    n = len(counts)
    nearby = np.array(
        [
            np.median(counts[max(0, i - COUNT_WINDOW_FRAMES) : i + COUNT_WINDOW_FRAMES])
            for i in range(n)
        ]
    )
    low = counts < OFF_SHARE * nearby
    off_starts = [
        i
        for i in range(1, n - OFF_MIN_FRAMES + 1)
        if low[i] and not low[i - 1] and low[i : i + OFF_MIN_FRAMES].all()
    ]
    if len(off_starts) < 2:
        raise ValueError(
            f"found {len(off_starts)} all-off slots; need at least 2. "
            "Record at least two cycles (4.2 s) of the pattern with the LEDs in view."
        )
    period = float(np.median(np.diff(capture.times[off_starts])))
    return off_starts, period / SLOT_COUNT


def blobs(gray: np.ndarray) -> list[tuple[float, float]]:
    """Pixel centers of the lit LEDs in a frame."""
    lit = (gray > LIT_LEVEL).astype(np.uint8)
    count, _, stats, centers = cv2.connectedComponentsWithStats(lit)
    surround = cv2.blur(gray, (SURROUND_SIZE, SURROUND_SIZE))
    found = []
    for i in range(1, count):
        _, _, w, h, area = stats[i]
        if not BLOB_AREA[0] <= area <= BLOB_AREA[1] or max(w, h) > BLOB_MAX_ASPECT * min(w, h):
            continue
        u, v = centers[i]
        if surround[int(v), int(u)] < SURROUND_MAX:
            found.append((float(u), float(v)))
    return found


def _decode_cycle(
    capture: Capture, cycle_start: float, slot: float, table: dict[int, int]
) -> list[tuple[int | None, np.ndarray]] | None:
    """Decode each LED lit in the cycle's all-on slot, or None if that slot wasn't recorded."""
    times = capture.times
    middle = (times >= cycle_start + 0.25 * slot) & (times <= cycle_start + 0.75 * slot)
    on_frames = np.flatnonzero(middle)
    if len(on_frames) == 0:
        return None
    reference = int(on_frames[len(on_frames) // 2])
    depth = capture.depth(reference)

    # Sample half a cycle either side of this one, so each slot has more than one chance to be
    # in view.
    first, last = np.searchsorted(
        times, [cycle_start - SLOT_COUNT / 2 * slot, cycle_start + 1.5 * SLOT_COUNT * slot]
    )
    window = [
        (i, int(np.floor(k)) % SLOT_COUNT)
        for i in range(first, last)
        if abs((k := (times[i] - cycle_start) / slot) - round(k)) >= BOUNDARY_MARGIN
    ]

    decoded: list[tuple[int | None, np.ndarray]] = []
    for u, v in blobs(capture.frames[reference]):
        point = _unproject(capture, reference, depth, u, v)
        if point is None:
            continue
        per_slot: list[list[float]] = [[] for _ in range(SLOT_COUNT)]
        for i, s in window:
            uv = _project(capture, i, point)
            if uv is not None:
                per_slot[s].append(_sample(capture.frames[i], uv))
        if not all(per_slot):
            decoded.append((None, point))
            continue
        level = [float(np.median(samples)) for samples in per_slot]
        decoded.append((decode(level, table), point))
    return decoded


def decode(level: list[float], table: dict[int, int]) -> int | None:
    """The LED index for one LED's brightness in each slot, or None if it doesn't decode."""
    on, off = level[ALL_ON], level[ALL_OFF]
    data = np.array(level[2 : 2 + BITS])
    order = np.argsort(data, kind="stable")[::-1]
    word = sum(1 << int(b) for b in order[:WEIGHT])
    gap = (data[order[WEIGHT - 1]] - data[order[WEIGHT]]) / max(on - off, 1)
    if on - off < MIN_CONTRAST or gap < MIN_GAP:
        return None
    return table.get(word)


def _unproject(
    capture: Capture, i: int, depth: np.ndarray, u: float, v: float
) -> np.ndarray | None:
    height, width = capture.frames[i].shape
    du, dv = int(u * depth.shape[1] / width), int(v * depth.shape[0] / height)
    patch = depth[max(0, dv - 1) : dv + 2, max(0, du - 1) : du + 2]
    d = float(np.median(patch))
    # LiDAR reports 0 where it has no reading.
    if not d > MIN_DEPTH:
        return None
    fx, fy, cx, cy = capture.intrinsics[i]
    camera = np.array([(u - cx) / fx * d, (v - cy) / fy * d, d])
    return capture.rotations[i] @ camera + capture.positions[i]


def _project(capture: Capture, i: int, point: np.ndarray) -> tuple[float, float] | None:
    camera = capture.rotations[i].T @ (point - capture.positions[i])
    if camera[2] <= MIN_DEPTH:
        return None
    fx, fy, cx, cy = capture.intrinsics[i]
    u, v = cx + fx * camera[0] / camera[2], cy + fy * camera[1] / camera[2]
    height, width = capture.frames[i].shape
    if not (EDGE_MARGIN <= u < width - EDGE_MARGIN and EDGE_MARGIN <= v < height - EDGE_MARGIN):
        return None
    return u, v


def _sample(frame: np.ndarray, uv: tuple[float, float]) -> float:
    u, v = round(uv[0]), round(uv[1])
    r = SAMPLE_RADIUS
    return float(frame[v - r : v + r + 1, u - r : u + r + 1].max())


def start_view(rotation: np.ndarray) -> np.ndarray:
    """World-to-start-view rotation (SPEC.md, LED positions) for the first frame's camera."""
    forward = rotation[:, 2]
    back = -np.array([forward[0], 0.0, forward[2]])
    length = np.linalg.norm(back)
    if length < 1e-6:
        raise ValueError("the capture starts looking straight up or down; start facing the LEDs")
    back /= length
    up = np.array([0.0, 1.0, 0.0])
    return np.stack([np.cross(up, back), up, back])


def interpolate(
    known: dict[int, np.ndarray], led_count: int, strand_length: int
) -> tuple[list[np.ndarray], list[int]]:
    """Fill in every unknown LED linearly by index from known LEDs on its strand.

    Past a strand's last known LED, the line through its two nearest known LEDs continues. A
    strand with fewer than two known LEDs borrows from the whole string instead, and is
    returned in the second list.
    """
    if len(known) < 2:
        raise ValueError(f"need at least 2 known LEDs to interpolate, got {len(known)}")
    everywhere = sorted(known)
    xyz: list[np.ndarray] = []
    borrowed = []
    for start in range(0, led_count, strand_length):
        strand = range(start, min(start + strand_length, led_count))
        anchors = [i for i in everywhere if i in strand]
        if len(anchors) < 2:
            anchors = everywhere
            borrowed.append(start // strand_length)
        for i in strand:
            xyz.append(known[i] if i in known else _along(known, anchors, i))
    return xyz, borrowed


def _along(known: dict[int, np.ndarray], anchors: list[int], i: int) -> np.ndarray:
    below = [k for k in anchors if k < i]
    above = [k for k in anchors if k > i]
    if below and above:
        a, b = below[-1], above[0]
    elif above:
        a, b = above[0], above[1]
    else:
        a, b = below[-2], below[-1]
    return known[a] + (known[b] - known[a]) * (i - a) / (b - a)
