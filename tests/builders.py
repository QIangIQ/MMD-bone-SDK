"""Build small PMX / PMD / VMD files byte by byte, independent of the codecs."""

from __future__ import annotations

import struct

from mmd_bone_tools.binio import encode_fixed


def _p(fmt, *v):
    return struct.pack("<" + fmt, *v)


def _idx(size, v, unsigned=False):
    if unsigned:
        return _p({1: "B", 2: "H", 4: "i"}[size], v)
    return _p({1: "b", 2: "h", 4: "i"}[size], v)


# Each bone: (name, name_en, position, parent, tail) where tail is a bone index
# or an offset tuple. A dict may add "ik": (target, [links]) and "inherit".
HUMANOID = [
    ("全ての親", "", (0, 0, 0), -1, (0, 1, 0)),
    ("センター", "", (0, 8, 0), 0, (0, -1, 0)),
    ("上半身", "", (0, 10, 0), 1, 3),
    ("首", "", (0, 15, 0), 2, 4),
    ("頭", "", (0, 16, 0), 3, (0, 1, 0)),
    ("左肩", "", (0.5, 14.5, 0), 2, 6),
    ("左腕", "", (1.5, 14, 0), 5, 7),
    ("左ひじ", "", (4, 11.5, 0), 6, 8),
    ("左手首", "", (6.5, 9, 0), 7, (0.5, -0.5, 0)),
    ("下半身", "", (0, 10, 0), 1, (0, -1, 0)),
    ("左足", "", (1, 9, 0), 9, 11),
    ("左ひざ", "", (1, 5, 0), 10, 12),
    ("左足首", "", (1, 1, 0), 11, (0, -1, -1)),
    ("左足ＩＫ", "", (1, 1, 0), 0, (0, 0, 1)),
    ("左髪１", "", (0.5, 16, -0.5), 4, (0, -1, 0)),
    ("右スカート前２", "", (-0.5, 8, 0.5), 9, (0, -1, 0)),
]


