# Mapping with ARKit

Why an iPhone Pro (ARKit plus LiDAR) is a good fit for mapping a WLED-driven
string, and what could go wrong. Assumes an iPhone Pro with LiDAR and a
WLED-driven string. Written 2026-11-14.

## What ARKit gives us

- **Camera pose per frame in a shared world frame.** No turntable, tripod, or
  120-degree camera spacing. Walk around and triangulate with known poses.
- **Metric scale and gravity.** Coordinates come out in meters with "up"
  known; camera-only methods have to recover both.
- **More viewpoints.** Occlusion becomes "walk around, crouch, reach over the
  top".
- **LiDAR.**
  - Works in the dark.
  - Useful for the tree's overall shape (fit a cone) and for visibility
    checks against the scene mesh.
  - Depth at a tiny bright point inside foliage lands on needles, so use it
    for initial guesses only, not the final answer.

## The catch with a moving camera

Sequential capture ("light LED 1, snap, light LED 2, snap") assumes a static
camera and takes N rounds per viewpoint. The existing iOS app avoids this with
gray-code scanning: every LED blinks its own index as a binary code in
parallel. For 500 LEDs that's 9 bits (2^9 = 512), about a second or two per
viewpoint. Two ways to use it:

- **Stations (simpler, more robust):** hold still, decode, move on.
- **Continuous:** track blobs across frames while walking and decode over
  time.

## Gotchas

- **Tracking in the dark.** Visual-inertial tracking wants visible features,
  and mapping is normally done in a dark room. A dim lamp and lowered LED
  brightness is probably the compromise. LiDAR may help low-light tracking
  **(unverified)**. This is the first thing to test.
- **Exposure.** Auto-exposure will bloom the LEDs. iOS 16+ may expose the
  underlying capture device so exposure can be locked **(unverified)**.
- **Drift.** ARKit poses drift slightly; a final bundle-adjustment step
  (refine poses and points together) would tighten the result.
- **Sync.** Align frame timestamps with the LED pattern, accounting for
  WLED/DDP latency and rolling shutter. Hold each bit for 3+ camera frames.
- **Native iOS only.** Safari on iPhone has no WebXR AR.

## Priors that make it robust

- **String continuity.** Consecutive LEDs on a strand are at most about 10 cm
  apart (50 LEDs per 5 m). Strand boundaries (every 50th LED) and the two
  250-pixel outputs are not constrained this way.
- **Tree shape.** LEDs sit near the surface of an approximate cone (about 2.29
  m tall, about 0.58 m base radius), refined by LiDAR.
- **Robust triangulation.** Many views, reject by reprojection error, take
  the median.

## First spike

Build a minimal ARKit app that logs `trackingState` while waving the phone at a
blinking string in a dim room. If tracking holds, the rest is straightforward
engineering. If it doesn't, fall back to stations with the room lit between
captures.

See [`../firmament/DESIGN.md`](../firmament/DESIGN.md) for the planned
pipeline.
