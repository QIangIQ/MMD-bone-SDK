"""PMX 2.0 / 2.1 model reader and writer.

Only the parts needed for bone work are decoded into fields (bone hierarchy,
names of bones, morphs, materials, display frames, rigid bodies and joints).
Everything else is kept as raw bytes, so ``write(read(data)) == data`` holds
byte for byte and renaming touches nothing but the names.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .binio import FormatError, Reader, Writer

# Bone flags
BONE_TAIL_IS_BONE = 0x0001
BONE_ROTATABLE = 0x0002
BONE_MOVABLE = 0x0004
BONE_VISIBLE = 0x0008
BONE_ENABLED = 0x0010
BONE_IK = 0x0020
BONE_INHERIT_ROTATION = 0x0100
BONE_INHERIT_TRANSLATION = 0x0200
BONE_FIXED_AXIS = 0x0400
BONE_LOCAL_AXIS = 0x0800
BONE_PHYSICS_AFTER_DEFORM = 0x1000
BONE_EXTERNAL_PARENT = 0x2000


@dataclass
class NamedItem:
    """Any PMX element that starts with a local + universal name pair."""

    name: str
    name_en: str
    body: bytes  # the rest of the element, kept verbatim


@dataclass
class IKLink:
    bone: int
    limits: tuple[tuple[float, float, float], tuple[float, float, float]] | None = None


@dataclass
class Bone:
    name: str
    name_en: str
    position: tuple[float, float, float]
    parent: int
    layer: int
    flags: int
    tail_bone: int = -1
    tail_offset: tuple[float, float, float] | None = None
    inherit_parent: int = -1
    inherit_weight: float = 0.0
    fixed_axis: tuple[float, float, float] | None = None
    local_x: tuple[float, float, float] | None = None
    local_z: tuple[float, float, float] | None = None
    external_key: int | None = None
    ik_target: int = -1
    ik_loops: int = 0
    ik_limit: float = 0.0
    ik_links: list[IKLink] = field(default_factory=list)
    body: bytes = b""  # verbatim encoding of everything after the names

    @property
    def is_ik(self) -> bool:
        return bool(self.flags & BONE_IK)


@dataclass
class PMXModel:
    version: float
    encoding: int  # 0 = UTF-16LE, 1 = UTF-8
    additional_uv: int
    index_sizes: dict[str, int]
    name: str
    name_en: str
    comment: str
    comment_en: str
    vertices_raw: bytes
    faces_raw: bytes
    textures: list[str]
    materials: list[NamedItem]
    bones: list[Bone]
    morphs: list[NamedItem]
    display_frames: list[NamedItem]
    rigid_bodies: list[NamedItem]
    joints: list[NamedItem]
    tail_raw: bytes = b""  # soft bodies (PMX 2.1) and anything after
    header_raw: bytes = b""

    @property
    def text_encoding(self) -> str:
        return "utf-16-le" if self.encoding == 0 else "utf-8"

    def bone_index(self, name: str) -> int:
        for i, b in enumerate(self.bones):
            if b.name == name:
                return i
        return -1


_INDEX_KEYS = ("vertex", "texture", "material", "bone", "morph", "rigid")


class _PMXReader(Reader):
    def __init__(self, data: bytes):
        super().__init__(data)
        self.encoding = "utf-16-le"
        self.sizes: dict[str, int] = {}

    def text(self) -> str:
        n = self.i32()
        if n < 0:
            raise FormatError("negative text length")
        return self.read(n).decode(self.encoding, errors="replace")

    def index(self, kind: str) -> int:
        size = self.sizes[kind]
        if kind == "vertex":  # vertex indices are unsigned for 1 and 2 bytes
            return self.unpack({1: "B", 2: "H", 4: "i"}[size])[0]
        return self.unpack({1: "b", 2: "h", 4: "i"}[size])[0]


def _skip_text(r: _PMXReader) -> None:
    r.skip(r.i32())


def read_pmx(data: bytes) -> PMXModel:
    r = _PMXReader(data)
    if r.read(4) != b"PMX ":
        raise FormatError("not a PMX file")
    version = r.f32()
    nglobals = r.u8()
    globals_ = list(r.read(nglobals))
    if nglobals < 8:
        raise FormatError("PMX header too short")
    encoding, additional_uv = globals_[0], globals_[1]
    r.encoding = "utf-16-le" if encoding == 0 else "utf-8"
    r.sizes = dict(zip(_INDEX_KEYS, globals_[2:8]))
    header_raw = data[:r.pos]

    name, name_en, comment, comment_en = r.text(), r.text(), r.text(), r.text()

    # Vertices
    start = r.pos
    for _ in range(r.i32()):
        r.skip(4 * (3 + 3 + 2 + 4 * additional_uv))
        kind = r.u8()
        bsz = r.sizes["bone"]
        if kind == 0:
            r.skip(bsz)
        elif kind == 1:
            r.skip(2 * bsz + 4)
        elif kind in (2, 4):
            r.skip(4 * bsz + 16)
        elif kind == 3:
            r.skip(2 * bsz + 4 + 36)
        else:
            raise FormatError(f"unknown vertex weight type {kind}")
        r.skip(4)  # edge scale
    vertices_raw = data[start:r.pos]

    start = r.pos
    r.skip(r.i32() * r.sizes["vertex"])
    faces_raw = data[start:r.pos]

    textures = [r.text() for _ in range(r.i32())]

    materials = []
    for _ in range(r.i32()):
        mname, mname_en = r.text(), r.text()
        s = r.pos
        r.skip(4 * 4 + 4 * 3 + 4 + 4 * 3 + 1 + 4 * 4 + 4)
        r.skip(2 * r.sizes["texture"])
        r.skip(1)  # sphere mode
        if r.u8() == 0:
            r.skip(r.sizes["texture"])
        else:
            r.skip(1)
        _skip_text(r)  # memo
        r.skip(4)  # face count
        materials.append(NamedItem(mname, mname_en, data[s:r.pos]))

    bones = []
    for _ in range(r.i32()):
        bname, bname_en = r.text(), r.text()
        s = r.pos
        pos = r.vec(3)
        parent = r.index("bone")
        layer = r.i32()
        flags = r.u16()
        b = Bone(bname, bname_en, pos, parent, layer, flags)
        if flags & BONE_TAIL_IS_BONE:
            b.tail_bone = r.index("bone")
        else:
            b.tail_offset = r.vec(3)
        if flags & (BONE_INHERIT_ROTATION | BONE_INHERIT_TRANSLATION):
            b.inherit_parent = r.index("bone")
            b.inherit_weight = r.f32()
        if flags & BONE_FIXED_AXIS:
            b.fixed_axis = r.vec(3)
        if flags & BONE_LOCAL_AXIS:
            b.local_x = r.vec(3)
            b.local_z = r.vec(3)
        if flags & BONE_EXTERNAL_PARENT:
            b.external_key = r.i32()
        if flags & BONE_IK:
            b.ik_target = r.index("bone")
            b.ik_loops = r.i32()
            b.ik_limit = r.f32()
            for _ in range(r.i32()):
                link = IKLink(r.index("bone"))
                if r.u8():
                    link.limits = (r.vec(3), r.vec(3))
                b.ik_links.append(link)
        b.body = data[s:r.pos]
        bones.append(b)

    morphs = []
    for _ in range(r.i32()):
        mname, mname_en = r.text(), r.text()
        s = r.pos
        r.skip(1)  # panel
        kind = r.u8()
        count = r.i32()
        sz = r.sizes
        per = {
            0: sz["morph"] + 4,
            1: sz["vertex"] + 12,
            2: sz["bone"] + 28,
            3: sz["vertex"] + 16, 4: sz["vertex"] + 16, 5: sz["vertex"] + 16,
            6: sz["vertex"] + 16, 7: sz["vertex"] + 16,
            8: sz["material"] + 1 + 4 * (4 + 3 + 1 + 3 + 4 + 1 + 4 + 4 + 4),
            9: sz["morph"] + 4,
            10: sz["rigid"] + 1 + 24,
        }.get(kind)
        if per is None:
            raise FormatError(f"unknown morph type {kind}")
        r.skip(per * count)
        morphs.append(NamedItem(mname, mname_en, data[s:r.pos]))

    frames = []
    for _ in range(r.i32()):
        fname, fname_en = r.text(), r.text()
        s = r.pos
        r.skip(1)
        for _ in range(r.i32()):
            target = r.u8()
            r.skip(r.sizes["bone"] if target == 0 else r.sizes["morph"])
        frames.append(NamedItem(fname, fname_en, data[s:r.pos]))

    rigid = []
    for _ in range(r.i32()):
        rname, rname_en = r.text(), r.text()
        s = r.pos
        r.skip(r.sizes["bone"] + 1 + 2 + 1 + 36 + 20 + 1)
        rigid.append(NamedItem(rname, rname_en, data[s:r.pos]))

    joints = []
    for _ in range(r.i32()):
        jname, jname_en = r.text(), r.text()
        s = r.pos
        r.skip(1 + 2 * r.sizes["rigid"] + 4 * 3 * 8)
        joints.append(NamedItem(jname, jname_en, data[s:r.pos]))

    return PMXModel(
        version=version, encoding=encoding, additional_uv=additional_uv,
        index_sizes=dict(r.sizes), name=name, name_en=name_en, comment=comment,
        comment_en=comment_en, vertices_raw=vertices_raw, faces_raw=faces_raw,
        textures=textures, materials=materials, bones=bones, morphs=morphs,
        display_frames=frames, rigid_bodies=rigid, joints=joints,
        tail_raw=data[r.pos:], header_raw=header_raw,
    )


def write_pmx(model: PMXModel) -> bytes:
    enc = model.text_encoding
    w = Writer()

    def text(s: str) -> None:
        b = s.encode(enc)
        w.i32(len(b))
        w.write(b)

    w.write(model.header_raw)
    for s in (model.name, model.name_en, model.comment, model.comment_en):
        text(s)
    w.write(model.vertices_raw)
    w.write(model.faces_raw)
    w.i32(len(model.textures))
    for t in model.textures:
        text(t)
    for items in (model.materials, model.bones, model.morphs, model.display_frames,
                  model.rigid_bodies, model.joints):
        w.i32(len(items))
        for it in items:
            text(it.name)
            text(it.name_en)
            w.write(it.body)
    w.write(model.tail_raw)
    return w.getvalue()


def load_pmx(path) -> PMXModel:
    with open(path, "rb") as f:
        return read_pmx(f.read())


def save_pmx(model: PMXModel, path) -> None:
    with open(path, "wb") as f:
        f.write(write_pmx(model))
