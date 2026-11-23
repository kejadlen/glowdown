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

## Map the LEDs

Mapping produces `leds.csv`: one row per LED with its position in meters (see
[`firmament/SPEC.md`](firmament/SPEC.md#led-positions)). You need Nix, WLED
on the network, and an iPhone Pro with
[Stray Scanner](https://github.com/strayrobots/scanner) installed. Run the
commands from `firmament/`, inside the repository's dev shell
(`nix develop ..`).

1. Play the ID pattern on the LEDs, and leave it running:

   ```sh
   uv run firmament play --host wled.local --leds 50
   ```

   Replace `wled.local` with your WLED's hostname or IP address, and `50` with
   the number of LEDs.
2. Record in Stray Scanner. Start with the phone facing the LEDs, because the
   map's axes come from where the recording starts: x to the right, y up, and z
   back toward you. Then walk slowly around the front of the LEDs for at least
   4.2 s, two cycles of the pattern.
3. Press Ctrl-C to stop the player.
4. Copy the recording's folder from the phone into `data/`, which is ignored
   by version control. Connect the phone to the Mac, select it in Finder's
   sidebar, open the Files tab, and drag the folder out from under Stray
   Scanner. Stray Scanner names the folder after a random hash, such as
   `fb770bb311`.
5. Find the LED positions, with the same LED count you played:

   ```sh
   uv run firmament solve ../data/fb770bb311 --leds 50
   ```

   `solve` writes `leds.csv` into the recording's folder (`--out` changes
   this) and reports how many LEDs it placed. It fills in each LED it couldn't
   identify by interpolating along its strand, and gives it 0 in the `views`
   column. Set `--strand-length` if your strands aren't 50 LEDs long.
6. Check the map by playing an effect in a 3D preview:

   ```sh
   uv run firmament stream examples/wipe.py --map ../data/fb770bb311/leds.csv --preview
   ```

[`firmament/README.md`](firmament/README.md) covers each command's options.

## Layout

| Path | What's there |
| --- | --- |
| [`notes/tree-setup.md`](notes/tree-setup.md) | The tree: dimensions, string count, controller, power |
| [`notes/wled-and-control.md`](notes/wled-and-control.md) | WLED addressing, realtime streaming, ledmaps, controller options |
| [`notes/hardware-reference.md`](notes/hardware-reference.md) | Pixel chips, form factors, power rules of thumb |
| [`notes/mapping-existing-solutions.md`](notes/mapping-existing-solutions.md) | Survey of existing 3D LED mapping tools |
| [`notes/mapping-arkit-approach.md`](notes/mapping-arkit-approach.md) | Why and how to use ARKit for mapping |
| [`notes/porch-festoon.md`](notes/porch-festoon.md) | Separate project: a smart porch festoon (research stage) |
| [`firmament/`](firmament/) | The mapping app: pattern player, solver, and effect streamer |

## Status

- Research and notes: written (2026-11-14), compiled from a web research
  session plus earlier chats from October and November 2026.
- `firmament/`: mapped a single 50-LED strand in daylight (2026-11-22).
  `solve` placed 34 of the 50 LEDs from a 10.8 s Stray Scanner walk and
  interpolated the rest. Nothing has run against the tree yet.
- Next steps (see [`firmament/DESIGN.md`](firmament/DESIGN.md#plan)): map the
  tree in a dim room, to see whether ARKit tracking survives it.

## A note on provenance

Claims in `notes/` come from web research done in those sessions. Items marked
**(unverified)** were stated in an earlier session and not re-checked when
these notes were assembled. Treat them as leads, not facts.
