"""Path helpers that work both when run as a script and when frozen by PyInstaller.

- app_dir(): a writable, persistent folder (next to the .exe when frozen, so
  data like the SQLite DB / Excel export / .env survive between runs).
- resource_path(*parts): a read-only bundled resource (images, documents),
  resolved from PyInstaller's onefile extraction folder when frozen.
"""
import os
import sys

_SOURCE_DIR = os.path.dirname(os.path.abspath(__file__))


def is_frozen():
    return getattr(sys, "frozen", False)


def app_dir():
    if is_frozen():
        return os.path.dirname(os.path.abspath(sys.executable))
    return _SOURCE_DIR


def resource_path(*parts):
    base = getattr(sys, "_MEIPASS", _SOURCE_DIR)
    return os.path.join(base, *parts)
