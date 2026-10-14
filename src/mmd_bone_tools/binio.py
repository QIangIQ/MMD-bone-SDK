"""Little-endian binary reader/writer helpers shared by the PMX, PMD and VMD codecs."""

from __future__ import annotations

import struct

SJIS = "cp932"  # Shift-JIS as written by MMD on Windows


class FormatError(ValueError):
    """Raised when a file does not match the expected binary layout."""


class Reader:
    def __init__(self, data: bytes):
        self.data = data
        self.pos = 0

    def remaining(self) -> int:
        return len(self.data) - self.pos

    def eof(self) -> bool:
        return self.pos >= len(self.data)

    def read(self, n: int) -> bytes:
        if n < 0 or self.pos + n > len(self.data):
            raise FormatError(f"unexpected end of file at offset {self.pos} (wanted {n} bytes)")
        b = self.data[self.pos:self.pos + n]
        self.pos += n
        return b

    def skip(self, n: int) -> None:
        self.read(n)

    def unpack(self, fmt: str):
        size = struct.calcsize("<" + fmt)
        return struct.unpack("<" + fmt, self.read(size))

    def u8(self) -> int:
        return self.unpack("B")[0]

    def u16(self) -> int:
        return self.unpack("H")[0]

    def i32(self) -> int:
        return self.unpack("i")[0]

    def u32(self) -> int:
        return self.unpack("I")[0]

    def f32(self) -> float:
        return self.unpack("f")[0]

    def vec(self, n: int) -> tuple[float, ...]:
        return self.unpack(f"{n}f")


class Writer:
    def __init__(self):
        self.parts: list[bytes] = []

    def write(self, b: bytes) -> None:
        self.parts.append(bytes(b))

    def pack(self, fmt: str, *values) -> None:
        self.parts.append(struct.pack("<" + fmt, *values))

    def u8(self, v: int) -> None:
        self.pack("B", v)

    def u16(self, v: int) -> None:
        self.pack("H", v)

    def i32(self, v: int) -> None:
        self.pack("i", v)

    def u32(self, v: int) -> None:
        self.pack("I", v)

    def f32(self, v: float) -> None:
        self.pack("f", v)

    def vec(self, values) -> None:
        self.pack(f"{len(values)}f", *values)

    def getvalue(self) -> bytes:
        return b"".join(self.parts)


def decode_fixed(raw: bytes, encoding: str = SJIS) -> str:
    """Decode a NUL-terminated fixed-width string field (PMD/VMD)."""
    end = raw.find(b"\x00")
    if end >= 0:
        raw = raw[:end]
    # Truncated multi-byte characters at the end of a field are common in VMD
    # files, so decode leniently and drop a dangling lead byte.
    return raw.decode(encoding, errors="ignore")


def encode_fixed(text: str, size: int, encoding: str = SJIS) -> tuple[bytes, bool]:
    """Encode text into a fixed-width NUL-padded field.

    Returns (field_bytes, truncated). Truncation never splits a multi-byte
    character, so the result always decodes cleanly.
    """
    out = bytearray()
    truncated = False
    for ch in text:
        try:
            enc = ch.encode(encoding)
        except UnicodeEncodeError:
            enc = b"?"
        if len(out) + len(enc) > size:
            truncated = True
            break
        out += enc
    return bytes(out) + b"\x00" * (size - len(out)), truncated


def encoded_len(text: str, encoding: str = SJIS) -> int:
    return len(text.encode(encoding, errors="replace"))
