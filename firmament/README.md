# firmament

A mapping app for finding where each LED on a string is in 3D space, built
around an iPhone Pro (ARKit + LiDAR) and a WLED-driven string.

The name: a sky full of points of light, each with a coordinate.

## Status

The pattern player is built and unit-tested, but it hasn't run against the
tree yet. Everything else is design only. See [`DESIGN.md`](DESIGN.md) for the
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
