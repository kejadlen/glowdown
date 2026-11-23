# firmament design

Draft, 2026-11-14; revised 2026-11-22. Mostly a plan; [Plan](#plan) records
what's built and checked so far.

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
| LED count | up to 500 | a few hundred expected; the full tree is ten strands of 50 |
| ID code | 12 bits, weight 6 | 924 codes >= 500; see [`SPEC.md`](SPEC.md#id-code) |
| Spacing along a strand | ~0.10 m | 50 LEDs per 5 m; max consecutive distance |
| Strand boundaries | every 50th LED | the spacing prior does not hold across these; set by `strand_length` |
| WLED outputs | 2 x 250 | to confirm: indices continue across both outputs |
| Tree | ~2.29 m tall, ~0.58 m base radius | approximate cone prior, optional in `lights.json` |

## Decisions

- **Solver language: Python** (NumPy, OpenCV, SciPy). The problem is small
  (500 points, a few dozen stations); revisit only if it's slow.
- **Continuous capture, not stations.** The plan was to hold still for two
  cycles at each station, but the first run decoded while walking:
  `firmament solve` follows each LED through a cycle with the poses and depth.
  The station-based session format in [`SPEC.md`](SPEC.md#capture-session) is
  unused while Stray Scanner records.
- **Map with the room lit.** The first run decoded in daylight, so mapping
  doesn't need a dark room, and ARKit tracking in the dark stops being a risk.
- **Unseen LEDs get approximate positions.** Any LED the solver can't place,
  whether hidden by the walls or a branch, or never decoded, is interpolated
  along its strand between its seen neighbors. Approximate is fine for these,
  and outputs mark them with 0 views. Start with linear interpolation, evenly
  spaced by index; at a strand's ends, continue the line through the last two
  seen LEDs. Improve it later from the positions that are known, for example
  a curve fit through the strand's seen LEDs, or the cone when `lights.json`
  gives one.
- **Develop on a single strand.** Development and testing run on one strand,
  not necessarily on the tree, so nothing may assume ten strands or a cone.
  The pattern player already takes any LED count; the solver's priors come
  from `lights.json`.
- **Front arc only.** The tree stays in a corner, so captures cover an arc in
  front of it, not a full circle. LEDs facing the walls are never seen, which
  makes interpolation part of v1 rather than polish.
- **Capture app: Stray Scanner for now.** It records everything the solver
  needs (see [Recorder](#2-recorder-iphone-swift)). Write a native Swift app
  (a Mac with Xcode is on hand) only if Stray Scanner falls short, for example
  if exposure needs locking.

## Pipeline

### 1. Pattern player (laptop, Python)

- Streams frames to WLED over DDP. 500 LEDs is about 1.5 KB per frame.
- One cycle, looped forever:
  1. all on (sync, and each LED's "on" brightness)
  2. all off (sync, and the background)
  3. 12 bits of a constant-weight code, plain white on/off
- Each slot lasts 150 ms, about 4.5 camera frames at 30 fps, so a 14-slot
  cycle is 2.1 s. [`SPEC.md`](SPEC.md#pattern) has the exact pattern.
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
- Cover the arc in front of the corner from many heights, including above and
  below, and as far around each side as the walls allow.

For now, [Stray Scanner](https://github.com/strayrobots/scanner) (MIT) stands
in. Per its `docs/format.md`, it records an HEVC video, an `odometry.csv` with
a pose and intrinsics for every frame, and LiDAR depth. Its docs don't state
the pose convention or the tracking state. A recording shows the camera axes
are OpenCV's (x right, y down, z forward), not ARKit's, in a gravity-aligned
world with y up. Depth is a 256 x 192 PNG in millimeters, and the video is
1920 x 1440 at a nominal 60 fps, with about 53 fps actually recorded.
Intrinsics change slightly every frame, so `camera_matrix.csv` (the last
frame's) isn't enough. No tracking state is recorded.

### 3. Solver (laptop, Python)

1. **Detect** blobs per frame: difference against the all-off frame,
   threshold, connected components.
2. **Sync**: find the all-on/all-off frames, then slice each station into bit
   slots.
3. **Decode** IDs per blob: call each LED's 6 brightest data slots ones,
   reject codes that aren't in the table, and use repeated cycles to reject
   bad decodes.
4. **Triangulate** each LED from all views with known poses, robustly (reject
   by reprojection error, take the median).
5. **Refine** with bundle adjustment (see below).
6. **Clean up** with priors:
   - String continuity within strands (~0.10 m).
   - Approximate cone fit from LiDAR or the point cloud, with LEDs near its
     surface.
   - Interpolate LEDs that were never seen along their strand.
7. **Score** every LED: number of views, reprojection error, prior agreement.

`firmament solve` does detect, sync, and decode. In place of triangulation, it
places each LED from one frame's depth in each cycle and takes the median
across cycles. It interpolates unplaced LEDs along their strand, and does no
refinement, priors, or scoring yet.

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
  confidence, and views per LED (0 for interpolated LEDs).
- **Exporters:** WLED ledmap (height order as the trivial first version),
  xLights 3D custom model, Pixelblaze map, Blender-friendly CSV.

### 5. Viewer

A 3D plot of the points, colored by confidence, so bad ones are easy to spot.
Later, a web or native app for exploring the map, with interpolated LEDs shown
apart from seen ones.

### 6. Streamer

A small service that computes a color per LED from (x, y, z) each frame and
sends DDP frames to WLED. Effects: vertical sweeps, rotating colors, rising
flames. It shares DDP code with the pattern player. Built as
`firmament stream`, which also shows effects in a 3D preview.

## Capture session layout

[`SPEC.md`](SPEC.md#capture-session) defines it: per-station directories of
JPEG frames and a `poses.jsonl`, with the LED count, strand length, and
optional cone in a separate `lights.json`. The synthetic generator writes this same format.

## Testing

- **Synthetic first.** Generate known LED positions, on a cone and as a loose
  single strand, render them through simulated cameras with realistic noise,
  drift, blooming, and occlusion, and check the solver recovers them. No tree
  needed.
- **Real baseline.** Map the same tree with MariMapper and compare.

## Risks

- Bright backgrounds. `solve` rejects a lit spot when the area around it is
  bright, so an LED in front of a window or a lamp can go unplaced.
- Exposure blooming the LEDs.
- LEDs facing away from the camera biasing detections.
- LEDs facing the walls never being seen. Each wrap of a strand passes behind
  the tree, so every strand has gaps to fill from the priors.
- Light reflecting off the walls. A reflection blinks the same code as its
  LED, so it decodes as that LED. A glossy reflection moves between views and
  fails triangulation, but a diffuse glow is a fixed spot on the wall and
  triangulates fine. Reject it by blob size and by distance from the cone.
  Shiny ornaments and tinsel reflect the same way.
- Drift over the walk.
- Rolling shutter splitting a bit transition across one frame (holding each
  slot for 3+ frames, and discarding transition frames, should cover it).

## Open questions

- Do WLED indices continue across the two 250-pixel outputs? (Answered by the
  pattern player's debug mode.)
- Can exposure be locked during an ARKit session?
- Whether LiDAR meaningfully improves the cone prior or visibility checks.
  It already helps decoding: one pixel, its depth, and the pose give an LED
  a position from a single view, and projecting that position into the
  other frames follows the LED through all 14 slots while the camera moves.
  Positions from separate cycles agreed within about 2 cm. On a strand
  along a beam, the depth is the beam's; on the tree, it may be a branch
  behind the LED.

## Plan

In order. Steps 1, 2 and 4 need no phone or tree; 3 and 5 do.

1. **Spec.** Pin down the code scheme, slot timing, and session format. These
   are the contract between capture, synthetic data, and solver. Drafted in
   [`SPEC.md`](SPEC.md).
2. **Pattern player.** DDP loop with debug modes; check it on the tree. Built,
   and checked by eye on a single 50-LED strand (2026-11-22). Whether indices
   continue across the two outputs is still open.
3. **Tracking spike.** An existing recorder app on the phone, with the pattern
   player running. Does tracking hold? Done (2026-11-22): Stray Scanner, one
   50-LED strand on a beam, daylight, a 10.8 s walk with no stations. Poses
   and depth reproject matched scene features within 1 to 9 px across cycles,
   and the decoder, now `firmament solve`, read 34 of the 50 IDs, with
   neighbors about 0.10 m apart. Mapping happens with the room lit, so a dim
   room needs no test.
4. **Solver:** detect, sync, decode, triangulate. Built through decode as
   `firmament solve`, with each LED placed from depth instead of
   triangulated, and tested against synthetic frames. Triangulation and a
   synthetic generator that writes whole recordings are still to do.
5. **Real data.** Record the tree and run the solver.
6. **Height-ordered WLED ledmap,** the quick win once any positions exist.
   Unseen LEDs get heights by linear interpolation along their strand between
   seen neighbors.
7. Priors and bundle adjustment.
8. Viewer and exporters.
9. Streamer with a first 3D effect. Built as `firmament stream`, with
   rainbow and wipe examples.

A v1 for this season would stop at step 6, plus a rough 3D map from raw ARKit
poses, with unseen LEDs linearly interpolated along their strand.
