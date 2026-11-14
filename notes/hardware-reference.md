# Hardware reference

Rules of thumb collected from earlier research sessions. Everything here came
from web research in those sessions and has not been re-verified; prefer the
linked primary sources.

## Pixel chips

- **WS2811 (12V):** cheapest and most common. Single data line, so one dead
  pixel kills or garbles everything downstream.
- **WS2815 / GS8208 (12V):** add a backup data line, so a dead pixel is
  skipped. GS8208 has a higher PWM refresh rate, which helps avoid flicker on
  camera and at low brightness. QuinLED's wiring guide notes WS2815 has other
  downsides, notably being very inefficient.
- **WS2812B (5V):** what the tree's fairy strings use.
- **RGBW** (SK6812, UCS2904): a dedicated white die gives a better warm white
  than RGB mixing, which looks bluish or pinkish when dimmed. Nearly all
  C9-style pixel strings are RGB only.
- Prefer **regulated** pixels over resistor-based ones, since they don't
  visibly fade with a little voltage drop.

## Form factors

- **Fairy / seed pixels:** small, low-power, disappear into branches when off.
  The usual choice for trees.
- **12mm bullets:** the standard for rooflines and props.
- **C9 / globe pixel bulbs:** the same chip inside a classic bulb shape.
- **Pixel nets, icicles, coro props, "mega trees":** the light-show hobby
  staples.

## Voltage and power

- 5V suits small fairy strings; 12V or 24V is better for long runs
  (voltage drop is much more manageable). 24V halves current at the cost of a
  narrower pixel selection.
- Inject power every 2-3 strings for 5V fairy lights.
- QuinLED's pixel guide: about 15 m / 50 ft of plain cable before voltage
  drop calls for extra injection wires.
- Size supplies from **measured** per-pixel draw, not datasheet worst case, and
  keep the load under about 80% of the supply's rating. Mean Well is the
  brand QuinLED recommends.
- For permanent installs, let WLED switch a relay to cut supply power when
  lights are off, and put a smart relay upstream so a hung controller can be
  power-cycled remotely.

## Primary sources

- [QuinLED power handling and wiring guides](https://quinled.info/llms.txt)
  (index of pages)
- [How much power do addressable LEDs use? (QuinLED)](https://quinled.info/2020/03/12/digital-led-power-usage/)
- [Power injection guide (QuinLED)](https://quinled.info/the-ultimate-led-strip-power-injection-guide/)
- [WLED Home Assistant integration](https://home-assistant.io/integrations/wled)