def build_pmx(bones=HUMANOID, *, utf8=False, sizes=(2, 1, 1, 2, 1, 1), version=2.0,
              soft_body_tail=b""):
    vsz, tsz, msz, bsz, mosz, rsz = sizes
    enc = "utf-8" if utf8 else "utf-16-le"

    def text(s):
        b = s.encode(enc)
        return _p("i", len(b)) + b

    out = b"PMX " + _p("f", version) + bytes([8, 1 if utf8 else 0, 1, vsz, tsz, msz, bsz, mosz, rsz])
    out += text("テストモデル") + text("Test model") + text("コメント") + text("comment")
    # vertices: one of each weight type, one additional vec4
    verts = []
    for kind in (0, 1, 2, 3):
        v = _p("8f", 0, 1, 2, 0, 1, 0, 0.5, 0.5) + _p("4f", 1, 2, 3, 4) + bytes([kind])
        if kind == 0:
            v += _idx(bsz, 2)
        elif kind == 1:
            v += _idx(bsz, 2) + _idx(bsz, 3) + _p("f", 0.25)
        elif kind == 2:
            v += b"".join(_idx(bsz, i) for i in (1, 2, 3, 4)) + _p("4f", 0.1, 0.2, 0.3, 0.4)
        else:
            v += _idx(bsz, 6) + _idx(bsz, 7) + _p("f", 0.5) + _p("9f", *range(9))
        v += _p("f", 1.0)
        verts.append(v)
    out += _p("i", len(verts)) + b"".join(verts)
    out += _p("i", 6) + b"".join(_idx(vsz, i, unsigned=True) for i in (0, 1, 2, 1, 2, 3))
    out += _p("i", 2) + text("tex/肌.png") + text("toon.bmp")
    # materials: one with shared toon, one with texture toon
    for shared in (1, 0):
        out_m = text("肌" if shared else "髪") + text("")
        out_m += _p("4f", 1, 1, 1, 1) + _p("3f", 0, 0, 0) + _p("f", 5) + _p("3f", .5, .5, .5)
        out_m += bytes([0x10]) + _p("4f", 0, 0, 0, 1) + _p("f", 1)
        out_m += _idx(tsz, 0) + _idx(tsz, -1) + bytes([0])
        out_m += bytes([shared]) + (bytes([3]) if shared else _idx(tsz, 1))
        out_m += text("メモ") + _p("i", 3)
        if shared:
            mats = out_m
        else:
            mats += out_m
    out += _p("i", 2) + mats
    # bones
    out += _p("i", len(bones))
    for name, name_en, pos, parent, tail in bones:
        flags = 0x0002 | 0x0008 | 0x0010
        if isinstance(tail, int):
            flags |= 0x0001
        extra = b""
        if "ＩＫ" in name or "IK" in name:
            flags |= 0x0020 | 0x0004
        if name == "左髪１":
            flags |= 0x0100 | 0x0400 | 0x0800 | 0x2000
        b = text(name) + text(name_en) + _p("3f", *pos) + _idx(bsz, parent) + _p("i", 0)
        b += _p("H", flags)
        b += _idx(bsz, tail) if isinstance(tail, int) else _p("3f", *tail)
        if flags & 0x0100:
            b += _idx(bsz, 4) + _p("f", 0.5)
        if flags & 0x0400:
            b += _p("3f", 1, 0, 0)
        if flags & 0x0800:
            b += _p("6f", 1, 0, 0, 0, 0, 1)
        if flags & 0x2000:
            b += _p("i", 7)
        if flags & 0x0020:
            b += _idx(bsz, 12) + _p("i", 40) + _p("f", 2.0) + _p("i", 2)
            b += _idx(bsz, 11) + bytes([1]) + _p("6f", -3.14, 0, 0, -0.01, 0, 0)
            b += _idx(bsz, 10) + bytes([0])
        out += b + extra
    # morphs: group, vertex, bone, uv, material
    morphs = []
    morphs.append(text("まばたき") + text("") + bytes([1, 1]) + _p("i", 1) + _idx(vsz, 0, True) + _p("3f", 0, .1, 0))
    morphs.append(text("あ") + text("") + bytes([3, 0]) + _p("i", 1) + _idx(mosz, 0) + _p("f", 1))
    morphs.append(text("骨") + text("") + bytes([4, 2]) + _p("i", 1) + _idx(bsz, 4) + _p("7f", 0, 0, 0, 0, 0, 0, 1))
    morphs.append(text("UV") + text("") + bytes([4, 3]) + _p("i", 1) + _idx(vsz, 1, True) + _p("4f", 1, 1, 0, 0))
    morphs.append(text("照れ") + text("") + bytes([4, 8]) + _p("i", 1) + _idx(msz, 0) + bytes([0]) + _p("28f", *range(28)))
    out += _p("i", len(morphs)) + b"".join(morphs)
    out += _p("i", 2)
    out += text("Root") + text("Root") + bytes([1]) + _p("i", 1) + bytes([0]) + _idx(bsz, 0)
    out += text("表情") + text("Exp") + bytes([1]) + _p("i", 2) + bytes([1]) + _idx(mosz, 0) + bytes([1]) + _idx(mosz, 1)
    out += _p("i", 1) + text("髪剛体") + text("") + _idx(bsz, 14) + bytes([1]) + _p("H", 0xFFFF)
    out += bytes([0]) + _p("9f", *range(9)) + _p("5f", 1, .5, .5, 0, .5) + bytes([1])
    out += _p("i", 1) + text("髪ジョイント") + text("") + bytes([0]) + _idx(rsz, 0) + _idx(rsz, -1)
    out += _p("24f", *range(24))
    return out + soft_body_tail


PMD_HUMANOID = [(n, pos, parent) for n, _, pos, parent, _ in HUMANOID]


