import pytest

from firmament.codes import BITS, MAX_LEDS, WEIGHT, bit, code


def test_first_codes_match_spec():
    assert [code(i) for i in range(6)] == [63, 4032, 95, 4000, 111, 3984]


def test_every_code_has_weight_six():
    assert all(code(i).bit_count() == WEIGHT for i in range(MAX_LEDS))


def test_codes_are_unique():
    assert len({code(i) for i in range(MAX_LEDS)}) == MAX_LEDS


def test_codes_fit_in_twelve_bits():
    assert all(0 <= code(i) < 1 << BITS for i in range(MAX_LEDS))


@pytest.mark.parametrize("led_count", range(2, MAX_LEDS + 1))
def test_every_slot_lights_half_the_leds(led_count):
    for position in range(BITS):
        lit = sum(bit(i, position) for i in range(led_count))
        assert led_count // 2 <= lit <= -(-led_count // 2)


def test_bit_reads_the_code_least_significant_first():
    assert [bit(0, j) for j in range(BITS)] == [True] * 6 + [False] * 6


@pytest.mark.parametrize("index", [-1, MAX_LEDS])
def test_code_rejects_out_of_range_index(index):
    with pytest.raises(ValueError, match="LED index"):
        code(index)


@pytest.mark.parametrize("position", [-1, BITS])
def test_bit_rejects_out_of_range_position(position):
    with pytest.raises(ValueError, match="bit position"):
        bit(0, position)
