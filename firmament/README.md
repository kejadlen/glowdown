# firmament

A mapping app for finding where each LED on a string is in 3D space, built
around an iPhone Pro (ARKit + LiDAR) and a WLED-driven string.

The name: a sky full of points of light, each with a coordinate.

## Status

The pattern player is built and checked on a single strand. The solver maps a
Stray Scanner recording, standing in for the iPhone recorder, without the
priors or bundle adjustment the design calls for. The streamer plays effect
files from the solver's positions file. Everything else is design only. See
[`DESIGN.md`](DESIGN.md) for the plan and [`SPEC.md`](SPEC.md) for the pattern
and session format, and the [top-level README](../README.md#map-the-leds) for
mapping end to end.

## Run the pattern player

The repository's Nix flake provides Python and uv. From this directory:

```sh
nix develop ..
uv run firmament play --host wled.local --leds 300
```

Replace `wled.local` with your WLED's hostname or IP address. `play` loops the
ID pattern until you press Ctrl-C, then turns the LEDs off.
WLED goes back to its own effect 2.5 s later. Add `--log player.jsonl` to
record each slot sent.

To check the wiring, light one LED or one 50-LED strand:

```sh
uv run firmament light --host wled.local --leds 500 --index 250
uv run firmament light --host wled.local --leds 500 --strand 5
```

`--level` sets the brightness of a lit LED, from 0 to 255 (default 32).

## Find the LED positions

`solve` reads a [Stray Scanner](https://github.com/strayrobots/scanner)
recording of the ID pattern and writes a positions file in the
[`leds.csv`](SPEC.md#led-positions) format:

```sh
uv run firmament solve ../data/fb770bb311 --leds 50
```

`--leds` must match the count the pattern was played on. The file goes in the
recording's folder unless `--out` names another path. `solve` finds each LED
lit in a cycle's all-on slot and places it from its depth and the camera pose.
Then it follows that point through the rest of the cycle to read the LED's
ID. Each cycle that reads an LED's ID counts as one view. `solve` interpolates
an LED it never read along its strand, `--strand-length` LEDs long (default
50). A strand with fewer than 2 placed LEDs is interpolated from the nearest
placed LEDs on other strands, and `solve` names it.

## Play an effect

An effect is a Python file that defines `color(led, t)`. It gets one LED and
the time in seconds since the stream started, and returns `(r, g, b)` from 0
to 255; values outside that range are clamped.

```python
def color(led, t):
    return (255, 80, 0) if led.h < t % 1 else (0, 0, 0)
```

Directions are from where the capture started: x points right, y up, and z
back toward the camera. `led` has the following fields:

| Field | Meaning |
| --- | --- |
| `index` | The LED's index. |
| `x`, `y`, `z` | Position in meters. |
| `h` | Height, 0 at the lowest LED to 1 at the highest. |
| `r` | Distance from a vertical axis through the middle of the LEDs, 0 to 1 at the farthest. |
| `theta` | Angle around that axis in radians, -π to π. 0 faces where the capture started, and it increases to the right. |
| `nx`, `ny`, `nz` | Position centered on the LEDs and scaled so the largest span is -1 to 1, keeping proportions. |
| `views` | How many observations placed the LED; 0 means interpolated. |

Stream it to WLED, to a 3D preview in [Rerun](https://rerun.io)'s viewer, or
both, using a positions file in the [`leds.csv`](SPEC.md#led-positions)
format:

```sh
uv run firmament stream examples/rainbow.py --map leds.csv --host wled.local --preview
```

Leave out `--host` to only preview, or `--preview` to only light the LEDs.
The preview marks the LEDs the solver interpolated rather than saw. Unlit,
they're purple dots instead of gray, and lit, they're drawn flat instead of
shaded. They're logged under `leds/interpolated` and `sockets/interpolated`,
so you can hide them in the viewer's blueprint panel, and hovering over a dot
shows its index and view count.
`stream` reloads the effect each time you save it. If a save fails to load
or raises an error, `stream` prints the error and keeps playing the last
version that worked. `--brightness` scales the colors sent to WLED, from 0 to
255 (default 64); the preview always shows full colors. `--fps` sets the
frame rate (default 30).

## Develop

```sh
uv run pytest
uv run ruff format && uv run ruff check
uv run ty check
```

## Shape of it

1. **Pattern player (laptop, Python).** Loops a self-clocking gray-code
   pattern to WLED over DDP.
2. **Recorder (iPhone).** Records frames, ARKit poses, intrinsics, and depth.
   A dumb recorder; it doesn't control the LEDs. Stray Scanner, for now.
3. **Solver (laptop, Python, offline).** Decodes LED IDs, triangulates, cleans up with
   string and tree-shape priors, exports positions.
4. **Viewer and exporters.** A 3D preview, plus CSV/JSON, xLights model, and
   WLED ledmap outputs.
5. **Streamer (laptop, Python).** Computes 3D effects per LED and sends them
   to WLED over DDP.

## Context

- Why this exists and what already exists:
  [`../notes/mapping-existing-solutions.md`](../notes/mapping-existing-solutions.md)
- Why ARKit: [`../notes/mapping-arkit-approach.md`](../notes/mapping-arkit-approach.md)
- The target hardware: [`../notes/tree-setup.md`](../notes/tree-setup.md)
