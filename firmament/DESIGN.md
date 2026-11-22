# firmament design

Draft, 2026-11-14; revised 2026-11-22. Everything here is a plan, not a record
of what works.

## Principle: the laptop plays, the phone records, the laptop solves

- **Laptop plays.** A small script loops the ID pattern to WLED over DDP. The
  phone has no part in LED control.
- **Phone records.** The iPhone app saves frames, per-frame ARKit poses and
  intrinsics, and depth. It doesn't need to know what the LEDs are doing.
- **Laptop solves.** The solver runs offline on the recordings.

The pattern clocks itself: each cycle starts with all-on and all-off sync
frames that are visible in the images, so the solver finds bit boundaries from
the frames themselves. That removes Wi-Fi jitter and DDP latency from the sync
problem, and keeps the phone app small. The solver can also be improved and
re-run without re-walking the tree, and sample sessions can live in the repo
as test data.

## Parameters (the first target)

| Parameter | Value | Notes |
| --- | --- | --- |
| LED count | 500 | ten strands of 50 |
| ID code length | 9 bits | 2^9 = 512 >= 500 |
| Spacing along a strand | ~0.10 m | 50 LEDs per 5 m; max consecutive distance |
| Strand boundaries | every 50th LED | the spacing prior does not hold across these |
| WLED outputs | 2 x 250 | to confirm: indices continue across both outputs |
| Tree | ~2.29 m tall, ~0.58 m base radius | approximate cone prior |

## Decisions

- **Solver language: Python** (NumPy, OpenCV, SciPy). The problem is small
  (500 points, a few dozen stations); revisit only if it's slow.
- **Stations, not continuous capture,** for v1: hold still for a cycle or two,
  then move. Continuous capture can come later on the same session format.
- **Capture app: native Swift** (a Mac with Xcode is on hand). An
  off-the-shelf LiDAR recorder that exports per-frame poses could stand in for
  a first spike; not checked which ones do.

## Pipeline

### 1. Pattern player (laptop, Python)

- Streams frames to WLED over DDP. 500 LEDs is about 1.5 KB per frame.
- One cycle, looped forever:
  1. all on (sync, and each LED's "on" brightness)
  2. all off (sync, and the background)
  3. 9 gray-code bits, plain white on/off
  4. a parity bit
- Each slot is held for 3 or more camera frames. At 30 fps and 100 ms per
  slot, a 12-slot cycle is about 1.2 s.
- Low brightness, to limit blooming and stay well inside the 10A supply.
- Debug modes: light a single index, or a single strand. Use these to answer
  whether WLED indices continue across the two 250-pixel outputs (light LED
  250 and see which strand it's on).
- Optionally logs its own timeline, for debugging only; the solver must not
  depend on it.

### 2. Recorder (iPhone, Swift)

- ARKit world-tracking session, gravity-aligned, with scene depth enabled.
- Lock exposure if the capture device allows it **(unverified)**; otherwise
  lower LED brightness.
- Per frame: timestamp, camera transform, intrinsics, image size, tracking
  state. Images as frames or a video.
- A button marks station start and end, so the solver knows when the camera
  was meant to be still.
- Stations: cover the tree from many heights and angles, including above and
  below.

### 3. Solver (laptop, Python)

1. **Detect** blobs per frame: difference against the all-off frame,
   threshold, connected components.
2. **Sync**: find the all-on/all-off frames, then slice each station into bit
   slots.
3. **Decode** IDs per blob: threshold each LED halfway between its own on and
   off brightness, read the gray code, check parity, and use repeated cycles to
   reject bad decodes.
4. **Triangulate** each LED from all views with known poses, robustly (reject
   by reprojection error, take the median).
5. **Refine** with bundle adjustment (see below).
6. **Clean up** with priors:
   - String continuity within strands (~0.10 m).
   - Approximate cone fit from LiDAR or the point cloud, with LEDs near its
     surface.
   - Interpolate LEDs that were never seen along their strand.
7. **Score** every LED: number of views, reprojection error, prior agreement.

#### Bundle adjustment

ARKit poses drift by millimeters to a centimeter or two over a walk-around, so
lines of sight from different views don't quite meet, and that error goes into
the LED positions. Bundle adjustment treats both the camera poses and the LED
positions as unknowns, and searches for the combination that minimizes
reprojection error: the pixel distance between where each LED projects into
each image and where it was actually seen.

- The problem is heavily overdetermined (each LED seen from many stations,
  each station seeing hundreds of LEDs), so a drifted pose can't hide.
- It's nonlinear least squares; SciPy's `least_squares` handles this size.
- It starts from ARKit's poses and the first triangulation.
- Keep it anchored: hold gravity and metric scale from ARKit so the solution
  can't slide, rotate, or rescale freely.
- It's a refinement, not a requirement. Raw ARKit poses are probably good
  enough for effects like vertical sweeps.

### 4. Outputs

- **Canonical:** `leds.json` or CSV with index, x, y, z (meters, y up),
  confidence, and views per LED.
- **Exporters:** WLED ledmap (height order as the trivial first version),
  xLights 3D custom model, Pixelblaze map, Blender-friendly CSV.

### 5. Viewer

A 3D plot of the points, colored by confidence, so bad ones are easy to spot.

### 6. Streamer (later)

A small service that computes a color per LED from (x, y, z) each frame and
sends DDP frames to WLED. Effects: vertical sweeps, rotating colors, rising
flames. It can share DDP code with the pattern player.

## Capture session layout (sketch)

```
session-YYYYMMDD-HHMM/
  session.json            # LED count, code scheme and slot timing, device model, notes
  stations/
    001/
      frames/             # image per frame (or a video)
      poses.jsonl         # {t, transform[16], fx, fy, cx, cy, w, h, tracking}
      depth/              # optional
  player.jsonl            # optional: pattern player's own timeline, debug only
```

The synthetic generator writes this same format.

## Testing

- **Synthetic first.** Generate known LED positions on a cone, render them
  through simulated cameras with realistic noise, drift, blooming, and
  occlusion, and check the solver recovers them. No tree needed.
- **Real baseline.** Map the same tree with MariMapper and compare.

## Risks

- ARKit tracking in a dim room (first thing to test).
- Exposure blooming the LEDs.
- LEDs facing away from the camera biasing detections.
- Drift between stations.
- Rolling shutter splitting a bit transition across one frame (holding each
  slot for 3+ frames, and discarding transition frames, should cover it).

## Open questions

- Do WLED indices continue across the two 250-pixel outputs? (Answered by the
  pattern player's debug mode.)
- Can exposure be locked during an ARKit session?
- Whether LiDAR meaningfully improves the cone prior or visibility checks.
- Is there a recorder app good enough to skip writing the Swift app for the
  spike?

## Plan

In order. Steps 1, 2 and 4 need no phone or tree; 3 and 5 do.

1. **Spec.** Pin down the code scheme, slot timing, and session format. These
   are the contract between capture, synthetic data, and solver.
2. **Pattern player.** DDP loop with debug modes; check it on the tree.
3. **Tracking spike.** Minimal Swift recorder (or an existing app) on the
   phone, with the pattern player running, in a dim room. Does tracking hold?
4. **Synthetic generator,** then the solver against it: detect, sync, decode,
   triangulate.
5. **Real data.** Record the tree and run the solver.
6. **Height-ordered WLED ledmap,** the quick win once any positions exist.
7. Priors and bundle adjustment.
8. Viewer and exporters.
9. Streamer with a first 3D effect.

A v1 for this season would stop at step 6, plus a rough 3D map from raw ARKit
poses.
