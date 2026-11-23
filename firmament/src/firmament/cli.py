"""Command-line entry point: `firmament play`, `light`, `stream`, and `solve`."""

import argparse
import json
import sys
import time
from collections.abc import Callable
from contextlib import ExitStack
from itertools import count
from pathlib import Path
from typing import TextIO

from firmament.codes import MAX_LEDS
from firmament.ddp import PORT, DdpSender
from firmament.effects import LiveEffect, effect_leds, scale
from firmament.pattern import (
    ALL_OFF,
    MIN_LEDS,
    SLOT_COUNT,
    SLOT_SECONDS,
    index_frame,
    slot_frame,
    strand_frame,
)
from firmament.positions import read_leds, write_leds

# Resend a static debug frame well inside WLED's 2.5 s realtime timeout.
LIGHT_RESEND_SECONDS = 1.0

type Send = Callable[[bytes], None]
type FrameForTick = Callable[[int], bytes]
type OnTick = Callable[[int], None]
type OnRebase = Callable[[float], None]
type Clock = Callable[[], float]
type Sleep = Callable[[float], None]
type ParseInt = Callable[[str], int]


def run(
    send: Send,
    frame_for_tick: FrameForTick,
    period: float,
    *,
    on_tick: OnTick = lambda _: None,
    on_rebase: OnRebase = lambda _: None,
    clock: Clock = time.monotonic,
    sleep: Sleep = time.sleep,
    limit: int | None = None,
) -> None:
    """Send one frame per `period` seconds, until interrupted or `limit` ticks."""
    next_at = clock()
    ticks = count() if limit is None else range(limit)
    for k in ticks:
        send(frame_for_tick(k))
        on_tick(k)
        next_at += period
        lag = clock() - next_at
        if lag <= 0:
            sleep(-lag)
        elif lag > period / 2:
            # Catching up would leave the next frame too short (for the pattern, too short to
            # decode), so start a fresh schedule.
            on_rebase(lag)
            next_at = clock()


def main(argv: list[str] | None = None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)
    if args.command == "stream":
        return _stream(parser, args)
    if args.command == "solve":
        return _solve(parser, args)
    try:
        frames = _frames(args)
    except ValueError as e:
        parser.error(str(e))

    try:
        sender = DdpSender(args.host, args.port)
    except OSError as e:
        print(f"firmament: can't find {args.host}: {e}", file=sys.stderr)
        return 1

    with sender:
        print(
            f"firmament: {_activity(args)} on {args.host} ({sender.ip}); press Ctrl-C to stop",
            file=sys.stderr,
        )
        try:
            if args.command == "play":
                _play(frames, sender, args.log)
            else:
                _light(frames[0], sender)
        except KeyboardInterrupt:
            pass
        except OSError as e:
            print(f"firmament: can't send to {args.host}: {e}", file=sys.stderr)
            return 1
        _turn_off(sender, slot_frame(ALL_OFF, args.leds, args.level))
    return 0


def _stream(parser: argparse.ArgumentParser, args: argparse.Namespace) -> int:
    if args.host is None and not args.preview:
        parser.error("stream needs --host, --preview, or both")
    if not args.effect.is_file():
        parser.error(f"can't find the effect file {args.effect}")
    try:
        leds = read_leds(args.map)
    except OSError as e:
        parser.error(f"can't read {args.map}: {e.strerror}")
    except ValueError as e:
        parser.error(str(e))

    placed = effect_leds(leds)
    effect = LiveEffect(
        args.effect, lambda message: print(f"firmament: {message}", file=sys.stderr)
    )
    with ExitStack() as stack:
        sender = None
        if args.host is not None:
            try:
                sender = stack.enter_context(DdpSender(args.host, args.port))
            except OSError as e:
                print(f"firmament: can't find {args.host}: {e}", file=sys.stderr)
                return 1
        preview = None
        if args.preview:
            # Imported here so play and light don't pay for loading Rerun.
            from firmament.preview import Preview

            preview = Preview(leds)

        def frame_for_tick(k: int) -> bytes:
            t = k / args.fps
            frame = effect.frame(placed, t)
            if preview:
                preview.show(t, frame)
            return scale(frame, args.brightness)

        def on_rebase(lag: float) -> None:
            print(
                f"firmament: fell {lag * 1000:.0f} ms behind; restarting frame timing",
                file=sys.stderr,
            )

        targets = [f"{args.host} ({sender.ip})"] if sender else []
        targets += ["the preview"] if preview else []
        print(
            f"firmament: streaming {args.effect.name} ({len(leds)} LEDs) to "
            f"{' and '.join(targets)}; press Ctrl-C to stop",
            file=sys.stderr,
        )
        try:
            run(
                sender.send if sender else lambda _: None,
                frame_for_tick,
                1 / args.fps,
                on_rebase=on_rebase,
            )
        except KeyboardInterrupt:
            pass
        except OSError as e:
            print(f"firmament: can't send to {args.host}: {e}", file=sys.stderr)
            return 1
        if sender:
            _turn_off(sender, bytes(3 * len(leds)))
        else:
            print("firmament: stopped", file=sys.stderr)
    return 0


