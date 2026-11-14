# Tree setup

Hardware plan for the Christmas tree. Compiled from earlier sessions
(2026-10-23 sizing, 2026-11-07 power).

## The tree

- About 7.5 ft tall, slim: ~46" diameter at the base.
- Useful for mapping priors: height ~2.29 m, base radius ~0.58 m (approximate
  cone).

## Pixels

- Fairy-light strings: **50 LEDs per 5 m** (10 cm spacing, about 3.9").
  Each string covers roughly 16.4 ft.
- Chip: WS2812B, GRB order, 5V.
- Plan: **ten strands of 50 = 500 pixels**.

### How the count was sized

For the 46" slim tree (surface about 47 sq ft), at ~4" spacing:

| Look | String length | Pixels |
| --- | --- | --- |
| Sparse spiral | ~95 ft | ~280 |
| Woven into branches, good density | ~140 ft | ~420 |
| Dense, show-tree look | ~195 ft | ~580 |

The "woven" look was the target (about 400-450 pixels, 9 strings of 50). The
build grew to ten strands, 500 pixels.

Pixels are much brighter than incandescent minis, so the old rule of 100
lights per foot of height overshoots.

## Controller

- QuinLED Dig-Next-2 running WLED.
- Two WLED outputs of 250 pixels each (five strands per output).

## Power

- 5V supply, **10A to 14A** (Mean Well LRS-75-5 is the 14A option with
  headroom).
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
