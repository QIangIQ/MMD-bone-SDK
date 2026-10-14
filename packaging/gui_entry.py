"""PyInstaller entry point for the desktop app (files dropped on the exe are loaded)."""

import sys

from mmd_bone_tools.gui import main

sys.exit(main(sys.argv[1:]))
