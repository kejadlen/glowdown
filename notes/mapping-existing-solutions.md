# 3D mapping: existing solutions

Researched 2026-11-14 (web), plus mapping leads from an earlier session
(2026-10-23, marked **earlier**).

Almost every tool uses the same method: light each LED in turn, find the
bright spot in a camera frame by diffing against a dark reference frame, repeat
from several angles, then triangulate into 3D.

## Comparison

| Option | How it works | Output / target | Catch |
| --- | --- | --- | --- |
| [MariMapper](https://github.com/TheMariday/marimapper) | Webcam maps addressable LEDs into 3D space; Pixelblaze backend plus a stub for writing your own (an **earlier** session also noted a WLED backend) | 3D map, uploadable to Pixelblaze | Most general-purpose; non-Pixelblaze needs a backend |
| [Parker / Harvard pipeline](https://github.com/GSD6338/XmasTree) | Capture script on a Pi with a webcam, a mapper notebook, then an adjuster notebook for outliers | CSV of coordinates | Research-grade notebooks; coordinates are tree-specific |
| [standupmaths/xmastree2020](https://github.com/standupmaths/xmastree2020), [2021](https://github.com/standupmaths/xmastree2021) | Original code and coordinates; 2021 adds auto-correcting `light_fixer.py` | Python scripts, coordinate CSV | Coordinates only apply to his tree |
| [aaknitt/pixel_mapper](https://github.com/aaknitt/pixel_mapper) | Three camera positions exactly 120 degrees apart; two would do in principle, but the tree blocks pixels from any single view | xLights 3D model | Needs careful camera alignment |
| [WLED→xLights iOS app](https://slbarker.github.io/wled-xlights-mapper-ios-app/) | Walk around with an iPhone; gray-code AR scanning, no LiDAR needed | xLights custom model | iOS only, xLights-centric; one free export, then a lifetime price of GBP 9.99 |
| xLights custom model | Video-based model generator (WLED forum mention) | xLights | Probably 2D-leaning; not verified for 3D |
| [Twinkly](https://help.twinkly.com/en/help/map-your-twinkly-pro) | Phone camera scans each bulb; 3D mode, including a front and back scan option | Their app only | Proprietary, only their lights |
| [blinkenxmas](https://blinkenxmas.readthedocs.io/en/latest/api_calibrate.html) | Angle scanner captures images; a positions calculator uses trigonometry and scores to reject bad estimates | Python library | Small project; a readable reference for the maths |
| [led_camera_map](https://github.com/savdb/led_camera_map) (**earlier**) | Webcam generates a WLED ledmap and uploads it | WLED 2D ledmap | 2D, grid-snapped **(unverified)** |
| [XMasTractor / 3d-wled-driver](https://github.com/gunicsba/3d-wled-driver) (**earlier**) | Takes a MariMapper 3D map and runs effects on ESP32 over DDP | Renderer | Needs the map first **(unverified)** |
| Pixelblaze mapper (**earlier**) | Controller with built-in mapped pattern engine | Pixelblaze | Replaces WLED |

Other open-source tree mappers that follow the same recipe:
[NoMoor/3dLEDs](https://github.com/NoMoor/3dLEDs),
[Valthoron/TreeLights](https://github.com/Valthoron/TreeLights),
[Davidster/ShapeOfLightX](https://github.com/Davidster/ShapeOfLightX),
[JolonB/XmasTree](https://github.com/JolonB/XmasTree) (ESP32 web UI).
For the effects side: [sirxemic/xmastree-app](https://github.com/sirxemic/xmastree-app)
(live-coding effects for Parker's tree) and the
[Blender add-on](https://github.com/Sharkmanblu/Blender_XmasTree).
[Jason Coon's led-mapper](https://jasoncoon.github.io/led-mapper/) works with
FastLED (not explored).

## What the existing tools teach us

- **Occlusion is the main problem.** A tree hides roughly half the LEDs from
  any one view. A completely black capture usually means the LED was hidden.
- **Strings, not strips.** Consecutive LEDs are spaced along a wire and can
  face different directions, so an LED facing away shows up as glow on nearby
  needles, biasing its detected position. Missing LEDs can be interpolated
  along the string ([Hackaday comments](https://hackaday.com/2020/11/03/computer-vision-maps-christmas-lights)).
- **Height-only is already useful.** See `wled-and-control.md`.
- **Output formats are siloed.** Each tool targets one ecosystem (xLights,
  Pixelblaze, WLED ledmap, bare CSV). A neutral format with exporters is a gap.

## Where this leaves us

1. Run MariMapper first, as a baseline and as ground truth for anything
   homemade.
2. Build a custom mapper only for specific gaps: string-continuity cleanup,
   neutral output format, and a handheld-camera (ARKit) scanner. See
   [`mapping-arkit-approach.md`](mapping-arkit-approach.md) and
   [`../firmament/`](../firmament/).

## Local-first caveat

Twinkly and Govee are cloud-first. An earlier session noted Twinkly's Home
Assistant integration polls locally, but effects must be loaded from their app
first **(unverified)**.
