"""Extract MMD download archives whose file names are Shift-JIS.

Most MMD zips are made on Japanese Windows without the UTF-8 flag, so
Python (and many unzip tools) show their names as mojibake. This decodes
them properly and refuses entries that would escape the output folder.
"""

from __future__ import annotations

import os
import zipfile
from pathlib import Path

UTF8_FLAG = 0x800


def decode_name(info: zipfile.ZipInfo) -> str:
    if info.flag_bits & UTF8_FLAG:
        return info.filename
    try:
        raw = info.filename.encode("cp437")
    except UnicodeEncodeError:
        return info.filename
    for enc in ("cp932", "utf-8"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return info.filename


def extract(zip_path: str | os.PathLike, out_dir: str | os.PathLike,
            password: bytes | None = None) -> list[Path]:
    out = Path(out_dir).resolve()
    out.mkdir(parents=True, exist_ok=True)
    written = []
    with zipfile.ZipFile(zip_path) as zf:
        for info in zf.infolist():
            name = decode_name(info).replace("\\", "/")
            target = (out / name).resolve()
            if target != out and out not in target.parents:
                raise ValueError(f"archive entry escapes output folder: {name}")
            if info.is_dir() or name.endswith("/"):
                target.mkdir(parents=True, exist_ok=True)
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            with zf.open(info, pwd=password) as src, open(target, "wb") as dst:
                while chunk := src.read(1 << 20):
                    dst.write(chunk)
            written.append(target)
    return written
