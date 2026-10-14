"""PMD (legacy MMD model) reader and writer.

PMD names are fixed 20-byte Shift-JIS fields; English names live in an
optional extension block. Unchanged names are written back verbatim so a
read/write cycle is byte-identical.
"""

from __future__ import annotations

from dataclasses import dataclass

from .binio import FormatError, Reader, Writer, decode_fixed, encode_fixed

NAME = 20


def _field_out(name: str, raw: bytes | None, size: int) -> bytes:
    if raw is not None and decode_fixed(raw) == name:
        return raw
    return encode_fixed(name, size)[0]


@dataclass
class PMDBone:
    name: str
    parent: int  # 0xFFFF = none
    tail: int
    kind: int
    ik_bone: int
    position: tuple[float, float, float]
    name_en: str = ""
    raw_name: bytes | None = None
    raw_name_en: bytes | None = None


@dataclass
class PMDMorph:
    name: str
    body: bytes
    name_en: str = ""
    raw_name: bytes | None = None
    raw_name_en: bytes | None = None


@dataclass
class PMDModel:
    head: bytes  # magic .. materials (model name/comment kept inside)
    name: str
    comment: str
    bones: list[PMDBone]
    ik_raw: bytes
    morphs: list[PMDMorph]
    display_raw: bytes  # morph display list, bone group names, bone display list
    group_count: int
    has_english: bool = False
    name_en: str = ""
    comment_en: str = ""
    raw_name_en: bytes | None = None
    raw_comment_en: bytes | None = None
    groups_en_raw: bytes = b""
    tail_raw: bytes = b""  # toon textures, rigid bodies, joints
    english_flag_present: bool = False

    @property
    def parent_index(self):
        return [(-1 if b.parent == 0xFFFF else b.parent) for b in self.bones]


def read_pmd(data: bytes) -> PMDModel:
    r = Reader(data)
    if r.read(3) != b"Pmd":
        raise FormatError("not a PMD file")
    r.f32()
    name = decode_fixed(r.read(20))
    comment = decode_fixed(r.read(256))
    r.skip(r.u32() * 38)
    r.skip(r.u32() * 2)
    r.skip(r.u32() * 70)
    head = data[:r.pos]

    bones = []
    for _ in range(r.u16()):
        raw = r.read(NAME)
        parent, tail, kind, ik = r.unpack("HHBH")
        pos = r.vec(3)
        bones.append(PMDBone(decode_fixed(raw), parent, tail, kind, ik, pos, raw_name=raw))

    s = r.pos
    for _ in range(r.u16()):
        r.skip(4)
        n = r.u8()
        r.skip(6 + 2 * n)
    ik_raw = data[s:r.pos]

    morphs = []
    for _ in range(r.u16()):
        raw = r.read(NAME)
        s = r.pos
        n = r.u32()
        r.skip(1 + 16 * n)
        morphs.append(PMDMorph(decode_fixed(raw), data[s:r.pos], raw_name=raw))

    s = r.pos
    r.skip(2 * r.u8())
    group_count = r.u8()
    r.skip(50 * group_count)
    r.skip(3 * r.u32())
    display_raw = data[s:r.pos]

    model = PMDModel(head, name, comment, bones, ik_raw, morphs, display_raw, group_count)
    if not r.eof():
        model.english_flag_present = True
        if r.u8() == 1:
            model.has_english = True
            model.raw_name_en = r.read(20)
            model.name_en = decode_fixed(model.raw_name_en)
            model.raw_comment_en = r.read(256)
            model.comment_en = decode_fixed(model.raw_comment_en)
            for b in bones:
                b.raw_name_en = r.read(NAME)
                b.name_en = decode_fixed(b.raw_name_en)
            for m in morphs[1:]:  # morph 0 is the implicit "base" morph
                m.raw_name_en = r.read(NAME)
                m.name_en = decode_fixed(m.raw_name_en)
            model.groups_en_raw = r.read(50 * group_count)
    model.tail_raw = data[r.pos:]
    return model


def write_pmd(m: PMDModel) -> bytes:
    w = Writer()
    w.write(m.head)
    w.u16(len(m.bones))
    for b in m.bones:
        w.write(_field_out(b.name, b.raw_name, NAME))
        w.pack("HHBH", b.parent, b.tail, b.kind, b.ik_bone)
        w.vec(b.position)
    w.write(m.ik_raw)
    w.u16(len(m.morphs))
    for mo in m.morphs:
        w.write(_field_out(mo.name, mo.raw_name, NAME))
        w.write(mo.body)
    w.write(m.display_raw)
    if m.has_english:
        w.u8(1)
        w.write(_field_out(m.name_en, m.raw_name_en, 20))
        w.write(_field_out(m.comment_en, m.raw_comment_en, 256))
        for b in m.bones:
            w.write(_field_out(b.name_en, b.raw_name_en, NAME))
        for mo in m.morphs[1:]:
            w.write(_field_out(mo.name_en, mo.raw_name_en, NAME))
        w.write(m.groups_en_raw or b"\x00" * (50 * m.group_count))
    elif m.english_flag_present:
        w.u8(0)
    w.write(m.tail_raw)
    return w.getvalue()


def enable_english(m: PMDModel) -> None:
    """Turn on the English extension block so English names can be stored."""
    m.has_english = True
    m.english_flag_present = True


def load_pmd(path) -> PMDModel:
    with open(path, "rb") as f:
        return read_pmd(f.read())


def save_pmd(model: PMDModel, path) -> None:
    with open(path, "wb") as f:
        f.write(write_pmd(model))
