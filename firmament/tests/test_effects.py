import os

import pytest

from firmament.effects import EffectError, LiveEffect, load, render, scale
from firmament.positions import Led

LEDS = [Led(0, 0.0, 0.0, 0.0, 1), Led(1, 0.0, 1.0, 0.0, 0)]


def _effect(tmp_path, source, name="effect.py"):
    path = tmp_path / name
    path.write_text(source)
    return path


def _save(path, source):
    """Rewrite the file with a newer mtime, as an editor's save would."""
    stat = path.stat()
    path.write_text(source)
    os.utime(path, ns=(stat.st_atime_ns, stat.st_mtime_ns + 1_000_000_000))


def test_renders_each_led_from_its_position_and_time(tmp_path):
    color = load(_effect(tmp_path, "def color(led, t):\n    return (led.index, led.y * 100, t)\n"))
    assert render(color, LEDS, 7.0, tmp_path) == bytes([0, 0, 7, 1, 100, 7])


def test_clamps_and_rounds_channels(tmp_path):
    color = load(_effect(tmp_path, "def color(led, t):\n    return [-5, 300, 12.6]\n"))
    assert render(color, LEDS[:1], 0, tmp_path) == bytes([0, 255, 13])


@pytest.mark.parametrize(
    ("returned", "match"),
    [
        ("None", "expected \\(r, g, b\\)"),
        ("(1, 2)", "expected \\(r, g, b\\)"),
        ("'abc'", "expected \\(r, g, b\\)"),
        ("(1, 2, 'x')", "expected numbers"),
        ("(1, 2, float('nan'))", "expected numbers"),
        ("(1, 2, True)", "expected numbers"),
    ],
)
def test_rejects_values_that_arent_colors(tmp_path, returned, match):
    color = load(_effect(tmp_path, f"def color(led, t):\n    return {returned}\n"))
    with pytest.raises(EffectError, match=f"for LED 0; {match}"):
        render(color, LEDS, 0, tmp_path)


def test_reports_the_effect_files_line_for_an_error(tmp_path):
    path = _effect(tmp_path, "def color(led, t):\n    return 1 / 0\n")
    with pytest.raises(EffectError, match="effect.py:2: ZeroDivisionError"):
        render(load(path), LEDS, 0, path)


@pytest.mark.parametrize(
    ("source", "match"),
    [
        ("def color(led, t)\n", "effect.py:1: SyntaxError"),
        ("x = 1\n\nraise RuntimeError('boom')\n", "effect.py:3: RuntimeError: boom"),
        ("def colour(led, t):\n    return (0, 0, 0)\n", "doesn't define color\\(led, t\\)"),
    ],
)
def test_load_rejects_broken_files(tmp_path, source, match):
    with pytest.raises(EffectError, match=match):
        load(_effect(tmp_path, source))


def test_scale_applies_brightness():
    assert scale(bytes([255, 128, 0]), 64) == bytes([64, 32, 0])


class TestLiveEffect:
    def test_reloads_when_the_file_changes(self, tmp_path):
        path = _effect(tmp_path, "def color(led, t):\n    return (1, 1, 1)\n")
        reports: list[str] = []
        live = LiveEffect(path, reports.append)
        assert live.frame(LEDS, 0) == bytes([1] * 6)
        _save(path, "def color(led, t):\n    return (2, 2, 2)\n")
        assert live.frame(LEDS, 0) == bytes([2] * 6)
        assert reports == ["reloaded effect.py"]

    def test_keeps_playing_when_a_save_doesnt_load(self, tmp_path):
        path = _effect(tmp_path, "def color(led, t):\n    return (1, 1, 1)\n")
        reports: list[str] = []
        live = LiveEffect(path, reports.append)
        live.frame(LEDS, 0)
        _save(path, "def color(led, t)\n")
        assert live.frame(LEDS, 0) == bytes([1] * 6)
        assert live.frame(LEDS, 0) == bytes([1] * 6)
        assert reports == ["effect.py:1: SyntaxError: expected ':'; keeping the current version"]

    def test_goes_back_to_the_last_working_version_when_a_save_fails_to_render(self, tmp_path):
        path = _effect(tmp_path, "def color(led, t):\n    return (1, 1, 1)\n")
        reports: list[str] = []
        live = LiveEffect(path, reports.append)
        live.frame(LEDS, 0)
        _save(path, "def color(led, t):\n    return led.w\n")
        assert live.frame(LEDS, 0) == bytes([1] * 6)
        assert live.frame(LEDS, 0) == bytes([1] * 6)
        assert len(reports) == 2
        assert "effect.py:2: AttributeError" in reports[1]
        assert reports[1].endswith("going back to the last version that worked")

    def test_shows_black_until_the_file_changes_when_nothing_works(self, tmp_path):
        path = _effect(tmp_path, "def color(led, t):\n    return (1, 1, 1) if t < 1 else None\n")
        reports: list[str] = []
        live = LiveEffect(path, reports.append)
        assert live.frame(LEDS, 0) == bytes([1] * 6)
        assert live.frame(LEDS, 1) == bytes(6)
        assert live.frame(LEDS, 2) == bytes(6)
        assert len(reports) == 1
        assert reports[0].endswith("showing black until the file changes")
        _save(path, "def color(led, t):\n    return (3, 3, 3)\n")
        assert live.frame(LEDS, 3) == bytes([3] * 6)

    def test_starts_black_when_the_first_load_fails(self, tmp_path):
        reports: list[str] = []
        live = LiveEffect(_effect(tmp_path, "def color(\n"), reports.append)
        assert live.frame(LEDS, 0) == bytes(6)
        assert len(reports) == 1
        assert "keeping" not in reports[0]
