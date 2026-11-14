# firmament design

Draft, 2026-11-14. Everything here is a plan, not a record of what works.

## Principle: phone records, laptop solves

The iPhone app only records. Each capture session saves frames, per-frame
poses and intrinsics, depth, and a timeline of what pattern WLED was showing.
The solver runs offline on a laptop, in any language. That means the solver can
be improved and re-run without re-walking the tree, and sample sessions can
live in the repo as test data.

## Parameters (the first target)

| Parameter | Value | Notes |
| --- | --- | --- |
| LED count | 500 | ten strands of 50 |
| ID code length | 9 bits | 2^9 = 512 >= 500 |
| Spacing along a strand | ~0.10 m | 50 LEDs per 5 m; max consecutive distance |
| Strand boundaries | every 50th LED | the spacing prior does not hold across these |
| WLED outputs | 2 x 250 | to confirm: indices continue across both outputs |
| Tree | ~2.29 m tall, ~0.58 m base radius | approximate cone prior |

## Pipeline

### 1. Capture (iPhone)

- ARKit world-tracking session, gravity-aligned, with scene depth enabled.
- LED control: stream frames to WLED over DDP (or UDP realtime), not the JSON
  API. 500 LEDs is about 1.5 KB per frame.
- Pattern, per station: all-on flash, all-off flash (sync), then 9 gray-code
  bits as plain white on/off, then a parity bit. Hold each bit for 3 or more
  camera frames. Repeat the cycle for redundancy.
- Stations: stand still for 1-2 seconds, then move on. Cover the tree from many
  heights and angles, including above and below.
- Lock exposure if the capture device allows it; otherwise lower LED
  brightness.
- Record per frame: timestamp, camera transform, intrinsics, image size,
  tracking state; plus the pattern timeline.

### 2. Solver (laptop)

1. **Detect** blobs per frame (difference against the all-off frame, threshold,
   connected components).
2. **Decode** IDs per blob track from the on/off sequence; use parity and the
   repeated cycles to reject bad decodes.
3. **Triangulate** each LED from all views with known poses, robustly (reject
   by reprojection error, median).
4. **Refine** with bundle adjustment over poses and points, since ARKit poses
   drift.
5. **Clean up** with priors:
   - String continuity within strands (~0.10 m).
   - Approximate cone fit from LiDAR or the point cloud, with LEDs near its
     surface.
   - Interpolate LEDs that were never seen along their strand.
6. **Score** every LED: number of views, reprojection error, prior agreement.

Language is undecided. Python (NumPy/OpenCV) is fastest to prototype.

### 3. Outputs

- **Canonical:** `leds.json` or CSV with index, x, y, z (meters, y up),
  confidence, and views per LED.
- **Exporters:** xLights 3D custom model, WLED ledmap (height order as the
  trivial fallback), Pixelblaze map, Blender-friendly CSV.

### 4. Viewer

A 3D plot of the points, colored by confidence, so bad ones are easy to spot.

### 5. Streamer (later)

A small service that computes a color per LED from (x, y, z) each frame and
sends DDP frames to WLED. Effects: vertical sweeps, rotating colors, rising
flames.

## Capture session layout (sketch)

```
session-YYYYMMDD-HHMM/
  session.json            # LED count, code scheme, device model, notes
  stations/
    001/
      frames/             # image per frame (or a video)
      poses.jsonl         # {t, transform[16], fx, fy, cx, cy, w, h, tracking}
      pattern.jsonl       # {t, bit_index or sync marker}
      depth/              # optional
```

## Testing

- **Synthetic first.** Generate known LED positions on a cone, render them
  through simulated cameras with realistic noise and occlusion, and check the
  solver recovers them. No tree needed.
- **Real baseline.** Map the same tree with MariMapper and compare.

## Risks

- ARKit tracking in a dim room (first thing to test).
- Exposure blooming the LEDs.
- LEDs facing away from the camera biasing detections.
- Pattern/frame sync under Wi-Fi jitter.
- Drift between stations.

## Open questions

- Stations or continuous capture?
- Solver language (Python vs. something compiled)?
- Whether LiDAR meaningfully improves the cone prior or visibility checks.
- Do WLED indices continue across the two 250-pixel outputs?

## Milestones

- [ ] Tracking spike: log `trackingState` waving a phone at the blinking
      string in a dim room.
- [ ] Capture app: ARKit session, DDP code player, recorder.
- [ ] Synthetic dataset generator.
- [ ] Solver: detect, decode, triangulate.
- [ ] Priors and bundle adjustment.
- [ ] Viewer and exporters.
- [ ] Streamer with a first 3D effect.