def _solve(parser: argparse.ArgumentParser, args: argparse.Namespace) -> int:
    if not args.capture.is_dir():
        parser.error(f"can't find the capture directory {args.capture}")
    out = args.out if args.out is not None else args.capture / "leds.csv"
    # Imported here so the other commands don't pay for loading OpenCV.
    from firmament.solve import read_stray, solve

    print(f"firmament: reading {args.capture}", file=sys.stderr)
    try:
        solution = solve(read_stray(args.capture), args.leds, args.strand_length)
    except ValueError as e:
        print(f"firmament: {e}", file=sys.stderr)
        return 1

    placed = sum(1 for led in solution.leds if led.views > 0)
    print(
        f"firmament: found {solution.cycles} cycles ({solution.slot_seconds * 1000:.0f} ms "
        f"slots): {solution.decodes} decodes placed {placed} of {args.leds} LEDs, "
        f"{solution.rejects} rejected",
        file=sys.stderr,
    )
    if solution.borrowed_strands:
        borrowed = solution.borrowed_strands
        label = "strand" if len(borrowed) == 1 else "strands"
        print(
            f"firmament: {label} {', '.join(map(str, borrowed))} had fewer than 2 placed LEDs "
            "each, so they were interpolated from other strands",
            file=sys.stderr,
        )
    try:
        write_leds(out, solution.leds)
    except OSError as e:
        print(f"firmament: can't write {out}: {e.strerror}", file=sys.stderr)
        return 1
    print(f"firmament: wrote {out}", file=sys.stderr)
    return 0


def _turn_off(sender: DdpSender, off: bytes) -> None:
    try:
        sender.send(off)
    except OSError:
        # WLED goes back to its own effect after its realtime timeout anyway.
        print("firmament: stopped, but couldn't turn the LEDs off", file=sys.stderr)
    else:
        print("firmament: stopped and turned the LEDs off", file=sys.stderr)


def _activity(args: argparse.Namespace) -> str:
    if args.command == "play":
        cycle = SLOT_COUNT * SLOT_SECONDS
        return f"playing the ID pattern ({args.leds} LEDs, {cycle:.1f} s per cycle)"
    if args.index is not None:
        return f"lighting LED {args.index}"
    first = args.strand * args.strand_length
    last = min(first + args.strand_length, args.leds) - 1
    return f"lighting strand {args.strand} (LEDs {first} to {last})"


def _frames(args: argparse.Namespace) -> list[bytes]:
    if args.command == "play":
        return [slot_frame(slot, args.leds, args.level) for slot in range(SLOT_COUNT)]
    if args.index is not None:
        return [index_frame(args.index, args.leds, args.level)]
    return [strand_frame(args.strand, args.strand_length, args.leds, args.level)]


def _play(frames: list[bytes], sender: DdpSender, log: TextIO | None) -> None:
    def on_tick(k: int) -> None:
        if log:
            log.write(json.dumps({"t": time.time(), "slot": k % SLOT_COUNT}) + "\n")

    def on_rebase(lag: float) -> None:
        print(
            f"firmament: fell {lag * 1000:.0f} ms behind; restarting slot timing", file=sys.stderr
        )

    try:
        run(
            sender.send,
            lambda k: frames[k % SLOT_COUNT],
            SLOT_SECONDS,
            on_tick=on_tick,
            on_rebase=on_rebase,
        )
    finally:
        if log:
            log.close()


