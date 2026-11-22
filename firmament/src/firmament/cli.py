"""Command-line entry point: `firmament play` and `firmament light`."""

import argparse
import json
import sys
import time
from collections.abc import Callable
from itertools import count
from typing import TextIO

from firmament.codes import MAX_LEDS
from firmament.ddp import PORT, DdpSender
from firmament.pattern import (
    ALL_OFF,
    MIN_LEDS,
    SLOT_COUNT,
    SLOT_SECONDS,
    index_frame,
    slot_frame,
    strand_frame,
)

# Resend a static debug frame well inside WLED's 2.5 s realtime timeout.
LIGHT_RESEND_SECONDS = 1.0


def play(
    send: Callable[[bytes], None],
    frame_for_slot: Callable[[int], bytes],
    *,
    on_slot: Callable[[int], None] = lambda _: None,
    on_rebase: Callable[[float], None] = lambda _: None,
    clock: Callable[[], float] = time.monotonic,
    sleep: Callable[[float], None] = time.sleep,
    limit: int | None = None,
) -> None:
    """Loop the pattern, one slot per SLOT_SECONDS, until interrupted or `limit` slots."""
    next_at = clock()
    slots = count() if limit is None else range(limit)
    for k in slots:
        slot = k % SLOT_COUNT
        send(frame_for_slot(slot))
        on_slot(slot)
        next_at += SLOT_SECONDS
        lag = clock() - next_at
        if lag <= 0:
            sleep(-lag)
        elif lag > SLOT_SECONDS / 2:
            # Catching up would leave the next slot too short to decode, so start a fresh schedule.
            on_rebase(lag)
            next_at = clock()


def main(argv: list[str] | None = None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)
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
        try:
            sender.send(slot_frame(ALL_OFF, args.leds, args.level))
        except OSError:
            # WLED goes back to its own effect after its realtime timeout anyway.
            print("firmament: stopped, but couldn't turn the LEDs off", file=sys.stderr)
        else:
            print("firmament: stopped and turned the LEDs off", file=sys.stderr)
    return 0


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
    def on_slot(slot: int) -> None:
        if log:
            log.write(json.dumps({"t": time.time(), "slot": slot}) + "\n")

    def on_rebase(lag: float) -> None:
        print(
            f"firmament: fell {lag * 1000:.0f} ms behind; restarting slot timing", file=sys.stderr
        )

    try:
        play(sender.send, frames.__getitem__, on_slot=on_slot, on_rebase=on_rebase)
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
    return parser


def _ranged(low: int, high: int) -> Callable[[str], int]:
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
