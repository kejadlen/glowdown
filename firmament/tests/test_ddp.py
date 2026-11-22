import socket

import pytest

from firmament.ddp import MAX_DATA, DdpSender, Flags, Header, packets

PUSHED = Flags.VERSION_1 | Flags.PUSH


def test_header_packs_to_wled_layout():
    packed = Header(PUSHED, 3, offset=1440, length=180).pack()
    assert packed == bytes([0x41, 3, 0x0B, 1, 0, 0, 0x05, 0xA0, 0, 180])


def test_header_round_trips():
    header = Header(Flags.VERSION_1, 9, offset=3, length=6)
    assert Header.unpack(header.pack()) == header


def test_small_frame_is_one_pushed_packet():
    frame = bytes(range(9))
    [packet] = packets(frame, 1)
    assert Header.unpack(packet) == Header(PUSHED, 1, offset=0, length=9)
    assert packet[Header.SIZE :] == frame


def test_large_frame_splits_on_pixel_boundaries_and_pushes_last():
    frame = bytes(i % 256 for i in range(1500))
    first, second = packets(frame, 7)
    assert Header.unpack(first) == Header(Flags.VERSION_1, 7, offset=0, length=MAX_DATA)
    assert Header.unpack(second) == Header(PUSHED, 7, offset=MAX_DATA, length=1500 - MAX_DATA)
    assert first[Header.SIZE :] + second[Header.SIZE :] == frame


def test_exact_multiple_of_max_data_has_no_empty_packet():
    assert len(packets(bytes(MAX_DATA * 2), 1)) == 2


@pytest.mark.parametrize("length", [0, 4])
def test_rejects_frames_that_are_not_whole_pixels(length):
    with pytest.raises(ValueError, match="multiple of 3"):
        packets(bytes(length), 1)


@pytest.mark.parametrize("sequence", [0, 16])
def test_rejects_sequence_outside_four_bits(sequence):
    with pytest.raises(ValueError, match="sequence"):
        packets(bytes(3), sequence)


def test_sender_delivers_packets_and_cycles_sequence_from_one_to_fifteen():
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as receiver:
        receiver.bind(("127.0.0.1", 0))
        receiver.settimeout(1)
        port = receiver.getsockname()[1]
        with DdpSender("127.0.0.1", port) as sender:
            for _ in range(16):
                sender.send(bytes(3))
            sequences = [Header.unpack(receiver.recv(2048)).sequence for _ in range(16)]
    assert sequences == [*range(1, 16), 1]
