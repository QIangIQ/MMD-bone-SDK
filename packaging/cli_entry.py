"""PyInstaller entry point for the mmdbt command line tool."""

import sys

from mmd_bone_tools.cli import main

sys.exit(main())
