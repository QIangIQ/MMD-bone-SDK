"""Format-independent access to PMX and PMD models."""

from __future__ import annotations

import os
from dataclasses import dataclass

from .binio import FormatError
from .pmd import PMDModel, enable_english, read_pmd, write_pmd
from .pmx import PMXModel, read_pmx, write_pmx

Model = PMXModel | PMDModel


@dataclass
class Skeleton:
    names: list[str]
    parents: list[int]
    heads: list[tuple[float, float, float]]
    tails: list[tuple[float, float, float] | None]  # world-space tail point

    def index(self, name: str) -> int:
        try:
            return self.names.index(name)
        except ValueError:
            return -1

    def direction(self, i: int):
        t = self.tails[i]
        if t is None:
            return None
        h = self.heads[i]
        v = (t[0] - h[0], t[1] - h[1], t[2] - h[2])
        return v if any(abs(c) > 1e-6 for c in v) else None

    def children(self, i: int) -> list[int]:
        return [j for j, p in enumerate(self.parents) if p == i]


def read_model(data: bytes) -> Model:
    if data[:4] == b"PMX ":
        return read_pmx(data)
    if data[:3] == b"Pmd":
        return read_pmd(data)
    raise FormatError("not a PMX or PMD model")


def write_model(model: Model) -> bytes:
    return write_pmx(model) if isinstance(model, PMXModel) else write_pmd(model)


def load_model(path: str | os.PathLike) -> Model:
    with open(path, "rb") as f:
        return read_model(f.read())


def save_model(model: Model, path: str | os.PathLike) -> None:
    with open(path, "wb") as f:
        f.write(write_model(model))


def skeleton(model: Model) -> Skeleton:
    names = [b.name for b in model.bones]
    heads = [tuple(b.position) for b in model.bones]
    tails: list = []
    if isinstance(model, PMXModel):
        parents = [b.parent for b in model.bones]
        for b in model.bones:
            if b.tail_offset is not None:
                tails.append(tuple(h + o for h, o in zip(b.position, b.tail_offset)))
            elif 0 <= b.tail_bone < len(model.bones):
                tails.append(tuple(model.bones[b.tail_bone].position))
            else:
                tails.append(None)
    else:
        parents = model.parent_index
        for i, b in enumerate(model.bones):
            ok = 0 < b.tail < len(model.bones) and b.tail != i
            tails.append(tuple(model.bones[b.tail].position) if ok else None)
    return Skeleton(names, parents, heads, tails)


def bone_names(model: Model) -> list[str]:
    return [b.name for b in model.bones]


def set_english_names(model: Model) -> None:
    """Make sure the model can store English names (PMD needs an extension block)."""
    if isinstance(model, PMDModel):
        enable_english(model)


def named_sections(model: Model):
    """Yield (section, items) for every list of named items in the model."""
    yield "bones", model.bones
    yield "morphs", model.morphs
    if isinstance(model, PMXModel):
        yield "materials", model.materials
        yield "display_frames", model.display_frames
        yield "rigid_bodies", model.rigid_bodies
        yield "joints", model.joints
