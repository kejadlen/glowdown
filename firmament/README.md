# firmament

A mapping app for finding where each LED on a string is in 3D space, built
around an iPhone Pro (ARKit + LiDAR) and a WLED-driven string.

The name: a sky full of points of light, each with a coordinate.

## Status

The pattern player is built and checked on a single strand. The streamer plays
effect files from a positions file. The solver is a prototype outside the
repository, and everything else is design only. See [`DESIGN.md`](DESIGN.md) for the
plan and [`SPEC.md`](SPEC.md) for the pattern and session format.

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

## Play an effect

An effect is a Python file that defines `color(led, t)`. It gets one LED and
the time in seconds since the stream started, and returns `(r, g, b)` from 0
to 255; values outside that range are clamped. `led` has `index`, `x`, `y`,
`z` (meters, y up), and `views` (0 for an interpolated position).

```python
def color(led, t):
    return (255, 80, 0) if led.y < t % 2 else (0, 0, 0)
```

Stream it to WLED, to a 3D preview in [Rerun](https://rerun.io)'s viewer, or
both, using a positions file in the [`leds.csv`](SPEC.md#led-positions)
format:

```sh
uv run firmament stream examples/rainbow.py --map leds.csv --host wled.local --preview
```

Leave out `--host` to only preview, or `--preview` to only light the LEDs.
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
2. **Recorder (iPhone, native Swift).** Records frames, ARKit poses,
   intrinsics, and depth. A dumb recorder; it doesn't control the LEDs.
3. **Solver (laptop, Python, offline).** Decodes LED IDs, triangulates, cleans up with
   string and tree-shape priors, exports positions.
4. **Viewer and exporters.** A 3D preview, plus CSV/JSON, xLights model, and
   WLED ledmap outputs.
5. **Streamer (later).** Computes 3D effects per LED and sends them to WLED
   over DDP.

## Context

- Why this exists and what already exists:
  [`../notes/mapping-existing-solutions.md`](../notes/mapping-existing-solutions.md)
- Why ARKit: [`../notes/mapping-arkit-approach.md`](../notes/mapping-arkit-approach.md)
- The target hardware: [`../notes/tree-setup.md`](../notes/tree-setup.md)
