# glowdown

Notes and tools from LED fiddling.

## Current project

A slim Christmas tree (~7.5 ft tall, ~46" base diameter) wrapped in 500
WS2812B pixels (ten 5 m strings of 50), driven by WLED on a QuinLED Dig-Next-2.

The hardware build largely follows QuinLED's
[DIY addressable Christmas tree guide](https://quinled.info/2020/11/29/diy-addressable-christmas-tree-guide/).

The goal is to record each LED's 3D position, so effects can be computed from
where the lights *are* rather than where they sit on the wire. The plan is to
do the mapping with an iPhone Pro (ARKit + LiDAR) and a WLED-driven string.

## Layout

| Path | What's there |
| --- | --- |
| [`notes/tree-setup.md`](notes/tree-setup.md) | The tree: dimensions, string count, controller, power |
| [`notes/wled-and-control.md`](notes/wled-and-control.md) | WLED addressing, realtime streaming, ledmaps, controller options |
| [`notes/hardware-reference.md`](notes/hardware-reference.md) | Pixel chips, form factors, power rules of thumb |
| [`notes/mapping-existing-solutions.md`](notes/mapping-existing-solutions.md) | Survey of existing 3D LED mapping tools |
| [`notes/mapping-arkit-approach.md`](notes/mapping-arkit-approach.md) | Why and how to use ARKit for mapping |
| [`notes/porch-festoon.md`](notes/porch-festoon.md) | Separate project: a smart porch festoon (research stage) |
| [`firmament/`](firmament/) | The mapping app (design only, nothing built yet) |

## Status

- Research and notes: written (2026-11-14), compiled from a web research
  session plus earlier chats from October and November 2026.
- `firmament/`: design only.
- Next step: a tracking spike, to see whether ARKit tracking survives a dim
  room with a blinking string.

## A note on provenance

Claims in `notes/` come from web research done in those sessions. Items marked
**(unverified)** were stated in an earlier session and not re-checked when
these notes were assembled. Treat them as leads, not facts.
