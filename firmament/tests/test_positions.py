import pytest

from firmament.positions import Led, read_leds


def _write(tmp_path, text):
    path = tmp_path / "leds.csv"
    path.write_text(text)
    return path


def test_reads_each_led_in_order(tmp_path):
    path = _write(tmp_path, "index,x,y,z,views\n0,0.1,0.2,0.3,2\n1,-1,0,1.5,0\n")
    assert read_leds(path) == [Led(0, 0.1, 0.2, 0.3, 2), Led(1, -1.0, 0.0, 1.5, 0)]


def test_finds_columns_by_name_and_ignores_extras(tmp_path):
    path = _write(tmp_path, "views,confidence,z,y,x,index\n1,0.9,3,2,1,0\n0,0.1,6,5,4,1\n")
    assert read_leds(path) == [Led(0, 1.0, 2.0, 3.0, 1), Led(1, 4.0, 5.0, 6.0, 0)]


@pytest.mark.parametrize(
    ("text", "match"),
    [
        ("index,x,y,views\n0,1,2,0\n1,1,2,0\n", "missing column z"),
        ("index,x,y,z,views\n0,0,0,0,0\n2,0,0,0,0\n", "expected LED 1 next, found 2"),
        ("index,x,y,z,views\n0,0,0,0,0\n0,0,0,0,0\n", "expected LED 1 next, found 0"),
        ("index,x,y,z,views\n0,0,0,0,0\n1,a,0,0,0\n", "line 3: expected whole numbers"),
        ("index,x,y,z,views\n0,0,0,0,0\n1,0,0,0\n", "line 3: expected whole numbers"),
        ("index,x,y,z,views\n0,0,0,0,0\n1,0,nan,0,0\n", "line 3: x, y, and z must be finite"),
        ("index,x,y,z,views\n0,0,0,0,-1\n1,0,0,0,0\n", "line 2: views must be 0 or more"),
        ("index,x,y,z,views\n0,0,0,0,0\n", "1 LEDs is outside 2 to 500"),
        ("", "missing column index"),
    ],
)
def test_rejects_malformed_files(tmp_path, text, match):
    with pytest.raises(ValueError, match=match):
        read_leds(_write(tmp_path, text))
