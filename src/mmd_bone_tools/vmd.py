"""VMD (MMD motion) reader and writer.

Bone and morph tracks are matched to a model purely by name, and VMD stores
those names in 15-byte Shift-JIS fields. That limit is why English renaming
needs care: ``"upper body2"`` fits, ``"left index finger 1"`` would not.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .binio import FormatError, Reader, Writer, decode_fixed, encode_fixed, encoded_len

BONE_NAME = 15
MORPH_NAME = 15
IK_NAME = 20
MAGIC_V2 = b"Vocaloid Motion Data 0002"
MAGIC_V1 = b"Vocaloid Motion Data file"


def _field_out(name: str, raw: bytes | None, size: int) -> tuple[bytes, bool]:
    if raw is not None and decode_fixed(raw) == name:
        return raw, False
    return encode_fixed(name, size)


@dataclass
class BoneFrame:
    name: str
    frame: int
    position: tuple[float, float, float]
    rotation: tuple[float, float, float, float]  # x, y, z, w
    interpolation: bytes = bytes(64)
    raw_name: bytes | None = None


@dataclass
class MorphFrame:
    name: str
    frame: int
    weight: float
    raw_name: bytes | None = None


@dataclass
class IKState:
    name: str
    enabled: bool
    raw_name: bytes | None = None


@dataclass
class IKFrame:
    frame: int
    visible: bool
    states: list[IKState]


@dataclass
class VMDMotion:
    model_name: str
    bones: list[BoneFrame] = field(default_factory=list)
    morphs: list[MorphFrame] = field(default_factory=list)
    camera_raw: bytes | None = None  # count + records, kept verbatim
    light_raw: bytes | None = None
    shadow_raw: bytes | None = None
    ik: list[IKFrame] | None = None
    trailing: bytes = b""
    header_raw: bytes = MAGIC_V2 + bytes(5)
    raw_model_name: bytes | None = None
    name_size: int = 20
    has_morph_section: bool = True
    # names that did not fit their field on the last write
    truncated: list[str] = field(default_factory=list)

    def bone_names(self) -> list[str]:
        seen: dict[str, None] = {}
        for f in self.bones:
            seen.setdefault(f.name)
        return list(seen)

    def morph_names(self) -> list[str]:
        seen: dict[str, None] = {}
        for f in self.morphs:
            seen.setdefault(f.name)
        return list(seen)


def _fixed_section(r: Reader, size: int) -> bytes | None:
    if r.eof():
        return None
    s = r.pos
    n = r.u32()
    r.skip(n * size)
    return r.data[s:r.pos]


def read_vmd(data: bytes) -> VMDMotion:
    r = Reader(data)
    header = r.read(30)
    if header.startswith(MAGIC_V2):
        name_size = 20
    elif header.startswith(MAGIC_V1):
        name_size = 10
    else:
        raise FormatError("not a VMD file")
    raw_name = r.read(name_size)
    m = VMDMotion(decode_fixed(raw_name), header_raw=header, raw_model_name=raw_name,
                  name_size=name_size)

    if r.eof():
        return m
    for _ in range(r.u32()):
        raw = r.read(BONE_NAME)
        frame = r.u32()
        pos = r.vec(3)
        rot = r.vec(4)
        interp = r.read(64)
        m.bones.append(BoneFrame(decode_fixed(raw), frame, pos, rot, interp, raw))

    if r.eof():
        m.has_morph_section = bool(m.morphs)
        return m
    for _ in range(r.u32()):
        raw = r.read(MORPH_NAME)
        frame = r.u32()
        weight = r.f32()
        m.morphs.append(MorphFrame(decode_fixed(raw), frame, weight, raw))

    m.camera_raw = _fixed_section(r, 61)
    m.light_raw = _fixed_section(r, 28)
    m.shadow_raw = _fixed_section(r, 9)
    if not r.eof():
        try:
            save = r.pos
            frames = []
            for _ in range(r.u32()):
                frame = r.u32()
                visible = bool(r.u8())
                states = []
                for _ in range(r.u32()):
                    raw = r.read(IK_NAME)
                    states.append(IKState(decode_fixed(raw), bool(r.u8()), raw))
                frames.append(IKFrame(frame, visible, states))
            m.ik = frames
        except FormatError:
            r.pos = save
    m.trailing = data[r.pos:]
    return m


def write_vmd(m: VMDMotion) -> bytes:
    w = Writer()
    truncated: list[str] = []

    def name_field(name, raw, size):
        b, cut = _field_out(name, raw, size)
        if cut and name not in truncated:
            truncated.append(name)
        w.write(b)

    w.write(m.header_raw)
    name_field(m.model_name, m.raw_model_name, m.name_size)
    w.u32(len(m.bones))
    for f in m.bones:
        name_field(f.name, f.raw_name, BONE_NAME)
        w.u32(f.frame)
        w.vec(f.position)
        w.vec(f.rotation)
        w.write(f.interpolation)
    if m.has_morph_section or m.morphs or m.camera_raw is not None or m.ik is not None:
        w.u32(len(m.morphs))
    for f in m.morphs:
        name_field(f.name, f.raw_name, MORPH_NAME)
        w.u32(f.frame)
        w.f32(f.weight)
    for raw in (m.camera_raw, m.light_raw, m.shadow_raw):
        if raw is None:
            if m.ik is None and not m.trailing:
                break
            raw = b"\x00\x00\x00\x00"
        w.write(raw)
    if m.ik is not None:
        w.u32(len(m.ik))
        for f in m.ik:
            w.u32(f.frame)
            w.u8(1 if f.visible else 0)
            w.u32(len(f.states))
            for st in f.states:
                name_field(st.name, st.raw_name, IK_NAME)
                w.u8(1 if st.enabled else 0)
    w.write(m.trailing)
    m.truncated = truncated
    return w.getvalue()


def fits_bone_field(name: str) -> bool:
    return encoded_len(name) <= BONE_NAME


def load_vmd(path) -> VMDMotion:
    with open(path, "rb") as f:
        return read_vmd(f.read())


def save_vmd(motion: VMDMotion, path) -> list[str]:
    data = write_vmd(motion)
    with open(path, "wb") as f:
        f.write(data)
    return motion.truncated
