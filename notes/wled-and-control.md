# WLED and control

How to drive and address the lights. Items from earlier sessions that weren't
re-checked are marked **(unverified)**.

## Addressing individual LEDs

- **Segments.** Split a string into ranges, down to a single LED, each with its
  own color, effect, and brightness. In Home Assistant each segment becomes its
  own light entity.
- **Pattern effects.** Grouping and spacing settings on a segment give repeats
  ("every other bulb", "two on, one off") without per-LED work.
- **JSON API.** Set the exact color of each LED by index in one request. Per-LED
  state is temporary; check how it interacts with saved presets before relying
  on it for scheduled looks.
- **Realtime streaming.** WLED can receive full frames over DDP or E1.31, for
  example from xLights, so an external program can compute every LED's color
  each frame. WLED returns to its own effect when the stream stops
  **(unverified)**, so the lights recover if the renderer dies.
- **Presets from Home Assistant.** Build looks as WLED presets and let Home
  Assistant switch between them (by date, for seasonal looks).

## Mapping inside WLED

- **2D mode plus an `ledmap`.** WLED can treat a string as a 2D grid with a
  `ledmap` file placing each LED in a cell, so built-in 2D effects play across
  the real layout. Map files are named `ledmap1` through `ledmap9`
  **(unverified)**.
- [led_camera_map](https://github.com/savdb/led_camera_map) generates a ledmap
  from a webcam and uploads it to WLED. The author developed it on the
  MoonModules fork of WLED for its better 2D support **(unverified)**.
- Limits: positions snap to a grid, and it's 2D only.
- Cheap trick from the WLED forum: a ledmap that orders pixels by **height
  only** already works well for most regular effects on a tree
  ([thread](https://wled.discourse.group/t/2d-effects-on-a-christmas-tree/10416)).

## xLights

xLights runs on a computer and sends data to WLED; set the output protocol to
DDP. See [Adafruit's guide](https://learn.adafruit.com/xlights-for-sparkle-motion-board/xlights-setup-and-mapping).
If xLights sits in the stack, a 3D custom model of the tree gives a ready-made
effects engine. xLights plus Falcon Player (FPP, on a Raspberry Pi) is the
usual next step for sequenced shows, and FPP can drive WLED over E1.31 or DDP
**(unverified)**.

## Controller options (earlier session, **unverified**)

The WLED firmware decides chip support, so any of these drive the same lights.
The differences are build quality, protection, and polish.

| Option | Notes |
| --- | --- |
| QuinLED Dig-Uno / Dig-Quad / Dig-Next-2 | Community favorite: level shifters, fused outputs, screw terminals. Bare board needs an enclosure. Mostly sold from the EU. |
| Athom | Pre-assembled, pre-flashed. Less protection (fusing); some models are older ESP8266. |
| Gledopto | ESP32 in a finished enclosure. Fewer config options. |
| ABC WLED controllers | ESP32 boards for 5/12/24V, optional Ethernet. German shop. |
| DIY ESP32 | Cheapest; you handle level shifting and fusing yourself. |

For anything permanent, wired Ethernet is worth having.

## Alternative: Pixelblaze

A commercial controller built around mapped, code-driven patterns. MariMapper
can export maps for it. It's arguably the most polished option for spatial
effects, but it replaces WLED, and Home Assistant integration goes through
community projects.
