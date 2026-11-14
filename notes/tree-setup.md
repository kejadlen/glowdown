# Tree setup

Hardware plan for the Christmas tree. Compiled from earlier sessions
(2026-10-23 sizing, 2026-11-07 power).

## Basis

This build largely follows QuinLED's
[DIY addressable Christmas tree guide](https://quinled.info/2020/11/29/diy-addressable-christmas-tree-guide/):
the same style of fairy-light strings, a similar pixel count, and its measured
power numbers and injection rules of thumb (see "Power" below). One known
difference: this build uses 500 pixels (ten strands) versus the guide's roughly
450.

## The tree

- About 7.5 ft tall, slim: ~46" diameter at the base.
- Useful for mapping priors: height ~2.29 m, base radius ~0.58 m (approximate
  cone).

## Pixels

- Fairy-light strings: **50 LEDs per 5 m** (10 cm spacing, about 3.9").
  Each string covers roughly 16.4 ft.
- Chip: WS2812B, GRB order, 5V.
- On hand: **ten 5 m strings of 50 WS2812B LEDs = 500 pixels**.

### How the count was sized

For the 46" slim tree (surface about 47 sq ft), at ~4" spacing:

| Look | String length | Pixels |
| --- | --- | --- |
| Sparse spiral | ~95 ft | ~280 |
| Woven into branches, good density | ~140 ft | ~420 |
| Dense, show-tree look | ~195 ft | ~580 |

The "woven" look was the target (about 400-450 pixels, 9 strings of 50). The
strings actually on hand are ten, 500 pixels, a bit denser than that target.

Pixels are much brighter than incandescent minis, so the old rule of 100
lights per foot of height overshoots.

## What's on hand (2026-11-14)

- Ten 5 m strings of 50 WS2812B LEDs
- QuinLED Dig-Next-2
- 5V 10A power supply

Not yet confirmed as owned: injection hardware (JST SM pigtails, 18 AWG wire,
Wago lever nuts).

## Controller

- QuinLED Dig-Next-2 running WLED.
- Two WLED outputs of 250 pixels each (five strands per output).

## Power

- 5V supply: **10A on hand**. The Mean Well LRS-75-5 (14A) was the
  alternative with more headroom.
- 10A is enough for effects (about 4.5A). Full white across all 500 pixels
  (about 8A) sits right at the 80%-of-rating guideline, so set WLED's maximum
  current limit rather than relying on never running full white (derived from
  the numbers below; not from the guide).
- Basis: QuinLED's own DIY Christmas tree guide ran about 450 fairy-light
  pixels on a 5V 10A supply. Measured draw was about 36 W at full white,
  about 16 W single-color, and about 20 W typical effects, which is roughly
  16 mA per pixel at full white. Scaled to 500 pixels: about 40 W (8 A) at
  full white, about 22 W (4.5 A) in effects.
- Do **not** size from the 60 mA-per-LED worst case: that's for WS2812B
  strip, and fairy lights use much smaller LEDs on thin wire.
- Power injection: every 2-3 strings (every 2 for full white). For two chains
  of five strands, about six injection points total: the front of each chain,
  plus one in the middle and one at the end of each.
- Parts: JST SM 3-pin pigtails, 18 AWG power wire, Wago lever nuts.
- The Dig-Next-2's built-in fused outputs cover fusing, so a separate fuse
  block is optional.
- If using a brick supply, wire it directly to the controller. Barrel-to-
  terminal adapter blocks aren't recommended above about 5A.
- Dig-Next-2 power rating: about 15A continuous at 5V (as read in an earlier
  session; **unverified** since).

## Sources

- [QuinLED DIY addressable Christmas tree guide](https://quinled.info/2020/11/29/diy-addressable-christmas-tree-guide/)
- [QuinLED docs index](https://quinled.info/llms.txt) (an index of pages
  that's easy to navigate for power, wiring, and injection guides)
