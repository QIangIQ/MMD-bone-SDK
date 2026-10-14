"""Command line interface: ``mmdbt <command> ...``"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

from . import __version__, archive, ops
from . import dictionary as d
from .binio import FormatError
from .model import load_model, save_model
from .vmd import load_vmd, save_vmd

MODEL_EXT = {".pmx", ".pmd"}
MOTION_EXT = {".vmd"}


def _kind(path: Path) -> str:
    ext = path.suffix.lower()
    if ext in MODEL_EXT:
        return "model"
    if ext in MOTION_EXT:
        return "motion"
    raise SystemExit(f"unsupported file type: {path} (expected .pmx, .pmd or .vmd)")


def _default_out(path: Path, tag: str) -> Path:
    return path.with_name(f"{path.stem}_{tag}{path.suffix}")


def _custom(args) -> dict[str, str]:
    return ops.load_mapping(args.map) if getattr(args, "map", None) else {}


def _print_report(rep: ops.Report, args, out=None) -> None:
    if getattr(args, "report", None):
        Path(args.report).write_text(json.dumps(rep.as_dict(), ensure_ascii=False, indent=2),
                                     encoding="utf-8")
    if getattr(args, "quiet", False):
        return
    if out:
        print(f"wrote {out}")
    print(f"  renamed: {len(rep.renamed)}")
    if getattr(args, "verbose", False):
        for sec, old, new in rep.renamed:
            print(f"    [{sec}] {old} -> {new}")
    for sec, old, best in rep.untranslated:
        print(f"  untranslated [{sec}] {old} (best effort: {best})")
    for sec, name in rep.too_long:
        print(f"  warning: [{sec}] '{name}' is longer than VMD's 15-byte name limit")
    if rep.unmatched:
        print(f"  motion tracks with no bone in the model ({len(rep.unmatched)}): "
              + ", ".join(rep.unmatched))
    if rep.missing:
        print("  model bones the motion does not drive: " + ", ".join(rep.missing))
    for n in rep.notes:
        print(f"  note: {n}")


def cmd_info(args) -> int:
    p = Path(args.path)
    if _kind(p) == "model":
        m = load_model(p)
        names = [b.name for b in m.bones]
        conv = d.detect_convention(names)
        std = sum(1 for n in names if d.lookup(n, conv))
        info = {
            "file": str(p), "format": type(m).__name__.replace("Model", ""),
            "name": m.name, "name_en": getattr(m, "name_en", ""), "bones": len(names),
            "standard_bones": std, "convention": conv, "morphs": len(m.morphs),
            "bones_without_english_name": sum(1 for b in m.bones if not b.name_en),
        }
        if args.bones:
            info["bone_list"] = [
                {"name": b.name, "name_en": b.name_en,
                 "standard": (d.lookup(b.name, conv).id if d.lookup(b.name, conv) else None)}
                for b in m.bones]
    else:
        mo = load_vmd(p)
        names = mo.bone_names()
        info = {
            "file": str(p), "format": "VMD", "model": mo.model_name,
            "bone_tracks": len(names), "bone_keys": len(mo.bones),
            "morph_tracks": len(mo.morph_names()), "morph_keys": len(mo.morphs),
            "convention": d.detect_convention(names),
            "last_frame": max((f.frame for f in mo.bones), default=0),
        }
        if args.bones:
            info["bone_list"] = names
            info["morph_list"] = mo.morph_names()
    if args.json:
        print(json.dumps(info, ensure_ascii=False, indent=2))
    else:
        for k, v in info.items():
            if isinstance(v, list):
                print(f"{k}:")
                for item in v:
                    print(f"  {item}")
            else:
                print(f"{k}: {v}")
    return 0


def cmd_translate(args) -> int:
    p = Path(args.input)
    out = Path(args.output) if args.output else _default_out(p, "en")
    custom = _custom(args)
    if _kind(p) == "model":
        m = load_model(p)
        rep = ops.translate_model(m, args.style, rename=args.rename, overwrite=args.overwrite,
                                  custom=custom)
        save_model(m, out)
    else:
        mo = load_vmd(p)
        rep = ops.translate_motion(mo, args.style, custom=custom)
        save_vmd(mo, out)
    _print_report(rep, args, out)
    return 0


def cmd_convert(args) -> int:
    p = Path(args.input)
    out = Path(args.output) if args.output else _default_out(p, args.to)
    custom = _custom(args)
    if _kind(p) == "model":
        m = load_model(p)
        rep = ops.convert_model(m, args.to, args.source, custom=custom)
        save_model(m, out)
    else:
        mo = load_vmd(p)
        rep = ops.convert_motion(mo, args.to, args.source, custom=custom)
        save_vmd(mo, out)
    _print_report(rep, args, out)
    return 0


def cmd_retarget(args) -> int:
    p = Path(args.motion)
    out = Path(args.output) if args.output else _default_out(p, Path(args.model).stem)
    mo = load_vmd(p)
    target = load_model(args.model)
    source = load_model(args.source_model) if args.source_model else None
    rep = ops.retarget(mo, target, source, scale=args.scale, keep_unmatched=args.keep_unmatched,
                       custom=_custom(args))
    save_vmd(mo, out)
    _print_report(rep, args, out)
    return 0


def cmd_map(args) -> int:
    m = load_model(args.model)
    mapping = ops.bone_map(m, args.to, args.source)
    if args.format == "json":
        text = json.dumps(mapping, ensure_ascii=False, indent=2)
    else:
        import io
        buf = io.StringIO()
        w = csv.writer(buf)
        w.writerow(["model_bone", args.to])
        w.writerows(mapping.items())
        text = buf.getvalue()
    if args.output:
        Path(args.output).write_text(text, encoding="utf-8")
        print(f"wrote {args.output} ({len(mapping)} bones)")
    else:
        sys.stdout.write(text + ("\n" if not text.endswith("\n") else ""))
    return 0


def cmd_table(args) -> int:
    convs = args.conventions or list(d.CONVENTIONS)
    bad = [c for c in convs if c not in d.CONVENTIONS]
    if bad:
        raise SystemExit(f"unknown convention: {', '.join(bad)}")
    w = csv.writer(sys.stdout)
    w.writerow(["id"] + convs)
    for b in d.BONES:
        row = [b.id]
        for c in convs:
            n = b.name(c) or ""
            row.append(d.jp_display(n) if c == "jp" and d._uses_fullwidth(b) else n)
        w.writerow(row)
    return 0


def cmd_lookup(args) -> int:
    for name in args.names:
        e = d.lookup(name, args.source)
        if e is None:
            from .translate import translate_bone
            print(f"{name}: not a standard bone; translation: {translate_bone(name).result}")
            continue
        parts = [f"{c}={d.convert(name, c, args.source) or '-'}" for c in d.CONVENTIONS]
        print(f"{name}: id={e.id} " + " ".join(parts))
    return 0


def cmd_unpack(args) -> int:
    out = Path(args.dir) if args.dir else Path(args.zip).with_suffix("")
    files = archive.extract(args.zip, out, args.password.encode() if args.password else None)
    print(f"extracted {len(files)} files to {out}")
    return 0


def cmd_batch(args) -> int:
    src = Path(args.folder)
    dst = Path(args.output) if args.output else src.with_name(src.name + "_en")
    custom = _custom(args)
    work = src
    zips = sorted(src.rglob("*.zip"))
    if zips and args.unpack:
        work = dst / "_unpacked"
        for z in zips:
            archive.extract(z, work / z.relative_to(src).with_suffix(""))
    roots = [src] + ([work] if work != src else [])
    count = errors = 0
    for root in roots:
        for p in sorted(root.rglob("*")):
            if p.suffix.lower() not in MODEL_EXT | MOTION_EXT or not p.is_file():
                continue
            if root == src and dst in p.parents:
                continue
            rel = p.relative_to(root)
            out = dst / rel if root == src else p
            out.parent.mkdir(parents=True, exist_ok=True)
            try:
                if p.suffix.lower() in MODEL_EXT:
                    m = load_model(p)
                    rep = ops.translate_model(m, args.style, rename=args.rename, custom=custom)
                    save_model(m, out)
                else:
                    mo = load_vmd(p)
                    rep = ops.translate_motion(mo, args.style, custom=custom)
                    save_vmd(mo, out)
                count += 1
                if not args.quiet:
                    print(f"{rel}: {len(rep.renamed)} renamed, {len(rep.untranslated)} untranslated")
            except (FormatError, OSError) as e:
                errors += 1
                print(f"{rel}: skipped ({e})", file=sys.stderr)
    print(f"processed {count} files into {dst}" + (f", {errors} skipped" if errors else ""))
    return 1 if errors and not count else 0


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        prog="mmdbt",
        description="Translate, map and retarget MMD bones (PMX, PMD, VMD).")
    ap.add_argument("--version", action="version", version=f"mmd-bone-tools {__version__}")
    sub = ap.add_subparsers(dest="cmd", required=True)
    conv_choices = list(d.CONVENTIONS)

    def common(p, report=True):
        p.add_argument("--map", help="custom name overrides (JSON object or 2-column CSV)")
        if report:
            p.add_argument("--report", help="write a JSON report of every change")
            p.add_argument("-v", "--verbose", action="store_true", help="list every rename")
            p.add_argument("-q", "--quiet", action="store_true")

    p = sub.add_parser("info", help="summarize a PMX/PMD/VMD file")
    p.add_argument("path")
    p.add_argument("--bones", action="store_true", help="list bones/tracks")
    p.add_argument("--json", action="store_true")
    p.set_defaults(fn=cmd_info)

    p = sub.add_parser("translate", help="translate Japanese bone/morph names to English")
    p.add_argument("input")
    p.add_argument("-o", "--output")
    p.add_argument("--style", choices=ops.ENGLISH_STYLES, default="en",
                   help="en: arm_L (MMD English), blender: arm.L")
    p.add_argument("--rename", action="store_true",
                   help="models: replace the Japanese names too, not just the English field")
    p.add_argument("--overwrite", action="store_true", help="replace existing English names")
    common(p)
    p.set_defaults(fn=cmd_translate)

    p = sub.add_parser("convert", help="rename bones to another naming convention")
    p.add_argument("input")
    p.add_argument("--to", required=True, choices=conv_choices)
    p.add_argument("--from", dest="source", choices=conv_choices, help="default: auto-detect")
    p.add_argument("-o", "--output")
    common(p)
    p.set_defaults(fn=cmd_convert)

    p = sub.add_parser("retarget", help="make a VMD motion fit a model's bones")
    p.add_argument("motion")
    p.add_argument("--model", required=True, help="target PMX/PMD model")
    p.add_argument("--source-model", help="model the motion was made for (enables rest-pose "
                                          "correction, e.g. A-pose to T-pose, and auto scale)")
    p.add_argument("--scale", type=float, help="scale for translations (default: auto or 1)")
    p.add_argument("--keep-unmatched", action="store_true", help="keep tracks with no target bone")
    p.add_argument("-o", "--output")
    common(p)
    p.set_defaults(fn=cmd_retarget)

    p = sub.add_parser("map", help="export a bone map from a model to a convention")
    p.add_argument("model")
    p.add_argument("--to", required=True, choices=conv_choices)
    p.add_argument("--from", dest="source", choices=conv_choices)
    p.add_argument("--format", choices=("json", "csv"), default="json")
    p.add_argument("-o", "--output")
    p.set_defaults(fn=cmd_map)

    p = sub.add_parser("table", help="print the standard bone table as CSV")
    p.add_argument("conventions", nargs="*", metavar="CONVENTION",
                   help="columns to print: " + ", ".join(conv_choices))
    p.set_defaults(fn=cmd_table)

    p = sub.add_parser("lookup", help="show a bone name in every convention")
    p.add_argument("names", nargs="+")
    p.add_argument("--from", dest="source", choices=conv_choices)
    p.set_defaults(fn=cmd_lookup)

    p = sub.add_parser("unpack", help="extract a zip with Shift-JIS file names")
    p.add_argument("zip")
    p.add_argument("-d", "--dir")
    p.add_argument("--password")
    p.set_defaults(fn=cmd_unpack)

    p = sub.add_parser("batch", help="translate every PMX/PMD/VMD in a folder (and its zips)")
    p.add_argument("folder")
    p.add_argument("-o", "--output", help="output folder (default: <folder>_en)")
    p.add_argument("--style", choices=ops.ENGLISH_STYLES, default="en")
    p.add_argument("--rename", action="store_true")
    p.add_argument("--no-unpack", dest="unpack", action="store_false", help="ignore zip files")
    p.add_argument("-q", "--quiet", action="store_true")
    common(p, report=False)
    p.set_defaults(fn=cmd_batch)
    return ap


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.fn(args)
    except FormatError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    except FileNotFoundError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
