# Porch festoon (separate project)

A smart, locally controlled decorative light string for a porch. Research stage
only; nothing bought. Compiled from an earlier session (2026-10-23).

All product, price, and vendor details below were gathered in that session and
have **not** been re-verified since. Listings change; recheck before buying.

The working one-pager lives in Claude's docs:
[Porch Festoon Lights](https://claude.ai/code/artifact/87779a28-798f-48ac-8f58-ab0a201540b7).
This file is the repo copy of the thinking.

## Requirements

- Strung across a porch, café/festoon style. Individual-looking bulbs, not
  pixel dots.
- Rejected along the way: house outlines, pixel track, C9 strings.
- Local control only (Home Assistant plus WLED), no cloud.
- Year-round use, with seasonal colors chosen by Home Assistant. Warm white on
  most nights, so a real white channel (RGBW) matters.
- Smaller pixel form factors preferred (mini globes, seed/fairy pixels).
- Wants independent reviews and track record; pushed back on unreviewed
  Amazon-sourced strands.
- **Open question:** is the porch covered? The doc assumes yes, which makes
  IP66 acceptable; if not, stick to IP68.

## Candidates (globes)

| Option | Chip / power | Spec highlights | Notes |
| --- | --- | --- | --- |
| [LED Lighting Hut 50mm Digital RGBW Pixel Bulb Strand](https://www.ledlightinghut.com/50mm-tm1814-rgbw-pixel-bulb-light-strand.html) | TM1814, 12V, RGB + 3000K white | 30 bulbs, 9 m, 28 cm (~11") spacing, UV-resistant milky acrylic globes, IP66 | Listed at $209.50 per strand. TM1814 is on WLED's supported list, so lower risk. Shenzhen-based manufacturer selling direct (an earlier note calling it a US vendor was corrected), so expect international shipping and returns |
| [PixNet Digital Festoon RGBW 3000K](https://pixnetcontrol.com/digital-festoon/226-digital-festoon-rgbw-3000k.html) | WS2811 protocol, 24V, RGBW 3000K | 50mm globe, IP66, built to hook onto a support wire | Closest in form. UK (Norfolk) professional supplier to AV installers. Needs a 24V supply; QuinLED boards handle that |
| Amazon 50mm milky globe strings (e.g. [this listing](https://www.amazon.com/Addressable-XConnect-pigtails-LEDS_20CM-6M_EPOXY/dp/B0DXDWZXCF), [WENWENLEE](https://www.amazon.com/WENWENLEE-Addressable-Spacing-LEDs_30CM-9M_EPOXY/dp/B0DXF1QT7G)) | UCS2904 RGBW, 12V (or WS2811 RGB) | 30 bulbs, 20/30/50 cm spacing, IP68, epoxy-filled, ~0.9 W per bulb in 12V RGBW | Cheapest and most spacing options, but anonymous factory product resold under several storefronts (part number suggests a Shenzhen pixel factory). Choose xConnect pigtails. Test-only |
| [Minleon T50 RGBW Festoon](https://www.minleon.com.au/collections/t50-rgbw-pixel-festoon-light-string) | Minleon's own "RGB+" chipset | Bulbs on short drops, faceted/opaque/clear lenses, custom spacing | Most polished, but Australian and WLED compatibility unclear; ask first |
| [Gilbert Engineering Smart RGBW Outdoor String](https://gilbertengineeringusa.com/collections/pixels-accessories) | 12V | Lantern-style bulbs, listed at $49.99 | Spec sheet not found; check chip, spacing, and IP rating |
| [Superlighting LED 30mm globes](https://www.superlightingled.com/addressable-led-pixel-module-lights-c-6_318.html) | UCS2904 RGBW, 12V | ~14.5 cm (5.7") spacing | Smaller and denser: fairy-light feel |
| YGZGting 50mm pixel ball, 40 count | RGB | 360-degree globes | RGB only, no white channel |

Ruled out: C9 strings (the reputable ones, from Gilbert, Wally's, and Mattos,
are RGB-only at dense 6" spacing; the one RGBW C9 with wider spacing was from
an unreviewed seller). The PixelFit C9 RGBW retrofit needs its own proprietary
controller, so it won't work with WLED.

### Reviews

There are no independent reviews for any of these strands. What exists:

- ScamAdviser rates LED Lighting Hut as very likely legitimate and long-lived,
  but notes no reviews on popular sites. Don't confuse it with LED Hut
  (ledhut.co.uk), a different UK retailer.
- PixNet is a trade supplier with trade-press coverage; its customers are
  installers who don't post public reviews.
- Best places for real-world feedback: r/WLED, the QuinLED Discord (search the
  chip), the xLights community forums and Facebook groups, and
  doityourselfchristmas.com.
- Suggested approach: order one strand of each top candidate, run them side by
  side on the controller for a week or two (warm-white color, diffusion,
  low-brightness behavior, outdoor durability), then order the rest from the
  winner in one batch so color matches.

### WLED configuration hint

A blog post testing inexpensive RGBW outdoor lights with WLED found the SK6812
RGBW pixel type with RGB color ordering was the best match for its lights, and
made all built-in effects work. A plausible starting point for UCS2904 globes,
though it isn't a review of these strands
([post](https://bikerglen.com/blog/controlling-inexpensive-led-lights-with-wled/)).

## Controller and power

- 30 RGBW bulbs at ~0.9 W is about 27 W. A QuinLED Dig-Uno (single output) with
  a small 12V supply (~60 W) is plenty; a Dig-Quad only if more runs are added.
- Put the controller and supply indoors near the porch and run one xConnect
  lead out. At this size power injection is probably unnecessary.
- Wired Ethernet is worth having for a permanent install.

## Hanging

Hang the string from a tensioned stainless guide wire, never by its own cable.

1. Screw stainless eye bolts into framing at each end (porch header, beams,
   posts, or ceiling joists if covered), with pilot holes.
2. Run stainless wire rope between them, secured with wire rope clamps and a
   turnbuckle at one end.
3. Tension it, mounting about a foot above the lowest point the bulbs should
   hang.
4. Tie the string to the wire at every bulb with UV-resistant black zip ties.
5. Leave a service loop at the controller end.
6. Re-tighten the turnbuckle after the first week.

Use stainless throughout for a year-round install in Seattle's climate;
galvanized will eventually streak rust.

## Alternatives considered

- **Twinkly Festoon:** the off-the-shelf version of the same idea. Home
  Assistant integration polls locally, but effects must be loaded from their
  app, and older devices have broken with integration updates.
- **Nanoleaf Matter outdoor string with a WLED controller swap:**
  [HA community thread](https://community.home-assistant.io/t/nanoleaf-matter-smart-multicolor-outdoor-string-lights-running-on-wled/923516).
  A mainstream, widely reviewed RGBW bulb string with full WLED control, but
  not plug-and-play: one person got no output at first. The working settings
  used the SK6812/WS2814 RGBW pixel type, BRG color order, with white and green
  channels swapped, and reversed IP68 connector polarity.
- **Fairy-light variant:** a
  [WS2812B fairy string with WLED](https://neon.ninja/2021/01/sparkling-lights/)
  (2021, 5V) is a good picture of a seed-pixel porch setup.
- **Dumb café lights on a Z-Wave outdoor plug:** rock-solid, but only on/off
  and dimming.

## Next steps (from the doc)

- [ ] Measure the porch span and pick spacing (28-30 cm for café density, 50 cm
      for sparser).
- [ ] Order one test strand from each of the top two candidates.
- [ ] Bench-test both on one controller for a week.
- [ ] Order the winner in one batch, plus controller, supply, and hanging
      hardware.
- [ ] Ask in r/WLED or the QuinLED Discord about the winning chip before
      scaling up.

## References

- [QuinLED 12V WS2811 pixel guide](https://quinled.info/12v-ws2811-pixel-guide/)
- [QuinLED power injection guide](https://quinled.info/the-ultimate-led-strip-power-injection-guide/)
- [QuinLED Dig-Quad wiring guide](https://quinled.info/2020/10/03/quinled-dig-quad-wiring-guide/)
- [Home Assistant WLED integration](https://home-assistant.io/integrations/wled)
- [Controlling inexpensive LED lights with WLED](https://bikerglen.com/blog/controlling-inexpensive-led-lights-with-wled/)
- [The best way to hang outdoor string lights (Old World Garden Farms)](https://oldworldgardenfarms.com/2025/05/25/hang-outdoor-string-lights/)
- [How to hang patio string lights (Blue i Style)](https://www.blueistyleblog.com/howtohangstringlights/)
- [How to hang outdoor string lights in 3 easy steps (The Turquoise Home)](https://theturquoisehome.com/how-to-hang-outdoor-string-lights/)
- [How to hang outdoor string lights (Ultra Bright Lightz)](https://ultrabrightlightz.com/blogs/ubl-insider/how-to-hang-outdoor-string-lights)
- [How to hang outdoor lights for a cozy deck (Outdoor Living Inc)](https://outdoorlivinginc.com/blog/how-to-hang-outdoor-lights/)
- [SmartHomeScene: best Christmas lights for Home Assistant (local)](https://smarthomescene.com/top-picks/home-assistant-christmas-lights-with-local-control/)

## Why it's in this repo

Spatial effects on a single sagging festoon are basically a 1D curve, so
mapping is only interesting with a 2D layout (parallel strands, a zigzag, a
canopy). If spatial effects matter, plan the hanging layout around that before
buying. The mapping work in [`../firmament/`](../firmament/) could be reused.