def _light(frame: bytes, sender: DdpSender) -> None:
    while True:
        sender.send(frame)
        time.sleep(LIGHT_RESEND_SECONDS)


def _parser() -> argparse.ArgumentParser:
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--host", required=True, help="WLED hostname or IP address")
    common.add_argument("--port", type=int, default=PORT, help=f"DDP port (default {PORT})")
    common.add_argument(
        "--leds",
        type=_ranged(MIN_LEDS, MAX_LEDS),
        required=True,
        help=f"number of LEDs, {MIN_LEDS} to {MAX_LEDS}",
    )
    common.add_argument(
        "--level",
        type=_ranged(0, 255),
        default=32,
        help="brightness of a lit LED, 0 to 255 (default 32)",
    )

    parser = argparse.ArgumentParser(prog="firmament")
    commands = parser.add_subparsers(dest="command", required=True)

    play_command = commands.add_parser("play", parents=[common], help="loop the ID pattern")
    play_command.add_argument(
        "--log",
        type=_writable_file,
        help="write each slot sent to this JSON Lines file, for debugging",
    )

    light = commands.add_parser("light", parents=[common], help="light one LED or one strand")
    target = light.add_mutually_exclusive_group(required=True)
    target.add_argument("--index", type=_ranged(0, MAX_LEDS - 1), help="LED index to light")
    target.add_argument(
        "--strand", type=_ranged(0, MAX_LEDS - 1), help="strand number to light, from 0"
    )
    light.add_argument(
        "--strand-length",
        type=_ranged(1, MAX_LEDS),
        default=50,
        help="LEDs per strand (default 50)",
    )

    stream = commands.add_parser("stream", help="play an effect file on the mapped LEDs")
    stream.add_argument("effect", type=Path, help="Python file that defines color(led, t)")
    stream.add_argument(
        "--map", type=Path, required=True, help="LED positions file (leds.csv, see SPEC.md)"
    )
    stream.add_argument("--host", help="WLED hostname or IP address; leave out to only preview")
    stream.add_argument("--port", type=int, default=PORT, help=f"DDP port (default {PORT})")
    stream.add_argument("--preview", action="store_true", help="show the effect in Rerun's viewer")
    stream.add_argument(
        "--fps", type=_ranged(1, 60), default=30, help="frames per second, 1 to 60 (default 30)"
    )
    stream.add_argument(
        "--brightness",
        type=_ranged(0, 255),
        default=64,
        help="scale for the colors sent to WLED, 0 to 255 (default 64); the preview isn't scaled",
    )

    solve = commands.add_parser("solve", help="find LED positions from a Stray Scanner capture")
    solve.add_argument("capture", type=Path, help="Stray Scanner capture directory")
    solve.add_argument(
        "--leds",
        type=_ranged(MIN_LEDS, MAX_LEDS),
        required=True,
        help=f"number of LEDs the pattern was played on, {MIN_LEDS} to {MAX_LEDS}",
    )
    solve.add_argument(
        "--strand-length",
        type=_ranged(1, MAX_LEDS),
        default=50,
        help="LEDs per strand, for interpolating unplaced LEDs (default 50)",
    )
    solve.add_argument(
        "--out", type=Path, help="positions file to write (default leds.csv in the capture)"
    )
    return parser


def _ranged(low: int, high: int) -> ParseInt:
    def parse(text: str) -> int:
        try:
            value = int(text)
        except ValueError:
            raise argparse.ArgumentTypeError(f"{text!r} isn't a whole number") from None
        if not low <= value <= high:
            raise argparse.ArgumentTypeError(f"{value} is outside {low} to {high}")
        return value

    return parse


def _writable_file(path: str) -> TextIO:
    try:
        return open(path, "w", encoding="utf-8")
    except OSError as e:
        raise argparse.ArgumentTypeError(f"can't write {path}: {e.strerror}") from None


if __name__ == "__main__":
    sys.exit(main())
