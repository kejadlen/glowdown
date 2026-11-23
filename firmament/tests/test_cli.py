import socket
from collections.abc import Iterator

import pytest

from firmament.cli import main, run
from firmament.ddp import Header


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


PERIOD = 0.150


def test_run_sends_each_ticks_frame_in_order():
    clock = FakeClock()
    sent: list[bytes] = []
    ticks: list[int] = []
    run(
        sent.append,
        lambda k: bytes([k]),
        PERIOD,
        on_tick=ticks.append,
        clock=clock,
        sleep=clock.sleep,
        limit=30,
    )
    assert sent == [bytes([k]) for k in range(30)]
    assert ticks == list(range(30))


def test_run_holds_each_frame_for_one_period():
    clock = FakeClock()
    run(lambda _: None, lambda _: bytes(3), PERIOD, clock=clock, sleep=clock.sleep, limit=5)
    assert clock.sleeps == pytest.approx([PERIOD] * 5)


def test_run_absorbs_small_lag_without_drift():
    clock = FakeClock()

    def slow_send(_: bytes) -> None:
        clock.now += 0.010

    run(slow_send, lambda _: bytes(3), PERIOD, clock=clock, sleep=clock.sleep, limit=10)
    assert clock.now == pytest.approx(10 * PERIOD)


def test_run_restarts_schedule_after_a_long_stall():
    clock = FakeClock()
    rebases: list[float] = []
    sends = 0

    def stalling_send(_: bytes) -> None:
        nonlocal sends
        sends += 1
        if sends == 2:
            clock.now += 1.0

    run(
        stalling_send,
        lambda _: bytes(3),
        PERIOD,
        on_rebase=rebases.append,
        clock=clock,
        sleep=clock.sleep,
        limit=4,
    )
    assert rebases == [pytest.approx(1.0 - PERIOD)]
    assert clock.sleeps[-2:] == pytest.approx([PERIOD] * 2)


def test_light_rejects_index_beyond_led_count(capsys):
    with pytest.raises(SystemExit) as exit_info:
        main(["light", "--host", "127.0.0.1", "--leds", "100", "--index", "100"])
    assert exit_info.value.code == 2
    assert "LED index 100 is outside 0 to 99" in capsys.readouterr().err


def test_unknown_host_is_reported(capsys):
    assert main(["play", "--host", "no-such-host.invalid", "--leds", "100"]) == 1
    assert "can't find no-such-host.invalid" in capsys.readouterr().err


def _stream_files(tmp_path):
    leds = tmp_path / "leds.csv"
    leds.write_text("index,x,y,z,views\n0,0,0,0,1\n1,0,1,0,0\n")
    effect = tmp_path / "effect.py"
    # Interrupt on the second frame, the way Ctrl-C would.
    effect.write_text(
        "def color(led, t):\n"
        "    if t > 0:\n"
        "        raise KeyboardInterrupt\n"
        "    return (255, 0, 128) if led.index == 0 else (0, 0, 0)\n"
    )
    return leds, effect


def test_stream_sends_scaled_frames_then_turns_leds_off(receiver, tmp_path, capsys):
    leds, effect = _stream_files(tmp_path)
    port = str(receiver.getsockname()[1])

    assert (
        main(["stream", str(effect), "--map", str(leds), "--host", "localhost", "--port", port])
        == 0
    )

    first, off = (receiver.recv(2048)[Header.SIZE :] for _ in range(2))
    assert first == bytes([64, 0, 32]) + bytes(3)
    assert off == bytes(6)
    err = capsys.readouterr().err
    assert "streaming effect.py (2 LEDs) to localhost (127.0.0.1); press Ctrl-C to stop" in err
    assert "stopped and turned the LEDs off" in err


@pytest.mark.parametrize(
    ("args", "match"),
    [
        ([], "stream needs --host, --preview, or both"),
        (["--host", "127.0.0.1", "--map", "missing.csv"], "can't read missing.csv"),
    ],
)
def test_stream_rejects_unusable_arguments(tmp_path, capsys, args, match):
    leds, effect = _stream_files(tmp_path)
    with pytest.raises(SystemExit) as exit_info:
        main(["stream", str(effect), "--map", str(leds), *args])
    assert exit_info.value.code == 2
    assert match in capsys.readouterr().err


def test_stream_rejects_a_missing_effect_file(tmp_path, capsys):
    leds, _ = _stream_files(tmp_path)
    with pytest.raises(SystemExit):
        main(["stream", "nope.py", "--map", str(leds), "--host", "127.0.0.1"])
    assert "can't find the effect file nope.py" in capsys.readouterr().err


def test_solve_rejects_a_missing_capture(tmp_path, capsys):
    with pytest.raises(SystemExit) as exit_info:
        main(["solve", str(tmp_path / "nope"), "--leds", "50"])
    assert exit_info.value.code == 2
    assert "can't find the capture directory" in capsys.readouterr().err


def test_solve_reports_a_directory_that_isnt_a_capture(tmp_path, capsys):
    assert main(["solve", str(tmp_path), "--leds", "50"]) == 1
    assert "missing odometry.csv; is this a Stray Scanner capture?" in capsys.readouterr().err
