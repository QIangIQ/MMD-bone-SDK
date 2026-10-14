"""High-level operations: translate, convert between conventions, retarget."""

from __future__ import annotations

import csv
import json
import os
from dataclasses import dataclass, field

from . import dictionary as d
from . import quat
from .binio import decode_fixed, encode_fixed, encoded_len
from .model import Model, named_sections, set_english_names, skeleton
from .pmd import PMDModel
from .translate import _has_japanese, translate_bone, translate_morph, translate_text
from .vmd import BONE_NAME, BoneFrame, VMDMotion

ENGLISH_STYLES = ("en", "blender")


@dataclass
class Report:
    renamed: list[tuple[str, str, str]] = field(default_factory=list)  # section, old, new
    untranslated: list[tuple[str, str, str]] = field(default_factory=list)  # section, old, best effort
    too_long: list[tuple[str, str]] = field(default_factory=list)  # section, name
    unmatched: list[str] = field(default_factory=list)  # motion tracks with no target bone
    missing: list[str] = field(default_factory=list)  # standard target bones the motion lacks
    notes: list[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {k: v for k, v in self.__dict__.items()}


# ------------------------------------------------------------ custom maps

def load_mapping(path: str | os.PathLike) -> dict[str, str]:
    """Load user overrides from JSON ({"old": "new"}) or a two-column CSV."""
    p = os.fspath(path)
    with open(p, encoding="utf-8-sig") as f:
        if p.lower().endswith(".json"):
            data = json.load(f)
            if not isinstance(data, dict):
                raise ValueError("mapping JSON must be an object of old -> new names")
            return {str(k): str(v) for k, v in data.items()}
        out = {}
        for row in csv.reader(f):
            if len(row) >= 2 and row[0] and not row[0].startswith("#"):
                out[row[0].strip()] = row[1].strip()
        return out


def _unique(names: list[str]) -> list[str]:
    seen: dict[str, int] = {}
    out = []
    for n in names:
        if n in seen:
            seen[n] += 1
            cand = f"{n}_{seen[n]}"
            while cand in seen:
                seen[n] += 1
                cand = f"{n}_{seen[n]}"
            seen[cand] = 0
            out.append(cand)
        else:
            seen[n] = 0
            out.append(n)
    return out


# -------------------------------------------------------------- translate

def _translator(section: str, style: str):
    if section == "bones":
        return lambda n: translate_bone(n, style)
    if section == "morphs":
        return translate_morph
    return translate_text


def _needs_english(current: str, overwrite: bool) -> bool:
    return overwrite or not current or _has_japanese(current)


def translate_model(model: Model, style: str = "en", *, rename: bool = False,
                    overwrite: bool = False, sections=("bones", "morphs", "materials",
                    "display_frames", "rigid_bodies", "joints"),
                    custom: dict[str, str] | None = None) -> Report:
    """Translate Japanese names in a model.

    By default the English (universal) name fields are filled in and the
    Japanese names are left alone, so Japanese motions still play. With
    ``rename=True`` the primary names are replaced too, which is what you want
    when the motions you use carry English bone names.
    """
    custom = custom or {}
    rep = Report()
    set_english_names(model)
    name_limit = 20 if isinstance(model, PMDModel) else None
    for section, items in named_sections(model):
        if section not in sections:
            continue
        tr = _translator(section, style)
        new_names = []
        for it in items:
            if it.name in custom:
                new_names.append(custom[it.name])
                continue
            t = tr(it.name)
            if not t.complete:
                rep.untranslated.append((section, it.name, t.result))
            new_names.append(t.result)
        new_names = _unique(new_names)
        for idx, (it, new) in enumerate(zip(items, new_names)):
            if isinstance(model, PMDModel) and section == "morphs" and idx == 0:
                continue  # implicit base morph has no English slot
            if rename:
                if new != it.name:
                    rep.renamed.append((section, it.name, new))
                if section == "bones" and encoded_len(new) > BONE_NAME:
                    rep.too_long.append((section, new))
                if _needs_english(it.name_en, overwrite):
                    it.name_en = new
                it.name = new
            elif _needs_english(it.name_en, overwrite):
                if it.name_en != new:
                    rep.renamed.append((section, it.name_en or it.name, new))
                it.name_en = new
            if name_limit and encoded_len(new) > name_limit:
                rep.too_long.append((section, new))
    if rename and isinstance(model, PMDModel):
        rep.notes.append("PMD names are limited to 20 bytes; longer names were truncated on save")
    return rep


def convert_model(model: Model, dst: str, src: str | None = None, *,
                  custom: dict[str, str] | None = None, translate_rest: bool = True) -> Report:
    """Rename bones to another naming convention (jp, en, blender, unity, vrm, mixamo).

    Standard humanoid bones are mapped through the canonical table. Other bones
    are translated to English when the target is an English-style convention,
    or left as they are.
    """
    custom = custom or {}
    rep = Report()
    src = src or d.detect_convention([b.name for b in model.bones])
    rep.notes.append(f"source convention: {src}")
    new_names = []
    for b in model.bones:
        if b.name in custom:
            new_names.append(custom[b.name])
            continue
        out = d.convert(b.name, dst, src) or d.convert(b.name, dst)
        if out is None:
            if translate_rest and dst != "jp":
                t = translate_bone(b.name, "blender" if dst == "blender" else "en")
                out = t.result
                if not t.complete:
                    rep.untranslated.append(("bones", b.name, out))
            else:
                out = b.name
        new_names.append(out)
    set_english_names(model)
    for b, new in zip(model.bones, _unique(new_names)):
        if new != b.name:
            rep.renamed.append(("bones", b.name, new))
            if dst != "jp" and (not b.name_en or d.lookup(b.name_en)):
                b.name_en = new
            b.name = new
        if encoded_len(new) > BONE_NAME:
            rep.too_long.append(("bones", new))
    return rep


def bone_map(model: Model, dst: str, src: str | None = None) -> dict[str, str]:
    """Return {model bone name: name in convention dst} for standard bones."""
    src = src or d.detect_convention([b.name for b in model.bones])
    out = {}
    for b in model.bones:
        n = d.convert(b.name, dst, src)
        if n:
            out[b.name] = n
    return out


# ----------------------------------------------------------------- motion

def _rename_tracks(motion: VMDMotion, fn) -> Report:
    rep = Report()
    cache: dict[str, str | None] = {}
    for kind, frames in (("bones", motion.bones), ("morphs", motion.morphs)):
        for f in frames:
            key = (kind, f.name)
            if key not in cache:
                cache[key] = fn(kind, f.name)
                new = cache[key]
                if new is not None and new != f.name:
                    rep.renamed.append((kind, f.name, new))
                    if encoded_len(new) > BONE_NAME:
                        rep.too_long.append((kind, new))
            new = cache[key]
            if new is not None:
                f.name = new
    if motion.ik:
        for fr in motion.ik:
            for st in fr.states:
                new = fn("bones", st.name)
                if new is not None:
                    st.name = new
    return rep


def translate_motion(motion: VMDMotion, style: str = "en",
                     custom: dict[str, str] | None = None) -> Report:
    """Rename a motion's bone and morph tracks from Japanese to English."""
    custom = custom or {}
    untranslated = []

    def fn(kind, name):
        if name in custom:
            return custom[name]
        t = translate_bone(name, style) if kind == "bones" else translate_morph(name)
        if not t.complete:
            untranslated.append((kind, name, t.result))
        return t.result

    rep = _rename_tracks(motion, fn)
    rep.untranslated = untranslated
    return rep


def convert_motion(motion: VMDMotion, dst: str, src: str | None = None,
                   custom: dict[str, str] | None = None) -> Report:
    """Rename a motion's bone tracks to another naming convention."""
    custom = custom or {}
    src = src or d.detect_convention(motion.bone_names())

    def fn(kind, name):
        if name in custom:
            return custom[name]
        if kind == "morphs":
            if dst == "jp":
                return d.MORPH_EN_JP.get(name, name)
            return translate_morph(name).result if dst in ENGLISH_STYLES else name
        return d.convert(name, dst, src) or name

    rep = _rename_tracks(motion, fn)
    rep.notes.append(f"source convention: {src}")
    return rep


def _truncated_key(name: str) -> str:
    return decode_fixed(encode_fixed(name, BONE_NAME)[0])


def match_tracks(track_names, target_names, motion_convention: str | None = None,
                 custom: dict[str, str] | None = None) -> dict[str, str]:
    """Map motion track names onto bone names of a target model.

    Tries, in order: custom overrides, exact name, the canonical bone table
    (so a JP motion finds ``arm_L`` or ``mixamorig:LeftArm``), the target's
    15-byte truncated names (long names are cut in VMD files), and finally the
    English translation of the track name.
    """
    custom = custom or {}
    targets = list(target_names)
    tset = set(targets)
    tconv = d.detect_convention(targets)
    mconv = motion_convention or d.detect_convention(track_names)
    by_canon: dict[str, str] = {}
    for t in targets:
        e = d.lookup(t, tconv) or d.lookup(t)
        if e and e.id not in by_canon:
            by_canon[e.id] = t
    by_trunc = {_truncated_key(t): t for t in targets}
    by_lower = {t.lower(): t for t in targets}

    out = {}
    for n in track_names:
        if n in custom and custom[n] in tset:
            out[n] = custom[n]
            continue
        if n in tset:
            out[n] = n
            continue
        e = d.lookup(n, mconv) or d.lookup(n)
        if e and e.id in by_canon:
            out[n] = by_canon[e.id]
            continue
        if n in by_trunc:
            out[n] = by_trunc[n]
            continue
        tr = translate_bone(n).result
        for cand in (tr, tr.lower(), translate_bone(n, "blender").result):
            hit = cand if cand in tset else by_lower.get(cand.lower())
            if hit:
                out[n] = hit
                break
    return out


def _rest_offsets(src_model: Model, dst_model: Model, mapping: dict[str, str]):
    """Per-target-bone rotation R_b taking the target rest direction onto the
    source rest direction (identity when they already agree)."""
    ss, ts = skeleton(src_model), skeleton(dst_model)
    inv = {v: k for k, v in mapping.items()}  # target -> source track name
    # also pair bones the motion does not animate, via the canonical table
    sconv, tconv = d.detect_convention(ss.names), d.detect_convention(ts.names)
    src_by_canon = {}
    for i, n in enumerate(ss.names):
        e = d.lookup(n, sconv)
        if e:
            src_by_canon.setdefault(e.id, i)
    own: dict[int, tuple] = {}
    for ti, tn in enumerate(ts.names):
        si = ss.index(inv[tn]) if tn in inv else -1
        if si < 0:
            e = d.lookup(tn, tconv)
            si = src_by_canon.get(e.id, -1) if e else -1
        if si < 0:
            continue
        dt, ds = ts.direction(ti), ss.direction(si)
        if dt is None or ds is None:
            continue
        r = quat.between(dt, ds)
        if quat.angle(r) > 0.0175:  # ignore differences under ~1 degree
            own[ti] = r
    memo: dict[int, tuple] = {}

    def R(i: int, depth: int = 0):
        if i < 0 or depth > 512:
            return quat.IDENTITY
        if i not in memo:
            memo[i] = own.get(i) or R(ts.parents[i], depth + 1)
        return memo[i]

    return ts, R


def leg_length(model: Model) -> float | None:
    sk = skeleton(model)
    conv = d.detect_convention(sk.names)
    idx = {}
    for i, n in enumerate(sk.names):
        e = d.lookup(n, conv)
        if e:
            idx.setdefault(e.id, i)
    for a, b in (("leg.L", "ankle.L"), ("leg.R", "ankle.R")):
        if a in idx and b in idx:
            pa, pb = sk.heads[idx[a]], sk.heads[idx[b]]
            return sum((x - y) ** 2 for x, y in zip(pa, pb)) ** 0.5
    return None


def retarget(motion: VMDMotion, target: Model, source: Model | None = None, *,
             scale: float | None = None, keep_unmatched: bool = False,
             custom: dict[str, str] | None = None) -> Report:
    """Make a motion play on ``target``.

    1. Every bone track is renamed to the matching bone of the target model.
    2. With a ``source`` model (the rig the motion was made for), rotations are
       corrected for rest-pose differences, e.g. an A-pose motion on a T-pose
       model: ``q' = R_parent^-1 * q * R_bone``.
    3. Translations are scaled by ``scale`` or, with a source model, by the
       ratio of leg lengths.
    """
    rep = Report()
    tnames = [b.name for b in target.bones]
    tracks = motion.bone_names()
    mapping = match_tracks(tracks, tnames, custom=custom)
    rep.unmatched = [n for n in tracks if n not in mapping]
    long_targets = sorted({t for t in mapping.values() if encoded_len(t) > BONE_NAME})
    if long_targets:
        rep.too_long = [("bones", t) for t in long_targets]
        rep.notes.append("some target bone names are longer than VMD's 15-byte limit, so MMD "
                         "cannot address them; rename the model's bones first (convert)")

    if source is not None:
        ts, R = _rest_offsets(source, target, mapping)
        corrected = 0
        for f in motion.bones:
            t = mapping.get(f.name)
            ti = ts.index(t) if t else -1
            if ti < 0:
                continue
            rb, rp = R(ti), R(ts.parents[ti])
            if quat.is_identity(rb) and quat.is_identity(rp):
                continue
            f.rotation = quat.normalize(quat.mul(quat.mul(quat.conj(rp), f.rotation), rb))
            corrected += 1
        # bones whose rest offset differs from their parent's need a constant
        # key even when the motion never animates them
        animated = {mapping[n] for n in tracks if n in mapping}
        added = []
        for ti, tn in enumerate(ts.names):
            if tn in animated:
                continue
            delta = quat.mul(quat.conj(R(ts.parents[ti])), R(ti))
            if not quat.is_identity(delta) and encoded_len(tn) <= BONE_NAME:
                motion.bones.append(BoneFrame(tn, 0, (0.0, 0.0, 0.0), quat.normalize(delta),
                                              _linear_interp()))
                added.append(tn)
        if corrected or added:
            rep.notes.append(f"rest-pose correction applied to {corrected} keys; "
                             f"added rest keys for: {', '.join(added) or 'none'}")
        if scale is None:
            ls, lt = leg_length(source), leg_length(target)
            if ls and lt:
                scale = lt / ls

    if scale is not None and abs(scale - 1.0) > 1e-6:
        for f in motion.bones:
            f.position = tuple(c * scale for c in f.position)
        rep.notes.append(f"translations scaled by {scale:.4f}")

    added_names = set(added) if source is not None else set()
    kept = []
    for f in motion.bones:
        t = mapping.get(f.name)
        if t is not None:
            f.name = t
            kept.append(f)
        elif keep_unmatched or f.name in added_names:
            kept.append(f)
    motion.bones = kept
    for old, new in mapping.items():
        if old != new:
            rep.renamed.append(("bones", old, new))
    if motion.ik:
        for fr in motion.ik:
            for st in fr.states:
                st.name = mapping.get(st.name, st.name)

    canon_targets = {}
    tconv = d.detect_convention(tnames)
    for t in tnames:
        e = d.lookup(t, tconv)
        if e and e.base in _CORE_BODY:
            canon_targets[t] = e.id
    have = set(mapping.values())
    rep.missing = [t for t in canon_targets if t not in have]
    return rep


_CORE_BODY = {"center", "lower_body", "upper_body", "upper_body2", "neck", "head", "shoulder",
              "arm", "elbow", "wrist", "leg_ik", "toe_ik"}


def _linear_interp() -> bytes:
    # 4 curves (x, y, z, rotation) with control points (20, 20) and (107, 107):
    # MMD's straight-line default
    return (bytes([20] * 8) + bytes([107] * 8)) * 4
