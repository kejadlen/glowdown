import socket
from collections.abc import Iterator

import pytest

from firmament.cli import main, play
from firmament.ddp import Header
from firmament.pattern import SLOT_COUNT, SLOT_SECONDS


@pytest.fixture
def receiver() -> Iterator[socket.socket]:
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.bind(("127.0.0.1", 0))
        s.settimeout(1)
        yield s


def _interrupt(_: float) -> None:
    raise KeyboardInterrupt


def test_light_reports_start_and_stop_and_turns_leds_off(receiver, monkeypatch, capsys):
    monkeypatch.setattr("firmament.cli.time.sleep", _interrupt)
    port = str(receiver.getsockname()[1])

    assert (
        main(["light", "--host", "localhost", "--port", port, "--leds", "4", "--index", "1"]) == 0
    )

    lit, off = (receiver.recv(2048)[Header.SIZE :] for _ in range(2))
    assert lit == bytes(3) + bytes([32] * 3) + bytes(6)
    assert off == bytes(12)
    err = capsys.readouterr().err
    assert "lighting LED 1 on localhost (127.0.0.1); press Ctrl-C to stop" in err
    assert "stopped and turned the LEDs off" in err


class FakeClock:
    def __init__(self) -> None:
        self.now = 0.0
        self.sleeps: list[float] = []

    def __call__(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.sleeps.append(seconds)
        self.now += seconds


def test_play_cycles_through_slots_in_order():
    clock = FakeClock()
    slots: list[int] = []
    play(
        lambda _: None,
        lambda s: bytes([s]),
        on_slot=slots.append,
        clock=clock,
        sleep=clock.sleep,
        limit=30,
    )
    assert slots == [k % SLOT_COUNT for k in range(30)]


def test_play_holds_each_slot_for_slot_seconds():
    clock = FakeClock()
    play(lambda _: None, lambda _: bytes(3), clock=clock, sleep=clock.sleep, limit=5)
    assert clock.sleeps == pytest.approx([SLOT_SECONDS] * 5)


def test_play_absorbs_small_lag_without_drift():
    clock = FakeClock()

    def slow_send(_: bytes) -> None:
        clock.now += 0.010

    play(slow_send, lambda _: bytes(3), clock=clock, sleep=clock.sleep, limit=10)
    assert clock.now == pytest.approx(10 * SLOT_SECONDS)


def test_play_restarts_schedule_after_a_long_stall():
    clock = FakeClock()
    rebases: list[float] = []
    sends = 0

    def stalling_send(_: bytes) -> None:
        nonlocal sends
        sends += 1
        if sends == 2:
            clock.now += 1.0

    play(
        stalling_send,
        lambda _: bytes(3),
        on_rebase=rebases.append,
        clock=clock,
        sleep=clock.sleep,
        limit=4,
    )
    assert rebases == [pytest.approx(1.0 - SLOT_SECONDS)]
    assert clock.sleeps[-2:] == pytest.approx([SLOT_SECONDS] * 2)


def test_light_rejects_index_beyond_led_count(capsys):
    with pytest.raises(SystemExit) as exit_info:
        main(["light", "--host", "127.0.0.1", "--leds", "100", "--index", "100"])
    assert exit_info.value.code == 2
    assert "LED index 100 is outside 0 to 99" in capsys.readouterr().err


def test_unknown_host_is_reported(capsys):
    assert main(["play", "--host", "no-such-host.invalid", "--leds", "100"]) == 1
    assert "can't find no-such-host.invalid" in capsys.readouterr().err
