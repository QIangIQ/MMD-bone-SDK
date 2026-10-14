"""File-level jobs shared by the command line and the desktop app."""

from __future__ import annotations

from pathlib import Path

from . import archive, ops
from .model import load_model, save_model
from .vmd import load_vmd, save_vmd

MODEL_EXT = {".pmx", ".pmd"}
MOTION_EXT = {".vmd"}
SUPPORTED = MODEL_EXT | MOTION_EXT


def kind(path: str | Path) -> str:
    ext = Path(path).suffix.lower()
    if ext in MODEL_EXT:
        return "model"
    if ext in MOTION_EXT:
        return "motion"
    raise ValueError(f"unsupported file type: {path} (expected .pmx, .pmd or .vmd)")


def default_out(path: str | Path, tag: str, out_dir: str | Path | None = None) -> Path:
    p = Path(path)
    name = f"{p.stem}_{tag}{p.suffix}"
    return Path(out_dir) / name if out_dir else p.with_name(name)


def translate_file(path, out=None, *, style="en", rename=False, overwrite=False,
                   custom=None) -> tuple[Path, ops.Report]:
    p = Path(path)
    out = Path(out) if out else default_out(p, "en")
    if kind(p) == "model":
        m = load_model(p)
        rep = ops.translate_model(m, style, rename=rename, overwrite=overwrite, custom=custom)
        save_model(m, out)
    else:
        mo = load_vmd(p)
        rep = ops.translate_motion(mo, style, custom=custom)
        save_vmd(mo, out)
    return out, rep


def convert_file(path, to, out=None, *, source=None, custom=None) -> tuple[Path, ops.Report]:
    p = Path(path)
    out = Path(out) if out else default_out(p, to)
    if kind(p) == "model":
        m = load_model(p)
        rep = ops.convert_model(m, to, source, custom=custom)
        save_model(m, out)
    else:
        mo = load_vmd(p)
        rep = ops.convert_motion(mo, to, source, custom=custom)
        save_vmd(mo, out)
    return out, rep


def retarget_file(motion, model, out=None, *, source_model=None, scale=None,
                  keep_unmatched=False, custom=None) -> tuple[Path, ops.Report]:
    p = Path(motion)
    out = Path(out) if out else default_out(p, Path(model).stem)
    mo = load_vmd(p)
    target = load_model(model)
    source = load_model(source_model) if source_model else None
    rep = ops.retarget(mo, target, source, scale=scale, keep_unmatched=keep_unmatched,
                       custom=custom)
    save_vmd(mo, out)
    return out, rep


def collect(paths, unpack_dir: str | Path | None = None) -> list[tuple[Path, Path]]:
    """Expand files, folders and zips into (file, path relative to its root) pairs."""
    found: list[tuple[Path, Path]] = []
    for raw in paths:
        p = Path(raw)
        if p.is_dir():
            for f in sorted(p.rglob("*")):
                if f.is_file() and f.suffix.lower() in SUPPORTED:
                    found.append((f, f.relative_to(p)))
                elif f.is_file() and f.suffix.lower() == ".zip" and unpack_dir:
                    found += _from_zip(f, Path(unpack_dir), f.relative_to(p).with_suffix(""))
        elif p.suffix.lower() == ".zip" and unpack_dir:
            found += _from_zip(p, Path(unpack_dir), Path(p.stem))
        elif p.is_file() and p.suffix.lower() in SUPPORTED:
            found.append((p, Path(p.name)))
    return found


def _from_zip(zip_path: Path, unpack_dir: Path, rel: Path) -> list[tuple[Path, Path]]:
    target = unpack_dir / rel
    files = archive.extract(zip_path, target)
    return [(f, rel / f.relative_to(target)) for f in files if f.suffix.lower() in SUPPORTED]


def report_lines(rep: ops.Report, verbose: bool = False) -> list[str]:
    lines = [f"  renamed: {len(rep.renamed)}"]
    if verbose:
        lines += [f"    [{sec}] {old} -> {new}" for sec, old, new in rep.renamed]
    lines += [f"  untranslated [{sec}] {old} (best effort: {best})"
              for sec, old, best in rep.untranslated]
    lines += [f"  warning: [{sec}] '{name}' is longer than VMD's 15-byte name limit"
              for sec, name in rep.too_long]
    if rep.unmatched:
        lines.append(f"  motion tracks with no bone in the model ({len(rep.unmatched)}): "
                     + ", ".join(rep.unmatched))
    if rep.missing:
        lines.append("  model bones the motion does not drive: " + ", ".join(rep.missing))
    lines += [f"  note: {n}" for n in rep.notes]
    return lines
