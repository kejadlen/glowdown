# firmament spec

Format 1, drafted 2026-11-22. This is the contract between the pattern
player, the recorder, the synthetic generator, and the solver. A change
here that breaks old sessions bumps the format number.

[`DESIGN.md`](DESIGN.md) covers why the pieces are shaped this way. This
document covers only what each piece must produce or accept.

## Lights description

The solver reads the lights' properties from `lights.json`, kept
separately from any recording. The same lights are recorded many times,
and the recorder never needs these values.

```json
{
  "led_count": 500,
  "strand_length": 50,
  "cone": { "height": 2.29, "base_radius": 0.58 }
}
```

| Field | Meaning |
| --- | --- |
| `led_count` | Number of LEDs, indexed `0` to `led_count - 1`. Between 2 and 500. |
| `strand_length` | LEDs per physical strand. Strands start at every multiple of this index, and the spacing prior doesn't hold across a strand boundary. The last strand may be shorter. |
| `cone` | Optional. The approximate shape the LEDs sit on: an upright cone, apex up, with `height` and `base_radius` in meters. The solver fits its position and refines its size. Without it, the solver uses no shape prior. |

A single test strand off the tree is `{"led_count": 50, "strand_length": 50}`.

## ID code

Each LED blinks a 12-bit **constant-weight code**: every codeword has
exactly 6 ones. Two properties follow from the fixed weight:

- Any single flipped bit changes the count of ones, so the decoder
  detects it.
- Two overlapping blobs with different codes read as more than 6 ones, so
  a merged detection is rejected rather than decoded as the wrong LED.

### Codeword table

LED index `i` gets codeword `code(i)`, built as follows:

1. List every 12-bit value below 2048 (bit 11 clear) that has exactly 6
   ones, in increasing order. The list has 462 entries, `c[0]` to
   `c[461]`.
2. Set `code(2k) = c[k]` and `code(2k + 1) = c[k] XOR 0xFFF`.

Each pair is a codeword and its complement, so every bit is on for
exactly one LED of each pair. For any `led_count`, each data slot lights
half the LEDs, give or take one. No data slot can be mistaken for a sync
slot, and the per-slot power draw stays flat.

The first six entries are `63, 4032, 95, 4000, 111, 3984`. The table
supports 924 LEDs, and this format caps them at 500.

## Pattern

The pattern player loops one 14-slot cycle forever:

| Slot | Content |
| --- | --- |
| 0 | All LEDs on |
| 1 | All LEDs off |
| 2 to 13 | Bit `s - 2` of each LED's codeword, least significant bit first |

The following rules apply to every slot:

- A slot lasts 150 ms, so a cycle lasts 2.1 s.
- "On" is white (R = G = B) at a single brightness for the whole run.
  "Off" is black.
- The player sends one DDP frame per slot, and may resend it within the
  slot to keep WLED in realtime mode. It never sends a frame that mixes
  two slots.

Slot timing is nominal. The solver finds slot boundaries from the sync
slots in the images, never from wall-clock time.

### Decoding rule

The solver decodes an LED from its brightness in each of the 12 data
slots. It calls the 6 brightest slots ones and the rest zeros. It rejects
the decode if the gap between the 6th and 7th brightest readings is too
small relative to that LED's on/off range, or if the result isn't a code
in the table for `led_count`. The threshold is a solver setting, not part
of this contract.

## Capture session

A session is one walk around the tree. The recorder writes it, the
synthetic generator writes the same layout, and the solver reads it.

```
session-YYYYMMDD-HHMMSS/
  session.json
  stations/
    001/
      poses.jsonl
      frames/
        000000.jpg
        000001.jpg
  player.jsonl            # optional, debug only
```

### Stations

A **station** is a stretch of capture where the camera is meant to be
still. The recorder saves frames only between a station's start and end,
so each station is its own directory, numbered from `001`.

A station must last at least two cycles (4.2 s). Any 14 consecutive slots
contain every slot once, so the solver doesn't need the station to start
on a cycle boundary.

### `session.json`

```json
{
  "format": 1,
  "pattern": "cw12-6/150ms",
  "started_at": "2026-11-22T19:04:11-08:00",
  "device": "iPhone16,1",
  "notes": ""
}
```

| Field | Meaning |
| --- | --- |
| `format` | This spec's format number. |
| `pattern` | The pattern the player was running. `cw12-6/150ms` is the pattern in this document. |
| `started_at` | Local time the session started, ISO 8601 with offset. |
| `device` | The device's model identifier. The synthetic generator writes `synthetic`. |
| `notes` | Free text. |

### `poses.jsonl`

`poses.jsonl` holds one JSON object per saved frame, in capture order:

```json
{"frame": 0, "t": 8123.4567, "transform": [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0.12, 1.43, 2.05, 1], "intrinsics": [1450.2, 1450.2, 959.5, 719.5], "width": 1920, "height": 1440, "tracking": "normal"}
```

| Field | Meaning |
| --- | --- |
| `frame` | Frame number within the station, from 0. The image is `frames/<frame, 6 digits>.jpg`. |
| `t` | ARKit frame timestamp in seconds. Only differences between values are meaningful. |
| `transform` | Camera-to-world transform, 16 numbers, column-major (ARKit's `camera.transform`). |
| `intrinsics` | `[fx, fy, cx, cy]` in pixels of the saved image. |
| `width`, `height` | Saved image size in pixels. |
| `tracking` | `normal`, `limited:<reason>`, or `notAvailable`, from ARKit's tracking state. |

The world frame is ARKit's gravity-aligned frame: meters, y up. The
camera frame follows ARKit: x right, y up, the camera looking down −z.

### Frames

Frames are JPEG, saved in the sensor's native orientation without
rotation, so `intrinsics` apply to them directly.

### `player.jsonl`

`player.jsonl` is an optional log from the pattern player, one object per
slot sent: `{"t": <laptop Unix time>, "slot": <0 to 13>}`. The solver must
not depend on it.

## LED positions

The solver writes each LED's position to `leds.csv`. The streamer and the
exporters read it.

```csv
index,x,y,z,views
0,-0.412,0.581,-1.402,0
1,-0.371,0.535,-1.364,2
```

| Column | Meaning |
| --- | --- |
| `index` | LED index. Every index from `0` to `led_count - 1` appears exactly once, in order. |
| `x`, `y`, `z` | Position in meters, in a gravity-aligned frame with y up. The origin and the heading are wherever the capture's world frame put them. |
| `views` | How many observations the position came from. `0` means the solver never placed the LED and interpolated it along its strand. |

Readers find columns by their header names and ignore columns they don't
know, so later versions can add columns such as a confidence score.

## Not in format 1

- Depth. LiDAR's value is still an open question in
  [`DESIGN.md`](DESIGN.md#open-questions), so the format leaves it out
  until that's answered.
- Video. Frames are always individual images.
- Continuous capture outside stations.
