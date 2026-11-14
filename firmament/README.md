# firmament

A mapping app for finding where each LED on a string is in 3D space, built
around an iPhone Pro (ARKit + LiDAR) and a WLED-driven string.

The name: a sky full of points of light, each with a coordinate.

## Status

Design only. Nothing is built. See [`DESIGN.md`](DESIGN.md).

## Shape of it

1. **Capture (iPhone, native Swift).** Plays a gray-code pattern to WLED while
   recording frames, ARKit poses, intrinsics, and depth. A dumb recorder.
2. **Solver (laptop, offline).** Decodes LED IDs, triangulates, cleans up with
   string and tree-shape priors, exports positions.
3. **Viewer and exporters.** A 3D preview, plus CSV/JSON, xLights model, and
   WLED ledmap outputs.
4. **Streamer (later).** Computes 3D effects per LED and sends them to WLED
   over DDP.

## Context

- Why this exists and what already exists:
  [`../notes/mapping-existing-solutions.md`](../notes/mapping-existing-solutions.md)
- Why ARKit: [`../notes/mapping-arkit-approach.md`](../notes/mapping-arkit-approach.md)
- The target hardware: [`../notes/tree-setup.md`](../notes/tree-setup.md)