def build_pmd(bones=PMD_HUMANOID, english=True, physics=True):
    out = b"Pmd" + _p("f", 1.0) + encode_fixed("テスト", 20)[0] + encode_fixed("コメント", 256)[0]
    out += _p("I", 1) + _p("8f", 0, 0, 0, 0, 1, 0, 0, 0) + _p("HH", 0, 1) + bytes([100, 0])
    out += _p("I", 3) + _p("3H", 0, 0, 0)
    out += _p("I", 1) + _p("4f", 1, 1, 1, 1) + _p("f", 5) + _p("6f", 0, 0, 0, .5, .5, .5)
    out += bytes([0, 1]) + _p("I", 3) + encode_fixed("tex.bmp", 20)[0]
    out += _p("H", len(bones))
    for i, (name, pos, parent) in enumerate(bones):
        tail = i + 1 if i + 1 < len(bones) else 0
        out += encode_fixed(name, 20)[0] + _p("HHBH", 0xFFFF if parent < 0 else parent, tail, 0, 0)
        out += _p("3f", *pos)
    out += _p("H", 1) + _p("HHBHf", 13, 12, 2, 40, 1.0) + _p("2H", 11, 10)
    out += _p("H", 2)
    out += encode_fixed("base", 20)[0] + _p("I", 1) + bytes([0]) + _p("I", 0) + _p("3f", 0, 0, 0)
    out += encode_fixed("まばたき", 20)[0] + _p("I", 1) + bytes([1]) + _p("I", 0) + _p("3f", 0, .1, 0)
    out += bytes([1]) + _p("H", 1)
    out += bytes([1]) + encode_fixed("体\n", 50)[0]
    out += _p("I", 2) + _p("HB", 1, 1) + _p("HB", 2, 1)
    if english:
        out += bytes([1]) + encode_fixed("test", 20)[0] + encode_fixed("comment", 256)[0]
        out += b"".join(encode_fixed("", 20)[0] for _ in bones)
        out += encode_fixed("", 20)[0]
        out += encode_fixed("Body", 50)[0]
    if physics:
        out += b"".join(encode_fixed(f"toon{i:02d}.bmp", 100)[0] for i in range(1, 11))
        out += _p("I", 1) + encode_fixed("剛体", 20)[0] + bytes(63)
        out += _p("I", 0)
    return out


def vmd_bone(name, frame, pos=(0, 0, 0), rot=(0, 0, 0, 1), garbage=False):
    raw = encode_fixed(name, 15)[0]
    if garbage:  # MMD pads names with 0xFD after the NUL terminator
        n = raw.find(b"\x00")
        raw = raw[:n + 1] + b"\xfd" * (15 - n - 1) if n >= 0 and n < 14 else raw
    return raw + _p("I", frame) + _p("3f", *pos) + _p("4f", *rot) + bytes(range(64))


def build_vmd(bones, morphs=(), *, camera=0, ik=None, model="テストモデル", sections="all"):
    out = b"Vocaloid Motion Data 0002\x00\x00\x00\x00\x00" + encode_fixed(model, 20)[0]
    out += _p("I", len(bones)) + b"".join(bones)
    if sections == "bones":
        return out
    out += _p("I", len(morphs)) + b"".join(
        encode_fixed(n, 15)[0] + _p("I", f) + _p("f", w) for n, f, w in morphs)
    if sections == "morphs":
        return out
    out += _p("I", camera) + bytes(61 * camera)
    out += _p("I", 1) + _p("I", 0) + _p("6f", .6, .6, .6, -.5, -1, .5)
    out += _p("I", 0)
    if ik is not None:
        out += _p("I", len(ik))
        for frame, states in ik:
            out += _p("I", frame) + bytes([1]) + _p("I", len(states))
            for n, on in states:
                out += encode_fixed(n, 20)[0] + bytes([on])
    return out
