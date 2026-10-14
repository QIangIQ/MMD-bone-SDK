"""Build standalone executables with PyInstaller.

    pip install pyinstaller
    python packaging/build.py

Writes dist/MMDBoneTools(.exe) (desktop app) and dist/mmdbt(.exe) (command line).
"""

import sys
from pathlib import Path

import PyInstaller.__main__

ROOT = Path(__file__).resolve().parent.parent
ICON = ROOT / "assets" / "icon.ico"


def build(name: str, entry: str, windowed: bool) -> None:
    args = [str(ROOT / "packaging" / entry), "--name", name, "--onefile", "--noconfirm",
            "--clean", "--paths", str(ROOT / "src"), "--distpath", str(ROOT / "dist"),
            "--workpath", str(ROOT / "build"), "--specpath", str(ROOT / "build")]
    if windowed:
        args.append("--windowed")
    if sys.platform in ("win32", "darwin"):
        args += ["--icon", str(ICON)]
    PyInstaller.__main__.run(args)


if __name__ == "__main__":
    build("MMDBoneTools", "gui_entry.py", windowed=True)
    build("mmdbt", "cli_entry.py", windowed=False)
