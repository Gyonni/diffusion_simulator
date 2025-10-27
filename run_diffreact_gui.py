"""Standalone launcher for the Diffusion–Reaction GUI.

This script wraps ``diffreact_gui.main.main`` so it can be frozen with tools
like PyInstaller without running into relative-import issues.
"""
from __future__ import annotations

from diffreact_gui.main import main


if __name__ == "__main__":
    main()

