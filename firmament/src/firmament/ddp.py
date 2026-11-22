"""A minimal DDP sender, matching what WLED's receiver accepts."""

import socket
import struct
from dataclasses import dataclass
from enum import IntFlag
from types import TracebackType
from typing import ClassVar, Self

PORT = 4048
RGB24 = 0x0B
DISPLAY = 1

# WLED's own sender uses this, and it's a whole number of RGB pixels (480).
MAX_DATA = 1440


class Flags(IntFlag):
    PUSH = 0x01
    VERSION_1 = 0x40


@dataclass(frozen=True)
class Header:
    flags: Flags
    sequence: int
    offset: int
    length: int
    data_type: int = RGB24
    destination: int = DISPLAY

    _FORMAT: ClassVar = struct.Struct(">BBBBIH")
    SIZE: ClassVar[int] = _FORMAT.size

    def pack(self) -> bytes:
        return self._FORMAT.pack(
            self.flags, self.sequence, self.data_type, self.destination, self.offset, self.length
        )

    @classmethod
    def unpack(cls, packet: bytes) -> Self:
        flags, sequence, data_type, destination, offset, length = cls._FORMAT.unpack_from(packet)
        return cls(Flags(flags), sequence, offset, length, data_type, destination)


def packets(frame: bytes, sequence: int) -> list[bytes]:
    """Split one RGB frame into DDP packets, with push set on the last."""
    if not frame or len(frame) % 3:
        raise ValueError(f"frame is {len(frame)} bytes; expected a nonzero multiple of 3")
    if not 1 <= sequence <= 15:
        raise ValueError(f"sequence {sequence} is outside 1 to 15")

    offsets = range(0, len(frame), MAX_DATA)
    result = []
    for offset in offsets:
        chunk = frame[offset : offset + MAX_DATA]
        flags = Flags.VERSION_1 | (Flags.PUSH if offset == offsets[-1] else 0)
        result.append(Header(flags, sequence, offset, len(chunk)).pack() + chunk)
    return result


class DdpSender:
    def __init__(self, host: str, port: int = PORT) -> None:
        results = socket.getaddrinfo(host, port, type=socket.SOCK_DGRAM)
        # Prefer IPv4: a hostname can resolve to IPv6 first, and WLED may not listen there.
        family, kind, proto, _, address = min(results, key=lambda r: r[0] != socket.AF_INET)
        self._socket = socket.socket(family, kind, proto)
        self._socket.connect(address)
        self._sequence = 0
        self.ip = str(address[0])

    def send(self, frame: bytes) -> None:
        self._sequence = self._sequence % 15 + 1
        for packet in packets(frame, self._sequence):
            self._socket.send(packet)

    def close(self) -> None:
        self._socket.close()

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.close()
